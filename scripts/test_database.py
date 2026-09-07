#!/usr/bin/env python3
"""Database test utility for Sympl Proposal RAG.

Performs non-destructive READ and temporary-transaction verification of:
1. DATABASE_URL environment configuration
2. Connection establishment
3. Current database name
4. PostgreSQL server version
5. pgvector extension installation and version
6. Expected table presence:
   - proposal_documents
   - proposal_chunks
   - sympl_reference_blocks
   - sympl_style_rules
   - dataset_imports
7. proposal_chunks.embedding column existence and 'vector' data type
8. Safe test transaction insertion and rollback verification
Never logs credentials or secret connection details.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import psycopg


def load_database_url() -> str | None:
    """Safely retrieve DATABASE_URL from environment or local .env files without echoing."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.strip():
        return db_url.strip()

    search_paths = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]

    for env_path in search_paths:
        if env_path.exists() and env_path.is_file():
            try:
                with env_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() == "DATABASE_URL" and v.strip():
                                os.environ["DATABASE_URL"] = v.strip().strip("'\"")
                                return os.environ["DATABASE_URL"]
            except Exception:
                pass

    return None


def run_checks() -> int:
    print("============================================================")
    print("SYMPL PROPOSAL RAG -- DATABASE VERIFICATION TEST")
    print("============================================================")

    # Check 1: DATABASE_URL exists
    db_url = load_database_url()
    if not db_url:
        print("[FAIL] Check 1: DATABASE_URL environment variable is NOT set.")
        return 1
    print("[PASS] Check 1: DATABASE_URL configuration detected.")

    # Check 2: Connection succeeds
    try:
        conn = psycopg.connect(db_url)
    except Exception as exc:
        # Mask any connection string details
        print(f"[FAIL] Check 2: Connection failed: {type(exc).__name__}")
        return 1
    print("[PASS] Check 2: Connection to PostgreSQL succeeded.")

    with conn:
        with conn.cursor() as cur:
            # Check 3: Current database
            cur.execute("SELECT current_database(), current_user;")
            row = cur.fetchone()
            db_name = row[0] if row else "unknown"
            print(f"[PASS] Check 3: Current Database: '{db_name}'")

            # Check 4: PostgreSQL version
            cur.execute("SELECT version();")
            ver_row = cur.fetchone()
            pg_ver = ver_row[0] if ver_row else "unknown"
            print(f"[PASS] Check 4: PostgreSQL Version: {pg_ver}")

            # Check 5 & 6: pgvector extension & version
            cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
            ext_row = cur.fetchone()
            if not ext_row:
                print("[FAIL] Check 5: pgvector extension is NOT installed/enabled.")
                return 1
            print(f"[PASS] Check 5: pgvector extension is installed and enabled.")
            print(f"[PASS] Check 6: pgvector version: {ext_row[1]}")

            # Check 7: Expected tables exist
            expected_tables = [
                "proposal_documents",
                "proposal_chunks",
                "sympl_reference_blocks",
                "sympl_style_rules",
                "dataset_imports",
            ]
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s);
                """,
                (expected_tables,),
            )
            found_tables = {r[0] for r in cur.fetchall()}
            missing_tables = [t for t in expected_tables if t not in found_tables]

            if missing_tables:
                print(f"[INFO] Check 7: Schema tables not found: {missing_tables}")
                print("       (Note: Initial migration 001_initial_schema.sql has not yet been executed)")
                print("============================================================")
                print("PRE-MIGRATION VERIFICATION COMPLETE: Database & pgvector ready.")
                print("============================================================")
                return 0

            print(f"[PASS] Check 7: All 5 schema tables exist: {sorted(found_tables)}")

            # Check 8 & 9: proposal_chunks.embedding column exists and uses vector type
            cur.execute(
                """
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'proposal_chunks'
                  AND column_name = 'embedding';
                """
            )
            emb_row = cur.fetchone()
            if not emb_row:
                print("[FAIL] Check 8: Column 'proposal_chunks.embedding' does NOT exist.")
                return 1
            print(f"[PASS] Check 8: Column 'proposal_chunks.embedding' exists.")

            col_type = emb_row[1]
            if col_type != "vector":
                print(f"[FAIL] Check 9: Column 'embedding' type is '{col_type}', expected 'vector'.")
                return 1
            print(f"[PASS] Check 9: Column 'proposal_chunks.embedding' data type is 'vector'.")

            # Check 10, 11, 12: Safe transaction insert and rollback
            print("Running Check 10-12: Transaction isolation & rollback test...")
            test_doc_code = "__TEST_VERIFICATION_PROPOSAL__"
            test_chunk_key = "__TEST_VERIFICATION_CHUNK__"

            try:
                # Begin nested savepoint/transaction test
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO proposal_documents (
                            proposal_code, client_name, source_filename, core_bookkeeping
                        ) VALUES (%s, %s, %s, %s)
                        RETURNING id;
                        """,
                        (test_doc_code, "Test Client", "test_file.pdf", True),
                    )
                    doc_id = cur.fetchone()[0]

                    cur.execute(
                        """
                        INSERT INTO proposal_chunks (
                            proposal_id, chunk_key, section_type, raw_text, cleaned_text, retrieval_text
                        ) VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (doc_id, test_chunk_key, "context_objectives", "raw", "clean", "retrieval"),
                    )

                    # Verify records exist inside active transaction
                    cur.execute("SELECT COUNT(*) FROM proposal_documents WHERE proposal_code = %s;", (test_doc_code,))
                    count_in_tx = cur.fetchone()[0]
                    assert count_in_tx == 1, "Test document not visible inside transaction"

                    # Explicitly rollback by raising a controlled cancellation
                    raise psycopg.Rollback()

            except psycopg.Rollback:
                pass

            # Check 12: Confirm no permanent test records remain
            cur.execute("SELECT COUNT(*) FROM proposal_documents WHERE proposal_code = %s;", (test_doc_code,))
            remaining_docs = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM proposal_chunks WHERE chunk_key = %s;", (test_chunk_key,))
            remaining_chunks = cur.fetchone()[0]

            if remaining_docs != 0 or remaining_chunks != 0:
                print("[FAIL] Check 12: Test data leaked! Records found after rollback.")
                return 1

            print("[PASS] Check 10: Temporary test data inserted successfully in transaction.")
            print("[PASS] Check 11: Transaction rollback executed.")
            print("[PASS] Check 12: Verified zero permanent test records remain.")

    print("============================================================")
    print("ALL DATABASE CHECKS PASSED SUCCESSFULLY")
    print("============================================================")
    return 0


def main() -> int:
    try:
        return run_checks()
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error during verification: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

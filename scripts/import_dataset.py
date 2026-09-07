#!/usr/bin/env python3
"""Dataset import utility for Sympl Proposal RAG.

Validates normalized JSON files and ingests proposal documents and semantic chunks
into PostgreSQL using psycopg 3.
Tracks import activity and content hashes in dataset_imports.
Never modifies text values. Never exposes credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg
from psycopg.types.json import Jsonb

# Import validator from sibling script
try:
    from validate_dataset import validate_directory
except ImportError:
    # Handle direct execution from scripts directory
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_dataset import validate_directory


def load_database_url() -> str:
    """Load DATABASE_URL from os.environ or .env files without logging values."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.strip():
        return db_url.strip()

    # Check potential .env file locations
    search_paths = [
        Path(__file__).resolve().parent.parent / ".env",         # sympl-proposal-rag/.env
        Path(__file__).resolve().parent.parent.parent / ".env",  # parent repo .env
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
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k == "DATABASE_URL" and v:
                                os.environ["DATABASE_URL"] = v
                                return v
            except Exception:
                pass

    print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
    print("Please set DATABASE_URL or provide a valid .env file.", file=sys.stderr)
    sys.exit(1)


def compute_file_hash(filepath: Path) -> str:
    """Calculate SHA-256 hex digest of file contents."""
    hasher = hashlib.sha256()
    with filepath.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class ImportStats:
    def __init__(self) -> None:
        self.files_processed: int = 0
        self.files_skipped: int = 0
        self.documents_inserted: int = 0
        self.documents_updated: int = 0
        self.chunks_inserted: int = 0
        self.chunks_updated: int = 0
        self.errors_encountered: int = 0

    def print_summary(self) -> None:
        print("\n============================================================")
        print("IMPORT SUMMARY")
        print("============================================================")
        print(f"Files Processed:     {self.files_processed}")
        print(f"Files Skipped:       {self.files_skipped}")
        print(f"Documents Inserted:  {self.documents_inserted}")
        print(f"Documents Updated:   {self.documents_updated}")
        print(f"Chunks Inserted:     {self.chunks_inserted}")
        print(f"Chunks Updated:      {self.chunks_updated}")
        print(f"Errors Encountered:  {self.errors_encountered}")
        print("============================================================")


def is_already_imported(conn: psycopg.Connection, source_name: str, source_hash: str) -> bool:
    """Check if this file hash has already been successfully imported."""
    query = """
        SELECT id FROM dataset_imports
        WHERE source_name = %s AND source_hash = %s AND status = 'completed'
        LIMIT 1;
    """
    with conn.cursor() as cur:
        cur.execute(query, (source_name, source_hash))
        return cur.fetchone() is not None


def record_import_start(conn: psycopg.Connection, source_name: str, source_hash: str) -> str:
    """Record started import in dataset_imports."""
    query = """
        INSERT INTO dataset_imports (source_name, source_hash, records_imported, status, started_at)
        VALUES (%s, %s, 0, 'started', NOW())
        RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(query, (source_name, source_hash))
        row = cur.fetchone()
        return str(row[0])


def record_import_complete(
    conn: psycopg.Connection, import_id: str, records_imported: int
) -> None:
    """Update dataset_imports record to completed status."""
    query = """
        UPDATE dataset_imports
        SET status = 'completed',
            records_imported = %s,
            completed_at = NOW()
        WHERE id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (records_imported, import_id))


def record_import_failed(
    conn: psycopg.Connection, import_id: str | None, source_name: str, source_hash: str, error_msg: str
) -> None:
    """Record failed import in dataset_imports."""
    try:
        with conn.cursor() as cur:
            if import_id:
                cur.execute(
                    """
                    UPDATE dataset_imports
                    SET status = 'failed',
                        error_message = %s,
                        completed_at = NOW()
                    WHERE id = %s;
                    """,
                    (error_msg, import_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO dataset_imports (source_name, source_hash, status, error_message, started_at, completed_at)
                    VALUES (%s, %s, 'failed', %s, NOW(), NOW());
                    """,
                    (source_name, source_hash, error_msg),
                )
        conn.commit()
    except Exception as e:
        print(f"Warning: Failed to log error to dataset_imports: {e}", file=sys.stderr)


def upsert_proposal_document(cur: psycopg.Cursor, doc_data: Dict[str, Any]) -> Tuple[str, bool]:
    """Upsert proposal_documents row using proposal_code. Returns (document_uuid, is_new_insert)."""
    query = """
        INSERT INTO proposal_documents (
            proposal_code, client_name, proposal_title, proposal_date,
            source_filename, organization_type, sector, engagement_type,
            proposal_complexity, core_bookkeeping, raw_text, cleaned_text, metadata
        ) VALUES (
            %(proposal_code)s, %(client_name)s, %(proposal_title)s, %(proposal_date)s,
            %(source_filename)s, %(organization_type)s, %(sector)s, %(engagement_type)s,
            %(proposal_complexity)s, %(core_bookkeeping)s, %(raw_text)s, %(cleaned_text)s, %(metadata)s
        )
        ON CONFLICT (proposal_code) DO UPDATE SET
            client_name = EXCLUDED.client_name,
            proposal_title = EXCLUDED.proposal_title,
            proposal_date = EXCLUDED.proposal_date,
            source_filename = EXCLUDED.source_filename,
            organization_type = EXCLUDED.organization_type,
            sector = EXCLUDED.sector,
            engagement_type = EXCLUDED.engagement_type,
            proposal_complexity = EXCLUDED.proposal_complexity,
            core_bookkeeping = EXCLUDED.core_bookkeeping,
            raw_text = EXCLUDED.raw_text,
            cleaned_text = EXCLUDED.cleaned_text,
            metadata = EXCLUDED.metadata
        RETURNING id, (xmax = 0) AS is_insert;
    """
    params = {
        "proposal_code": doc_data["proposal_code"],
        "client_name": doc_data["client_name"],
        "proposal_title": doc_data.get("proposal_title"),
        "proposal_date": doc_data.get("proposal_date"),
        "source_filename": doc_data["source_filename"],
        "organization_type": doc_data.get("organization_type"),
        "sector": doc_data.get("sector"),
        "engagement_type": doc_data.get("engagement_type"),
        "proposal_complexity": doc_data.get("proposal_complexity"),
        "core_bookkeeping": bool(doc_data.get("core_bookkeeping", True)),
        "raw_text": doc_data.get("raw_text"),
        "cleaned_text": doc_data.get("cleaned_text"),
        "metadata": Jsonb(doc_data.get("metadata") or {}),
    }
    cur.execute(query, params)
    row = cur.fetchone()
    assert row is not None
    return str(row[0]), bool(row[1])


def upsert_proposal_chunk(
    cur: psycopg.Cursor, proposal_id: str, chunk_data: Dict[str, Any]
) -> Tuple[str, bool]:
    """Upsert proposal_chunks row using chunk_key. Returns (chunk_uuid, is_new_insert)."""
    query = """
        INSERT INTO proposal_chunks (
            proposal_id, chunk_key, section_order, section_type, section_title,
            service_modules, organization_type, sector, engagement_type,
            core_bookkeeping, accounting_systems, payroll_systems, cadence,
            special_requirements, raw_text, cleaned_text, retrieval_text,
            retrieval_enabled, commercial_reference_only, pricing_content,
            boilerplate_content, embedding, embedded_at, metadata
        ) VALUES (
            %(proposal_id)s, %(chunk_key)s, %(section_order)s, %(section_type)s, %(section_title)s,
            %(service_modules)s, %(organization_type)s, %(sector)s, %(engagement_type)s,
            %(core_bookkeeping)s, %(accounting_systems)s, %(payroll_systems)s, %(cadence)s,
            %(special_requirements)s, %(raw_text)s, %(cleaned_text)s, %(retrieval_text)s,
            %(retrieval_enabled)s, %(commercial_reference_only)s, %(pricing_content)s,
            %(boilerplate_content)s, NULL, NULL, %(metadata)s
        )
        ON CONFLICT (chunk_key) DO UPDATE SET
            proposal_id = EXCLUDED.proposal_id,
            section_order = EXCLUDED.section_order,
            section_type = EXCLUDED.section_type,
            section_title = EXCLUDED.section_title,
            service_modules = EXCLUDED.service_modules,
            organization_type = EXCLUDED.organization_type,
            sector = EXCLUDED.sector,
            engagement_type = EXCLUDED.engagement_type,
            core_bookkeeping = EXCLUDED.core_bookkeeping,
            accounting_systems = EXCLUDED.accounting_systems,
            payroll_systems = EXCLUDED.payroll_systems,
            cadence = EXCLUDED.cadence,
            special_requirements = EXCLUDED.special_requirements,
            raw_text = EXCLUDED.raw_text,
            cleaned_text = EXCLUDED.cleaned_text,
            retrieval_text = EXCLUDED.retrieval_text,
            retrieval_enabled = EXCLUDED.retrieval_enabled,
            commercial_reference_only = EXCLUDED.commercial_reference_only,
            pricing_content = EXCLUDED.pricing_content,
            boilerplate_content = EXCLUDED.boilerplate_content,
            metadata = EXCLUDED.metadata
        RETURNING id, (xmax = 0) AS is_insert;
    """
    params = {
        "proposal_id": proposal_id,
        "chunk_key": chunk_data["chunk_key"],
        "section_order": chunk_data.get("section_order"),
        "section_type": chunk_data["section_type"],
        "section_title": chunk_data.get("section_title"),
        "service_modules": chunk_data.get("service_modules", []),
        "organization_type": chunk_data.get("organization_type"),
        "sector": chunk_data.get("sector"),
        "engagement_type": chunk_data.get("engagement_type"),
        "core_bookkeeping": bool(chunk_data.get("core_bookkeeping", False)),
        "accounting_systems": chunk_data.get("accounting_systems", []),
        "payroll_systems": chunk_data.get("payroll_systems", []),
        "cadence": chunk_data.get("cadence", []),
        "special_requirements": chunk_data.get("special_requirements", []),
        "raw_text": chunk_data["raw_text"],
        "cleaned_text": chunk_data["cleaned_text"],
        "retrieval_text": chunk_data["retrieval_text"],
        "retrieval_enabled": bool(chunk_data.get("retrieval_enabled", True)),
        "commercial_reference_only": bool(chunk_data.get("commercial_reference_only", False)),
        "pricing_content": bool(chunk_data.get("pricing_content", False)),
        "boilerplate_content": bool(chunk_data.get("boilerplate_content", False)),
        "metadata": Jsonb(chunk_data.get("metadata") or {}),
    }
    cur.execute(query, params)
    row = cur.fetchone()
    assert row is not None
    return str(row[0]), bool(row[1])


def import_single_file(
    conn: psycopg.Connection, filepath: Path, stats: ImportStats
) -> bool:
    """Import a single validated normalized JSON proposal file within a transaction."""
    source_name = filepath.name
    source_hash = compute_file_hash(filepath)

    if is_already_imported(conn, source_name, source_hash):
        print(f"[SKIP] {source_name}: Identical content hash already imported successfully.")
        stats.files_skipped += 1
        return True

    print(f"[IMPORTING] {source_name} ...")
    with filepath.open("r", encoding="utf-8") as f:
        data = json.load(f)

    proposal_data = data["proposal"]
    chunks_data = data["chunks"]

    import_id: str | None = None
    try:
        with conn.transaction():
            import_id = record_import_start(conn, source_name, source_hash)

            with conn.cursor() as cur:
                doc_id, doc_inserted = upsert_proposal_document(cur, proposal_data)
                if doc_inserted:
                    stats.documents_inserted += 1
                else:
                    stats.documents_updated += 1

                chunks_count = 0
                for chunk in chunks_data:
                    _, chunk_inserted = upsert_proposal_chunk(cur, doc_id, chunk)
                    if chunk_inserted:
                        stats.chunks_inserted += 1
                    else:
                        stats.chunks_updated += 1
                    chunks_count += 1

                record_import_complete(conn, import_id, records_imported=chunks_count + 1)

        stats.files_processed += 1
        print(f"[DONE] {source_name}: 1 document, {len(chunks_data)} chunks processed.")
        return True

    except Exception as exc:
        stats.errors_encountered += 1
        print(f"[ERROR] Failed to import {source_name}: {exc}", file=sys.stderr)
        record_import_failed(conn, import_id, source_name, source_hash, str(exc))
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest validated proposal JSON into PostgreSQL.")
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Path to normalized dataset directory (defaults to data/normalized relative to project root)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    target_dir = Path(args.dir).resolve() if args.dir else project_root / "data" / "normalized"

    print("============================================================")
    print("SYMPL PROPOSAL DATASET IMPORTER")
    print("============================================================")
    print(f"Target Directory: {target_dir}")

    # Step 1: Pre-import validation
    print("\nStep 1: Running dataset validation...")
    validation_report = validate_directory(target_dir)

    if not validation_report.is_valid:
        print("\n[!] Import aborted due to validation errors:")
        for err in validation_report.errors:
            print(f"  {err}")
        return 1

    json_files = sorted(target_dir.glob("*.json"))
    if not json_files:
        print("\nNo JSON files found to import. Exiting cleanly.")
        return 0

    # Step 2: Database Connection
    print("\nStep 2: Connecting to database...")
    db_url = load_database_url()

    stats = ImportStats()
    try:
        with psycopg.connect(db_url) as conn:
            print("Database connection established.")

            # Step 3: Ingest files
            print("\nStep 3: Processing proposal files...")
            for filepath in json_files:
                import_single_file(conn, filepath, stats)

    except Exception as exc:
        print(f"\n[FATAL] Database connection or transaction error: {exc}", file=sys.stderr)
        return 1

    stats.print_summary()
    return 0 if stats.errors_encountered == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

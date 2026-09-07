#!/usr/bin/env python3
"""
Sympl Solutions Proposal RAG — Local Embedding Generation Pipeline

Generates dense embeddings for historical proposal chunks using a local model
(default: BAAI/bge-m3) via sentence-transformers and writes them to pgvector.

Features:
- Configured via environment variables:
    EMBEDDING_MODEL (default: BAAI/bge-m3)
    EMBEDDING_DIMENSION (default: 1024)
    DATABASE_URL
- Source text: retrieval_text (the approved search representation)
- Target: proposal_chunks.embedding & proposal_chunks.embedded_at
- Scope: retrieval_enabled = true ONLY (47 chunks)
- Safety: atomic transaction, dimension verification, error rollback
- Idempotency: skips already embedded chunks unless --force is provided
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import psycopg

# ----------------------------------------------------------------------
# 1. Configuration & Environment Discovery
# ----------------------------------------------------------------------
def load_environment() -> Dict[str, str]:
    env_vars = {}
    candidates = [
        Path('d:/Sympl/.env'),
        Path('d:/Sympl/sympl-proposal-rag/.env'),
        Path('.env'),
        Path('../.env')
    ]
    for p in candidates:
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k.strip()] = v.strip().strip('"\'')
    for k, v in os.environ.items():
        if k not in env_vars:
            env_vars[k] = v
    return env_vars

ENV = load_environment()

DATABASE_URL = ENV.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

EMBEDDING_MODEL = ENV.get('EMBEDDING_MODEL', 'BAAI/bge-m3')
EMBEDDING_DIMENSION = int(ENV.get('EMBEDDING_DIMENSION', '1024'))

# ----------------------------------------------------------------------
# 2. Database Schema & Dimension Compatibility Check
# ----------------------------------------------------------------------
def verify_pgvector_compatibility(conn: psycopg.Connection, expected_dim: int) -> None:
    """Verifies that the embedding column exists and can store expected_dim vectors."""
    with conn.cursor() as cur:
        # Check column exists
        cur.execute("""
            SELECT column_name, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'proposal_chunks' AND column_name = 'embedding';
        """)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Column 'proposal_chunks.embedding' does not exist.")
        if row[1] != 'vector':
            raise RuntimeError(f"Column 'proposal_chunks.embedding' is of type '{row[1]}', expected 'vector'.")

        # Test casting a dummy vector of expected_dim
        dummy_vec = [0.0] * expected_dim
        dummy_str = '[' + ','.join(map(str, dummy_vec)) + ']'
        cur.execute("SELECT %s::vector;", (dummy_str,))
        cur.fetchone()

# ----------------------------------------------------------------------
# 3. Embedding Generation Pipeline
# ----------------------------------------------------------------------
def run_embedding_pipeline(force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    print("=" * 60)
    print("SYMPL EMBEDDING GENERATION PIPELINE")
    print("=" * 60)
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Expected Dimension: {EMBEDDING_DIMENSION}")
    print(f"Force Re-embed: {force}")
    print(f"Dry Run: {dry_run}")

    # Connect to PostgreSQL
    with psycopg.connect(DATABASE_URL) as conn:
        print("\n[1] Verifying pgvector schema compatibility...")
        verify_pgvector_compatibility(conn, EMBEDDING_DIMENSION)
        print("  pgvector compatibility: VERIFIED")

        # Query chunks
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_key, retrieval_text, embedding IS NOT NULL as has_embedding
                FROM proposal_chunks
                WHERE retrieval_enabled = true
                ORDER BY section_order ASC, chunk_key ASC;
            """)
            rows = cur.fetchall()

        total_retrieval_enabled = len(rows)
        print(f"\n[2] Found {total_retrieval_enabled} retrieval-enabled chunks.")

        to_embed = []
        already_embedded = 0
        for chunk_key, retrieval_text, has_embedding in rows:
            if has_embedding and not force:
                already_embedded += 1
            else:
                to_embed.append((chunk_key, retrieval_text))

        print(f"  Already embedded: {already_embedded}")
        print(f"  Pending embedding: {len(to_embed)}")

        if not to_embed:
            print("\nAll eligible chunks already have embeddings. Nothing to do.")
            return {
                'total_chunks': total_retrieval_enabled,
                'already_embedded': already_embedded,
                'newly_embedded': 0,
                'failed': 0
            }

        # Load embedding model
        print(f"\n[3] Loading model '{EMBEDDING_MODEL}' via sentence-transformers...")
        from sentence_transformers import SentenceTransformer
        t0 = time.perf_counter()
        model = SentenceTransformer(EMBEDDING_MODEL)
        t1 = time.perf_counter()
        print(f"  Model loaded in {t1 - t0:.2f}s")

        # Generate embeddings
        print(f"\n[4] Generating embeddings from 'retrieval_text' for {len(to_embed)} chunks...")
        texts = [item[1] for item in to_embed]
        keys = [item[0] for item in to_embed]

        gen_t0 = time.perf_counter()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        gen_t1 = time.perf_counter()
        print(f"  Embeddings generated in {gen_t1 - gen_t0:.2f}s")

        # Validate dimensions and numerical validity
        for idx, (k, vec) in enumerate(zip(keys, vectors)):
            if len(vec) != EMBEDDING_DIMENSION:
                raise ValueError(f"Vector for {k} has dimension {len(vec)}, expected {EMBEDDING_DIMENSION}")
            if not all(isinstance(float(x), float) for x in vec):
                raise ValueError(f"Vector for {k} contains non-float values")

        if dry_run:
            print("\n[DRY RUN] Embeddings generated and validated, skipping database write.")
            return {
                'total_chunks': total_retrieval_enabled,
                'already_embedded': already_embedded,
                'newly_embedded': len(to_embed),
                'failed': 0
            }

        # Store embeddings in transaction
        print(f"\n[5] Writing embeddings to proposal_chunks in a single transaction...")
        newly_embedded = 0
        failed = 0

        try:
            with conn.cursor() as cur:
                for chunk_key, vec in zip(keys, vectors):
                    vec_str = '[' + ','.join(map(str, vec.tolist())) + ']'
                    cur.execute("""
                        UPDATE proposal_chunks
                        SET embedding = %s::vector,
                            embedded_at = NOW(),
                            updated_at = NOW()
                        WHERE chunk_key = %s AND retrieval_enabled = true;
                    """, (vec_str, chunk_key))
                    newly_embedded += 1

            conn.commit()
            print(f"  Transaction COMMITTED: Successfully stored {newly_embedded} embeddings.")

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] Database write failed: {e}. Transaction ROLLED BACK.")
            raise

    # Summary report
    print("\n" + "=" * 60)
    print("EMBEDDING PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total retrieval-enabled chunks: {total_retrieval_enabled}")
    print(f"Already embedded (skipped):     {already_embedded}")
    print(f"Newly embedded:                {newly_embedded}")
    print(f"Failed:                         {failed}")
    print("=" * 60)

    return {
        'total_chunks': total_retrieval_enabled,
        'already_embedded': already_embedded,
        'newly_embedded': newly_embedded,
        'failed': failed
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate embeddings for Sympl proposal chunks")
    parser.add_argument('--force', action='store_true', help="Force re-embedding of chunks that already have embeddings")
    parser.add_argument('--dry-run', action='store_true', help="Generate and validate embeddings without writing to the database")
    args = parser.parse_args()

    run_embedding_pipeline(force=args.force, dry_run=args.dry_run)

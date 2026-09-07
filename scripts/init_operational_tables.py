"""
Sympl Solutions Proposal RAG — Operational Database Tables Migration

Creates the lightweight operational tracking tables required for production hardening:
  - proposal_jobs: High-level asynchronous proposal generation jobs
  - proposal_runs: Fine-grained execution timing per pipeline stage (PLANNER, WRITER, RENDERER)

CRITICAL INVARIANT:
  Does NOT modify or touch frozen RAG tables:
  - proposal_documents (7)
  - proposal_chunks (71)
  - embeddings (47)
  - sympl_style_rules (21)
  - sympl_reference_blocks (13)
  - dataset_imports (7)
"""

import sys
import psycopg
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_planner.retrieval import DATABASE_URL


CREATE_PROPOSAL_JOBS_SQL = """
CREATE TABLE IF NOT EXISTS proposal_jobs (
    id VARCHAR(64) PRIMARY KEY,
    proposal_id VARCHAR(64),
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    request_payload_hash VARCHAR(64)
);
"""

CREATE_PROPOSAL_RUNS_SQL = """
CREATE TABLE IF NOT EXISTS proposal_runs (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL REFERENCES proposal_jobs(id) ON DELETE CASCADE,
    stage VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms DOUBLE PRECISION,
    status VARCHAR(32) NOT NULL
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_proposal_jobs_status ON proposal_jobs(status);
CREATE INDEX IF NOT EXISTS idx_proposal_runs_job_id ON proposal_runs(job_id);
"""


def init_operational_tables(database_url: str = DATABASE_URL) -> None:
    """Executes the DDL to create operational tracking tables."""
    print("Connecting to PostgreSQL database...")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            print("Creating table proposal_jobs...")
            cur.execute(CREATE_PROPOSAL_JOBS_SQL)
            print("Creating table proposal_runs...")
            cur.execute(CREATE_PROPOSAL_RUNS_SQL)
            print("Creating operational indexes...")
            cur.execute(CREATE_INDEXES_SQL)
            conn.commit()

            # Verify tables exist
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_name IN ('proposal_jobs', 'proposal_runs')
                ORDER BY table_name;
            """)
            found = [row[0] for row in cur.fetchall()]
            print(f"Verified operational tables in database: {found}")
            if set(found) != {"proposal_jobs", "proposal_runs"}:
                raise RuntimeError(f"Expected operational tables missing! Found: {found}")

            # Verify frozen asset counts are untouched
            cur.execute("SELECT count(*) FROM proposal_documents;")
            assert cur.fetchone()[0] == 7, "proposal_documents must remain 7"
            cur.execute("SELECT count(*) FROM proposal_chunks;")
            assert cur.fetchone()[0] == 71, "proposal_chunks must remain 71"
            cur.execute("SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL;")
            assert cur.fetchone()[0] == 47, "embeddings must remain 47"
            cur.execute("SELECT count(*) FROM sympl_style_rules;")
            assert cur.fetchone()[0] == 21, "sympl_style_rules must remain 21"
            cur.execute("SELECT count(*) FROM sympl_reference_blocks;")
            assert cur.fetchone()[0] == 13, "sympl_reference_blocks must remain 13"

    print("Operational tables initialized successfully. All frozen assets verified unchanged.")


if __name__ == "__main__":
    init_operational_tables()

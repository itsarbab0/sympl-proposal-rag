"""
Sympl Solutions Proposal RAG — Operational Job & Run Tracker (Phase 6B)

Database access layer for managing asynchronous proposal generation jobs (proposal_jobs)
and fine-grained stage executions (proposal_runs) in PostgreSQL.
"""

import uuid
import hashlib
import json
import psycopg
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from sympl_planner.retrieval import DATABASE_URL
from sympl_observability.logging import obs_logger


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of a JSON payload for audit and idempotency."""
    serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()[:32]


def verify_operational_tables_exist(database_url: str = DATABASE_URL) -> bool:
    """
    Verifies that the operational tables (proposal_jobs, proposal_runs) exist in PostgreSQL.
    Does NOT auto-create tables; raises or returns False if missing.
    """
    try:
        with psycopg.connect(database_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND table_name IN ('proposal_jobs', 'proposal_runs');
                """)
                tables = {row[0] for row in cur.fetchall()}
                return tables == {"proposal_jobs", "proposal_runs"}
    except Exception as e:
        obs_logger.warning(f"Failed checking operational tables: {e}")
        return False


class JobTracker:
    """Encapsulates PostgreSQL operations for proposal_jobs and proposal_runs."""

    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url

    def create_job(self, payload: Optional[Dict[str, Any]] = None) -> str:
        """Creates a new record in proposal_jobs in 'CREATED' status."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        payload_hash = compute_payload_hash(payload) if payload else None

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO proposal_jobs (id, status, request_payload_hash, created_at)
                    VALUES (%s, 'CREATED', %s, NOW());
                    """,
                    (job_id, payload_hash)
                )
                conn.commit()

        obs_logger.info(f"Created proposal job: {job_id} (hash={payload_hash})")
        return job_id

    def update_job_status(
        self,
        job_id: str,
        status: str,
        proposal_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Updates proposal_jobs status and completion timestamp."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                if status in ("COMPLETED", "FAILED"):
                    cur.execute(
                        """
                        UPDATE proposal_jobs
                        SET status = %s,
                            proposal_id = COALESCE(%s, proposal_id),
                            completed_at = NOW(),
                            error_message = %s
                        WHERE id = %s;
                        """,
                        (status, proposal_id, error_message, job_id)
                    )
                else:
                    cur.execute(
                        """
                        UPDATE proposal_jobs
                        SET status = %s,
                            proposal_id = COALESCE(%s, proposal_id),
                            error_message = %s
                        WHERE id = %s;
                        """,
                        (status, proposal_id, error_message, job_id)
                    )
                conn.commit()

        obs_logger.info(f"Updated job {job_id} status to {status}")

    def record_run(
        self,
        job_id: str,
        stage: str,
        duration_ms: float,
        status: str = "COMPLETED"
    ) -> str:
        """Records a stage run in proposal_runs."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO proposal_runs (id, job_id, stage, duration_ms, status, completed_at)
                    VALUES (%s, %s, %s, %s, %s, NOW());
                    """,
                    (run_id, job_id, stage, duration_ms, status)
                )
                conn.commit()

        obs_logger.info(f"Recorded stage run {run_id} for job {job_id} (stage={stage}, status={status}, ms={duration_ms})")
        return run_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves status, current stage, and progress for a proposal job.
        Stages order: PLANNER (0.33) -> WRITER (0.66) -> RENDERER (1.00).
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, proposal_id, status, created_at, completed_at, error_message
                    FROM proposal_jobs
                    WHERE id = %s;
                    """,
                    (job_id,)
                )
                job_row = cur.fetchone()
                if not job_row:
                    return None

                # Fetch completed runs
                cur.execute(
                    """
                    SELECT stage, status
                    FROM proposal_runs
                    WHERE job_id = %s
                    ORDER BY started_at ASC;
                    """,
                    (job_id,)
                )
                runs = cur.fetchall()

        j_id, proposal_id, status, created_at, completed_at, error_message = job_row

        # Determine current stage and numeric progress
        stage_map = {"PLANNER": 0.33, "WRITER": 0.66, "RENDERER": 1.0}
        current_stage = "INITIALIZING"
        progress = 0.0

        if status == "COMPLETED":
            current_stage = "COMPLETED"
            progress = 1.0
        elif status == "FAILED":
            current_stage = "FAILED"
        elif status == "RUNNING":
            completed_stages = [r[0] for r in runs if r[1] == "COMPLETED"]
            if not completed_stages:
                current_stage = "PLANNER"
                progress = 0.1
            elif "PLANNER" in completed_stages and "WRITER" not in completed_stages:
                current_stage = "WRITER"
                progress = 0.33
            elif "WRITER" in completed_stages and "RENDERER" not in completed_stages:
                current_stage = "RENDERER"
                progress = 0.66
            elif "RENDERER" in completed_stages:
                current_stage = "FINALIZING"
                progress = 0.95
        elif status == "CREATED":
            current_stage = "QUEUED"
            progress = 0.0

        res: Dict[str, Any] = {
            "job_id": j_id,
            "status": status,
            "current_stage": current_stage,
            "progress": round(progress, 2),
            "proposal_id": proposal_id
        }
        if error_message:
            res["error_message"] = error_message

        return res

    def fetch_pending_jobs(self, limit: int = 5) -> List[str]:
        """Fetches IDs of jobs in 'CREATED' status awaiting execution."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM proposal_jobs
                    WHERE status = 'CREATED'
                    ORDER BY created_at ASC
                    LIMIT %s;
                    """,
                    (limit,)
                )
                return [row[0] for row in cur.fetchall()]

    def claim_job(self, job_id: str, proposal_id: Optional[str] = None) -> bool:
        """
        Atomically claims a CREATED job by setting status to RUNNING.
        Returns True if claimed successfully, False if already claimed or processed.
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE proposal_jobs
                    SET status = 'RUNNING',
                        proposal_id = COALESCE(%s, proposal_id)
                    WHERE id = %s AND status = 'CREATED'
                    RETURNING id;
                    """,
                    (proposal_id, job_id)
                )
                row = cur.fetchone()
                conn.commit()
                return row is not None


# Default tracker instance
default_tracker = JobTracker()

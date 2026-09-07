"""
Sympl Solutions Proposal RAG — Dedicated Production Worker Daemon (Phase 6C)

Consumes asynchronous proposal generation tasks directly from PostgreSQL operational tables
without requiring external message brokers (Redis, Celery, Kafka, RabbitMQ).

Key Features:
- Safe atomic claiming of CREATED jobs (duplicate job prevention)
- Direct reuse of sympl_observability.executor._run_job
- Signal-aware graceful shutdown (SIGTERM / SIGINT)
- Shared artifact storage for intake payloads and generated outputs
- Structured JSON logging and telemetry emission
"""

import os
import sys
import time
import signal
import uuid
from typing import Optional

from sympl_observability.logging import obs_logger, generate_request_id
from sympl_observability.job_tracker import default_tracker, JobTracker, verify_operational_tables_exist
from sympl_observability.executor import default_executor, LocalBackgroundExecutor
from sympl_storage.store import default_store, ArtifactStore


class ProposalWorker:
    """
    Dedicated worker process consuming queued proposal generation jobs.
    Runs independently in containerized deployments.
    """

    def __init__(
        self,
        tracker: Optional[JobTracker] = None,
        executor: Optional[LocalBackgroundExecutor] = None,
        store: Optional[ArtifactStore] = None,
        orchestrator: Optional[object] = None,
        poll_interval: float = 2.0
    ):
        self.tracker = tracker or default_tracker
        self.executor = executor or default_executor
        self.store = store or default_store
        self.orchestrator = orchestrator
        self.poll_interval = poll_interval
        self.stop_requested = False
        self._current_job_id: Optional[str] = None

        # Setup signal handlers for graceful termination
        self._setup_signals()

    def _setup_signals(self) -> None:
        """Configures OS signal handlers for graceful shutdown."""
        try:
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)
        except (ValueError, AttributeError):
            # Signal handling might be restricted in some execution contexts
            pass

    def _handle_signal(self, signum, frame) -> None:
        obs_logger.info(f"Worker received signal {signum}. Initiating graceful shutdown...")
        self.stop_requested = True

    def process_next_job(self) -> bool:
        """
        Polls and attempts to claim and execute a single pending job.
        Returns True if a job was processed, False if no jobs were pending.
        """
        pending_job_ids = self.tracker.fetch_pending_jobs(limit=1)
        if not pending_job_ids:
            return False

        job_id = pending_job_ids[0]
        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"

        # Atomic claim prevents duplicate processing by concurrent workers
        claimed = self.tracker.claim_job(job_id, proposal_id=proposal_id)
        if not claimed:
            obs_logger.debug(f"Job {job_id} already claimed by another worker; skipping.")
            return False

        self._current_job_id = job_id
        obs_logger.info(f"[Worker] Claimed job {job_id} -> assigned proposal_id={proposal_id}")

        # Load input intake payload from shared storage
        intake_payload = self.store.load_intake(job_id)
        req_id = generate_request_id()

        if not intake_payload:
            err_msg = f"Missing intake payload for job {job_id}. Cannot proceed."
            obs_logger.error(err_msg)
            self.tracker.update_job_status(
                job_id=job_id,
                status="FAILED",
                proposal_id=proposal_id,
                error_message=err_msg
            )
            self._current_job_id = None
            return True

        # Execute the pipeline reusing existing executor logic
        try:
            if self.orchestrator is not None:
                orch = self.orchestrator
            else:
                from sympl_api.services import service
                orch = service

            self.executor._run_job(
                job_id=job_id,
                payload=intake_payload,
                request_id=req_id,
                orchestrator=orch
            )
        except Exception as e:
            obs_logger.error(f"[Worker] Unexpected exception executing job {job_id}: {e}", exc_info=True)
            self.tracker.update_job_status(
                job_id=job_id,
                status="FAILED",
                proposal_id=proposal_id,
                error_message=str(e)
            )
        finally:
            self._current_job_id = None

        return True

    def run(self) -> None:
        """Continuous execution loop."""
        obs_logger.info("Sympl Proposal RAG Worker starting up...")

        # Verify database operational tables exist before entering polling loop
        if not verify_operational_tables_exist(self.tracker.database_url):
            obs_logger.error("Operational tables (proposal_jobs, proposal_runs) missing. Worker aborting.")
            sys.exit(1)

        obs_logger.info(f"Worker initialized and ready. Polling every {self.poll_interval}s...")

        while not self.stop_requested:
            try:
                processed = self.process_next_job()
                if not processed:
                    time.sleep(self.poll_interval)
            except Exception as e:
                obs_logger.error(f"Error in worker polling loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)

        obs_logger.info("Worker stopped gracefully.")


def main():
    """CLI entrypoint for standalone container execution."""
    poll_sec = float(os.getenv("WORKER_POLL_INTERVAL", "2.0"))
    worker = ProposalWorker(poll_interval=poll_sec)
    worker.run()


if __name__ == "__main__":
    main()

"""
Sympl Solutions Proposal RAG — Job Execution Architecture (Phase 6B)

Defines the JobExecutor abstraction and LocalBackgroundExecutor implementation.
Designed so future replacement with Celery, Redis Queue, or AWS SQS is seamless.
"""

import time
import uuid
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from sympl_observability.logging import obs_logger, set_current_request_id
from sympl_observability.telemetry import PipelineTelemetry
from sympl_observability.job_tracker import default_tracker, JobTracker
from sympl_storage.store import default_store, ArtifactStore


class JobExecutor(ABC):
    """Abstract job execution contract allowing pluggable worker backends."""

    @abstractmethod
    def submit_job(
        self,
        job_id: str,
        payload: Dict[str, Any],
        request_id: str,
        orchestrator: Any
    ) -> None:
        """Schedules a proposal generation task for asynchronous background processing."""
        pass


class LocalBackgroundExecutor(JobExecutor):
    """
    Local multi-threaded worker executing proposal jobs asynchronously.
    Enforces the stage progression (PLANNER -> WRITER -> RENDERER),
    records timing in proposal_runs, updates proposal_jobs, and persists artifacts.
    """

    def __init__(
        self,
        max_workers: int = 4,
        tracker: Optional[JobTracker] = None,
        store: Optional[ArtifactStore] = None
    ):
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sympl_worker")
        self.tracker = tracker or default_tracker
        self.store = store or default_store

    def submit_job(
        self,
        job_id: str,
        payload: Dict[str, Any],
        request_id: str,
        orchestrator: Any
    ) -> None:
        """Enqueues job execution onto the thread pool."""
        obs_logger.info(f"Submitting job {job_id} to LocalBackgroundExecutor")
        self._pool.submit(self._run_job, job_id, payload, request_id, orchestrator)

    def _run_job(
        self,
        job_id: str,
        payload: Dict[str, Any],
        request_id: str,
        orchestrator: Any
    ) -> None:
        """Worker thread entrypoint."""
        set_current_request_id(request_id)
        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
        telemetry = PipelineTelemetry(proposal_id=proposal_id, request_id=request_id)
        current_stage = "INITIALIZING"

        obs_logger.info(f"[Job {job_id}] Starting async proposal generation (proposal_id={proposal_id})")
        self.tracker.update_job_status(job_id, status="RUNNING", proposal_id=proposal_id)

        try:
            # ------------------------------------------------------------------
            # Stage 1: Proposal Planner
            # ------------------------------------------------------------------
            current_stage = "PLANNER"
            obs_logger.info(f"[Job {job_id}] Running PLANNER stage")
            t0 = time.perf_counter()
            plan_dict = orchestrator.execute_planner(payload)
            t_plan = (time.perf_counter() - t0) * 1000.0
            telemetry.record_planner(t_plan)
            self.tracker.record_run(job_id, stage="PLANNER", duration_ms=round(t_plan, 2), status="COMPLETED")
            self.store.save_plan(proposal_id, plan_dict)

            # ------------------------------------------------------------------
            # Stage 2: Proposal Writer
            # ------------------------------------------------------------------
            current_stage = "WRITER"
            obs_logger.info(f"[Job {job_id}] Running WRITER stage")
            t1 = time.perf_counter()
            draft_dict = orchestrator.execute_writer(plan_dict)
            t_write = (time.perf_counter() - t1) * 1000.0
            telemetry.record_writer(t_write)
            self.tracker.record_run(job_id, stage="WRITER", duration_ms=round(t_write, 2), status="COMPLETED")
            self.store.save_draft(proposal_id, draft_dict)

            # ------------------------------------------------------------------
            # Stage 3: Proposal Renderer
            # ------------------------------------------------------------------
            current_stage = "RENDERER"
            obs_logger.info(f"[Job {job_id}] Running RENDERER stage")
            t2 = time.perf_counter()
            render_dict = orchestrator.execute_renderer(draft_dict)
            t_render = (time.perf_counter() - t2) * 1000.0
            telemetry.record_renderer(t_render)
            self.tracker.record_run(job_id, stage="RENDERER", duration_ms=round(t_render, 2), status="COMPLETED")
            self.store.save_render(proposal_id, render_dict)

            # Mark job COMPLETED
            self.tracker.update_job_status(job_id, status="COMPLETED", proposal_id=proposal_id)
            telemetry.complete()
            obs_logger.info(f"[Job {job_id}] Proposal generation completed successfully in {round(telemetry.stages.total_ms, 2)}ms")

        except Exception as e:
            err_msg = str(e)
            obs_logger.error(f"[Job {job_id}] Stage {current_stage} failed: {err_msg}", exc_info=True)
            self.tracker.record_run(job_id, stage=current_stage, duration_ms=0.0, status="FAILED")
            self.tracker.update_job_status(job_id, status="FAILED", proposal_id=proposal_id, error_message=err_msg)
            telemetry.fail(err_msg)


# Default shared executor instance
default_executor = LocalBackgroundExecutor()

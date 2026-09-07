"""
Sympl Solutions Proposal RAG — Pipeline Telemetry (Phase 6B)

Captures and formats standardized execution telemetry for every proposal generation run:
  - Stage timings (planner_ms, writer_ms, renderer_ms, total_ms)
  - Fine-grained sub-stage latencies (retrieval_ms, llm_ms, render_ms)
  - Correlation tracking (request_id, proposal_id, status)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sympl_observability.logging import obs_logger, get_current_request_id


@dataclass
class StageTimers:
    planner_ms: float = 0.0
    writer_ms: float = 0.0
    renderer_ms: float = 0.0
    total_ms: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "planner_ms": round(self.planner_ms, 2),
            "writer_ms": round(self.writer_ms, 2),
            "renderer_ms": round(self.renderer_ms, 2),
            "total_ms": round(self.total_ms, 2)
        }


@dataclass
class SubstageLatencies:
    retrieval_ms: float = 0.0
    llm_ms: float = 0.0
    render_ms: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "retrieval_ms": round(self.retrieval_ms, 2),
            "llm_ms": round(self.llm_ms, 2),
            "render_ms": round(self.render_ms, 2)
        }


class PipelineTelemetry:
    """Aggregates execution timings and produces production telemetry records."""

    def __init__(self, proposal_id: str, request_id: Optional[str] = None):
        self.proposal_id = proposal_id
        self.request_id = request_id or get_current_request_id()
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.stages = StageTimers()
        self.substages = SubstageLatencies()
        self.status: str = "RUNNING"
        self._start_perf: float = time.perf_counter()

    def record_planner(self, duration_ms: float, retrieval_ms: float = 0.0) -> None:
        self.stages.planner_ms = duration_ms
        if retrieval_ms > 0:
            self.substages.retrieval_ms = retrieval_ms

    def record_writer(self, duration_ms: float, llm_ms: float = 0.0) -> None:
        self.stages.writer_ms = duration_ms
        if llm_ms > 0:
            self.substages.llm_ms = llm_ms

    def record_renderer(self, duration_ms: float, render_ms: float = 0.0) -> None:
        self.stages.renderer_ms = duration_ms
        if render_ms > 0:
            self.substages.render_ms = render_ms

    def complete(self) -> Dict[str, Any]:
        """Finalizes total execution time and marks telemetry COMPLETED."""
        elapsed = (time.perf_counter() - self._start_perf) * 1000.0
        stage_sum = self.stages.planner_ms + self.stages.writer_ms + self.stages.renderer_ms
        total = max(elapsed, stage_sum)
        self.stages.total_ms = total
        self.status = "COMPLETED"
        telemetry_dict = self.to_dict()
        self._emit(telemetry_dict)
        return telemetry_dict

    def fail(self, error_message: str) -> Dict[str, Any]:
        """Marks telemetry as FAILED and captures total elapsed duration."""
        elapsed = (time.perf_counter() - self._start_perf) * 1000.0
        stage_sum = self.stages.planner_ms + self.stages.writer_ms + self.stages.renderer_ms
        total = max(elapsed, stage_sum)
        self.stages.total_ms = total
        self.status = "FAILED"
        telemetry_dict = self.to_dict()
        telemetry_dict["error_message"] = error_message
        self._emit(telemetry_dict, is_error=True)
        return telemetry_dict

    def to_dict(self) -> Dict[str, Any]:
        """Produces the exact required production telemetry JSON structure."""
        return {
            "request_id": self.request_id,
            "proposal_id": self.proposal_id,
            "timestamp": self.timestamp,
            "stages": self.stages.to_dict(),
            "substages": self.substages.to_dict(),
            "status": self.status
        }

    def _emit(self, record: Dict[str, Any], is_error: bool = False) -> None:
        """Emits structured JSON telemetry record to standard logging."""
        extra = {"telemetry": record}
        msg = f"Proposal pipeline finished with status: {self.status}"
        if is_error:
            obs_logger.error(msg, extra=extra)
        else:
            obs_logger.info(msg, extra=extra)

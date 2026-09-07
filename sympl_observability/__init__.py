"""
Sympl Solutions Proposal RAG — Observability Package (Phase 6B)
"""

from sympl_observability.logging import (
    setup_logger,
    obs_logger,
    generate_request_id,
    get_current_request_id,
    set_current_request_id,
    StructuredJsonFormatter,
    RequestIdFilter
)
from sympl_observability.telemetry import (
    PipelineTelemetry,
    StageTimers,
    SubstageLatencies
)
from sympl_observability.job_tracker import (
    JobTracker,
    default_tracker,
    verify_operational_tables_exist,
    compute_payload_hash
)
from sympl_observability.executor import (
    JobExecutor,
    LocalBackgroundExecutor,
    default_executor
)
from sympl_observability.environment import (
    validate_environment,
    EnvironmentReport,
    EnvironmentValidationError
)
from sympl_observability.resilience import (
    RequestSizeLimitMiddleware,
    sanitize_error_message,
    MAX_REQUEST_SIZE
)
from sympl_observability.worker import ProposalWorker

__all__ = [
    "setup_logger",
    "obs_logger",
    "generate_request_id",
    "get_current_request_id",
    "set_current_request_id",
    "StructuredJsonFormatter",
    "RequestIdFilter",
    "PipelineTelemetry",
    "StageTimers",
    "SubstageLatencies",
    "JobTracker",
    "default_tracker",
    "verify_operational_tables_exist",
    "compute_payload_hash",
    "JobExecutor",
    "LocalBackgroundExecutor",
    "default_executor",
    "ProposalWorker",
    "validate_environment",
    "EnvironmentReport",
    "EnvironmentValidationError",
    "RequestSizeLimitMiddleware",
    "sanitize_error_message",
    "MAX_REQUEST_SIZE"
]

"""
Sympl Solutions Proposal RAG — API Package (Phase 6A)

Production orchestration API layer providing HTTP REST endpoints for automated
proposal generation, planning, narrative writing, and presentation rendering.
"""

from sympl_api.main import app, create_app
from sympl_api.config import settings
from sympl_api.services import service, OrchestrationService
from sympl_api.auth import verify_api_key
from sympl_api.schemas import (
    HealthResponse,
    ProposalGenerateResponse,
    ExecutionMetadata,
    ErrorResponse
)
from sympl_api.exceptions import (
    APIException,
    InvalidIntakeException,
    ApprovalRequiredException,
    EmptyApprovedScopeException
)

__all__ = [
    "app",
    "create_app",
    "settings",
    "service",
    "OrchestrationService",
    "verify_api_key",
    "HealthResponse",
    "ProposalGenerateResponse",
    "ExecutionMetadata",
    "ErrorResponse",
    "APIException",
    "InvalidIntakeException",
    "ApprovalRequiredException",
    "EmptyApprovedScopeException"
]

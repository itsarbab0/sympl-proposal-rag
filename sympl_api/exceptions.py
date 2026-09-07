"""
Sympl Solutions Proposal RAG — API Exception Handling

Custom API exceptions and uniform JSON error handlers translating domain and validation
failures into standard HTTP responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any, Optional

from sympl_api.logging import get_current_request_id, logger
from sympl_writer.exceptions import ScopeFirewallError, WriterError
from sympl_renderer.exceptions import InvalidDraftError, RendererError


class APIException(Exception):
    """Base API exception with HTTP status code and error code."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class InvalidIntakeException(APIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INVALID_INTAKE",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {}
        )


class ApprovalRequiredException(APIException):
    """Raised when approved_scope is missing from the client intake."""

    def __init__(
        self,
        message: str = "approved_scope is required before proposal generation",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="APPROVAL_REQUIRED",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {}
        )


class EmptyApprovedScopeException(APIException):
    """Raised when approved_scope is present but empty."""

    def __init__(
        self,
        message: str = "approved_scope cannot be empty",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="EMPTY_APPROVED_SCOPE",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {}
        )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handles explicit APIExceptions."""
    req_id = get_current_request_id()
    logger.error(f"APIException [{exc.error_code}]: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": req_id
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles FastAPI Pydantic schema validation failures."""
    req_id = get_current_request_id()
    logger.warning(f"Request validation failure: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "The request body failed schema validation.",
            "details": {"errors": exc.errors()},
            "request_id": req_id
        }
    )


async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handles domain exceptions from Planner, Writer, and Renderer."""
    req_id = get_current_request_id()
    logger.error(f"Domain exception [{type(exc).__name__}]: {exc}")

    # Map specific domain exceptions
    if isinstance(exc, (ScopeFirewallError, InvalidDraftError)):
        status_code = status.HTTP_400_BAD_REQUEST
        error_code = type(exc).__name__.upper()
    elif isinstance(exc, (WriterError, RendererError)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        error_code = type(exc).__name__.upper()
    elif isinstance(exc, ValueError):
        status_code = status.HTTP_400_BAD_REQUEST
        error_code = "VALUE_ERROR"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_SERVER_ERROR"

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "message": str(exc),
            "details": {"exception_type": type(exc).__name__},
            "request_id": req_id
        }
    )

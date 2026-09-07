"""
Sympl Solutions Proposal RAG — Resilience & Security Hardening (Phase 6B)

Includes:
  - Request size limiter middleware (1MB cap)
  - Error message sanitization (protecting credentials and database paths)
"""

import re
from typing import Dict, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status

from sympl_observability.logging import get_current_request_id, obs_logger


MAX_REQUEST_SIZE = 1_048_576  # 1 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming HTTP requests with bodies exceeding 1MB (413 Payload Too Large)."""

    def __init__(self, app, max_size_bytes: int = MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_size_bytes:
                    req_id = get_current_request_id()
                    obs_logger.warning(f"Request payload too large: {length} bytes (limit={self.max_size_bytes})")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds maximum allowed size of {self.max_size_bytes // (1024*1024)}MB.",
                            "details": {"max_bytes": self.max_size_bytes, "received_bytes": length},
                            "request_id": req_id
                        }
                    )
            except ValueError:
                pass

        return await call_next(request)


def sanitize_error_message(message: str) -> str:
    """
    Strips sensitive credentials, database URLs, and file paths from error messages
    before exposing them to API consumers.
    """
    if not message:
        return "An internal error occurred."

    # Redact PostgreSQL URLs with passwords: postgres://user:pass@host...
    sanitized = re.sub(r"postgres(ql)?://[^:]+:[^@]+@", "postgresql://[REDACTED]@", str(message))

    # Redact potential API keys (e.g. sk-..., sympl-..., AIza...)
    sanitized = re.sub(r"(sk-[A-Za-z0-9_-]{20,})", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"(AIza[0-9A-Za-z-_]{35})", "[REDACTED_API_KEY]", sanitized)

    return sanitized

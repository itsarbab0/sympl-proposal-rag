"""
Sympl Solutions Proposal RAG — Resilience & Security Hardening (Phase 6B)

Includes:
  - Request size limiter middleware (1MB cap)
  - Error message sanitization (protecting credentials and database paths)
"""

import re
import time
import threading
from typing import Dict, Any, Optional, Tuple, List, Set
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


class SlidingWindowRateLimiter:
    """
    In-memory thread-safe sliding window rate limiter.

    Note on Architectural Scaling:
    This in-memory implementation provides robust single-instance API protection.
    For future multi-instance horizontal scaling (e.g. across multiple Kubernetes pods
    or container nodes), this interface can be backed by a distributed Redis cache
    using atomic Lua scripts or sliding sorted sets.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_key: str) -> Tuple[bool, int]:
        """
        Determines whether an incoming request from client_key is allowed.
        Returns: (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests.get(client_key, [])
            # Prune timestamps outside the current sliding window
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) < self.max_requests:
                timestamps.append(now)
                self._requests[client_key] = timestamps
                return True, 0
            else:
                self._requests[client_key] = timestamps
                earliest = timestamps[0]
                retry_after = max(1, int(earliest + self.window_seconds - now) + 1)
                return False, retry_after

    def reset(self) -> None:
        """Clears all tracked client sliding windows (for test reset)."""
        with self._lock:
            self._requests.clear()


# Global default rate limiter instance
default_rate_limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware enforcing rate limits across API endpoints.
    Protects the backend from abusive automation bursts while exempting
    critical health probe endpoints.
    """

    EXEMPT_PATHS: Set[str] = {
        "/health",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json"
    }

    def __init__(
        self,
        app,
        limiter: Optional[SlidingWindowRateLimiter] = None,
        enabled: bool = True,
        exempt_paths: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.limiter = limiter or default_rate_limiter
        self.enabled = enabled
        self.exempt_paths = exempt_paths or self.EXEMPT_PATHS

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.url.path in self.exempt_paths:
            return await call_next(request)

        # Identify client by API Key if available, or client IP
        api_key = request.headers.get("X-API-Key")
        client_ip = request.client.host if request.client else "unknown_ip"
        client_key = f"key:{api_key}" if api_key else f"ip:{client_ip}"

        allowed, retry_after = self.limiter.is_allowed(client_key)
        if not allowed:
            req_id = get_current_request_id()
            obs_logger.warning(f"Rate limit exceeded for {client_key} on {request.url.path} (retry_after={retry_after}s)")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                    "details": {
                        "limit": self.limiter.max_requests,
                        "window_seconds": self.limiter.window_seconds,
                        "retry_after": retry_after
                    },
                    "request_id": req_id
                }
            )

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


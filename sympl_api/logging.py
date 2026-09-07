"""
Sympl Solutions Proposal RAG — API Request Logging & Correlation

Provides request ID generation, context correlation, and standardized logging
across all API execution pipelines.
"""

import logging
import uuid
import contextvars
from typing import Optional

# Context variable to hold request_id across async request contexts
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def generate_request_id() -> str:
    """Generates a unique request correlation ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def get_current_request_id() -> str:
    """Retrieves current request ID from context or generates a new one."""
    req_id = request_id_ctx.get()
    return req_id if req_id else generate_request_id()


def set_current_request_id(req_id: str) -> None:
    """Sets the current request ID in context."""
    request_id_ctx.set(req_id)


class RequestIdFilter(logging.Filter):
    """Logging filter that injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "system"
        return True


def setup_logger(name: str = "sympl_api") -> logging.Logger:
    """Configures and returns the application logger with request_id correlation."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
    return logger


logger = setup_logger()

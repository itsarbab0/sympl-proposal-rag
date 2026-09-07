"""
Sympl Solutions Proposal RAG — Structured JSON Logging & Correlation IDs (Phase 6B)

Provides structured JSON logging for production observability, request correlation tracking
via ASGI context variables, and standard console/file handlers.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Correlation ID context variable
REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="req_system")


def generate_request_id(prefix: str = "req_") -> str:
    """Generates a random unique request correlation identifier."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def get_current_request_id() -> str:
    """Retrieves the request correlation ID for the active async/thread context."""
    return REQUEST_ID_CTX.get()


def set_current_request_id(request_id: str) -> None:
    """Sets the request correlation ID for the active context."""
    REQUEST_ID_CTX.set(request_id)


class RequestIdFilter(logging.Filter):
    """Injects the current request correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_current_request_id()
        return True


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as structured single-line JSON objects for log aggregation engines
    (Datadog, CloudWatch, Loki, Elasticsearch).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", get_current_request_id()),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }

        # Include structured extra properties if passed
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry["details"] = record.extra_fields
        elif hasattr(record, "telemetry") and isinstance(record.telemetry, dict):
            log_entry["telemetry"] = record.telemetry

        # Include exception trace if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logger(
    name: str = "sympl",
    level: int = logging.INFO,
    json_format: bool = True
) -> logging.Logger:
    """Configures a standardized application logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(RequestIdFilter())
        if json_format:
            handler.setFormatter(StructuredJsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%SZ"
                )
            )
        logger.addHandler(handler)

    return logger


# Default shared application logger
obs_logger = setup_logger("sympl_observability")

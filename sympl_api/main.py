"""
Sympl Solutions Proposal RAG — FastAPI Application Entrypoint

Initializes the FastAPI application, registers middleware (CORS, Request ID tracking),
attaches exception handlers, and mounts the API routes.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from contextlib import asynccontextmanager

from sympl_api.config import settings
from sympl_api.routes import router
from sympl_api.logging import generate_request_id, set_current_request_id, logger
from sympl_api.exceptions import (
    APIException,
    ScopeFirewallError,
    WriterError,
    InvalidDraftError,
    RendererError,
    api_exception_handler,
    validation_exception_handler,
    domain_exception_handler
)
from sympl_observability.resilience import (
    RequestSizeLimitMiddleware,
    RateLimitMiddleware,
    default_rate_limiter
)
from sympl_observability.environment import validate_environment


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown diagnostics."""
    logger.info("Validating environment and operational prerequisites...")
    validate_environment(strict=False)
    yield
    logger.info("Application shutdown complete.")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Intercepts incoming HTTP requests to assign or propagate request correlation IDs."""

    async def dispatch(self, request: Request, call_next):
        # Propagate client-supplied header or generate a new request correlation ID
        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        set_current_request_id(req_id)

        logger.info(f"Incoming {request.method} {request.url.path}")
        response = await call_next(request)

        # Inject X-Request-ID into response headers
        response.headers["X-Request-ID"] = req_id
        return response


def create_app() -> FastAPI:
    """Application factory configuring the FastAPI service."""
    docs_url = "/docs" if settings.DOCS_ENABLED else None
    redoc_url = "/redoc" if settings.DOCS_ENABLED else None
    openapi_url = "/openapi.json" if settings.DOCS_ENABLED else None

    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description=settings.API_DESCRIPTION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan
    )

    # 1. Rate Limiting Middleware (in-memory sliding window, configurable limit)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=default_rate_limiter,
        enabled=settings.RATE_LIMIT_ENABLED
    )

    # 2. Request Size Limiter Middleware (1MB)
    app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=settings.MAX_REQUEST_SIZE_BYTES)

    # 3. Request Correlation ID Middleware
    app.add_middleware(RequestIdMiddleware)

    # 4. CORS Middleware (Outermost: adds CORS headers across all status codes)
    cors_origins = settings.get_cors_origins()
    is_prod = settings.ENVIRONMENT.lower() == "production"
    allow_creds = not (is_prod and "*" in cors_origins)
    active_origins = cors_origins if cors_origins else (["https://app.sympl.com"] if is_prod else ["*"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_origins,
        allow_credentials=allow_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 5. Exception Handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ScopeFirewallError, domain_exception_handler)
    app.add_exception_handler(InvalidDraftError, domain_exception_handler)
    app.add_exception_handler(WriterError, domain_exception_handler)
    app.add_exception_handler(RendererError, domain_exception_handler)
    app.add_exception_handler(ValueError, domain_exception_handler)
    app.add_exception_handler(Exception, domain_exception_handler)

    # 6. Route Mounts: Dual mounting for API Versioning and Backward Compatibility
    # Unversioned legacy endpoints: /proposal/generate/async, /health, /proposal/{id}/pdf, etc.
    app.include_router(router)
    # Versioned endpoints: /api/v1/proposal/generate/async, /api/v1/health, /api/v1/proposal/{id}/pdf, etc.
    app.include_router(router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sympl_api.main:app", host="0.0.0.0", port=8000, reload=True)

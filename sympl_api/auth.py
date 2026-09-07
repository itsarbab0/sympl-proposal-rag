"""
Sympl Solutions Proposal RAG — API Security & Authentication

Implements API key authentication middleware and dependency injection:
  - Header: X-API-Key
  - Active when API_AUTH_ENABLED=true
  - Bypassed in local development mode when API_AUTH_ENABLED=false
"""

import os
from fastapi import Header, HTTPException, status
from typing import Optional

from sympl_api.config import settings
from sympl_api.logging import get_current_request_id, logger


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> Optional[str]:
    """
    Dependency that enforces API key authentication when enabled.
    Returns the valid API key or raises HTTP 401.
    """
    # In production, authentication cannot be bypassed
    is_production = os.environ.get("ENVIRONMENT", settings.ENVIRONMENT).lower() == "production"
    auth_enabled = is_production or os.environ.get("API_AUTH_ENABLED", "").lower() in ("true", "1", "yes") or settings.API_AUTH_ENABLED

    if not auth_enabled:
        return None

    valid_keys = settings.get_valid_api_keys()
    req_id = get_current_request_id()

    if not x_api_key:
        logger.warning("Authentication failed: Missing X-API-Key header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Missing required 'X-API-Key' authentication header.",
                "request_id": req_id
            }
        )

    if x_api_key.strip() not in valid_keys:
        logger.warning("Authentication failed: Invalid X-API-Key provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Invalid 'X-API-Key' provided.",
                "request_id": req_id
            }
        )

    return x_api_key

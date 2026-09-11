"""
Sympl Solutions — Canva Connect API OAuth 2.0 & Token Management Layer
Implements RFC 7636 (PKCE) authorization code flow and persistent token management.
Tokens are stored securely in PostgreSQL database (never committed to repository).
"""

import os
import json
import base64
import hashlib
import secrets
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

import logging

try:
    import psycopg
except ImportError:
    psycopg = None

logger = logging.getLogger("canva.oauth")


CANVA_AUTH_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_DEFAULT_SCOPES = [
    "design:read",
    "design:content:read",
    "design:content:write",
    "design:meta:read",
    "brandtemplate:meta:read",
    "brandtemplate:content:read",
    "asset:read",
    "asset:write"
]

TABLE_INIT_SQL = """
CREATE TABLE IF NOT EXISTS canva_oauth_tokens (
    id VARCHAR(50) PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at DOUBLE PRECISION NOT NULL,
    scope TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS canva_pkce_states (
    state VARCHAR(128) PRIMARY KEY,
    code_verifier VARCHAR(128) NOT NULL,
    redirect_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


def get_database_url() -> Optional[str]:
    """Retrieves PostgreSQL connection string from environment or candidate .env."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url
    candidates = [Path("d:/Sympl/.env"), Path("d:/Sympl/sympl-proposal-rag/.env"), Path(".env")]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("DATABASE_URL="):
                            return line.split("=", 1)[1].strip().strip("'\"")
            except Exception:
                pass
    return None


def get_canva_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Retrieves Canva Client ID and Secret from environment."""
    client_id = os.environ.get("CANVA_CLIENT_ID")
    client_secret = os.environ.get("CANVA_CLIENT_SECRET")
    if not client_id or not client_secret:
        candidates = [Path("d:/Sympl/.env"), Path("d:/Sympl/sympl-proposal-rag/.env"), Path(".env")]
        for p in candidates:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("CANVA_CLIENT_ID="):
                                client_id = line.split("=", 1)[1].strip().strip("'\"")
                            elif line.startswith("CANVA_CLIENT_SECRET="):
                                client_secret = line.split("=", 1)[1].strip().strip("'\"")
                except Exception:
                    pass
    return client_id, client_secret


def init_token_tables():
    """Ensures Canva token and PKCE state tables exist in PostgreSQL."""
    db_url = get_database_url()
    if not db_url:
        return
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(TABLE_INIT_SQL)
            conn.commit()
    except Exception as e:
        logger.warning(f"Could not initialize canva_oauth_tokens tables: {e}")


def generate_pkce_pair() -> Tuple[str, str]:
    """Generates PKCE code_verifier and code_challenge according to RFC 7636."""
    verifier = secrets.token_urlsafe(64)
    # SHA-256 hash of verifier
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    # Base64url encode without trailing '='
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def create_authorization_url(redirect_uri: str, scopes: Optional[list] = None) -> Tuple[str, str]:
    """
    Creates Canva authorization redirect URL with PKCE challenge and saves state.
    Returns (authorization_url, state).
    """
    client_id, _ = get_canva_credentials()
    if not client_id:
        raise ValueError("CANVA_CLIENT_ID is not configured in environment.")

    init_token_tables()
    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    db_url = get_database_url()
    if db_url:
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO canva_pkce_states (state, code_verifier, redirect_uri) VALUES (%s, %s, %s) "
                        "ON CONFLICT (state) DO UPDATE SET code_verifier = EXCLUDED.code_verifier, redirect_uri = EXCLUDED.redirect_uri",
                        (state, verifier, redirect_uri)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist PKCE state in database: {e}")

    active_scopes = " ".join(scopes or CANVA_DEFAULT_SCOPES)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": active_scopes,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state
    }
    auth_url = f"{CANVA_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return auth_url, state


def exchange_code_for_token(code: str, state: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchanges authorization code for access and refresh tokens.
    Saves the result to PostgreSQL database table canva_oauth_tokens.
    """
    client_id, client_secret = get_canva_credentials()
    if not client_id or not client_secret:
        raise ValueError("CANVA_CLIENT_ID or CANVA_CLIENT_SECRET is missing.")

    # Retrieve verifier from database
    db_url = get_database_url()
    verifier = None
    stored_redirect_uri = redirect_uri

    if db_url:
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT code_verifier, redirect_uri FROM canva_pkce_states WHERE state = %s", (state,))
                    row = cur.fetchone()
                    if row:
                        verifier, r_uri = row
                        stored_redirect_uri = redirect_uri or r_uri
                        cur.execute("DELETE FROM canva_pkce_states WHERE state = %s", (state,))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error querying PKCE state from database: {e}")

    if not verifier:
        raise ValueError("Invalid or expired OAuth state parameter.")

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": stored_redirect_uri
    }

    req = urllib.request.Request(
        CANVA_TOKEN_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            save_tokens(data)
            logger.info("Canva access token exchanged and stored successfully.")
            return data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"Failed to exchange Canva token (HTTP {e.code}): {err_body}")
        raise ValueError(f"Canva token exchange failed (HTTP {e.code}): {err_body}")


def refresh_token(refresh_token_value: str) -> Dict[str, Any]:
    """Refreshes expired access token using refresh_token."""
    client_id, client_secret = get_canva_credentials()
    if not client_id or not client_secret:
        raise ValueError("CANVA_CLIENT_ID or CANVA_CLIENT_SECRET is missing.")

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value
    }

    req = urllib.request.Request(
        CANVA_TOKEN_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            save_tokens(data)
            logger.info("Canva access token refreshed successfully.")
            return data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"Failed to refresh Canva token (HTTP {e.code}): {err_body}")
        raise ValueError(f"Canva token refresh failed: {err_body}")


def save_tokens(token_data: Dict[str, Any]):
    """Persists tokens into PostgreSQL database table canva_oauth_tokens."""
    db_url = get_database_url()
    if not db_url:
        return

    init_token_tables()
    access_token = token_data.get("access_token")
    refresh_token_val = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 14400)
    expires_at = time.time() + float(expires_in)
    scope = token_data.get("scope", "")

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO canva_oauth_tokens (id, access_token, refresh_token, expires_at, scope, updated_at)
                    VALUES ('canva_default', %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        access_token = EXCLUDED.access_token,
                        refresh_token = COALESCE(EXCLUDED.refresh_token, canva_oauth_tokens.refresh_token),
                        expires_at = EXCLUDED.expires_at,
                        scope = COALESCE(EXCLUDED.scope, canva_oauth_tokens.scope),
                        updated_at = NOW()
                    """,
                    (access_token, refresh_token_val, expires_at, scope)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save Canva tokens to database: {e}")


def get_valid_access_token() -> Optional[str]:
    """
    Returns an active, valid Canva Bearer token.
    1. Checks direct environment override CANVA_ACCESS_TOKEN or CANVA_API_KEY.
    2. Checks PostgreSQL database table canva_oauth_tokens.
    3. Automatically refreshes token if expired.
    Returns None if no token is available or authenticated.
    """
    # 1. Environment variable override
    env_token = os.environ.get("CANVA_ACCESS_TOKEN") or os.environ.get("CANVA_API_KEY")
    if env_token and env_token.strip():
        return env_token.strip()

    # 2. Database lookup
    db_url = get_database_url()
    if not db_url:
        return None

    try:
        init_token_tables()
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT access_token, refresh_token, expires_at FROM canva_oauth_tokens WHERE id = 'canva_default'")
                row = cur.fetchone()
                if not row:
                    return None
                access_token, refresh_tok, expires_at = row
                
                # Check expiration (with 60-second safety window)
                now = time.time()
                if expires_at and now >= (float(expires_at) - 60):
                    if refresh_tok:
                        logger.info("Canva access token expired, refreshing with refresh_token...")
                        refreshed = refresh_token(refresh_tok)
                        return refreshed.get("access_token")
                    else:
                        logger.warning("Canva access token expired and no refresh_token available.")
                        return None
                return access_token
    except Exception as e:
        logger.error(f"Error checking Canva access token in database: {e}")
        return None

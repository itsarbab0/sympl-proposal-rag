"""
Sympl Solutions Proposal RAG — API Configuration

Loads environment variables, defines API metadata, authentication parameters,
and default engine providers.
"""

import os
from typing import List
from pathlib import Path


def load_environment() -> dict:
    """Reads environment variables from candidate .env files if present."""
    env = {}
    candidates = [
        Path("d:/Sympl/.env"),
        Path("d:/Sympl/sympl-proposal-rag/.env"),
        Path(".env")
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass
    return env


ENV = load_environment()


class Settings:
    """Application settings and runtime configuration."""

    API_TITLE: str = "Sympl Solutions Proposal RAG API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Production orchestration API layer for automated financial service proposal generation."

    # Runtime Environment
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", ENV.get("ENVIRONMENT", "development"))

    # Authentication & Key Rotation
    API_AUTH_ENABLED: bool = os.environ.get("API_AUTH_ENABLED", ENV.get("API_AUTH_ENABLED", "false")).lower() in ("true", "1", "yes")
    API_KEY: str = os.environ.get("API_KEY", ENV.get("API_KEY", "sympl-proposal-secret-key-2026"))
    API_KEYS: str = os.environ.get("API_KEYS", ENV.get("API_KEYS", ""))

    # Documentation visibility
    DOCS_ENABLED: bool = os.environ.get("DOCS_ENABLED", "true" if ENVIRONMENT.lower() != "production" else "false").lower() in ("true", "1", "yes")

    def get_valid_api_keys(self) -> set:
        """
        Returns set of all authorized API keys to support zero-downtime key rotation.
        In production, the hardcoded development key is excluded.
        """
        keys = set()
        is_prod = os.environ.get("ENVIRONMENT", self.ENVIRONMENT).lower() == "production"

        # Only trust the default fallback key in non-production environments
        if not is_prod:
            if self.API_KEY:
                keys.add(self.API_KEY.strip())

        env_key = os.environ.get("API_KEY")
        if env_key:
            keys.add(env_key.strip())

        all_keys_raw = os.environ.get("API_KEYS", self.API_KEYS)
        if all_keys_raw:
            for k in all_keys_raw.split(","):
                k_clean = k.strip()
                if k_clean:
                    keys.add(k_clean)
        return keys

    # Resilience & Protection
    MAX_REQUEST_SIZE_BYTES: int = 1_048_576  # 1 MB
    LLM_TIMEOUT_SECONDS: int = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
    LLM_MAX_RETRIES: int = int(os.environ.get("LLM_MAX_RETRIES", "2"))

    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", ENV.get("DATABASE_URL", ""))

    # Engine Defaults
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", ENV.get("LLM_PROVIDER", "mock"))
    RENDERER_MODE: str = os.environ.get("RENDERER_MODE", ENV.get("RENDERER_MODE", "mock"))

    # CORS
    def get_cors_origins(self) -> List[str]:
        """Returns authorized CORS origins. Restricts wildcard in production."""
        raw = os.environ.get("CORS_ORIGINS", ENV.get("CORS_ORIGINS", ""))
        if raw:
            return [orig.strip() for orig in raw.split(",") if orig.strip()]
        if os.environ.get("ENVIRONMENT", self.ENVIRONMENT).lower() == "production":
            return []  # Disallow open wildcard in production unless explicitly configured
        return ["*"]

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return self.get_cors_origins()


settings = Settings()

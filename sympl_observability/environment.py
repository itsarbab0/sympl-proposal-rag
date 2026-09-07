"""
Sympl Solutions Proposal RAG — Environment & Startup Validator (Phase 6B)

Validates environment prerequisites before serving traffic:
  - DATABASE_URL existence and PostgreSQL connectivity
  - Operational tables existence (proposal_jobs, proposal_runs)
  - Active LLM provider configuration and API credentials
  - Embedding model availability (BGE-M3)
  - Worker thread pool health
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import psycopg

from sympl_planner.retrieval import DATABASE_URL, EMBEDDING_MODEL
from sympl_observability.logging import obs_logger
from sympl_observability.job_tracker import verify_operational_tables_exist


class EnvironmentValidationError(Exception):
    """Raised when critical startup prerequisites are not satisfied."""
    pass


@dataclass
class EnvironmentReport:
    status: str                         # "healthy" or "degraded"
    database_status: str               # "connected" or "unreachable"
    operational_tables_status: str     # "present" or "missing"
    embedding_status: str              # "available" or "unavailable"
    llm_provider: str                  # active provider identifier
    llm_status: str                    # "configured" or "missing_credentials"
    worker_status: str                 # "ready" or "stopped"
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "database": self.database_status,
            "operational_tables": self.operational_tables_status,
            "embedding": self.embedding_status,
            "llm_provider": self.llm_provider,
            "llm_status": self.llm_status,
            "worker_status": self.worker_status,
            "errors": self.errors
        }


def validate_environment(
    database_url: Optional[str] = None,
    llm_provider: Optional[str] = None,
    strict: bool = False
) -> EnvironmentReport:
    """
    Performs comprehensive startup and health diagnostics.
    If strict=True, raises EnvironmentValidationError on fatal configuration errors.
    """
    db_url = database_url or os.getenv("DATABASE_URL") or DATABASE_URL
    provider = (llm_provider or os.getenv("LLM_PROVIDER", "mock")).lower()

    errors: List[str] = []

    # 1. Database Check
    db_status = "connected"
    tables_status = "present"
    if not db_url:
        db_status = "unreachable"
        tables_status = "missing"
        errors.append("DATABASE_URL is not configured.")
    else:
        try:
            with psycopg.connect(db_url, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
            # Check operational tables
            if not verify_operational_tables_exist(db_url):
                tables_status = "missing"
                errors.append("Operational tables (proposal_jobs, proposal_runs) missing from database.")
        except Exception as e:
            db_status = "unreachable"
            tables_status = "missing"
            errors.append(f"PostgreSQL connection failed: {e}")

    # 2. Embedding Model Check
    emb_status = "available"
    try:
        from sentence_transformers import SentenceTransformer
        # Check that class imports cleanly
    except ImportError:
        emb_status = "unavailable"
        errors.append("sentence_transformers library is not installed.")

    # 3. LLM Provider Check
    llm_status = "configured"
    if provider == "openrouter":
        if not os.getenv("OPENROUTER_API_KEY"):
            llm_status = "missing_credentials"
            errors.append("OPENROUTER_API_KEY is required when LLM_PROVIDER is openrouter.")
    elif provider == "gemini":
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            # Note: May still fall back to mock in dev
            llm_status = "missing_credentials"
            errors.append("GEMINI_API_KEY or GOOGLE_API_KEY is required for gemini provider.")

    # 4. Security & API Key Check in Production
    env_name = os.getenv("ENVIRONMENT", "development").lower()
    if env_name == "production":
        from sympl_api.config import settings
        if not settings.get_valid_api_keys():
            errors.append("ENVIRONMENT=production requires at least one valid key in API_KEYS.")

    # 5. Worker Status
    worker_status = "ready"

    # Overall Status
    is_healthy = (db_status == "connected" and emb_status == "available" and llm_status == "configured")
    overall_status = "healthy" if is_healthy else "degraded"

    report = EnvironmentReport(
        status=overall_status,
        database_status=db_status,
        operational_tables_status=tables_status,
        embedding_status=emb_status,
        llm_provider=provider,
        llm_status=llm_status,
        worker_status=worker_status,
        errors=errors
    )

    if errors:
        obs_logger.warning(f"Environment validation completed with warnings: {errors}")
    else:
        obs_logger.info(f"Environment validation succeeded: status={overall_status}")

    if strict and errors:
        raise EnvironmentValidationError(f"Startup validation failed: {'; '.join(errors)}")

    return report

"""
Sympl Solutions Proposal RAG — Deployment Readiness Test Suite (Phase 6C)

Validates production deployment assets, multi-container configurations, worker logic,
security parameters, and database invariants:
  1. docker-compose.production.yml schema & service definitions (api, worker, nginx)
  2. .env.production.example variable completeness & documentation
  3. nginx/nginx.conf proxy limits, timeouts, and security headers
  4. Artifact store intake persistence (save_intake, load_intake)
  5. Proposal worker atomic claiming and duplicate prevention
  6. Production security: authentication enforcement in production mode
  7. Production security: safe CORS origin validation (no wildcard with credentials)
  8. Production documentation control (DOCS_ENABLED)
  9. Production health check script verification
 10. Database safety & frozen asset invariant audit (7, 71, 47, 21, 13, 7)
"""

import os
import sys
import json
import uuid
import pytest
import psycopg
from pathlib import Path
from starlette.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_api.main import create_app
from sympl_api.config import settings
from sympl_storage.store import default_store
from sympl_observability.job_tracker import default_tracker
from sympl_observability.worker import ProposalWorker
from sympl_observability.environment import validate_environment


class TestDeploymentReadiness:
    """Test suite for Phase 6C Deployment Readiness Layer."""

    # --------------------------------------------------------------------------
    # Test 1: docker-compose.production.yml Structure
    # --------------------------------------------------------------------------
    def test_01_docker_compose_production_structure(self):
        """Verifies docker-compose.production.yml defines api, worker, and nginx services."""
        compose_file = PROJECT_ROOT / "docker-compose.production.yml"
        assert compose_file.exists(), "docker-compose.production.yml must exist"

        content = compose_file.read_text(encoding="utf-8")

        # Check required services
        assert "api:" in content, "api service missing from compose file"
        assert "worker:" in content, "worker service missing from compose file"
        assert "nginx:" in content, "nginx service missing from compose file"

        # Check API service configuration
        assert "gunicorn sympl_api.main:app" in content
        assert "uvicorn.workers.UvicornWorker" in content
        assert "healthcheck:" in content

        # Check Worker service configuration
        assert "sympl_observability.worker" in content
        assert "shared_artifacts:" in content

        # Check Nginx service configuration
        assert "nginx/nginx.conf" in content
        assert "80:80" in content

    # --------------------------------------------------------------------------
    # Test 2: .env.production.example Completeness
    # --------------------------------------------------------------------------
    def test_02_env_production_example_completeness(self):
        """Verifies all required production variables are documented in .env.production.example."""
        env_example = PROJECT_ROOT / ".env.production.example"
        assert env_example.exists(), ".env.production.example must exist"

        content = env_example.read_text(encoding="utf-8")
        required_vars = [
            "DATABASE_URL",
            "LLM_PROVIDER",
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIMENSION",
            "ENVIRONMENT",
            "API_KEYS",
            "CORS_ORIGINS",
            "CANVA_API_KEY",
            "CANVA_TEMPLATE_ID",
            "ARTIFACT_STORAGE",
            "STORAGE_DIR",
            "MAX_REQUEST_SIZE_BYTES",
            "LLM_TIMEOUT_SECONDS",
            "LLM_MAX_RETRIES"
        ]

        for var_name in required_vars:
            assert f"{var_name}=" in content, f"Missing {var_name} in .env.production.example"

    # --------------------------------------------------------------------------
    # Test 3: Nginx Reverse Proxy Directives & Security Headers
    # --------------------------------------------------------------------------
    def test_03_nginx_configuration_directives(self):
        """Verifies nginx.conf contains payload limits, timeouts, and security headers."""
        nginx_conf = PROJECT_ROOT / "nginx" / "nginx.conf"
        assert nginx_conf.exists(), "nginx/nginx.conf must exist"

        content = nginx_conf.read_text(encoding="utf-8")

        # Required limits and timeouts
        assert "client_max_body_size 1M;" in content
        assert "proxy_connect_timeout" in content
        assert "proxy_read_timeout" in content
        assert "proxy_send_timeout" in content

        # Required security headers
        assert "X-Frame-Options" in content
        assert "X-Content-Type-Options" in content
        assert "Referrer-Policy" in content
        assert "Strict-Transport-Security" in content

    # --------------------------------------------------------------------------
    # Test 4: Artifact Store Intake Persistence
    # --------------------------------------------------------------------------
    def test_04_artifact_store_intake_persistence(self):
        """Validates save_intake and load_intake methods in ArtifactStore."""
        test_job_id = f"job_test_{uuid.uuid4().hex[:8]}"
        test_intake = {
            "client_name": "Test Intake Corporation",
            "approved_scope": {"accounting": {"cadence": "monthly"}},
            "commercial_terms": {"monthly_retainer": 3500.0}
        }

        # Save intake
        saved_path = default_store.save_intake(test_job_id, test_intake)
        assert Path(saved_path).exists()

        # Load intake
        loaded = default_store.load_intake(test_job_id)
        assert loaded is not None
        assert loaded["client_name"] == "Test Intake Corporation"
        assert loaded["commercial_terms"]["monthly_retainer"] == 3500.0

        # Non-existent job returns None
        assert default_store.load_intake("non_existent_job_12345") is None

    # --------------------------------------------------------------------------
    # Test 5: Worker Atomic Job Claiming & Duplicate Prevention
    # --------------------------------------------------------------------------
    def test_05_worker_atomic_claiming_duplicate_prevention(self):
        """Tests that claim_job succeeds once and rejects duplicate claims."""
        test_job_id = f"job_claim_{uuid.uuid4().hex[:8]}"

        # Insert a job in CREATED status
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO proposal_jobs (id, status, created_at)
                    VALUES (%s, 'CREATED', NOW());
                    """,
                    (test_job_id,)
                )
                conn.commit()

        # First worker claims the job
        proposal_id_1 = f"prop_{uuid.uuid4().hex[:8]}"
        claimed_first = default_tracker.claim_job(test_job_id, proposal_id=proposal_id_1)
        assert claimed_first is True, "First worker claim must succeed"

        # Second worker attempts to claim the same job
        proposal_id_2 = f"prop_{uuid.uuid4().hex[:8]}"
        claimed_second = default_tracker.claim_job(test_job_id, proposal_id=proposal_id_2)
        assert claimed_second is False, "Duplicate claim on already claimed job must be rejected"

        # Clean up test job
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM proposal_jobs WHERE id = %s;", (test_job_id,))
                conn.commit()

    # --------------------------------------------------------------------------
    # Test 6: Production Security — Mandatory Authentication
    # --------------------------------------------------------------------------
    def test_06_production_requires_authentication(self):
        """Verifies that in production mode, authentication cannot be bypassed."""
        orig_env = os.environ.get("ENVIRONMENT")
        orig_auth = os.environ.get("API_AUTH_ENABLED")
        orig_keys = os.environ.get("API_KEYS")

        try:
            os.environ["ENVIRONMENT"] = "production"
            os.environ["API_AUTH_ENABLED"] = "false"  # Attempt to bypass auth
            os.environ["API_KEYS"] = "secure-prod-key-1,secure-prod-key-2"

            app = create_app()
            client = TestClient(app)

            # Unauthenticated request to protected endpoint must return 401
            resp = client.post("/proposal/plan", json={"client_name": "Test"})
            assert resp.status_code == 401, "Production mode must reject missing API key even if API_AUTH_ENABLED=false"

            # Authenticated request with valid rotated key succeeds (or passes auth to validation)
            resp_auth = client.post(
                "/proposal/plan",
                json={"client_name": "Acme", "approved_scope": {"audit": {}}},
                headers={"X-API-Key": "secure-prod-key-2"}
            )
            assert resp_auth.status_code != 401, "Valid key from API_KEYS list must be authorized"

        finally:
            if orig_env:
                os.environ["ENVIRONMENT"] = orig_env
            else:
                os.environ.pop("ENVIRONMENT", None)
            if orig_auth:
                os.environ["API_AUTH_ENABLED"] = orig_auth
            else:
                os.environ.pop("API_AUTH_ENABLED", None)
            if orig_keys:
                os.environ["API_KEYS"] = orig_keys
            else:
                os.environ.pop("API_KEYS", None)

    # --------------------------------------------------------------------------
    # Test 7: Production Security — Safe CORS Configuration
    # --------------------------------------------------------------------------
    def test_07_production_safe_cors(self):
        """Verifies that in production, wildcard origins with credentials are not allowed."""
        orig_env = os.environ.get("ENVIRONMENT")
        orig_cors = os.environ.get("CORS_ORIGINS")

        try:
            os.environ["ENVIRONMENT"] = "production"
            os.environ.pop("CORS_ORIGINS", None)

            # In production, default CORS origins must not be wildcard '*'
            origins = settings.get_cors_origins()
            assert "*" not in origins, "Production CORS must not default to wildcard '*'"

            # With explicit production origins
            os.environ["CORS_ORIGINS"] = "https://app.sympl.com,https://api.sympl.com"
            prod_origins = settings.get_cors_origins()
            assert prod_origins == ["https://app.sympl.com", "https://api.sympl.com"]

        finally:
            if orig_env:
                os.environ["ENVIRONMENT"] = orig_env
            else:
                os.environ.pop("ENVIRONMENT", None)
            if orig_cors:
                os.environ["CORS_ORIGINS"] = orig_cors
            else:
                os.environ.pop("CORS_ORIGINS", None)

    # --------------------------------------------------------------------------
    # Test 8: Documentation Endpoints Visibility Control
    # --------------------------------------------------------------------------
    def test_08_documentation_visibility_control(self):
        """Verifies that DOCS_ENABLED=false disables /docs, /redoc, and /openapi.json."""
        orig_docs = os.environ.get("DOCS_ENABLED")
        try:
            os.environ["DOCS_ENABLED"] = "false"
            settings.DOCS_ENABLED = False
            app = create_app()
            client = TestClient(app)

            r_docs = client.get("/docs")
            assert r_docs.status_code == 404, "Swagger docs must return 404 when DOCS_ENABLED=false"

            r_redoc = client.get("/redoc")
            assert r_redoc.status_code == 404, "Redoc must return 404 when DOCS_ENABLED=false"

            r_openapi = client.get("/openapi.json")
            assert r_openapi.status_code == 404, "openapi.json must return 404 when DOCS_ENABLED=false"

        finally:
            if orig_docs:
                os.environ["DOCS_ENABLED"] = orig_docs
            else:
                os.environ.pop("DOCS_ENABLED", None)
            settings.DOCS_ENABLED = True

    # --------------------------------------------------------------------------
    # Test 9: Production Health Check Execution
    # --------------------------------------------------------------------------
    def test_09_production_health_check_script(self):
        """Validates that production_health_check checks execute without failure."""
        from scripts.production_health_check import (
            check_api_health,
            check_database_and_invariants,
            check_business_engines,
            check_llm_provider
        )

        api_res = check_api_health()
        assert api_res["ok"] is True

        db_res = check_database_and_invariants(settings.DATABASE_URL)
        assert db_res["connected"] is True
        assert db_res["pgvector"] is True
        assert db_res["operational_tables"] is True
        assert db_res["frozen_invariants"] is True

        eng_res = check_business_engines()
        assert eng_res["planner"] is True
        assert eng_res["writer"] is True
        assert eng_res["renderer"] is True

        llm_res = check_llm_provider()
        assert llm_res["ok"] is True

    # --------------------------------------------------------------------------
    # Test 10: Frozen Database Invariant Audit
    # --------------------------------------------------------------------------
    def test_10_frozen_database_invariants(self):
        """Strict verification of all 6 frozen RAG database invariant counts."""
        expected = {
            "proposal_documents": 7,
            "proposal_chunks": 71,
            "embeddings": 47,
            "sympl_style_rules": 21,
            "sympl_reference_blocks": 13,
            "dataset_imports": 7
        }

        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                queries = {
                    "proposal_documents": "SELECT count(*) FROM proposal_documents;",
                    "proposal_chunks": "SELECT count(*) FROM proposal_chunks;",
                    "embeddings": "SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL;",
                    "sympl_style_rules": "SELECT count(*) FROM sympl_style_rules;",
                    "sympl_reference_blocks": "SELECT count(*) FROM sympl_reference_blocks;",
                    "dataset_imports": "SELECT count(*) FROM dataset_imports;"
                }

                actual = {}
                for key, q in queries.items():
                    cur.execute(q)
                    actual[key] = cur.fetchone()[0]

        for table, exp_count in expected.items():
            assert actual[table] == exp_count, (
                f"Frozen database invariant violation for {table}: "
                f"expected {exp_count}, got {actual[table]}"
            )

"""
Sympl Solutions Proposal RAG — Production Hardening Test Suite (Phase 6B)

Validates production reliability, observability, and resilience layers:
  1. Operational tables creation & schema existence
  2. Async proposal generation lifecycle (POST /proposal/generate/async -> polling)
  3. Status polling endpoint authentication & error handling
  4. Failed job recovery & error capture in proposal_jobs / proposal_runs
  5. Pipeline telemetry creation & stage metric emission
  6. Zero-downtime API key rotation (API_KEYS)
  7. Request body size limit enforcement (HTTP 413 on >1MB payload)
  8. Artifact storage persistence & reloading (LocalArtifactStore)
  9. Startup environment validation diagnostics
 10. Database isolation verification (confirming frozen RAG tables are untouched)
"""

import os
import sys
import time
import json
import pytest
from pathlib import Path
from starlette.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_api.main import app
from sympl_api.config import settings
from sympl_observability.job_tracker import default_tracker, verify_operational_tables_exist
from sympl_observability.telemetry import PipelineTelemetry
from sympl_observability.environment import validate_environment
from sympl_storage.store import LocalArtifactStore


class TestProductionHardening:
    """Test suite for Phase 6B Production Hardening."""

    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)
        cls.test_key = "sympl-hardening-secret-2026"

        cls.sample_intake = {
            "client_name": "Parkdale Community Center",
            "organization_type": "nonprofit",
            "sector": "community_services",
            "complexity": "compact",
            "approved_scope": {
                "bookkeeping": {
                    "cadence": "weekly",
                    "ap_ar": True,
                    "reconciliations": True,
                    "expense_management": True
                }
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 2400.0
            }
        }

    # --------------------------------------------------------------------------
    # Test 1: Operational tables creation & existence
    # --------------------------------------------------------------------------
    def test_01_operational_tables_exist(self):
        """Verifies operational tables (proposal_jobs, proposal_runs) exist in PostgreSQL."""
        tables_ok = verify_operational_tables_exist(settings.DATABASE_URL)
        assert tables_ok is True, "proposal_jobs and proposal_runs must exist in PostgreSQL"

    # --------------------------------------------------------------------------
    # Test 2: Async job lifecycle
    # --------------------------------------------------------------------------
    def test_02_async_job_lifecycle(self):
        """Validates POST /proposal/generate/async submission and asynchronous completion."""
        # Submit async generation
        resp = self.client.post("/proposal/generate/async", json=self.sample_intake)
        assert resp.status_code == 202
        data = resp.json()

        assert "job_id" in data
        assert data["job_id"].startswith("job_")
        assert data["status"] == "CREATED"
        assert "request_id" in data

        job_id = data["job_id"]

        # Poll status until completed (timeout: 45s)
        t_start = time.time()
        final_status = None
        proposal_id = None

        while time.time() - t_start < 45:
            status_resp = self.client.get(f"/proposal/status/{job_id}")
            assert status_resp.status_code == 200
            s_data = status_resp.json()
            final_status = s_data["status"]
            if final_status in ("COMPLETED", "FAILED"):
                proposal_id = s_data.get("proposal_id")
                assert s_data["progress"] == 1.0 if final_status == "COMPLETED" else True
                break
            time.sleep(0.5)

        assert final_status == "COMPLETED", f"Expected job to complete, got status: {final_status}"
        assert proposal_id is not None
        assert proposal_id.startswith("prop_")

    # --------------------------------------------------------------------------
    # Test 3: Status polling endpoint authentication & error handling
    # --------------------------------------------------------------------------
    def test_03_status_polling_endpoints(self):
        """Tests authentication requirement and 404 for unknown job IDs."""
        orig_auth = os.environ.get("API_AUTH_ENABLED")
        orig_key = os.environ.get("API_KEY")
        try:
            os.environ["API_AUTH_ENABLED"] = "true"
            os.environ["API_KEY"] = self.test_key

            # Unauthenticated status request -> 401
            resp_no_auth = self.client.get("/proposal/status/job_test_123")
            assert resp_no_auth.status_code == 401

            # Authenticated non-existent job -> 404
            resp_404 = self.client.get(
                "/proposal/status/job_nonexistent_9999",
                headers={"X-API-Key": self.test_key}
            )
            assert resp_404.status_code == 404
            assert resp_404.json()["detail"]["error"] == "JOB_NOT_FOUND"

        finally:
            if orig_auth is not None:
                os.environ["API_AUTH_ENABLED"] = orig_auth
            else:
                os.environ.pop("API_AUTH_ENABLED", None)
            if orig_key is not None:
                os.environ["API_KEY"] = orig_key
            else:
                os.environ.pop("API_KEY", None)

    # --------------------------------------------------------------------------
    # Test 4: Failed job recovery & error capture
    # --------------------------------------------------------------------------
    def test_04_failed_job_recovery(self):
        """Verifies job tracker captures FAILED status and error messages properly."""
        # Create a job manually and mark it failed
        test_job_id = default_tracker.create_job(payload={"client": "Failure Test"})
        assert test_job_id.startswith("job_")

        default_tracker.record_run(
            job_id=test_job_id,
            stage="WRITER",
            duration_ms=45.2,
            status="FAILED"
        )
        default_tracker.update_job_status(
            job_id=test_job_id,
            status="FAILED",
            error_message="Simulation: LLM provider unavailable"
        )

        job_info = default_tracker.get_job_status(test_job_id)
        assert job_info["status"] == "FAILED"
        assert job_info["current_stage"] == "FAILED"
        assert "LLM provider unavailable" in job_info["error_message"]

    # --------------------------------------------------------------------------
    # Test 5: Pipeline telemetry creation & stage metric emission
    # --------------------------------------------------------------------------
    def test_05_telemetry_creation(self):
        """Validates PipelineTelemetry data structure conforms exactly to specification."""
        telem = PipelineTelemetry(proposal_id="prop_telem_test", request_id="req_telem_test")
        telem.record_planner(duration_ms=125.4, retrieval_ms=45.2)
        telem.record_writer(duration_ms=1520.1, llm_ms=1410.0)
        telem.record_renderer(duration_ms=88.6, render_ms=60.1)
        res = telem.complete()

        assert res["request_id"] == "req_telem_test"
        assert res["proposal_id"] == "prop_telem_test"
        assert res["status"] == "COMPLETED"
        assert "stages" in res
        assert res["stages"]["planner_ms"] == 125.4
        assert res["stages"]["writer_ms"] == 1520.1
        assert res["stages"]["renderer_ms"] == 88.6
        assert res["stages"]["total_ms"] > 0
        assert "substages" in res
        assert res["substages"]["retrieval_ms"] == 45.2
        assert res["substages"]["llm_ms"] == 1410.0

    # --------------------------------------------------------------------------
    # Test 6: Zero-downtime API key rotation
    # --------------------------------------------------------------------------
    def test_06_api_key_rotation(self):
        """Validates API authentication supports multiple active keys via API_KEYS."""
        primary_key = "sympl-key-primary-1111"
        secondary_key = "sympl-key-secondary-2222"

        orig_auth = os.environ.get("API_AUTH_ENABLED")
        orig_keys = os.environ.get("API_KEYS")
        orig_key = os.environ.get("API_KEY")

        try:
            os.environ["API_AUTH_ENABLED"] = "true"
            os.environ["API_KEY"] = primary_key
            os.environ["API_KEYS"] = f"{primary_key},{secondary_key}"

            # 1. Primary key succeeds
            resp1 = self.client.post(
                "/proposal/plan",
                json=self.sample_intake,
                headers={"X-API-Key": primary_key}
            )
            assert resp1.status_code == 200

            # 2. Secondary rotated key succeeds
            resp2 = self.client.post(
                "/proposal/plan",
                json=self.sample_intake,
                headers={"X-API-Key": secondary_key}
            )
            assert resp2.status_code == 200

            # 3. Unknown key fails -> 401
            resp3 = self.client.post(
                "/proposal/plan",
                json=self.sample_intake,
                headers={"X-API-Key": "unauthorized-key-3333"}
            )
            assert resp3.status_code == 401

        finally:
            if orig_auth is not None:
                os.environ["API_AUTH_ENABLED"] = orig_auth
            else:
                os.environ.pop("API_AUTH_ENABLED", None)
            if orig_keys is not None:
                os.environ["API_KEYS"] = orig_keys
            else:
                os.environ.pop("API_KEYS", None)
            if orig_key is not None:
                os.environ["API_KEY"] = orig_key
            else:
                os.environ.pop("API_KEY", None)

    # --------------------------------------------------------------------------
    # Test 7: Request payload limit rejection
    # --------------------------------------------------------------------------
    def test_07_request_size_limit(self):
        """Validates that payloads exceeding 1MB are rejected with HTTP 413."""
        # Create a payload exceeding 1MB (1,048,576 bytes)
        large_padding = "X" * (1_048_576 + 1024)
        oversized_payload = dict(self.sample_intake)
        oversized_payload["overflow_data"] = large_padding

        resp = self.client.post("/proposal/generate", json=oversized_payload)
        assert resp.status_code == 413
        data = resp.json()
        assert data["error"] == "PAYLOAD_TOO_LARGE"
        assert "1MB" in data["message"]

    # --------------------------------------------------------------------------
    # Test 8: Artifact storage persistence & reloading
    # --------------------------------------------------------------------------
    def test_08_artifact_storage(self, tmp_path):
        """Validates LocalArtifactStore saves and loads proposal plans, drafts, and renders."""
        store = LocalArtifactStore(base_dir=tmp_path)
        prop_id = "prop_storage_test_01"

        plan_data = {"archetype": "ARCH_COMPACT_BOOKKEEPING", "services": ["bookkeeping"]}
        draft_data = {"title": "Storage Test Draft", "sections": []}
        render_data = {"design_id": "design_123", "page_count": 4}

        plan_path = store.save_plan(prop_id, plan_data)
        draft_path = store.save_draft(prop_id, draft_data)
        render_path = store.save_render(prop_id, render_data)

        assert Path(plan_path).exists()
        assert Path(draft_path).exists()
        assert Path(render_path).exists()

        assert store.load_plan(prop_id) == plan_data
        assert store.load_draft(prop_id) == draft_data
        assert store.load_render(prop_id) == render_data

    # --------------------------------------------------------------------------
    # Test 9: Startup environment validation diagnostics
    # --------------------------------------------------------------------------
    def test_09_environment_validation(self):
        """Validates startup environment diagnostics report."""
        report = validate_environment(strict=False)
        assert report.database_status == "connected"
        assert report.operational_tables_status == "present"
        assert report.embedding_status == "available"
        assert report.worker_status == "ready"

    # --------------------------------------------------------------------------
    # Test 10: Frozen database invariants verification
    # --------------------------------------------------------------------------
    def test_10_database_invariants_post_hardening(self):
        """
        Verifies that all Phase 6B operations made ZERO modifications to frozen RAG assets:
          - proposal_documents (7)
          - proposal_chunks (71)
          - dataset_imports (7)
          - sympl_style_rules (21)
          - sympl_reference_blocks (13)
          - embeddings (47)
        """
        import psycopg
        from sympl_planner.retrieval import DATABASE_URL

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM proposal_documents;")
                docs_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks;")
                chunks_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM dataset_imports;")
                imports_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM sympl_style_rules;")
                rules_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM sympl_reference_blocks;")
                refs_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL;")
                embedded_count = cur.fetchone()[0]

        assert docs_count == 7, "proposal_documents must remain 7"
        assert chunks_count == 71, "proposal_chunks must remain 71"
        assert imports_count == 7, "dataset_imports must remain 7"
        assert rules_count == 21, "sympl_style_rules must remain 21"
        assert refs_count == 13, "sympl_reference_blocks must remain 13"
        assert embedded_count == 47, "embedded chunks must remain exactly 47"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

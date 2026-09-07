"""
Sympl Solutions Proposal RAG — API Integration Test Suite (Phase 6A)

Tests the production FastAPI orchestration layer:
  1. Health endpoint (service liveness, database status, engine availability).
  2. API authentication (enforcing X-API-Key when API_AUTH_ENABLED=true).
  3. Full proposal generation pipeline (Intake -> Planner -> Writer -> Renderer).
  4. Planner-only endpoint (/proposal/plan).
  5. Writer-only endpoint (/proposal/write).
  6. Renderer-only endpoint (/proposal/render).
  7. Invalid input handling (empty payloads, missing fields, firewall violations).
  8. Database invariant verification (ensuring 0 database mutations).
"""

import os
import sys
import json
import copy
import pytest
from pathlib import Path
from starlette.testclient import TestClient

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_api.main import app
from sympl_api.config import settings


class TestProposalAPI:
    """Test suite for Phase 6A Sympl Proposal Production API Layer."""

    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

        # Standard test intake payload
        cls.sample_intake = {
            "client_name": "High Park Community Hub",
            "organization_type": "nonprofit",
            "sector": "community_services",
            "current_systems": ["QuickBooks Online"],
            "engagement_type": "recurring",
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
                "monthly_retainer": 2200.0,
                "include_backlog_exclusion": True
            },
            "preferences": {
                "include_why_us": False
            }
        }

    # --------------------------------------------------------------------------
    # Test 1: Health endpoint
    # --------------------------------------------------------------------------
    def test_01_health_endpoint(self):
        """Validates GET /health returns service status, DB connectivity, and engine availability."""
        resp = self.client.get("/health")
        assert resp.status_code == 200
        data = resp.json()

        assert "status" in data
        assert data["status"] in ("healthy", "degraded")
        assert data["version"] in ("1.0", "1.0.0")
        assert data["database"] in ("connected", "unreachable")
        assert data["planner"] == "available"
        assert data["writer"] == "available"
        assert data["renderer"] == "available"
        assert "llm_provider" in data

        # Verify request_id header injection
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req_")

    # --------------------------------------------------------------------------
    # Test 2: API authentication
    # --------------------------------------------------------------------------
    def test_02_api_authentication(self):
        """Validates API key enforcement when enabled and transparency when disabled."""
        test_key = "sympl-test-auth-key-12345"

        # 1. When authentication is enabled
        orig_auth_env = os.environ.get("API_AUTH_ENABLED")
        orig_key_env = os.environ.get("API_KEY")
        try:
            os.environ["API_AUTH_ENABLED"] = "true"
            os.environ["API_KEY"] = test_key

            # Request without X-API-Key header -> 401 Unauthorized
            resp_missing = self.client.post("/proposal/plan", json=self.sample_intake)
            assert resp_missing.status_code == 401
            assert resp_missing.json()["detail"]["error"] == "UNAUTHORIZED"

            # Request with invalid X-API-Key header -> 401 Unauthorized
            resp_invalid = self.client.post(
                "/proposal/plan",
                json=self.sample_intake,
                headers={"X-API-Key": "wrong-secret-key"}
            )
            assert resp_invalid.status_code == 401
            assert resp_invalid.json()["detail"]["error"] == "UNAUTHORIZED"

            # Request with valid X-API-Key header -> 200 OK
            resp_valid = self.client.post(
                "/proposal/plan",
                json=self.sample_intake,
                headers={"X-API-Key": test_key}
            )
            assert resp_valid.status_code == 200

        finally:
            # Restore environment
            if orig_auth_env is not None:
                os.environ["API_AUTH_ENABLED"] = orig_auth_env
            else:
                os.environ.pop("API_AUTH_ENABLED", None)

            if orig_key_env is not None:
                os.environ["API_KEY"] = orig_key_env
            else:
                os.environ.pop("API_KEY", None)

        # 2. When authentication is disabled (local dev mode)
        resp_dev = self.client.post("/proposal/plan", json=self.sample_intake)
        assert resp_dev.status_code == 200

    # --------------------------------------------------------------------------
    # Test 3: Full generation pipeline
    # --------------------------------------------------------------------------
    def test_03_full_generation_pipeline(self):
        """Validates POST /proposal/generate runs Planner -> Writer -> Renderer and returns complete package."""
        resp = self.client.post("/proposal/generate", json=self.sample_intake)
        assert resp.status_code == 200
        data = resp.json()

        assert "proposal_id" in data and data["proposal_id"].startswith("prop_")
        assert "request_id" in data and data["request_id"].startswith("req_")
        assert data["status"] == "COMPLETED"

        # Plan structure check
        assert "plan" in data
        assert data["plan"]["selected_archetype"] == "ARCH_COMPACT_BOOKKEEPING"

        # Draft structure check
        assert "draft" in data
        assert "High Park Community Hub" in data["draft"]["title"]
        assert len(data["draft"]["sections"]) >= 1

        # Rendered output check
        assert "rendered_output" in data
        assert data["rendered_output"]["page_count"] >= 4
        assert "design_id" in data["rendered_output"]

        # Execution timing metadata check
        meta = data["execution_metadata"]
        assert "planner_time_ms" in meta and meta["planner_time_ms"] > 0
        assert "writer_time_ms" in meta and meta["writer_time_ms"] > 0
        assert "renderer_time_ms" in meta and meta["renderer_time_ms"] > 0
        assert "total_time_ms" in meta and meta["total_time_ms"] > 0

    # --------------------------------------------------------------------------
    # Test 4: Planner endpoint
    # --------------------------------------------------------------------------
    def test_04_planner_endpoint(self):
        """Validates POST /proposal/plan runs only the planner and outputs proposal_plan."""
        resp = self.client.post("/proposal/plan", json=self.sample_intake)
        assert resp.status_code == 200
        plan = resp.json()

        assert "selected_archetype" in plan
        assert "sections" in plan
        assert "approved_scope" in plan
        assert "reference_blocks" in plan
        assert "pricing" in plan

        # Writer scope firewall check: must not contain requested_scope
        assert "requested_scope" not in plan
        assert "unapproved_requested_scope" not in plan

    # --------------------------------------------------------------------------
    # Test 5: Writer endpoint
    # --------------------------------------------------------------------------
    def test_05_writer_endpoint(self):
        """Validates POST /proposal/write runs only the writer on proposal_plan."""
        # First obtain a plan
        plan_resp = self.client.post("/proposal/plan", json=self.sample_intake)
        plan_data = plan_resp.json()

        # Call writer
        write_resp = self.client.post("/proposal/write", json=plan_data)
        assert write_resp.status_code == 200
        draft = write_resp.json()

        assert "title" in draft
        assert "executive_summary" in draft
        assert "sections" in draft
        assert "pricing" in draft
        assert "validation_metadata" in draft
        assert draft["validation_metadata"]["passed"] is True

    # --------------------------------------------------------------------------
    # Test 6: Renderer endpoint
    # --------------------------------------------------------------------------
    def test_06_renderer_endpoint(self):
        """Validates POST /proposal/render runs only the renderer on proposal_draft."""
        # Use existing canonical proposal_draft.json
        with open("proposal_draft.json", "r", encoding="utf-8") as f:
            draft_data = json.load(f)

        resp = self.client.post("/proposal/render", json=draft_data)
        assert resp.status_code == 200
        rendered = resp.json()

        assert "design_id" in rendered
        assert "page_count" in rendered
        assert "pages" in rendered
        assert "export_status" in rendered
        assert rendered["export_status"] in ("EXPORTED", "POPULATED")
        assert len(rendered["pages"]) == rendered["page_count"]

    # --------------------------------------------------------------------------
    # Test 7: Invalid input handling
    # --------------------------------------------------------------------------
    def test_07_invalid_input_handling(self):
        """Validates structured rejection of empty, malformed, or rule-violating inputs."""
        # 1. Empty intake payload -> 400 Bad Request
        resp_empty = self.client.post("/proposal/generate", json={})
        assert resp_empty.status_code == 400
        assert resp_empty.json()["error"] == "INVALID_INTAKE"
        assert "request_id" in resp_empty.json()

        # 2. Intake missing client name -> 400 Bad Request
        resp_no_name = self.client.post("/proposal/plan", json={"sector": "arts_culture"})
        assert resp_no_name.status_code == 400
        assert resp_no_name.json()["error"] == "INVALID_INTAKE"

        # 3. Writer rejects unapproved scope in plan (ScopeFirewallError) -> 400 Bad Request
        dirty_plan = {
            "client_context": {"name": "Test Client"},
            "approved_scope": {"bookkeeping": {"cadence": "weekly"}},
            "requested_scope": {"payroll": {"headcount": 5}},  # FORBIDDEN
            "sections": []
        }
        resp_firewall = self.client.post("/proposal/write", json=dirty_plan)
        assert resp_firewall.status_code == 400
        assert "SCOPEFIREWALLERROR" in resp_firewall.json()["error"]

        # 4. Renderer rejects draft missing required fields (InvalidDraftError) -> 400 Bad Request
        bad_draft = {"title": "Incomplete Draft"}
        resp_renderer_bad = self.client.post("/proposal/render", json=bad_draft)
        assert resp_renderer_bad.status_code == 400
        assert "INVALIDDRAFTERROR" in resp_renderer_bad.json()["error"]

    # --------------------------------------------------------------------------
    # Test 8: Scope firewall - APPROVAL_REQUIRED when approved_scope missing
    # --------------------------------------------------------------------------
    def test_08_scope_firewall_approval_required(self):
        """
        Validates rejection when requested_scope is provided without approved_scope.
        Must return HTTP 400 with error 'APPROVAL_REQUIRED'.
        """
        payload = {
            "client_name": "Unapproved Scope Client",
            "organization_type": "nonprofit",
            "requested_scope": {
                "payroll": {
                    "headcount": 10,
                    "remittances": True
                }
            }
        }
        # Test on /proposal/generate
        resp_gen = self.client.post("/proposal/generate", json=payload)
        assert resp_gen.status_code == 400
        data_gen = resp_gen.json()
        assert data_gen["error"] == "APPROVAL_REQUIRED"
        assert data_gen["message"] == "approved_scope is required before proposal generation"
        assert "request_id" in data_gen

        # Test on /proposal/plan
        resp_plan = self.client.post("/proposal/plan", json=payload)
        assert resp_plan.status_code == 400
        data_plan = resp_plan.json()
        assert data_plan["error"] == "APPROVAL_REQUIRED"
        assert data_plan["message"] == "approved_scope is required before proposal generation"

    # --------------------------------------------------------------------------
    # Test 9: Scope firewall - EMPTY_APPROVED_SCOPE when approved_scope is empty
    # --------------------------------------------------------------------------
    def test_09_scope_firewall_empty_approved_scope(self):
        """
        Validates rejection when approved_scope is provided but empty.
        Must return HTTP 400 with error 'EMPTY_APPROVED_SCOPE'.
        """
        payload = {
            "client_name": "Empty Scope Client",
            "organization_type": "nonprofit",
            "approved_scope": {}
        }
        # Test on /proposal/generate
        resp_gen = self.client.post("/proposal/generate", json=payload)
        assert resp_gen.status_code == 400
        data_gen = resp_gen.json()
        assert data_gen["error"] == "EMPTY_APPROVED_SCOPE"
        assert "request_id" in data_gen

        # Test on /proposal/plan
        resp_plan = self.client.post("/proposal/plan", json=payload)
        assert resp_plan.status_code == 400
        data_plan = resp_plan.json()
        assert data_plan["error"] == "EMPTY_APPROVED_SCOPE"

    # --------------------------------------------------------------------------
    # Test 10: Scope firewall - Only approved_scope reaches planner
    # --------------------------------------------------------------------------
    def test_10_scope_firewall_approved_reaches_planner_requested_isolated(self):
        """
        Validates that when both requested_scope and approved_scope are provided,
        ONLY approved_scope reaches the planner and influences archetype / sections.
        requested_scope does not leak into archetype selection, sections, or writer input.
        """
        payload = {
            "client_name": "Scoped Harmony Org",
            "organization_type": "nonprofit",
            "complexity": "compact",
            "requested_scope": {
                "payroll": {
                    "headcount": 25,
                    "remittances": True
                },
                "digital_transformation": {
                    "system_migrations": ["NetSuite", "Workday"]
                }
            },
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
                "monthly_retainer": 1800.0
            }
        }

        # 1. Execute planner endpoint
        resp = self.client.post("/proposal/plan", json=payload)
        assert resp.status_code == 200
        plan = resp.json()

        # Archetype MUST be derived exclusively from approved_scope (bookkeeping -> ARCH_COMPACT_BOOKKEEPING)
        assert plan["selected_archetype"] == "ARCH_COMPACT_BOOKKEEPING"

        # Approved scope in plan must contain ONLY approved items
        assert "bookkeeping" in plan["approved_scope"]
        assert "payroll" not in plan["approved_scope"]
        assert "digital_transformation" not in plan["approved_scope"]

        # Writer scope firewall checks: requested_scope must be completely absent from plan output
        assert "requested_scope" not in plan
        assert "unapproved_requested_scope" not in plan

        # Sections must only reflect approved bookkeeping scope
        section_ids = [s["section_id"] for s in plan["sections"]]
        for s_id in section_ids:
            assert "payroll" not in s_id.lower()
            assert "transformation" not in s_id.lower()

        # 2. Execute full generate pipeline and verify writer/renderer succeed without leakage
        resp_gen = self.client.post("/proposal/generate", json=payload)
        assert resp_gen.status_code == 200
        gen_data = resp_gen.json()
        assert gen_data["status"] == "COMPLETED"
        assert gen_data["plan"]["selected_archetype"] == "ARCH_COMPACT_BOOKKEEPING"
        assert gen_data["draft"]["validation_metadata"]["passed"] is True

    # --------------------------------------------------------------------------
    # Test 11: Database invariant verification
    # --------------------------------------------------------------------------
    def test_11_database_invariants_post_api(self):
        """
        Verifies that running all API endpoints made ZERO modifications to:
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

                cur.execute("SELECT count(*) FROM proposal_chunks WHERE retrieval_enabled = false AND embedding IS NOT NULL;")
                unsafe_embedded = cur.fetchone()[0]

        assert docs_count == 7, "proposal_documents must remain 7"
        assert chunks_count == 71, "proposal_chunks must remain 71"
        assert imports_count == 7, "dataset_imports must remain 7"
        assert rules_count == 21, "sympl_style_rules must remain 21"
        assert refs_count == 13, "sympl_reference_blocks must remain 13"
        assert embedded_count == 47, "embedded chunks must remain exactly 47"
        assert unsafe_embedded == 0, "unsafe embedded must remain 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

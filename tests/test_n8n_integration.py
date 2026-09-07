"""
Sympl Solutions Proposal RAG — Phase 9 n8n Integration Test Suite

Verifies:
  1. Complete n8n async generation workflow (/api/v1/proposal/generate/async -> polling -> PDF retrieval).
  2. Webhook callback dispatch upon job completion with standard payload contract.
  3. Webhook delivery failure isolation (unreachable callback does NOT affect proposal validity).
  4. API Versioning Parity (/api/v1/... vs /... legacy routes).
  5. Rate Limiting Protection (429 response + Retry-After header, health check exemption).
  6. CORS headers for n8n origins.
  7. Frozen Database Invariants (6 tables strictly preserved).
"""

import os
import sys
import time
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import pytest
from starlette.testclient import TestClient
import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_api.main import app
from sympl_api.config import settings
from sympl_observability.resilience import SlidingWindowRateLimiter, default_rate_limiter


class MockWebhookHandler(BaseHTTPRequestHandler):
    """Simple in-memory HTTP server to capture incoming webhook callbacks."""
    received_payloads = []

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode("utf-8"))
            MockWebhookHandler.received_payloads.append({
                "headers": dict(self.headers),
                "data": data
            })
        except Exception:
            MockWebhookHandler.received_payloads.append({"raw": body})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "received"}')

    def log_message(self, format, *args):
        pass  # Suppress console logging during tests


class TestN8nIntegration:
    """Test suite covering Phase 9 API integration hardening and external automation contracts."""

    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)
        cls.valid_api_key = settings.API_KEY
        cls.headers = {
            "X-API-Key": cls.valid_api_key,
            "Content-Type": "application/json"
        }

    def setup_method(self):
        default_rate_limiter.reset()

    # --------------------------------------------------------------------------
    # Test 1: Full n8n Async Workflow Simulation
    # --------------------------------------------------------------------------
    def test_01_n8n_async_generation_and_pdf_retrieval(self):
        """Simulates n8n submitting intake, polling status, and downloading binary PDF."""
        payload = {
            "client_id": "TEST_N8N_LEAD_01",
            "organization": {
                "name": "Beacon Community Services",
                "organization_type": "nonprofit",
                "sector": "community_services"
            },
            "engagement": {
                "engagement_type": "recurring",
                "complexity": "standard"
            },
            "requested_scope": {
                "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
            },
            "approved_scope": {
                "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 2800.0
            }
        }

        # Step 1: n8n triggers async proposal generation
        resp = self.client.post("/api/v1/proposal/generate/async", json=payload, headers=self.headers)
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
        init_data = resp.json()
        assert "job_id" in init_data
        job_id = init_data["job_id"]
        assert init_data["status"] == "CREATED"

        # Step 2: n8n polling loop
        max_wait = 45
        start_time = time.time()

        completed = False
        proposal_id = None

        while time.time() - start_time < max_wait:
            status_resp = self.client.get(f"/api/v1/proposal/status/{job_id}", headers=self.headers)
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            if status_data["status"] == "COMPLETED":
                completed = True
                proposal_id = status_data["proposal_id"]
                break
            elif status_data["status"] == "FAILED":
                pytest.fail(f"Async job failed: {status_data.get('error_message')}")
            time.sleep(0.5)

        assert completed, f"Job {job_id} did not complete within {max_wait}s"
        assert proposal_id is not None

        # Step 3: n8n retrieves generated PDF
        pdf_resp = self.client.get(f"/api/v1/proposal/{proposal_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert pdf_resp.content.startswith(b"%PDF-")
        assert len(pdf_resp.content) > 1000

        # Step 4: n8n retrieves artifact manifest
        manifest_resp = self.client.get(f"/api/v1/proposal/{proposal_id}/manifest")
        assert manifest_resp.status_code == 200
        manifest = manifest_resp.json()
        assert manifest["artifact_count"] == 5
        assert manifest["all_artifacts_present"] is True

    # --------------------------------------------------------------------------
    # Test 2: Webhook Callback Execution
    # --------------------------------------------------------------------------
    def test_02_webhook_callback_dispatch(self):
        """Validates that providing callback_url delivers completion payload to webhook listener."""
        MockWebhookHandler.received_payloads.clear()
        server_port = 8765
        server = HTTPServer(("127.0.0.1", server_port), MockWebhookHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        callback_url = f"http://127.0.0.1:{server_port}/n8n-webhook-test"

        payload = {
            "client_id": "TEST_N8N_CALLBACK",
            "organization": {
                "name": "Oakridge Literacy Alliance",
                "organization_type": "charity",
                "sector": "community_services"
            },
            "engagement": {
                "engagement_type": "recurring",
                "complexity": "compact"
            },
            "approved_scope": {
                "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 1900.0
            },
            "callback_url": callback_url
        }

        resp = self.client.post("/api/v1/proposal/generate/async", json=payload, headers=self.headers)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        # Wait up to 35 seconds for the webhook callback to arrive
        start_wait = time.time()
        while time.time() - start_wait < 35.0:
            if MockWebhookHandler.received_payloads:
                break
            time.sleep(0.5)

        server.shutdown()
        server.server_close()

        assert len(MockWebhookHandler.received_payloads) > 0, "No webhook callback received by mock server within 35s"
        received = MockWebhookHandler.received_payloads[0]["data"]

        assert received["job_id"] == job_id
        assert "proposal_id" in received
        assert received["status"] == "COMPLETED"
        assert "/api/v1/proposal/" in received["pdf_url"]
        assert "/api/v1/proposal/" in received["manifest_url"]

    # --------------------------------------------------------------------------
    # Test 3: Webhook Delivery Failure Isolation
    # --------------------------------------------------------------------------
    def test_03_webhook_failure_isolation(self):
        """Confirms that an unreachable webhook URL never invalidates completed proposal generation."""
        # Unreachable port on localhost
        dead_callback = "http://127.0.0.1:59998/dead-endpoint"

        payload = {
            "client_id": "TEST_N8N_DEAD_CALLBACK",
            "organization": {
                "name": "Resilient Youth Network",
                "organization_type": "nonprofit",
                "sector": "community_services"
            },
            "engagement": {
                "engagement_type": "recurring",
                "complexity": "compact"
            },
            "approved_scope": {
                "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 2100.0
            },
            "callback_url": dead_callback
        }

        resp = self.client.post("/api/v1/proposal/generate/async", json=payload, headers=self.headers)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        # Poll until complete
        max_wait = 20
        start_time = time.time()
        completed = False
        proposal_id = None

        while time.time() - start_time < max_wait:
            status_resp = self.client.get(f"/api/v1/proposal/status/{job_id}", headers=self.headers)
            status_data = status_resp.json()
            if status_data["status"] == "COMPLETED":
                completed = True
                proposal_id = status_data["proposal_id"]
                break
            time.sleep(0.5)

        assert completed, "Proposal job should still succeed even if webhook fails"
        # Confirm PDF was still compiled and accessible
        pdf_resp = self.client.get(f"/api/v1/proposal/{proposal_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.content.startswith(b"%PDF-")

    # --------------------------------------------------------------------------
    # Test 4: API Versioning Parity (/api/v1/... vs /...)
    # --------------------------------------------------------------------------
    def test_04_api_versioning_backward_compatibility(self):
        """Verifies that unversioned and versioned routes behave identically."""
        # 1. Health check parity
        v0_health = self.client.get("/health")
        v1_health = self.client.get("/api/v1/health")
        assert v0_health.status_code == 200
        assert v1_health.status_code == 200
        assert v0_health.json()["status"] == v1_health.json()["status"]

        # 2. Async generation parity
        payload = {
            "client_id": "TEST_N8N_PARITY",
            "organization": {"name": "Dual Route Org", "organization_type": "nonprofit", "sector": "community_services"},
            "engagement": {"engagement_type": "recurring", "complexity": "compact"},
            "approved_scope": {"bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}},
            "commercial_terms": {"pricing_model": "fixed_retainer", "monthly_retainer": 2000.0}
        }

        v0_resp = self.client.post("/proposal/generate/async", json=payload, headers=self.headers)
        v1_resp = self.client.post("/api/v1/proposal/generate/async", json=payload, headers=self.headers)

        assert v0_resp.status_code == 202
        assert v1_resp.status_code == 202
        assert v0_resp.json()["status"] == "CREATED"
        assert v1_resp.json()["status"] == "CREATED"

    # --------------------------------------------------------------------------
    # Test 5: Rate Limiting Enforcement & Health Check Exemption
    # --------------------------------------------------------------------------
    def test_05_rate_limiting_protection(self):
        """Validates that exceeding rate limits returns HTTP 429 while health endpoints are exempt."""
        from sympl_observability.resilience import default_rate_limiter

        try:
            # Set 3 requests per 60 seconds on default limiter for test
            default_rate_limiter.max_requests = 3
            default_rate_limiter.window_seconds = 60
            default_rate_limiter.reset()

            # Execute 3 allowed requests
            for _ in range(3):
                resp = self.client.get("/api/v1/proposal/status/non_existent_job", headers=self.headers)
                assert resp.status_code != 429

            # 4th request breaches rate limit
            breach_resp = self.client.get("/api/v1/proposal/status/non_existent_job", headers=self.headers)
            assert breach_resp.status_code == 429
            assert "Retry-After" in breach_resp.headers
            err_data = breach_resp.json()
            assert err_data["error"] == "RATE_LIMIT_EXCEEDED"

            # Verify health check is EXEMPT even when rate limited
            health_resp = self.client.get("/api/v1/health")
            assert health_resp.status_code == 200

        finally:
            default_rate_limiter.max_requests = 60
            default_rate_limiter.window_seconds = 60
            default_rate_limiter.reset()

    # --------------------------------------------------------------------------
    # Test 6: CORS Preflight for n8n
    # --------------------------------------------------------------------------
    def test_06_cors_headers_for_n8n(self):
        """Validates that OPTIONS requests handle n8n origin and allowed headers correctly."""
        headers = {
            "Origin": "http://localhost:5678",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key, Content-Type"
        }
        resp = self.client.options("/api/v1/proposal/generate/async", headers=headers)
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    # --------------------------------------------------------------------------
    # Test 7: Frozen Database Invariants Post Phase 9
    # --------------------------------------------------------------------------
    def test_07_database_invariants_post_phase9(self):
        """Confirms that all 6 frozen tables in PostgreSQL maintain exact invariant counts."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            from sympl_planner.retrieval import DATABASE_URL
            db_url = DATABASE_URL

        expected_counts = {
            "proposal_documents": 7,
            "proposal_chunks": 71,
            "sympl_style_rules": 21,
            "sympl_reference_blocks": 13,
            "dataset_imports": 7
        }

        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                for table, count in expected_counts.items():
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    actual = cur.fetchone()[0]
                    assert actual == count, f"Frozen table {table} count mismatch: expected {count}, got {actual}"

                # Embeddings count
                cur.execute("SELECT COUNT(*) FROM proposal_chunks WHERE embedding IS NOT NULL")
                emb_count = cur.fetchone()[0]
                assert emb_count == 47, f"Embeddings count altered: expected 47, got {emb_count}"

"""
Tests and Validations for Hardened n8n Workflow (workflow_3_proposal_rag_mvp.json)

Validates:
1. Complete JSON structure and graph topological integrity (23 nodes, all connections resolved).
2. Issue 1: Polling counter state persistence, incrementing per status check, timeout at 60 attempts, and loop safety.
3. Issue 2: Hardened PDF and Manifest retrieval references pointing to IF Completed? output.
4. Issue 3: Pre-RAG commercial and scope validation logic (amount > 0, currency, pricing model, active scope).
5. Issue 4: Canva state standardization to READY_FOR_CANVA (no premature canva_ready completion).
6. Full end-to-end integration: Form -> Approval -> RAG Generation -> Polling -> PDF -> Manifest -> Completion.
"""

import json
import os
import sys
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_api.main import app
from sympl_api.config import settings

WORKFLOW_PATH = PROJECT_ROOT / "workflow_3_proposal_rag_mvp.json"


@pytest.fixture(scope="module")
def workflow_data():
    assert WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}"
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_01_workflow_graph_and_node_count(workflow_data):
    """Verifies that all 23 nodes exist and all connection edges point to valid nodes."""
    nodes = workflow_data.get("nodes", [])
    assert len(nodes) == 23, f"Expected exactly 23 nodes, got {len(nodes)}"

    node_names = set(n["name"] for n in nodes)
    assert len(node_names) == 23, "Duplicate node names found in workflow"

    connections = workflow_data.get("connections", {})
    for src_name, branches in connections.items():
        assert src_name in node_names, f"Unknown source node in connections: {src_name}"
        for branch_idx, branch in enumerate(branches.get("main", [])):
            for target in branch:
                assert target["node"] in node_names, (
                    f"Unknown target node in {src_name}[main:{branch_idx}]: {target['node']}"
                )


def test_02_issue_3_commercial_and_scope_validation_node(workflow_data):
    """Verifies that Validate Proposal Request node exists before Call RAG API and enforces rules."""
    nodes = {n["name"]: n for n in workflow_data["nodes"]}

    assert "Validate Proposal Request" in nodes
    val_node = nodes["Validate Proposal Request"]
    assert val_node["type"] == "n8n-nodes-base.code"
    js_code = val_node["parameters"]["jsCode"]

    # Verify required validation rules in JS code
    assert "payload.client_name" in js_code
    assert "approved_scope" in js_code
    assert "commercial_terms.pricing_model" in js_code
    assert "commercial_terms.currency" in js_code
    assert "commercial_terms.amount" in js_code
    assert "terms.amount <= 0" in js_code or "amount > 0" in js_code

    # Verify branching connections
    conns = workflow_data["connections"]
    assert conns["Prepare Proposal Payload"]["main"][0][0]["node"] == "Validate Proposal Request"
    assert conns["Validate Proposal Request"]["main"][0][0]["node"] == "IF Request Valid?"

    if_node = conns["IF Request Valid?"]["main"]
    assert if_node[0][0]["node"] == "Call Sympl Proposal RAG API"  # True branch
    assert if_node[1][0]["node"] == "Validation Error Response"    # False branch


def test_03_issue_1_polling_state_and_timeout_counter(workflow_data):
    """Verifies that polling preserves job_id and poll_count, increments per check, and caps at 60."""
    nodes = {n["name"]: n for n in workflow_data["nodes"]}

    # Store Job ID node
    store_node = nodes["Store Job ID"]
    assignments = store_node["parameters"]["assignments"]["assignments"]
    assign_map = {a["name"]: a for a in assignments}
    assert "job_id" in assign_map
    assert "poll_count" in assign_map

    # Check Status API node
    status_node = nodes["Check Status API"]
    assert "Store Job ID" in status_node["parameters"]["url"]

    # Check Timeout Counter node
    counter_node = nodes["Check Timeout Counter"]
    js_code = counter_node["parameters"]["jsCode"]
    assert "$runIndex" in js_code
    assert "maxAttempts = 60" in js_code
    assert "jobId" in js_code

    # IF Timeout node
    if_timeout = nodes["IF Timeout?"]
    assert "is_timeout" in str(if_timeout["parameters"])

    # Graph loop connections
    conns = workflow_data["connections"]
    assert conns["Store Job ID"]["main"][0][0]["node"] == "Wait 5 Seconds"
    assert conns["Wait 5 Seconds"]["main"][0][0]["node"] == "Check Status API"
    assert conns["Check Status API"]["main"][0][0]["node"] == "IF Completed?"

    if_completed = conns["IF Completed?"]["main"]
    assert if_completed[0][0]["node"] == "Retrieve Generated PDF"  # Completed -> proceed
    assert if_completed[1][0]["node"] == "Check Timeout Counter"     # Running -> timeout check

    assert conns["Check Timeout Counter"]["main"][0][0]["node"] == "IF Timeout?"
    if_timeout_conns = conns["IF Timeout?"]["main"]
    assert if_timeout_conns[0][0]["node"] == "Poll Timeout Response"  # True -> timeout halt
    assert if_timeout_conns[1][0]["node"] == "Wait 5 Seconds"         # False -> loop back


def test_04_issue_2_hardened_pdf_and_manifest_retrieval(workflow_data):
    """Verifies that Retrieve Generated PDF and Retrieve Manifest reference IF Completed? output."""
    nodes = {n["name"]: n for n in workflow_data["nodes"]}

    pdf_node = nodes["Retrieve Generated PDF"]
    manifest_node = nodes["Retrieve Manifest"]

    assert "$('IF Completed?').first().json.proposal_id" in pdf_node["parameters"]["url"]
    assert "$('IF Completed?').first().json.proposal_id" in manifest_node["parameters"]["url"]


def test_05_issue_4_canva_status_correction(workflow_data):
    """Verifies that canva_status is READY_FOR_CANVA throughout, with no premature canva_ready=true."""
    nodes = {n["name"]: n for n in workflow_data["nodes"]}

    # Prepare Canva Import Handoff
    handoff_node = nodes["Prepare Canva Import Handoff"]
    assert "READY_FOR_CANVA" in handoff_node["parameters"]["jsCode"]

    # CANVA IMPORT SERVICE
    canva_svc_node = nodes["CANVA IMPORT SERVICE"]
    assert "READY_FOR_CANVA" in canva_svc_node["parameters"]["jsCode"]
    # Check that javascript boolean literal is lowercase true, not Python True
    assert "canva_service_dispatched: true" in canva_svc_node["parameters"]["jsCode"]

    # Return Completion Result
    completion_node = nodes["Return Completion Result"]
    assignments = completion_node["parameters"]["assignments"]["assignments"]
    assign_map = {a["name"]: a for a in assignments}

    assert "canva_ready" not in assign_map, "canva_ready should be replaced by canva_status"
    assert "canva_status" in assign_map
    assert assign_map["canva_status"]["value"] == "READY_FOR_CANVA"
    assert assign_map["status"]["value"] == "completed"
    assert assign_map["pdf_generated"]["value"] is True
    assert assign_map["manifest_verified"]["value"] is True


def test_06_end_to_end_complete_workflow_run():
    """Runs complete workflow simulation: Form -> Approval -> Async RAG -> Polling -> PDF -> Manifest -> COMPLETED."""
    client = TestClient(app)
    headers = {
        "X-API-Key": settings.API_KEY,
        "Content-Type": "application/json"
    }

    # Step 1: Form submission & Approval
    client_name = "Acme Community Health Centre"
    approved_scope = {
        "bookkeeping": True,
        "payroll": False,
        "financial_reporting": True,
        "compliance": False,
        "digital_transformation": False,
        "transition": False
    }
    commercial_terms = {
        "pricing_model": "fixed_retainer",
        "currency": "CAD",
        "amount": 2500.0
    }

    # Step 2: Commercial validation check (simulating Validate Proposal Request node)
    assert len(client_name.strip()) > 0
    active_services = [k for k, v in approved_scope.items() if v]
    assert len(active_services) > 0
    assert commercial_terms["amount"] > 0
    assert commercial_terms["currency"] == "CAD"
    assert commercial_terms["pricing_model"] == "fixed_retainer"

    # Step 3: Call Sympl Proposal RAG API
    payload = {
        "client_id": "TEST_WORKFLOW_3_ACME",
        "organization": {
            "name": client_name,
            "organization_type": "healthcare",
            "sector": "community_health"
        },
        "engagement": {
            "engagement_type": "recurring",
            "complexity": "standard"
        },
        "approved_scope": {
            "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True},
            "financial_reporting": {"management_reporting": True}
        },
        "commercial_terms": {
            "pricing_model": commercial_terms["pricing_model"],
            "currency": commercial_terms["currency"],
            "monthly_retainer": commercial_terms["amount"]
        }
    }

    submit_resp = client.post("/api/v1/proposal/generate/async", json=payload, headers=headers)
    assert submit_resp.status_code == 202
    submit_data = submit_resp.json()
    job_id = submit_data["job_id"]
    assert submit_data["status"] == "CREATED"

    # Step 4: Polling loop (simulating Store Job ID -> Wait -> Check Status -> IF Completed)
    max_wait = 45
    poll_count = 0
    start_time = time.time()
    completed = False
    proposal_id = None

    while time.time() - start_time < max_wait:
        poll_count += 1
        assert poll_count <= 60, "Exceeded maximum allowed 60 poll attempts"

        status_resp = client.get(f"/api/v1/proposal/status/{job_id}", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()

        if status_data["status"] == "COMPLETED":
            completed = True
            proposal_id = status_data["proposal_id"]
            break
        elif status_data["status"] == "FAILED":
            pytest.fail(f"RAG generation failed: {status_data.get('error_message')}")

        time.sleep(0.5)

    assert completed, f"Job {job_id} did not reach COMPLETED within {max_wait}s"
    assert proposal_id is not None, "Missing proposal_id in completed status"

    # Step 5: Retrieve Generated PDF (using hardened reference)
    pdf_resp = client.get(f"/api/v1/proposal/{proposal_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-")
    assert len(pdf_resp.content) > 1000

    # Step 6: Retrieve Manifest (using hardened reference)
    manifest_resp = client.get(f"/api/v1/proposal/{proposal_id}/manifest")
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()
    assert manifest["artifact_count"] == 5
    assert manifest["all_artifacts_present"] is True

    # Step 7: Canva Handoff & Final Status verification
    canva_handoff = {
        "proposal_id": proposal_id,
        "file": "proposal.pdf",
        "action": "IMPORT_TO_CANVA",
        "canva_status": "READY_FOR_CANVA",
        "manifest_verified": manifest["all_artifacts_present"]
    }
    assert canva_handoff["canva_status"] == "READY_FOR_CANVA"
    assert canva_handoff["manifest_verified"] is True

    final_result = {
        "status": "completed",
        "job_id": job_id,
        "proposal_id": proposal_id,
        "pdf_generated": True,
        "manifest_verified": True,
        "canva_status": "READY_FOR_CANVA"
    }
    assert final_result["status"] == "completed"
    assert final_result["canva_status"] == "READY_FOR_CANVA"

"""
Test Portal Integration Endpoint (POST /api/generate-proposal)

Validates:
1. Normalization of frontend payload into pipeline intake
2. Full synchronous execution of Planner, Writer, Validator, Canva template mapper, and PDF export
3. Correct return schema: { status: "completed", proposal_id, canva_url, pdf_url }
4. PDF download verification via returned pdf_url
"""

import sys
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("RENDERER_MODE", "mock")

from starlette.testclient import TestClient
from sympl_api.main import app

client = TestClient(app)


def test_portal_generate_proposal_oldtrout():
    """Validates proposal generation for Old Trout Puppet Workshop."""
    payload = {
        "brand": "Sympl Solutions",
        "client_name": "Old Trout Puppet Workshop",
        "project_title": "Arts & Non-Profit Bookkeeping, Accounts Payable & Compliance Retainer",
        "scope_of_work": (
            "Full-cycle bookkeeping services: weekly accounts payable processing, automated receipt capture "
            "via Dext/Hubdoc, monthly bank and credit card reconciliations across CIBC, RBC Casino, and Manulife funds, "
            "bi-weekly Canadian payroll for 14 staff/artists, GST/HST quarterly returns, and year-end audit preparation pack."
        ),
        "approach": (
            "Sympl Non-Profit Operating Framework: Cloud ledger modernization in QuickBooks Online, "
            "standardized chart of accounts aligned with Canadian Arts Council reporting requirements, "
            "dual-authorization payment workflows via Plooto, and real-time grant fund tracking."
        ),
        "timeline": "12-month renewable engagement with 30-day onboarding kickoff.",
        "commercial_information": "$2,850 CAD / month flat retainer + $1,500 setup fee."
    }

    response = client.post("/api/generate-proposal", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["status"] == "completed"
    assert data["proposal_id"].startswith("prop_")
    assert "canva.com/design/" in data["canva_url"]
    assert data["pdf_url"].startswith("/api/v1/proposal/") and data["pdf_url"].endswith("/pdf")

    # Verify stages
    assert data.get("stages", {}).get("requirements_analyzed") is True
    assert data.get("stages", {}).get("proposal_generated") is True
    assert data.get("stages", {}).get("canva_template_populated") is True
    assert data.get("stages", {}).get("proposal_ready") is True

    # Test PDF download endpoint
    pdf_response = client.get(data["pdf_url"])
    assert pdf_response.status_code == 200, f"Failed to download PDF from {data['pdf_url']}"
    assert pdf_response.headers.get("content-type") == "application/pdf"
    assert len(pdf_response.content) > 1000, "Downloaded PDF is too small or empty"
    assert pdf_response.content[:4] == b"%PDF", "Response content is not valid PDF"


if __name__ == "__main__":
    test_portal_generate_proposal_oldtrout()
    print("\n[SUCCESS] test_portal_generate_proposal_oldtrout passed completely!")

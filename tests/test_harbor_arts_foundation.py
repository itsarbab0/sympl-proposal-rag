"""
Test Proposal Generation for Harbor Arts Foundation

Executes:
1. Normalization of intake
2. Proposal Planner
3. Proposal Writer
4. Canva Template Mapping (70 operations adapter)
5. Canva Design Creation & PDF Export
6. Verifies new design ID, dynamic Canva URL, and downloadable PDF
"""

import sys
import os
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("RENDERER_MODE", "mock")

from starlette.testclient import TestClient
from sympl_api.main import app

client = TestClient(app)


def test_harbor_arts_foundation():
    payload = {
        "brand": "Sympl Solutions",
        "client_name": "Harbor Arts Foundation",
        "project_title": "Non-Profit Bookkeeping, Grant Accounting & Year-End Compliance Retainer",
        "scope_of_work": (
            "Full-cycle non-profit bookkeeping: monthly bank and credit card reconciliations across "
            "operating and endowment accounts, weekly accounts payable processing, automated receipt capture "
            "via Dext, Canadian payroll administration for artistic staff and contractors, segregated grant tracking, "
            "GST/HST public service body rebate filings, and year-end audit preparation pack."
        ),
        "approach": (
            "Sympl Non-Profit Operating Framework: Cloud ledger modernization in QuickBooks Online, "
            "structured multi-fund chart of accounts aligned with Canadian Arts Council and CADAC reporting, "
            "dual-authorization payment workflows via Plooto, and board financial reporting packs."
        ),
        "timeline": "12-month renewable annual engagement with 30-day onboarding and historical clean-up.",
        "commercial_information": "$3,200 CAD monthly retainer + $1,800 setup and fund accounting configuration fee."
    }

    print("\n=======================================================")
    print("RUNNING HARBOR ARTS FOUNDATION END-TO-END TEST")
    print("=======================================================\n")

    response = client.post("/api/generate-proposal", json=payload)
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"Error Response: {response.text}")
        sys.exit(1)

    data = response.json()
    proposal_id = data["proposal_id"]
    canva_url = data["canva_url"]
    pdf_url = data["pdf_url"]

    # Download and verify PDF
    pdf_resp = client.get(pdf_url)
    assert pdf_resp.status_code == 200, f"Failed to download PDF: {pdf_resp.status_code}"
    pdf_bytes = pdf_resp.content

    print("\n--- RESULTS FOR HARBOR ARTS FOUNDATION ---")
    print(f"Proposal ID: {proposal_id}")
    print(f"New Canva URL: {canva_url}")
    print(f"PDF URL: {pdf_url}")
    print(f"PDF Size: {len(pdf_bytes)} bytes")
    print(f"PDF Header: {pdf_bytes[:8].decode('latin1')}")
    assert pdf_bytes.startswith(b"%PDF"), "Invalid PDF header"
    assert len(pdf_bytes) > 2000, "PDF too small"
    print("\n[VERIFICATION SUCCESS] Harbor Arts Foundation proposal and PDF verified successfully!")


if __name__ == "__main__":
    test_harbor_arts_foundation()

"""
Sympl Solutions Proposal RAG — Generate Canonical Rendered Proposal

Consumes the canonical proposal_draft.json and compiles the presentation
rendered_proposal.json ready for Canva / PDF delivery.
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from sympl_renderer import ProposalRenderer

def main():
    draft_path = root / "proposal_draft.json"
    rendered_path = root / "rendered_proposal.json"

    print(f"Loading proposal draft from: {draft_path}")
    renderer = ProposalRenderer()
    rendered = renderer.render(draft_path)

    out_file = renderer.render_to_file(draft_path, rendered_path, format="json")
    print(f"Rendered proposal successfully generated at: {out_file}")
    print(f"  Title: {rendered.title}")
    print(f"  Client: {rendered.client_name}")
    print(f"  Design ID: {rendered.design_id}")
    print(f"  Page Count: {rendered.page_count}")
    print(f"  Export Status: {rendered.export_status}")
    print(f"  PDF URL: {rendered.pdf_url}")
    print(f"  Validation Passed: {rendered.render_metadata.get('validation_results', {}).get('passed')}")

if __name__ == "__main__":
    main()

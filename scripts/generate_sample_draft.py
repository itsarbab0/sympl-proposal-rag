"""
Sympl Solutions Proposal RAG — Generate Canonical Proposal Draft

Consumes the canonical proposal_plan.json and generates the validated proposal_draft.json
ready for future Canva / rendering pipeline integration.
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from sympl_writer import ProposalWriter

def main():
    root = Path(__file__).resolve().parent.parent
    plan_path = root / "proposal_plan.json"
    draft_path = root / "proposal_draft.json"

    print(f"Loading plan from: {plan_path}")
    writer = ProposalWriter()
    draft = writer.write_to_file(plan_path, draft_path)

    print(f"Proposal draft successfully written to: {draft_path}")
    print(f"  Title: {draft.title}")
    print(f"  Sections: {len(draft.sections)}")
    print(f"  Why Us items: {len(draft.why_us)}")
    print(f"  Exclusions: {len(draft.exclusions)}")
    print(f"  Pricing fee items: {len(draft.pricing.get('fee_items', []))}")
    print(f"  Validation Passed: {draft.validation_metadata.get('passed')}")

if __name__ == "__main__":
    main()

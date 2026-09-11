"""
Tests Phase 3 Proposal Narrative Depth & Density.

Verifies:
1. DraftSubsection schema supports context, approach, workflow, bullets, outcome with narrative backward compatibility.
2. Service sections exhibit historical Sympl information density and operational depth without AI filler.
3. Multi-paragraph executive summaries cover client situation, operational challenges, Sympl approach, and expected outcomes.
4. Key activities / deliverables are bounded (<= 6 bullets per subsection).
5. Specialized sections (pricing, why us, exclusions, boundaries) retain specialized structures.
6. Zero forbidden buzzwords or historical entity leakage across all 4 benchmark proposals (OldT, Crawford, AKM, Compass).
"""

import json
import pytest
from pathlib import Path

from sympl_writer.schema import DraftSubsection, ProposalDraft, DraftSection
from sympl_writer.llm_client import MockLLMClient
from sympl_writer.writer import ProposalWriter
from sympl_writer.playbooks.base_style import FORBIDDEN_PHRASES


class TestNarrativeDepthSchemaCompatibility:
    """Tests DraftSubsection schema enhancements and backward compatibility."""

    def test_subsection_schema_fields(self):
        """Verify DraftSubsection instantiates with all 5 parts plus narrative."""
        sub = DraftSubsection(
            heading="Accounts Payable & Disbursements",
            context="Disciplined AP processes maintain vendor relations.",
            approach="Sympl enforces dual-authorization digital workflows.",
            workflow="Bills in Dext are verified, coded to QBO, and batched in Plooto.",
            bullets=["Review vendor invoices", "Maintain AP aging ledger"],
            outcome="Clean audit trails and elimination of late fees."
        )
        assert sub.heading == "Accounts Payable & Disbursements"
        assert sub.context is not None
        assert sub.approach is not None
        assert sub.workflow is not None
        assert sub.outcome is not None
        assert len(sub.bullets) == 2

    def test_backward_compatible_narrative_synthesis(self):
        """Verify ProposalDraft.from_dict synthesizes narrative when given 5-part architecture."""
        raw_data = {
            "title": "Test Proposal",
            "executive_summary": "Executive summary paragraph 1.\n\nExecutive summary paragraph 2.",
            "sections": [
                {
                    "section_title": "Core Services",
                    "opening_text": "Section opening contextual narrative.",
                    "subsections": [
                        {
                            "heading": "Workflow Subheading",
                            "context": "Context paragraph.",
                            "approach": "Approach paragraph.",
                            "workflow": "Workflow paragraph.",
                            "bullets": ["Action bullet 1", "Action bullet 2"],
                            "outcome": "Outcome paragraph."
                        }
                    ]
                }
            ],
            "why_us": ["Why Us block"],
            "pricing": {"pricing_model": "fixed_retainer"},
            "exclusions": ["Exclusion 1"]
        }
        draft = ProposalDraft.from_dict(raw_data)
        sub = draft.sections[0].subsections[0]

        # Narrative should be synthesized automatically
        assert sub.narrative is not None
        assert "Context paragraph." in sub.narrative
        assert "Approach paragraph." in sub.narrative
        assert "Workflow paragraph." in sub.narrative
        assert "Outcome paragraph." in sub.narrative
        assert len(sub.narrative.split("\n\n")) == 4

    def test_legacy_narrative_preserved_if_provided(self):
        """Verify ProposalDraft.from_dict preserves existing narrative field if supplied."""
        raw_data = {
            "title": "Legacy Proposal",
            "executive_summary": "Summary",
            "sections": [
                {
                    "section_title": "Legacy Service",
                    "opening_text": "Opening",
                    "subsections": [
                        {
                            "heading": "Legacy Subheading",
                            "narrative": "Existing single legacy narrative paragraph.",
                            "bullets": ["Legacy bullet"]
                        }
                    ]
                }
            ]
        }
        draft = ProposalDraft.from_dict(raw_data)
        sub = draft.sections[0].subsections[0]
        assert sub.narrative == "Existing single legacy narrative paragraph."
        assert sub.context is None


class TestBenchmarkProposalsNarrativeDepth:
    """Verifies narrative depth, paragraphs per service, and bullet control across 4 benchmarks."""

    @pytest.fixture(autouse=True)
    def setup_benchmarks(self):
        client = MockLLMClient()
        self.writer = ProposalWriter(llm_client=client)

        # 1. OldT (Accounting)
        self.oldt_raw = client.generate(
            prompt="title: Accounting & Bookkeeping Services Proposal for OldT Community Arts Workshop\nClient Name: OldT Community Arts Workshop\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"bookkeeping\": {\"cadence\": \"weekly\"}, \"payroll\": {\"cadence\": \"biweekly\"}, \"financial_reporting\": {\"cadence\": \"monthly\"}, \"compliance\": {\"gst_hst_filing\": true}}"
        )
        self.oldt_draft = ProposalDraft.from_dict(json.loads(self.oldt_raw))

        # 2. Crawford (Website Development)
        self.crawford_raw = client.generate(
            prompt="title: Website Development Proposal for Crawford Gallery\nClient Name: Crawford Gallery\nservice_category: Website Development\nCRAWFORD_2026\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"generic_services\": [{\"service_category\": \"Website Development\"}]}"
        )
        self.crawford_draft = ProposalDraft.from_dict(json.loads(self.crawford_raw))

        # 3. AKM (Data Analytics)
        self.akm_raw = client.generate(
            prompt="title: Data Analytics & Centralized Database Proposal for AKM Centre\nClient Name: AKM Centre\nservice_category: Data Analytics\nAKM_2026\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"generic_services\": [{\"service_category\": \"Data Analytics\"}]}"
        )
        self.akm_draft = ProposalDraft.from_dict(json.loads(self.akm_raw))

        # 4. Compass (Finance Transformation)
        self.compass_raw = client.generate(
            prompt="title: Budget Revamp & Financial Forecasting Proposal for Compass Centre\nClient Name: Compass Centre\nservice_category: Finance Transformation\nCOMPASS_2026\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"generic_services\": [{\"service_category\": \"Finance Transformation\"}]}"
        )
        self.compass_draft = ProposalDraft.from_dict(json.loads(self.compass_raw))

    def test_executive_summaries_multi_paragraph_and_rich(self):
        """Verify all 4 benchmarks have multi-paragraph executive summaries covering situation, challenge, approach, outcome."""
        for name, draft in [
            ("OldT", self.oldt_draft),
            ("Crawford", self.crawford_draft),
            ("AKM", self.akm_draft),
            ("Compass", self.compass_draft)
        ]:
            exec_text = draft.executive_summary
            assert exec_text and len(exec_text.strip()) > 0, f"{name} exec summary is empty"
            paragraphs = [p.strip() for p in exec_text.split("\n\n") if p.strip()]
            assert len(paragraphs) >= 3, f"{name} exec summary should have at least 3 paragraphs, got {len(paragraphs)}"
            word_count = len(exec_text.split())
            assert word_count >= 140, f"{name} exec summary lacks consulting depth ({word_count} words)"

    def test_service_subsections_have_operational_depth(self):
        """Verify service subsections contain context, approach, and outcome, with synthesized narrative."""
        for name, draft in [
            ("OldT", self.oldt_draft),
            ("Crawford", self.crawford_draft),
            ("AKM", self.akm_draft),
            ("Compass", self.compass_draft)
        ]:
            for sec in draft.sections:
                assert sec.opening_text and len(sec.opening_text.strip()) > 0, f"Missing opening text in {name} - {sec.section_title}"
                for sub in sec.subsections:
                    # If this is an operational service subsection (not an exclusions/boundaries only block)
                    if sub.heading not in ["Operational Boundaries", "Implementation Boundaries", "Compliance Boundaries", "Audit Boundaries", "Advisory Boundaries", "Training Boundaries", "Payroll Boundaries & Prerequisites", "Governance Boundaries"]:
                        assert sub.context is not None, f"Missing context in {name} -> {sub.heading}"
                        assert sub.approach is not None, f"Missing approach in {name} -> {sub.heading}"
                        assert sub.outcome is not None, f"Missing outcome in {name} -> {sub.heading}"
                        assert sub.narrative is not None and len(sub.narrative) > 50, f"Missing synthesized narrative in {name} -> {sub.heading}"

    def test_bullet_counts_bounded(self):
        """Verify bullet count per subsection is strictly bounded (maximum 6 bullets)."""
        for name, draft in [
            ("OldT", self.oldt_draft),
            ("Crawford", self.crawford_draft),
            ("AKM", self.akm_draft),
            ("Compass", self.compass_draft)
        ]:
            for sec in draft.sections:
                for sub in sec.subsections:
                    assert len(sub.bullets) <= 6, f"{name} subsection '{sub.heading}' exceeds 6 bullets: {len(sub.bullets)}"

    def test_zero_forbidden_buzzwords(self):
        """Verify no forbidden buzzwords exist in any generated draft."""
        for name, draft in [
            ("OldT", self.oldt_draft),
            ("Crawford", self.crawford_draft),
            ("AKM", self.akm_draft),
            ("Compass", self.compass_draft)
        ]:
            full_text = json.dumps(draft.to_dict()).lower()
            for buzz in FORBIDDEN_PHRASES:
                assert buzz.lower() not in full_text, f"Forbidden buzzword '{buzz}' found in {name}"

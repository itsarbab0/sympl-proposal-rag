"""
Sympl Solutions Proposal RAG — Proposal Writer Narrative Balance Regression Test Suite

Verifies:
  1. Enriched context generates narrative paragraphs (Service Context, Sympl Approach, Expected Outcomes).
  2. Bullet count is reduced and controlled (maximum 5-7 bullets per subsection; timeline/exclusions allowed).
  3. JSON schema guidance supports optional bullets and subsection narrative ({heading, narrative, bullets}).
  4. Explicit rules on readability over information density and natural paragraphs over bullet lists.
  5. Legacy payloads still work with 100% backward compatibility and passing validation.
  6. Pricing placeholders and reference blocks remain strictly preserved.
"""

import os
import sys
import json
from pathlib import Path
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sympl_writer.prompt_builder import PromptBuilder
from sympl_writer import ProposalWriter, MockLLMClient, ProposalDraft


@pytest.fixture
def oldt_fixture():
    """Loads the OldT regression fixture JSON."""
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "oldt_enriched_payload.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def enriched_plan_data(oldt_fixture):
    """Constructs a validated proposal_plan dictionary with enriched context."""
    return {
        "plan_id": "plan_test_narrative_001",
        "client_name": oldt_fixture["client_name"],
        "client_context": {
            "name": oldt_fixture["client_name"],
            "organization_type": oldt_fixture["organization_type"],
            "sector": oldt_fixture["sector"],
            "current_systems": [oldt_fixture["current_accounting_system"]],
            "target_systems": ["QuickBooks Online", "Dext"],
            "engagement_type": "recurring",
            "complexity": "standard",
            "client_situation_summary": oldt_fixture["client_situation_summary"],
            "client_challenges_summary": oldt_fixture["client_challenges_summary"],
            "organization_description": oldt_fixture["organization_description"],
            "current_accounting_system": oldt_fixture["current_accounting_system"],
            "current_finance_process": oldt_fixture["current_finance_process"],
            "current_finance_team_structure": oldt_fixture["current_finance_team_structure"],
            "current_finance_challenges": oldt_fixture["current_finance_challenges"],
            "reason_for_engagement": oldt_fixture["reason_for_engagement"],
            "desired_outcomes": oldt_fixture["desired_outcomes"],
            "client_priorities": oldt_fixture["client_priorities"],
            "context_quality": "HIGH",
            "context_score": 95
        },
        "approved_scope": oldt_fixture["approved_scope"],
        "sections": [
            {
                "section_id": "sec_01",
                "section_title": "Accounting & Bookkeeping Services",
                "section_type": "service_scope",
                "service_family": "bookkeeping",
                "structural_role": "core_service",
                "section_instructions": ["Provide operational bookkeeping scope"],
                "style_rules_applied": ["Active verbs", "No periods"]
            },
            {
                "section_id": "sec_02",
                "section_title": "Payroll Administration",
                "section_type": "service_scope",
                "service_family": "payroll",
                "structural_role": "core_service",
                "section_instructions": ["Provide biweekly payroll administration"],
                "style_rules_applied": []
            }
        ],
        "pricing": oldt_fixture["commercial_terms"],
        "metadata": {"context_quality": "HIGH", "context_score": 95}
    }


@pytest.fixture
def legacy_plan_data():
    """Minimal legacy plan without enriched narrative fields."""
    return {
        "plan_id": "plan_test_narrative_legacy_001",
        "client_name": "Legacy Foundation",
        "client_context": {
            "name": "Legacy Foundation",
            "organization_type": "nonprofit",
            "sector": "community_services",
            "current_systems": [],
            "target_systems": [],
            "engagement_type": "recurring",
            "complexity": "standard",
            "context_quality": "LOW",
            "context_score": 0
        },
        "approved_scope": {
            "bookkeeping": {"cadence": "weekly", "ap_ar": True, "reconciliations": True}
        },
        "sections": [
            {
                "section_id": "sec_01",
                "section_title": "Accounting & Bookkeeping Services",
                "section_type": "service_scope",
                "service_family": "bookkeeping",
                "structural_role": "core_service"
            }
        ],
        "pricing": {
            "pricing_model": "fixed_retainer",
            "currency": "CAD",
            "billing_schedule": "Monthly in advance",
            "fee_items": [
                {
                    "category": "Monthly Recurring Retainer",
                    "amount": 1850.0,
                    "currency": "CAD",
                    "billing_frequency": "monthly",
                    "is_placeholder": False
                }
            ],
            "has_placeholders": False
        },
        "metadata": {"context_quality": "LOW", "context_score": 0}
    }


class TestWriterNarrativeBalance:
    """Regression test suite for consulting proposal narrative balance and bullet control."""

    # --------------------------------------------------------------------------
    # Test 1: Consulting Narrative Instructions & Philosophy in Prompt
    # --------------------------------------------------------------------------
    def test_01_consulting_narrative_instructions_present(self, enriched_plan_data):
        """
        Verifies that PromptBuilder includes explicit narrative philosophy,
        the 4-part section pattern (Service Context, Sympl Approach, Key Activities, Expected Outcome),
        bullet reduction rules, and readability prioritization.
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        # 1. Philosophy & Readability Rules
        assert "consulting proposal narrative" in user_prompt
        assert "Do not create a bullet list if information can be explained naturally in paragraphs." in user_prompt
        assert "Professional proposals should prioritize readability and explanation over information density." in user_prompt

        # 2. 4-part Mandatory Section Pattern
        assert "MANDATORY SECTION PATTERN" in user_prompt
        assert "A. Service Context Narrative:" in user_prompt
        assert "B. Sympl Approach Narrative:" in user_prompt
        assert "C. Key Activities:" in user_prompt
        assert "D. Expected Outcome Paragraph:" in user_prompt

        # 3. Bullet Point Reduction Limits
        assert "4-6 bullets" in user_prompt
        assert "timeline: bullets allowed" in user_prompt.lower()
        assert "exclusions: bullets allowed" in user_prompt.lower()

        # 4. JSON Schema guidance allows narrative and optional bullets in subsections
        assert '"narrative":' in user_prompt
        assert "Bullets are optional if explained naturally in paragraphs." in user_prompt
        assert "leave [] if fully explained in narrative" in user_prompt

        # 5. System prompt invariants
        assert "consulting proposal narrative" in system_prompt
        assert "Do not create a bullet list if information can be explained naturally in paragraphs." in system_prompt
        assert "Professional proposals should prioritize readability and explanation over information density." in system_prompt
        assert "Maximum 4-6 bullets per subsection" in system_prompt

    # --------------------------------------------------------------------------
    # Test 2: Enriched Context Generates Narrative Paragraphs
    # --------------------------------------------------------------------------
    def test_02_enriched_context_generates_narrative_paragraphs(self, enriched_plan_data, oldt_fixture):
        """
        Confirms enriched context flows into prompt narrative fields and generated
        draft contains substantial contextual opening paragraphs.
        """
        _, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        # Enriched context fields present in prompt
        assert oldt_fixture["client_situation_summary"] in user_prompt
        assert oldt_fixture["client_challenges_summary"] in user_prompt
        assert oldt_fixture["organization_description"] in user_prompt

        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(enriched_plan_data)

        assert isinstance(draft, ProposalDraft)
        assert draft.validation_metadata["passed"] is True

        # Verify sections contain substantive narrative opening_text
        for sec in draft.sections:
            assert len(sec.opening_text.strip()) > 30, f"Section '{sec.section_title}' opening_text too short"
            # Must not be a bullet list
            assert not sec.opening_text.strip().startswith("- ")
            assert not sec.opening_text.strip().startswith("* ")

    # --------------------------------------------------------------------------
    # Test 3: Bullet Count is Reduced and Controlled
    # --------------------------------------------------------------------------
    def test_03_bullet_count_reduced_and_controlled(self, enriched_plan_data):
        """
        Verifies that subsections in the generated proposal adhere to the maximum
        bullet limit (<= 7 bullets per subsection) to eliminate whitespace fragmentation.
        """
        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(enriched_plan_data)

        for sec in draft.sections:
            for sub in sec.subsections:
                bullet_count = len(sub.bullets)
                assert bullet_count <= 7, (
                    f"Subsection '{sub.heading}' in section '{sec.section_title}' "
                    f"has {bullet_count} bullets, exceeding maximum limit of 7."
                )

    # --------------------------------------------------------------------------
    # Test 4: Legacy Payload Still Works (Backward Compatibility)
    # --------------------------------------------------------------------------
    def test_04_legacy_payload_still_works(self, legacy_plan_data):
        """
        Confirms that legacy payloads without enriched narrative fields:
        1. Receive the updated consulting narrative instructions.
        2. Successfully generate a validated ProposalDraft.
        3. Comply with bullet limits and validation invariants.
        """
        _, user_prompt = PromptBuilder.build_prompt(legacy_plan_data)

        assert "consulting proposal narrative" in user_prompt
        assert "Do not create a bullet list if information can be explained naturally in paragraphs." in user_prompt

        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(legacy_plan_data)

        assert isinstance(draft, ProposalDraft)
        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0

        # Verify bullet limits on legacy draft
        for sec in draft.sections:
            assert len(sec.opening_text.strip()) > 0
            for sub in sec.subsections:
                assert len(sub.bullets) <= 7

    # --------------------------------------------------------------------------
    # Test 5: Pricing and Reference Blocks Preserved
    # --------------------------------------------------------------------------
    def test_05_preserves_pricing_and_reference_blocks(self, enriched_plan_data):
        """
        Verifies that narrative and bullet improvements preserve commercial terms,
        pricing items, and canonical reference blocks without corruption.
        """
        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(enriched_plan_data)

        assert draft.validation_metadata["passed"] is True
        assert "fee_items" in draft.pricing
        assert len(draft.why_us) > 0
        assert len(draft.exclusions) > 0

"""
Sympl Solutions Proposal RAG — Proposal Writer Style Instructions Regression Test Suite

Verifies:
  1. Enriched proposals receive explicit consulting style instructions in the prompt.
  2. Legacy proposals still generate successfully and preserve backward compatibility.
  3. Pricing placeholders remain unchanged and protected against invention.
  4. Narrative context (situation, challenges, outcomes, finance obstacles) appears in writer prompt.
  5. System prompt aligns with historical benchmark style (TACT, YPT, RPFF).
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
        "plan_id": "plan_test_enriched_001",
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
        "plan_id": "plan_test_legacy_001",
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
            "monthly_retainer": 1850.0
        },
        "metadata": {"context_quality": "LOW", "context_score": 0}
    }


@pytest.fixture
def placeholder_pricing_plan_data():
    """Plan with pending commercial terms and pricing placeholders."""
    return {
        "plan_id": "plan_test_placeholder_001",
        "client_name": "Metro Transit Guild",
        "client_context": {
            "name": "Metro Transit Guild",
            "organization_type": "nonprofit",
            "sector": "community_services",
            "current_systems": ["Sage 50"],
            "target_systems": [],
            "engagement_type": "recurring",
            "complexity": "standard"
        },
        "approved_scope": {
            "bookkeeping": {"cadence": "monthly", "ap_ar": True}
        },
        "sections": [
            {
                "section_id": "sec_01",
                "section_title": "Accounting & Bookkeeping Services",
                "section_type": "service_scope",
                "service_family": "bookkeeping"
            }
        ],
        "pricing": {
            "pricing_model": "placeholder",
            "currency": "CAD",
            "billing_schedule": "Invoiced at the beginning of each service month.",
            "fee_items": [
                {
                    "category": "Monthly Recurring Retainer",
                    "amount": None,
                    "currency": "CAD",
                    "placeholder_token": "[PRICING_PLACEHOLDER: Monthly Retainer Fee (CAD)]",
                    "billing_frequency": "monthly",
                    "description": "Monthly recurring accounting fee to be confirmed upon final scope sign-off.",
                    "is_placeholder": True
                }
            ],
            "has_placeholders": True,
            "disclaimers": []
        }
    }


class TestWriterStyleInstructions:
    """Regression test suite for proposal writer consulting style instructions."""

    # --------------------------------------------------------------------------
    # Test 1: Enriched Proposals Receive Explicit Style Instructions
    # --------------------------------------------------------------------------
    def test_01_enriched_proposals_receive_style_instructions(self, enriched_plan_data):
        """
        Verifies that PromptBuilder.build_prompt() prepends the full suite of
        consulting writing style instructions before the proposal generation task.
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        # Style section header
        assert "SYMPL PROPOSAL WRITING STYLE & CONSULTING INSTRUCTIONS" in user_prompt
        assert "historical benchmark proposals (TACT, YPT, RPFF)" in user_prompt

        # Narrative-first architecture
        assert "A) NARRATIVE-FIRST ARCHITECTURE:" in user_prompt
        assert "substantive contextual paragraph in 'opening_text'" in user_prompt
        assert "NEVER begin a section immediately with a bullet list" in user_prompt

        # Bullet point control
        assert "B) BULLET POINT CONTROL & SELECTIVITY:" in user_prompt
        assert "Do NOT create bullet lists for:" in user_prompt
        assert "Executive summary: narrative only. Provide sufficient detail to explain the client's situation" in user_prompt

        # Consulting progression
        assert "C) SYMPL CONSULTING STYLE & PROGRESSION:" in user_prompt
        assert "Client Situation  -->  Business Challenge  -->  Sympl Approach  -->  Specific Deliverables" in user_prompt
        assert "Avoid generic, mechanical statements such as 'Sympl will provide bookkeeping services.'" in user_prompt
        assert "Given the organization's transition from internal bookkeeping operations" in user_prompt

        # Repetitive verb reduction
        assert "D) REDUCE REPETITIVE BULLETS (NATURAL CONSULTING LANGUAGE):" in user_prompt
        assert "Manage" in user_prompt and "Provide" in user_prompt and "Maintain" in user_prompt and "Ensure" in user_prompt

        # Preservation of invariants
        assert "E) PRESERVE INVARIANTS & INTEGRITY:" in user_prompt
        assert "[PRICING_PLACEHOLDER]" in user_prompt

    # --------------------------------------------------------------------------
    # Test 2: Narrative Context Appears in Enriched Writer Prompt
    # --------------------------------------------------------------------------
    def test_02_narrative_context_appears_in_writer_prompt(self, enriched_plan_data, oldt_fixture):
        """
        Ensures client situation summary, challenges summary, finance obstacles,
        and desired outcomes appear prominently in the constructed user prompt payload.
        """
        _, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        assert "Client Situation:" in user_prompt
        assert oldt_fixture["client_situation_summary"] in user_prompt

        assert "Client Challenges:" in user_prompt
        assert oldt_fixture["client_challenges_summary"] in user_prompt

        assert "Finance Challenges:" in user_prompt
        for fc in oldt_fixture["current_finance_challenges"]:
            assert fc in user_prompt

        assert "Desired Outcomes:" in user_prompt
        for do in oldt_fixture["desired_outcomes"]:
            assert do in user_prompt

        assert "Engagement Reason:" in user_prompt
        assert oldt_fixture["reason_for_engagement"] in user_prompt

        assert "Org Description:" in user_prompt
        assert oldt_fixture["organization_description"] in user_prompt

    # --------------------------------------------------------------------------
    # Test 3: Legacy Proposals Receive Style Instructions & Generate Successfully
    # --------------------------------------------------------------------------
    def test_03_legacy_proposals_receive_style_instructions_and_generate_successfully(self, legacy_plan_data):
        """
        Confirms legacy payloads without enriched narrative fields:
        1. Receive the consulting style instructions.
        2. Do NOT contain empty 'Client Situation:' headers.
        3. Successfully generate a validated ProposalDraft using ProposalWriter.
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(legacy_plan_data)

        # Style instructions are still present
        assert "SYMPL PROPOSAL WRITING STYLE & CONSULTING INSTRUCTIONS" in user_prompt
        assert "NARRATIVE-FIRST ARCHITECTURE" in user_prompt

        # Narrative context headers are omitted
        assert "Client Situation:" not in user_prompt
        assert "Client Challenges:" not in user_prompt
        assert "Finance Challenges:" not in user_prompt
        assert "Desired Outcomes:" not in user_prompt

        # Generate proposal with ProposalWriter
        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(legacy_plan_data)

        assert isinstance(draft, ProposalDraft)
        assert "Legacy Foundation" in draft.title or "Legacy Foundation" in draft.executive_summary
        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0

    # --------------------------------------------------------------------------
    # Test 4: Pricing Placeholders Remain Protected and Unchanged
    # --------------------------------------------------------------------------
    def test_04_pricing_placeholders_remain_unchanged(self, placeholder_pricing_plan_data):
        """
        Verifies that when fees are pending approval:
        1. Prompt instructs preservation of [PRICING_PLACEHOLDER].
        2. Draft contains [PRICING_PLACEHOLDER] and does not invent amounts.
        3. Pricing safety validator passes.
        """
        _, user_prompt = PromptBuilder.build_prompt(placeholder_pricing_plan_data)
        assert "[PRICING_PLACEHOLDER]" in user_prompt

        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(placeholder_pricing_plan_data)

        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0
        assert draft.pricing.get("has_placeholders") is True
        fee_items = draft.pricing.get("fee_items", [])
        assert any(item.get("is_placeholder") is True or item.get("amount") is None for item in fee_items)

    # --------------------------------------------------------------------------
    # Test 5: System Prompt Enforces Consulting Invariants
    # --------------------------------------------------------------------------
    def test_05_system_prompt_enforces_consulting_invariants(self):
        """
        Confirms PromptBuilder.SYSTEM_PROMPT incorporates consulting-style guidelines,
        references historical benchmarks (TACT, YPT, RPFF), and enforces narrative openings.
        """
        sp = PromptBuilder.SYSTEM_PROMPT

        assert "historical benchmark proposals (TACT, YPT, RPFF)" in sp
        assert "Client Situation -> Business Challenge -> Sympl Approach -> Specific Deliverables" in sp
        assert "Narrative-First Section Architecture:" in sp
        assert "Bullet Point Control & Natural Consulting Language:" in sp
        assert "Manage" in sp and "Provide" in sp and "Maintain" in sp and "Ensure" in sp

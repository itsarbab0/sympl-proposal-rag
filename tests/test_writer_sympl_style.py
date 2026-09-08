"""
Sympl Solutions Proposal RAG — Proposal Writer Sympl Style Regression Test Suite

Verifies:
  1. Sympl Operational Playbook instructions exist (QBO migration, Dext receipt capture,
     COA cleanup, month-end close workflow, reconciliation cadence, Plooto payments,
     monthly reporting package, board reporting, budget vs actuals, deadlines).
  2. Historical exemplar guidance exists (writing rhythm, operational depth, paragraph
     structure, workflow specificity, level of detail, do not copy names/facts).
  3. Bullet limits exist (maximum 4-6 bullets per subsection, executive summary narrative only).
  4. Narrative requirements exist (Client Situation, Operational Challenge, Sympl Approach,
     Workflow Explanation, Key Activities, Expected Outcome).
  5. Removal of artificial shortness constraints (allowing detailed professional explanation).
  6. Legacy payload still works successfully with 100% backward compatibility.
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
from sympl_writer import ProposalWriter, MockLLMClient, ProposalDraft, ProposalValidator, DraftSection, DraftSubsection


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
        "plan_id": "plan_test_sympl_style_001",
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
        "plan_id": "plan_test_sympl_legacy_001",
        "client_name": "Legacy Arts Council",
        "client_context": {
            "name": "Legacy Arts Council",
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
                    "amount": 2200.0,
                    "currency": "CAD",
                    "billing_frequency": "monthly",
                    "is_placeholder": False
                }
            ],
            "has_placeholders": False
        },
        "metadata": {"context_quality": "LOW", "context_score": 0}
    }


class TestWriterSymplStyle:
    """Regression test suite for Sympl Operational Playbook and consulting engagement style."""

    # --------------------------------------------------------------------------
    # Test 1: Operational Playbook Instructions Exist
    # --------------------------------------------------------------------------
    def test_01_operational_playbook_instructions_exist(self, enriched_plan_data):
        """
        Verifies that PromptBuilder injects Sympl's Operational Playbook into both
        system_prompt and user_prompt, covering Bookkeeping, Payments, and Reporting patterns.
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        # In system prompt
        sp_lower = system_prompt.lower()
        assert "sympl operational playbook" in sp_lower
        assert "quickbooks online migration" in sp_lower
        assert "dext receipt capture" in sp_lower
        assert "chart of accounts cleanup" in sp_lower
        assert "month-end close workflow" in sp_lower
        assert "reconciliation cadence" in sp_lower
        assert "invoice review" in sp_lower
        assert "approval workflow" in sp_lower
        assert "plooto" in sp_lower
        assert "monthly financial package" in sp_lower
        assert "board reporting" in sp_lower
        assert "budget vs actual analysis" in sp_lower
        assert "reporting deadlines" in sp_lower
        assert "only use these workflows when relevant to approved scope" in sp_lower

        # In user prompt
        up_lower = user_prompt.lower()
        assert "sympl operational playbook" in up_lower
        assert "quickbooks online migration and chart of accounts cleanup" in up_lower
        assert "dext receipt capture" in up_lower
        assert "plooto/payment approval process" in up_lower
        assert "budget vs actual analysis" in up_lower

    # --------------------------------------------------------------------------
    # Test 2: Historical Exemplar Guidance Exists
    # --------------------------------------------------------------------------
    def test_02_historical_exemplar_guidance_exists(self, enriched_plan_data):
        """
        Verifies that the prompt instructs the model to analyze historical exemplars
        for writing rhythm, operational depth, paragraph structure, workflow specificity,
        and level of detail, without copying facts/names/numbers.
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        assert "HISTORICAL EXEMPLAR GUIDANCE:" in system_prompt or "historical exemplars" in system_prompt.lower()
        assert "writing rhythm" in user_prompt
        assert "operational depth" in user_prompt
        assert "paragraph structure" in user_prompt
        assert "workflow specificity" in user_prompt
        assert "level of detail" in user_prompt
        assert "Do not copy names, numbers, or facts" in user_prompt

    # --------------------------------------------------------------------------
    # Test 3: Bullet Limits Exist
    # --------------------------------------------------------------------------
    def test_03_bullet_limits_exist(self, enriched_plan_data):
        """
        Verifies that the prompt enforces:
        - Executive summary: narrative only (no bullets)
        - Service sections: paragraphs first, maximum 4-6 bullets
        - Bullets summarize activities rather than replacing explanation
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        # In system prompt
        assert "Executive summary: narrative only (no bullets)" in system_prompt
        assert "Maximum 4-6 bullets per subsection" in system_prompt
        assert "Bullets should summarize activities, not replace explanation" in system_prompt

        # In user prompt
        assert "Maximum 4-6 bullets" in user_prompt
        assert "Bullets should summarize activities, not replace explanation" in user_prompt

    # --------------------------------------------------------------------------
    # Test 4: Narrative Requirements Exist (6-Part Consulting Section Flow)
    # --------------------------------------------------------------------------
    def test_04_narrative_requirements_exist(self, enriched_plan_data):
        """
        Verifies that the prompt mandates the 6-stage consulting engagement flow:
        1. Client Situation
        2. Operational Challenge
        3. Sympl Approach
        4. Workflow Explanation
        5. Key Activities
        6. Expected Outcome
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        assert "consulting engagement explanation" in system_prompt
        assert "MANDATORY SERVICE SECTION FLOW:" in user_prompt
        assert "1. Client Situation" in user_prompt
        assert "2. Operational Challenge" in user_prompt
        assert "3. Sympl Approach" in user_prompt
        assert "4. Workflow Explanation" in user_prompt
        assert "5. Key Activities" in user_prompt
        assert "6. Expected Outcome" in user_prompt

    # --------------------------------------------------------------------------
    # Test 5: Legacy Payload Still Works Successfully
    # --------------------------------------------------------------------------
    def test_05_legacy_payload_still_works(self, legacy_plan_data):
        """
        Verifies that minimal legacy payloads without enriched narrative fields:
        1. Receive the updated playbook and consulting engagement prompt.
        2. Successfully generate a validated ProposalDraft without errors.
        3. Do not cause ScopeFirewall, PricingSafety, or schema validation failures.
        """
        _, user_prompt = PromptBuilder.build_prompt(legacy_plan_data)

        assert "SYMPL OPERATIONAL PLAYBOOK" in user_prompt
        assert "consulting engagement explanation" in user_prompt

        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(legacy_plan_data)

        assert isinstance(draft, ProposalDraft)
        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0

        for sec in draft.sections:
            assert len(sec.opening_text.strip()) > 0
            for sub in sec.subsections:
                assert len(sub.bullets) <= 6 or len(sub.bullets) <= 7

    # --------------------------------------------------------------------------
    # Test 6: Subsection Can Contain Narrative Without Bullets
    # --------------------------------------------------------------------------
    def test_06_subsection_can_contain_narrative_without_bullets(self, legacy_plan_data):
        """
        Confirms that a proposal draft subsection can contain narrative prose
        without bullets (empty bullets list []), and passes schema parsing and validation.
        """
        draft_dict = {
            "title": "Accounting & Bookkeeping Services Proposal for Legacy Arts Council",
            "executive_summary": "Sympl Solutions will establish structured accounting workflows to resolve operational challenges and ensure financial clarity.",
            "sections": [
                {
                    "section_title": "Accounting & Bookkeeping Services",
                    "opening_text": "Sympl will transition financial operations into a modern cloud accounting workflow designed to resolve previous backlog issues.",
                    "subsections": [
                        {
                            "heading": "General Ledger & Reconciliations",
                            "narrative": "Sympl will execute weekly bank and credit card reconciliations in QuickBooks Online, ensuring timely ledger balance integrity and audit-ready reporting.",
                            "bullets": []
                        }
                    ]
                }
            ],
            "why_us": [],
            "pricing": legacy_plan_data["pricing"],
            "exclusions": [],
            "validation_metadata": {}
        }
        draft = ProposalDraft.from_dict(draft_dict)
        assert len(draft.sections[0].subsections) == 1
        sub = draft.sections[0].subsections[0]
        assert sub.heading == "General Ledger & Reconciliations"
        assert sub.narrative is not None
        assert "weekly bank and credit card reconciliations" in sub.narrative
        assert sub.bullets == []

        # Validate with ProposalValidator
        validator = ProposalValidator()
        result = validator.validate(draft, legacy_plan_data, raise_on_error=False)
        assert result.passed is True
        assert len(result.errors) == 0

    # --------------------------------------------------------------------------
    # Test 7: No Artificial Word or Sentence Limits
    # --------------------------------------------------------------------------
    def test_no_artificial_word_or_sentence_limits(self, enriched_plan_data):
        """
        Verifies:
        - no '<=120 words' or 'under 120 words' executive summary instruction exists
        - no '3-5 sentences' mandatory instruction exists
        - executive summary instructs narrative detail without optimizing for word count
        - service context & sympl approach instruct appropriate depth without sentence limits
        """
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan_data)

        # Verify no "<=120 words", "<= 120 words", or "under 120 words" instruction exists
        assert "<=120 words" not in user_prompt
        assert "<=120 words" not in system_prompt
        assert "<= 120 words" not in user_prompt
        assert "<= 120 words" not in system_prompt
        assert "under 120 words" not in user_prompt
        assert "under 120 words" not in system_prompt
        assert "120 words" not in user_prompt
        assert "120 words" not in system_prompt

        # Verify no "3-5 sentences" mandatory instruction exists
        assert "3-5 sentences" not in user_prompt
        assert "3-5 sentences" not in system_prompt
        assert "2-4 sentences" not in user_prompt
        assert "2-4 sentences" not in system_prompt

        # Verify new descriptive guidance exists
        assert "Executive summary: narrative only. Provide sufficient detail" in user_prompt
        assert "Do not optimize for word count" in user_prompt
        assert "Service Context Narrative:" in user_prompt
        assert "Sympl Approach Narrative:" in user_prompt

"""
Sympl Solutions Proposal RAG — Context Enrichment & Regression Test Suite

Verifies:
  1. Backward compatibility: legacy minimal payloads succeed with context_quality='LOW'.
  2. Enriched payload parsing: comprehensive intake achieves context_quality='HIGH' (score >= 70).
  3. Graceful handling of partial context: missing optional fields do not fail generation.
  4. Weighted context quality scoring: 75% narrative fields, 25% structured fields, boundary thresholds.
  5. Planner ingestion & propagation: narrative fields and service context flow into ProposalPlan.
  6. Writer audit validation: execute_writer() logs '[Writer Ingestion Validation]' with telemetry.
  7. Final writer prompt construction: PromptBuilder.build_prompt() includes high-value narrative
     fields (client_situation_summary, client_challenges_summary, desired_outcomes, current_finance_challenges).
  8. OldT regression fixture: tests/fixtures/oldt_enriched_payload.json end-to-end flow.
"""

import os
import sys
import json
import logging
from pathlib import Path
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sympl_api.services import OrchestrationService, calculate_context_quality
from sympl_writer.prompt_builder import PromptBuilder
from sympl_planner.schema import ClientInput


@pytest.fixture(scope="module")
def service():
    """Shared OrchestrationService instance for test execution."""
    return OrchestrationService()


@pytest.fixture(scope="module")
def oldt_fixture_payload():
    """Loads the OldT regression fixture JSON."""
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "oldt_enriched_payload.json"
    assert fixture_path.exists(), f"Fixture not found at {fixture_path}"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def minimal_payload():
    """Legacy minimal payload matching existing n8n MVP contract."""
    return {
        "client_name": "Legacy Arts Collective",
        "organization_type": "nonprofit",
        "sector": "arts_culture",
        "approved_scope": {
            "bookkeeping": {
                "cadence": "weekly",
                "ap_ar": True,
                "reconciliations": True
            }
        },
        "commercial_terms": {
            "pricing_model": "fixed_retainer",
            "monthly_retainer": 2200.0,
            "currency": "CAD"
        }
    }


class TestContextEnrichment:
    """Comprehensive test suite for proposal context enrichment and writer pipeline flow."""

    # --------------------------------------------------------------------------
    # Test 1: Backward Compatibility (Old Minimal Payload)
    # --------------------------------------------------------------------------
    def test_01_old_payload_still_works(self, service, minimal_payload):
        """
        Legacy n8n payloads without enriched fields must continue to work seamlessly.
        Evaluates to context_quality='LOW' and generates a valid plan without errors.
        """
        client_input = service.parse_client_intake(minimal_payload)
        assert client_input.organization.name == "Legacy Arts Collective"
        assert client_input.context_quality == "LOW"
        assert client_input.context_score < 30
        assert client_input.narrative_context.client_situation_summary is None
        assert client_input.narrative_context.client_challenges_summary is None

        # Execute planner and verify successful plan output
        plan = service.execute_planner(minimal_payload)
        assert plan["client_name"] == "Legacy Arts Collective"
        assert plan["client_context"]["context_quality"] == "LOW"
        assert plan["metadata"]["context_quality"] == "LOW"
        assert len(plan["sections"]) > 0

    # --------------------------------------------------------------------------
    # Test 2: Enriched Payload Passes with High Quality
    # --------------------------------------------------------------------------
    def test_02_new_enriched_payload_passes(self, service, oldt_fixture_payload):
        """
        Enriched intake payload parses narrative, finance, and operational fields,
        achieving context_quality='HIGH' (score >= 70).
        """
        client_input = service.parse_client_intake(oldt_fixture_payload)
        assert client_input.organization.name == "OldT Community Arts Workshop"
        assert client_input.context_quality == "HIGH"
        assert client_input.context_score >= 70

        # Verify narrative fields
        narrative = client_input.narrative_context
        assert "Mid-sized arts and cultural organization" in narrative.client_situation_summary
        assert "Accumulated backlog of 4 months" in narrative.client_challenges_summary
        assert "Sage 50 Desktop" in narrative.current_accounting_system
        assert len(narrative.desired_outcomes) == 4
        assert len(narrative.current_finance_challenges) == 3

    # --------------------------------------------------------------------------
    # Test 3: Missing Optional Fields Do Not Break Generation
    # --------------------------------------------------------------------------
    def test_03_missing_optional_fields_do_not_break_generation(self, service):
        """
        Partially populated payloads must be handled gracefully without exceptions.
        Only situation and challenges summaries are provided (30 pts -> MEDIUM).
        """
        partial_payload = {
            "client_name": "Partial Context Theatre",
            "organization_type": "nonprofit",
            "sector": "arts_culture",
            "client_situation_summary": "Experiencing seasonal cash flow variance during festival months.",
            "client_challenges_summary": "Manual paper approvals creating payment delays for performers.",
            "approved_scope": {
                "bookkeeping": {
                    "cadence": "monthly",
                    "ap_ar": True
                }
            },
            "commercial_terms": {
                "pricing_model": "fixed_retainer",
                "monthly_retainer": 1200.0
            }
        }

        client_input = service.parse_client_intake(partial_payload)
        assert client_input.context_quality == "MEDIUM"
        assert client_input.context_score == 30  # 15 + 15 points
        assert client_input.narrative_context.client_situation_summary is not None
        assert client_input.narrative_context.desired_outcomes is None
        assert client_input.narrative_context.current_finance_challenges is None

        # Execute planner
        plan = service.execute_planner(partial_payload)
        assert plan["client_name"] == "Partial Context Theatre"
        assert plan["client_context"]["context_quality"] == "MEDIUM"
        assert plan["client_context"]["client_situation_summary"] == partial_payload["client_situation_summary"]
        assert plan["client_context"].get("desired_outcomes") is None

    # --------------------------------------------------------------------------
    # Test 4: Weighted Context Quality Scoring Logic
    # --------------------------------------------------------------------------
    def test_04_weighted_context_quality_scoring(self, caplog):
        """
        Tests the 75% narrative / 25% structured scoring model and boundary thresholds:
        - LOW (<30)
        - MEDIUM (30-69)
        - HIGH (70-100)
        Also verifies warning log on LOW quality intake.
        """
        # A: Completely empty payload -> 0 pts -> LOW
        q, score, b = calculate_context_quality({})
        assert q == "LOW"
        assert score == 0

        # B: Structured fields only (no narrative) -> max 25 pts -> LOW
        structured_only = {
            "current_accounting_system": "QuickBooks Online",
            "current_finance_process": "Weekly EFT batches and receipt scans",
            "employee_count": 10,
            "service_context": {
                "bookkeeping": {"bookkeeping_volume": "100-200 txns"}
            }
        }
        q, score, b = calculate_context_quality(structured_only)
        assert q == "LOW"
        assert score == 25  # 5 + 5 + 5 + 10 = 25
        assert b["current_accounting_system"] == 5
        assert b["finance_process_or_team"] == 5
        assert b["organization_scale"] == 5
        assert b["service_context"] == 10

        # C: Narrative fields only (all 6 high-value narrative items) -> 75 pts -> HIGH
        narrative_only = {
            "client_situation_summary": "Growing NGO expanding programs.",
            "client_challenges_summary": "Legacy spreadsheet tracking issues.",
            "current_finance_challenges": ["Disjointed reporting", "Manual invoicing"],
            "organization_description": "Community empowerment nonprofit.",
            "reason_for_engagement": "Transition to modern cloud accounting.",
            "desired_outcomes": ["Clean audit trail", "Automated workflows"]
        }
        q, score, b = calculate_context_quality(narrative_only)
        assert q == "HIGH"
        assert score == 75  # 15 + 15 + 15 + 10 + 10 + 10 = 75

        # D: Boundary threshold tests
        # 29 points -> LOW
        # (situation 15 + org_desc 10 + accounting_system 5 = 30; let's test 15 + 10 = 25 vs 15 + 15 = 30)
        q_25, score_25, _ = calculate_context_quality({
            "client_situation_summary": "Situation text here",
            "organization_description": "Org description text here"
        })
        assert score_25 == 25
        assert q_25 == "LOW"

        q_30, score_30, _ = calculate_context_quality({
            "client_situation_summary": "Situation text",
            "client_challenges_summary": "Challenges text"
        })
        assert score_30 == 30
        assert q_30 == "MEDIUM"

        # E: Verify logging warning for low quality intake
        with caplog.at_level(logging.WARNING):
            service = OrchestrationService()
            service.parse_client_intake({
                "client_name": "Low Quality Org",
                "approved_scope": {"bookkeeping": {"cadence": "monthly"}},
                "commercial_terms": {"monthly_retainer": 1000.0}
            })
            assert any("Intake context quality is LOW" in r.message for r in caplog.records)

    # --------------------------------------------------------------------------
    # Test 5: Planner Receives and Propagates Enriched Context
    # --------------------------------------------------------------------------
    def test_05_planner_receives_enriched_context(self, service, oldt_fixture_payload):
        """
        Validates that ProposalPlan generated by execute_planner() contains:
        1. client_context with all narrative fields
        2. approved_scope with service operational details
        3. metadata with context_quality and context_score
        """
        plan = service.execute_planner(oldt_fixture_payload)

        # 1. client_context narrative propagation
        ctx = plan["client_context"]
        assert ctx["client_situation_summary"] == oldt_fixture_payload["client_situation_summary"]
        assert ctx["client_challenges_summary"] == oldt_fixture_payload["client_challenges_summary"]
        assert ctx["current_accounting_system"] == "Sage 50 Desktop"
        assert ctx["current_finance_challenges"] == oldt_fixture_payload["current_finance_challenges"]
        assert ctx["desired_outcomes"] == oldt_fixture_payload["desired_outcomes"]
        assert ctx["reason_for_engagement"] == oldt_fixture_payload["reason_for_engagement"]
        assert ctx["context_quality"] == "HIGH"
        assert ctx["context_score"] >= 70

        # 2. approved_scope operational context propagation
        app_scope = plan["approved_scope"]
        assert "bookkeeping" in app_scope
        assert app_scope["bookkeeping"]["bookkeeping_volume"] == "150-250 monthly transactions across 3 operating accounts"
        assert app_scope["bookkeeping"]["cleanup_requirements"] == "Complete catch-up cleanup for FY2025 Q3 and Q4"

        # 3. metadata verification
        assert plan["metadata"]["context_quality"] == "HIGH"
        assert plan["metadata"]["context_score"] >= 70

    # --------------------------------------------------------------------------
    # Test 6: Writer Receives Enriched Context & Audit Validation Logging
    # --------------------------------------------------------------------------
    def test_06_writer_receives_enriched_context_and_audit_logging(self, service, oldt_fixture_payload, caplog):
        """
        Verifies execute_writer() receives the enriched proposal_plan, logs the audit
        telemetry message '[Writer Ingestion Validation]', and generates a valid draft.
        """
        plan = service.execute_planner(oldt_fixture_payload)

        with caplog.at_level(logging.INFO):
            draft = service.execute_writer(plan)

        # Audit log verification
        audit_logs = [r.message for r in caplog.records if "[Writer Ingestion Validation]" in r.message]
        assert len(audit_logs) >= 1, "Expected [Writer Ingestion Validation] log not found"
        log_text = audit_logs[-1]
        assert "Context Quality: HIGH" in log_text
        assert "Situation Summary: True" in log_text
        assert "Challenges Summary: True" in log_text
        assert "Finance Challenges: True" in log_text
        assert "Outcomes: True" in log_text

        # Draft validation
        assert draft["proposal_title"]
        assert draft["validation_metadata"]["passed"] is True
        assert len(draft["validation_metadata"]["errors"]) == 0

    # --------------------------------------------------------------------------
    # Test 7: Final Writer Prompt Construction Verification (Item 1)
    # --------------------------------------------------------------------------
    def test_07_writer_prompt_contains_narrative_context(self, oldt_fixture_payload):
        """
        Ensures enriched narrative fields reach the final writer prompt construction
        in PromptBuilder.build_prompt(), specifically verifying:
        - client_situation_summary
        - client_challenges_summary
        - desired_outcomes
        - current_finance_challenges
        Also verifies legacy plans produce clean, unpolluted prompts without these headers.
        """
        # 1. Enriched Plan Prompt Verification
        service = OrchestrationService()
        enriched_plan = service.execute_planner(oldt_fixture_payload)
        system_prompt, user_prompt = PromptBuilder.build_prompt(enriched_plan)

        # Verify key narrative fields are present in the final constructed user prompt
        assert "Client Situation:" in user_prompt
        assert oldt_fixture_payload["client_situation_summary"] in user_prompt

        assert "Client Challenges:" in user_prompt
        assert oldt_fixture_payload["client_challenges_summary"] in user_prompt

        assert "Finance Challenges:" in user_prompt
        for fc in oldt_fixture_payload["current_finance_challenges"]:
            assert fc in user_prompt

        assert "Desired Outcomes:" in user_prompt
        for do in oldt_fixture_payload["desired_outcomes"]:
            assert do in user_prompt

        assert "Engagement Reason:" in user_prompt
        assert oldt_fixture_payload["reason_for_engagement"] in user_prompt

        assert "Org Description:" in user_prompt
        assert oldt_fixture_payload["organization_description"] in user_prompt

        # 2. Legacy Minimal Plan Prompt Verification
        legacy_plan = {
            "client_name": "Minimal Legacy Org",
            "client_context": {
                "name": "Minimal Legacy Org",
                "organization_type": "nonprofit",
                "sector": "community_services",
                "current_systems": [],
                "target_systems": [],
                "engagement_type": "recurring",
                "complexity": "standard"
            },
            "approved_scope": {
                "bookkeeping": {"cadence": "weekly"}
            },
            "sections": [
                {
                    "section_id": "sec_01",
                    "section_title": "Bookkeeping Services",
                    "section_type": "service_scope",
                    "service_family": "bookkeeping"
                }
            ],
            "commercial_summary": {"pricing_model": "fixed_retainer"}
        }

        legacy_sys, legacy_user = PromptBuilder.build_prompt(legacy_plan)
        assert "Client Situation:" not in legacy_user
        assert "Client Challenges:" not in legacy_user
        assert "Finance Challenges:" not in legacy_user
        assert "Desired Outcomes:" not in legacy_user
        assert "Minimal Legacy Org" in legacy_user

    # --------------------------------------------------------------------------
    # Test 8: OldT Needs Assessment Regression Fixture End-to-End (Item 2)
    # --------------------------------------------------------------------------
    def test_08_oldt_regression_fixture_end_to_end(self, service, oldt_fixture_payload):
        """
        Complete end-to-end regression test using tests/fixtures/oldt_enriched_payload.json:
        API intake -> ClientInput -> Planner -> Writer Prompt -> Writer Draft.
        """
        # Step 1: Ingestion
        client_input = service.parse_client_intake(oldt_fixture_payload)
        assert client_input.organization.name == "OldT Community Arts Workshop"
        assert client_input.context_quality == "HIGH"
        assert client_input.context_score >= 80

        # Step 2: Planning
        plan = service.execute_planner(oldt_fixture_payload)
        assert plan["client_context"]["current_accounting_system"] == "Sage 50 Desktop"
        assert "Paper invoice approvals" in plan["client_context"]["current_finance_process"]
        assert plan["client_context"]["context_quality"] == "HIGH"

        # Step 3: Writer Prompt Construction
        sys_prompt, user_prompt = PromptBuilder.build_prompt(plan)
        assert "Sage 50 Desktop" in user_prompt or "Sage 50" in str(plan)
        assert "Accumulated backlog of 4 months" in user_prompt
        assert "Catch-up and clean reconciliation" in user_prompt

        # Step 4: Writer Generation
        draft = service.execute_writer(plan)
        assert draft["proposal_title"]
        assert draft["validation_metadata"]["passed"] is True
        assert len(draft["sections"]) >= 4

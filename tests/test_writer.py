"""
Sympl Solutions Proposal RAG — Proposal Writer Test Suite (Phase 4)

Covers all 11 required test scenarios:
  Test 1:  Compact bookkeeping proposal
  Test 2:  Nonprofit proposal with Why Us
  Test 3:  Arts organization proposal
  Test 4:  Transformation proposal
  Test 5:  Transition proposal
  Test 6:  Audit proposal
  Test 7:  Pending pricing placeholder
  Test 8:  Unapproved scope rejection (Scope Firewall)
  Test 9:  Historical leakage detection (Historical Firewall)
  Test 10: Provider switching (Mock, Ollama, OpenRouter)
  Test 11: Database invariant check (Zero DB modifications)
"""

import os
import sys
import json
import copy
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sympl_planner.schema import (
    ClientInput,
    OrganizationInfo,
    EngagementContext,
    ScopeContainer,
    BookkeepingScope,
    PayrollScope,
    ReportingScope,
    ComplianceScope,
    TransformationScope,
    TrainingScope,
    TransitionScope,
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.engine import ProposalPlanner

from sympl_writer import (
    ProposalWriter,
    ProposalDraft,
    DraftSection,
    DraftSubsection,
    ProposalValidator,
    MockLLMClient,
    get_llm_client,
    ScopeFirewallError,
    HistoricalLeakageError,
    ScopeViolationError,
    MissingApprovedScopeItemError,
    PricingSafetyError,
    StyleViolationError,
    ReferenceBlockTamperingError
)


class TestProposalWriter:
    """Test suite for Phase 4 Sympl Proposal Writer layer."""

    @classmethod
    def setup_class(cls):
        cls.planner = ProposalPlanner()
        cls.validator = ProposalValidator()
        cls.writer = ProposalWriter(llm_client=MockLLMClient())

    # --------------------------------------------------------------------------
    # Test 1: Compact bookkeeping proposal
    # --------------------------------------------------------------------------
    def test_01_compact_bookkeeping_proposal(self):
        """Validates generation and validation of a lean bookkeeping proposal."""
        client_input = ClientInput(
            client_id="TEST_01_COMPACT",
            organization=OrganizationInfo(
                name="Oakridge Neighborhood Association",
                organization_type="nonprofit",
                sector="community_services",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="compact"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=1850.0,
                include_backlog_exclusion=True
            ),
            preferences=Preferences(include_why_us=False)
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert "Oakridge" in draft.title or "Oakridge" in draft.executive_summary
        assert any("Bookkeeping" in s.section_title or "Accounting" in s.section_title for s in draft.sections)
        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0

    # --------------------------------------------------------------------------
    # Test 2: Nonprofit proposal with Why Us
    # --------------------------------------------------------------------------
    def test_02_nonprofit_proposal_with_why_us(self):
        """Validates standard nonprofit proposal including exact Why Us reference blocks."""
        client_input = ClientInput(
            client_id="TEST_02_NONPROFIT",
            organization=OrganizationInfo(
                name="Evergreen Community Care",
                organization_type="nonprofit",
                sector="community_services"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=2800.0
            ),
            preferences=Preferences(include_why_us=True)
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert len(draft.why_us) > 0
        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0

    # --------------------------------------------------------------------------
    # Test 3: Arts organization
    # --------------------------------------------------------------------------
    def test_03_arts_organization_proposal(self):
        """Validates proposal tailored for an arts & culture nonprofit."""
        client_input = ClientInput(
            client_id="TEST_03_ARTS",
            organization=OrganizationInfo(
                name="Lakeside Cultural Festival",
                organization_type="nonprofit",
                sector="arts_culture"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="semi_monthly", ap_ar=True, reconciliations=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="semi_monthly", ap_ar=True, reconciliations=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=2500.0
            ),
            preferences=Preferences(include_why_us=True)
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert draft.validation_metadata["passed"] is True
        assert len(draft.validation_metadata["errors"]) == 0

    # --------------------------------------------------------------------------
    # Test 4: Transformation proposal
    # --------------------------------------------------------------------------
    def test_04_transformation_proposal(self):
        """Validates systems transformation proposal with digital workflows and migrations."""
        client_input = ClientInput(
            client_id="TEST_04_TRANSFORM",
            organization=OrganizationInfo(
                name="Toronto Community Arts Collective",
                organization_type="nonprofit",
                sector="community_services",
                current_systems=["Manual Paper", "Excel"],
                target_systems=["QuickBooks Online", "Dext", "Wagepoint"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="comprehensive"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=12),
                digital_transformation=TransformationScope(
                    system_migrations=["QuickBooks Online Setup", "Dext Expense Ingestion"],
                    workflow_redesign=True
                )
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=12),
                digital_transformation=TransformationScope(
                    system_migrations=["QuickBooks Online Setup", "Dext Expense Ingestion"],
                    workflow_redesign=True
                )
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=3800.0,
                setup_fee=1500.0
            )
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert any("Transformation" in s.section_title or "Digital" in s.section_title for s in draft.sections)
        assert any("Payroll" in s.section_title for s in draft.sections)
        assert draft.validation_metadata["passed"] is True

    # --------------------------------------------------------------------------
    # Test 5: Transition proposal
    # --------------------------------------------------------------------------
    def test_05_transition_proposal(self):
        """Validates transition / interim financial management proposal."""
        client_input = ClientInput(
            client_id="TEST_05_TRANSITION",
            organization=OrganizationInfo(
                name="Metro Social Housing Society",
                organization_type="nonprofit",
                sector="community_services"
            ),
            engagement=EngagementContext(
                engagement_type="interim",
                complexity="standard",
                fixed_term_duration="6 months"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                transition=TransitionScope(
                    onboarding_duration_weeks=6,
                    handover_continuity=True
                )
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                transition=TransitionScope(
                    onboarding_duration_weeks=6,
                    handover_continuity=True
                )
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=4200.0
            )
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert any("Transition" in s.section_title or "Interim" in s.section_title or "Summary" in s.section_title for s in draft.sections)
        assert draft.validation_metadata["passed"] is True

    # --------------------------------------------------------------------------
    # Test 6: Audit proposal
    # --------------------------------------------------------------------------
    def test_06_audit_proposal(self):
        """Validates audit preparation and oversight proposal."""
        client_input = ClientInput(
            client_id="TEST_06_AUDIT",
            organization=OrganizationInfo(
                name="Alliance for Community Wellbeing",
                organization_type="nonprofit",
                sector="community_services"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="comprehensive"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                compliance=ComplianceScope(gst_hst_filing=True, audit_support=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                compliance=ComplianceScope(gst_hst_filing=True, audit_support=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=3400.0
            )
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert any("Audit" in s.section_title or "Compliance" in s.section_title for s in draft.sections)
        assert draft.validation_metadata["passed"] is True

    # --------------------------------------------------------------------------
    # Test 7: Pending pricing placeholder
    # --------------------------------------------------------------------------
    def test_07_pending_pricing_placeholder(self):
        """Validates that placeholder pricing is preserved with no invented numbers."""
        client_input = ClientInput(
            client_id="TEST_07_PLACEHOLDER",
            organization=OrganizationInfo(
                name="Downtown Youth Action",
                organization_type="nonprofit",
                sector="community_services"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="compact"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="placeholder"
            )
        )

        plan = self.planner.plan(client_input)
        plan_dict = json.loads(plan.to_json(for_writer=True))

        draft = self.writer.write(plan_dict)

        assert draft.pricing.get("has_placeholders") is True
        # Verify no invented amount
        fee_items = draft.pricing.get("fee_items", [])
        assert any(item.get("is_placeholder") is True or item.get("amount") is None for item in fee_items)
        assert draft.validation_metadata["passed"] is True

    # --------------------------------------------------------------------------
    # Test 8: Unapproved scope rejection (Scope Firewall)
    # --------------------------------------------------------------------------
    def test_08_unapproved_scope_rejection(self):
        """Validates that plans containing requested_scope or unapproved_requested_scope are rejected."""
        # A plan directly serialized with requested_scope
        forbidden_plan_1 = {
            "client_context": {"name": "Test Client"},
            "approved_scope": {"bookkeeping": {"cadence": "weekly"}},
            "requested_scope": {"payroll": {"headcount": 10}},  # FORBIDDEN
            "sections": []
        }

        with pytest.raises(ScopeFirewallError):
            self.writer.write(forbidden_plan_1)

        forbidden_plan_2 = {
            "client_context": {"name": "Test Client"},
            "approved_scope": {"bookkeeping": {"cadence": "weekly"}},
            "unapproved_requested_scope": [{"service_family": "payroll"}],  # FORBIDDEN
            "sections": []
        }

        with pytest.raises(ScopeFirewallError):
            self.writer.write(forbidden_plan_2)

    # --------------------------------------------------------------------------
    # Test 9: Historical leakage detection (Historical Firewall)
    # --------------------------------------------------------------------------
    def test_09_historical_leakage_detection(self):
        """Validates that historical client names, years (2025/2026), and headcounts are detected and rejected."""
        base_plan = {
            "client_context": {"name": "Safe Client"},
            "approved_scope": {"bookkeeping": {"cadence": "weekly", "ap_ar": True}},
            "sections": [],
            "pricing": {"pricing_model": "fixed_retainer", "fee_items": []}
        }

        # 1. Leakage of historical code TACT
        draft_tact = ProposalDraft(
            title="Proposal for Safe Client",
            executive_summary="We delivered similar operational success for TACT during their audit.",
            sections=[],
            why_us=[],
            pricing={},
            exclusions=[]
        )
        with pytest.raises(HistoricalLeakageError):
            self.validator.validate(draft_tact, base_plan, raise_on_error=True)

        # 2. Leakage of historical year 2025
        draft_2025 = ProposalDraft(
            title="Proposal for Safe Client",
            executive_summary="Services commence in the 2025 fiscal year cycle.",
            sections=[],
            why_us=[],
            pricing={},
            exclusions=[]
        )
        with pytest.raises(HistoricalLeakageError):
            self.validator.validate(draft_2025, base_plan, raise_on_error=True)

        # 3. Leakage of historical headcount
        draft_headcount = ProposalDraft(
            title="Proposal for Safe Client",
            executive_summary="We support the organization with 19 employees on biweekly payroll.",
            sections=[],
            why_us=[],
            pricing={},
            exclusions=[]
        )
        with pytest.raises(HistoricalLeakageError):
            self.validator.validate(draft_headcount, base_plan, raise_on_error=True)

        # 4. Leakage of historical client name CAHOOTS
        draft_cahoots = ProposalDraft(
            title="Proposal for Safe Client",
            executive_summary="Our experience working with Cahoots Theatre provides relevant domain context.",
            sections=[],
            why_us=[],
            pricing={},
            exclusions=[]
        )
        with pytest.raises(HistoricalLeakageError):
            self.validator.validate(draft_cahoots, base_plan, raise_on_error=True)

    # --------------------------------------------------------------------------
    # Test 10: Provider switching
    # --------------------------------------------------------------------------
    def test_10_provider_switching(self):
        """Validates multi-provider abstraction and instantiation."""
        # 1. Mock provider
        mock_client = get_llm_client("mock")
        assert mock_client.provider_name == "mock"
        assert mock_client.model_name == "mock-sympl-v1"

        # 2. Ollama provider
        ollama_client = get_llm_client("ollama", model="llama3.2")
        assert ollama_client.provider_name == "ollama"
        assert ollama_client.model_name == "llama3.2"

        # 3. OpenRouter provider
        openrouter_client = get_llm_client("openrouter", api_key="sk-test", model="google/gemini-flash-1.5")
        assert openrouter_client.provider_name == "openrouter"
        assert openrouter_client.model_name == "google/gemini-flash-1.5"

        # 4. Invalid provider
        with pytest.raises(ValueError) as excinfo:
            get_llm_client("anthropic_direct")
        assert "Unsupported LLM provider" in str(excinfo.value)

        # 5. Respects environment variable
        orig_env = os.environ.get("LLM_PROVIDER")
        try:
            os.environ["LLM_PROVIDER"] = "mock"
            env_client = get_llm_client()
            assert env_client.provider_name == "mock"
        finally:
            if orig_env:
                os.environ["LLM_PROVIDER"] = orig_env
            else:
                os.environ.pop("LLM_PROVIDER", None)

    # --------------------------------------------------------------------------
    # Test 11: Database invariant check
    # --------------------------------------------------------------------------
    def test_11_database_invariants_post_writer(self):
        """
        Verifies that running the writer layer made ZERO modifications to:
          - proposal_documents (must be 7)
          - proposal_chunks (must be 71)
          - embeddings (must be 47)
          - dataset_imports (must be 7)
          - sympl_style_rules (must be 21)
          - sympl_reference_blocks (must be 13)
        """
        import psycopg
        from sympl_planner.retrieval import DATABASE_URL

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM proposal_documents;")
                docs_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks;")
                chunks_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM dataset_imports;")
                imports_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM sympl_style_rules;")
                rules_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM sympl_reference_blocks;")
                refs_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL;")
                embedded_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM proposal_chunks WHERE retrieval_enabled = false AND embedding IS NOT NULL;")
                unsafe_embedded = cur.fetchone()[0]

        assert docs_count == 7, "proposal_documents must remain 7"
        assert chunks_count == 71, "proposal_chunks must remain 71"
        assert imports_count == 7, "dataset_imports must remain 7"
        assert rules_count == 21, "sympl_style_rules must remain 21"
        assert refs_count == 13, "sympl_reference_blocks must remain 13"
        assert embedded_count == 47, "embedded chunks must remain exactly 47"
        assert unsafe_embedded == 0, "unsafe embedded must remain 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

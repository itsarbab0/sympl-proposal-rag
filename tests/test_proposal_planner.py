"""
Sympl Solutions Proposal RAG — Proposal Planner Synthetic Test Suite (unittest)

Validates:
  1. Archetype Precedence Priority System across all 5 archetypes.
  2. Scope Firewall: requested vs approved scope separation and unapproved item logging.
  3. Retrieval Chunk Attachment: 1-3 exemplars per section, cleaned_text strictly under retrieval_context.exemplars.
  4. Commercial Terms: pricing categories only appear from approved commercial inputs; placeholders when pending.
  5. Dynamic Why Us inclusion: not hardcoded by archetype; variant selection for charity, nonprofit, arts, and community.
  6. Excluded sections with explicit audit reasons.
  7. Confidence metadata and validation flags.
  8. Preserved invariants (zero mutation to DB records, embeddings, benchmark, style rules, reference blocks).
"""

import os
import sys
import json
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


class TestProposalPlanner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.planner = ProposalPlanner()

    def test_scenario_1_compact_bookkeeping_unapproved_requested(self):
        """
        Scenario 1: Compact Bookkeeping Only with Unapproved Requested Scope & Backlog Exclusion
        - Prospect requested payroll, but leadership approved ONLY bookkeeping.
        - Placeholder pricing.
        - Archetype must be ARCH_COMPACT_BOOKKEEPING.
        - Payroll must appear in excluded_sections and unapproved_requested_scope.
        """
        client_input = ClientInput(
            client_id="SCENARIO_001",
            organization=OrganizationInfo(
                name="Meadowvale Community Hub",
                organization_type="nonprofit",
                sector="community_services",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="compact"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="biweekly", headcount_employees=8)  # Requested in intake!
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True)
                # Payroll explicitly omitted by leadership
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="placeholder",
                include_backlog_exclusion=True
            ),
            preferences=Preferences(
                include_why_us=False  # Direct preference for lean schedule
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_COMPACT_BOOKKEEPING")
        self.assertLess(plan.confidence_metadata.scope_alignment_score, 1.0)
        self.assertIn("UNAPPROVED_REQUESTED_ITEMS_PRESENT", plan.confidence_metadata.flags)
        self.assertEqual(len(plan.unapproved_requested_scope), 1)
        self.assertEqual(plan.unapproved_requested_scope[0]["service_family"], "payroll")

        # Verify excluded sections
        excluded_types = [e.section_type for e in plan.excluded_sections]
        self.assertIn("payroll", excluded_types)
        payroll_ex = next(e for e in plan.excluded_sections if e.section_type == "payroll")
        self.assertEqual(payroll_ex.reason, "SCOPE_NOT_APPROVED_BY_LEADERSHIP")

        # Verify sections present
        sec_types = [s.section_type for s in plan.sections]
        self.assertIn("operational_schedule", sec_types)
        self.assertNotIn("payroll", sec_types)
        self.assertIn("pricing", sec_types)
        self.assertIn("exclusions", sec_types)

        # Verify exclusions block attached
        excl_sec = next(s for s in plan.sections if s.section_type == "exclusions")
        block_keys = [b["block_key"] for b in excl_sec.reference_blocks]
        self.assertIn("REF_BLOCK_EXCLUSIONS_BACKLOG", block_keys)

        # Verify cleaned_text strictly placed only inside exemplars
        for sec in plan.sections:
            self.assertFalse(hasattr(sec, "cleaned_text"))
            if sec.retrieval_context:
                self.assertTrue(1 <= len(sec.retrieval_context.exemplars) <= 3)
                for ex in sec.retrieval_context.exemplars:
                    self.assertIsNotNone(ex.cleaned_text)
                    self.assertGreater(len(ex.cleaned_text), 0)

    def test_scenario_2_compact_bookkeeping_charity_approved_pricing(self):
        """
        Scenario 2: Compact Bookkeeping with Approved Fees (Registered Charity)
        - Fixed approved fee categories ($1,850/mo, $500 setup).
        - Why Us explicitly requested.
        - Must select REF_BLOCK_WHY_US_EXP_CHARITY (not nonprofit).
        """
        client_input = ClientInput(
            client_id="SCENARIO_002",
            organization=OrganizationInfo(
                name="St. Jude Literacy Foundation",
                organization_type="charity",
                sector="literacy",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="compact"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="biweekly", ap_ar=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="biweekly", ap_ar=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=1850.0,
                setup_fee=500.0,
                approved_categories=["monthly_retainer", "setup_fee"]
            ),
            preferences=Preferences(
                include_why_us=True
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_COMPACT_BOOKKEEPING")
        self.assertFalse(plan.commercial_summary["has_placeholders"])
        self.assertEqual(len(plan.commercial_summary["fee_items"]), 2)
        self.assertEqual(plan.commercial_summary["fee_items"][0]["amount"], 1850.0)
        self.assertEqual(plan.commercial_summary["fee_items"][1]["amount"], 500.0)

        # Verify charity Why Us block
        self.assertIn("REF_BLOCK_WHY_US_EXP_CHARITY", plan.reference_block_manifest)
        self.assertNotIn("REF_BLOCK_WHY_US_EXP_NONPROFIT", plan.reference_block_manifest)

    def test_scenario_3_standard_nonprofit_recurring_accounting(self):
        """
        Scenario 3: Standard Nonprofit Recurring Accounting (Social Services)
        - Full recurring scope: Bookkeeping + Payroll + Reporting + Compliance.
        - Archetype must be ARCH_STANDARD_NONPROFIT.
        - Why Us includes community/social lived experiences.
        - Software fee pass-through and payroll HR boundary disclaimers attached.
        """
        client_input = ClientInput(
            client_id="SCENARIO_003",
            organization=OrganizationInfo(
                name="Toronto Community Care Society",
                organization_type="nonprofit",
                sector="social_services",
                current_systems=["QuickBooks Online", "Wagepoint"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="monthly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=12, sympl_processes_payroll=True, manager_input_responsibility=True, hr_functions_excluded=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True),
                compliance=ComplianceScope(gst_hst_filing=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="monthly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=12, sympl_processes_payroll=True, manager_input_responsibility=True, hr_functions_excluded=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True),
                compliance=ComplianceScope(gst_hst_filing=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=3200.0,
                software_fees_excluded=True
            ),
            preferences=Preferences()  # Dynamic decision: standard nonprofit -> include Why Us
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_STANDARD_NONPROFIT")
        self.assertIn("REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL", plan.reference_block_manifest)
        self.assertIn("REF_BLOCK_EXCLUSIONS_SOFTWARE_NOT_INCLUDED", plan.reference_block_manifest)
        self.assertIn("REF_BLOCK_PAYROLL_HR_BOUNDARY", plan.reference_block_manifest)

        # Verify section sequence
        sec_types = [s.section_type for s in plan.sections]
        self.assertEqual(sec_types[0], "context_objectives")
        self.assertIn("bookkeeping", sec_types)
        self.assertIn("payroll", sec_types)
        self.assertIn("financial_reporting", sec_types)
        self.assertIn("compliance", sec_types)
        self.assertIn("why_us", sec_types)
        self.assertIn("pricing", sec_types)
        self.assertIn("exclusions", sec_types)

    def test_scenario_4_standard_nonprofit_arts_national(self):
        """
        Scenario 4: Standard Nonprofit Arts Organization with National Scope
        - Sector: arts_culture, national scope in description.
        - Must select REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP and REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF.
        """
        client_input = ClientInput(
            client_id="SCENARIO_004",
            organization=OrganizationInfo(
                name="Canadian Contemporary Arts Guild",
                organization_type="charity",
                sector="arts_culture",
                description="National community arts organization operating across Canada.",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="monthly"),
                financial_reporting=ReportingScope(cadence="quarterly", funder_tracking=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="monthly"),
                financial_reporting=ReportingScope(cadence="quarterly", funder_tracking=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="placeholder"
            ),
            preferences=Preferences(
                identity_credential_preference="arts_leadership"
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_STANDARD_NONPROFIT")
        self.assertIn("REF_BLOCK_WHY_US_SECTOR_ARTS_LEADERSHIP", plan.reference_block_manifest)
        self.assertIn("REF_BLOCK_WHY_US_SECTOR_ARTS_EXP_RPFF", plan.reference_block_manifest)
        self.assertNotIn("REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL", plan.reference_block_manifest)

    def test_scenario_5_transition_interim_engagement(self):
        """
        Scenario 5: Interim Handover / Transition Engagement
        - Precedence Priority 1 must trigger: ARCH_TRANSITION_INTERIM.
        - Frame around Summary of Engagement and Transition Milestones.
        """
        client_input = ClientInput(
            client_id="SCENARIO_005",
            organization=OrganizationInfo(
                name="Eastside Youth Alliance",
                organization_type="nonprofit",
                sector="community_services"
            ),
            engagement=EngagementContext(
                engagement_type="interim",
                complexity="standard",
                fixed_term_duration="6 months"
            ),
            requested_scope=ScopeContainer(
                transition=TransitionScope(onboarding_duration_weeks=4, handover_continuity=True, legacy_shadowing=True),
                bookkeeping=BookkeepingScope(cadence="monthly")
            ),
            approved_scope=ScopeContainer(
                transition=TransitionScope(onboarding_duration_weeks=4, handover_continuity=True, legacy_shadowing=True),
                bookkeeping=BookkeepingScope(cadence="monthly")
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=2900.0
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_TRANSITION_INTERIM")
        self.assertEqual(plan.precedence_applied["selected_archetype"], "ARCH_TRANSITION_INTERIM")
        sec_types = [s.section_type for s in plan.sections]
        self.assertIn("transition", sec_types)
        self.assertEqual(sec_types[0], "context_objectives")  # Summary of engagement

    def test_scenario_6_comprehensive_transformation_migration(self):
        """
        Scenario 6: Comprehensive Digital Transformation (Systems Migration)
        - System migration from legacy Sage to QBO + Dext.
        - Precedence Priority 3 must trigger: ARCH_COMPREHENSIVE_TRANSFORMATION.
        - Modular sections: Part A Transformation, Part C Training.
        """
        client_input = ClientInput(
            client_id="SCENARIO_006",
            organization=OrganizationInfo(
                name="Metro Health Alliance",
                organization_type="nonprofit",
                sector="health",
                current_systems=["Sage 50"],
                target_systems=["QuickBooks Online", "Dext"]
            ),
            engagement=EngagementContext(
                engagement_type="transformation",
                complexity="comprehensive"
            ),
            requested_scope=ScopeContainer(
                digital_transformation=TransformationScope(
                    system_migrations=["Sage 50 to QuickBooks Online", "Receipt Bank/Dext integration"],
                    workflow_redesign=True
                ),
                training=TrainingScope(
                    target_roles=["Operations Director", "Bookkeeper"],
                    sop_documentation=True,
                    post_golive_support_weeks=4
                )
            ),
            approved_scope=ScopeContainer(
                digital_transformation=TransformationScope(
                    system_migrations=["Sage 50 to QuickBooks Online", "Receipt Bank/Dext integration"],
                    workflow_redesign=True
                ),
                training=TrainingScope(
                    target_roles=["Operations Director", "Bookkeeper"],
                    sop_documentation=True,
                    post_golive_support_weeks=4
                )
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="phased_milestone",
                setup_fee=4500.0,
                approved_categories=["setup_fee"]
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_COMPREHENSIVE_TRANSFORMATION")
        sec_types = [s.section_type for s in plan.sections]
        self.assertIn("digital_transformation", sec_types)
        self.assertIn("training", sec_types)

    def test_scenario_7_comprehensive_multi_workstream(self):
        """
        Scenario 7: Comprehensive Multi-Workstream (Transformation + Ongoing Ops + Training)
        - Transformation + Ongoing Bookkeeping + Payroll + Training.
        - Precedence Priority 3: ARCH_COMPREHENSIVE_TRANSFORMATION.
        - Verifies 1-3 exemplars attached per section with similarity scores.
        """
        client_input = ClientInput(
            client_id="SCENARIO_007",
            organization=OrganizationInfo(
                name="Community Housing Collective",
                organization_type="charity",
                sector="social_services",
                current_systems=["Manual Paper", "Excel"],
                target_systems=["QuickBooks Online", "Wagepoint"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="comprehensive"
            ),
            requested_scope=ScopeContainer(
                digital_transformation=TransformationScope(
                    system_migrations=["Spreadsheets to QuickBooks Online"],
                    workflow_redesign=True
                ),
                bookkeeping=BookkeepingScope(cadence="monthly", ap_ar=True),
                payroll=PayrollScope(cadence="biweekly", headcount_employees=15),
                training=TrainingScope(sop_documentation=True)
            ),
            approved_scope=ScopeContainer(
                digital_transformation=TransformationScope(
                    system_migrations=["Spreadsheets to QuickBooks Online"],
                    workflow_redesign=True
                ),
                bookkeeping=BookkeepingScope(cadence="monthly", ap_ar=True),
                payroll=PayrollScope(cadence="biweekly", headcount_employees=15),
                training=TrainingScope(sop_documentation=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=4200.0,
                setup_fee=2500.0,
                include_backlog_exclusion=True
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_COMPREHENSIVE_TRANSFORMATION")
        sec_types = [s.section_type for s in plan.sections]
        self.assertIn("digital_transformation", sec_types)
        self.assertIn("bookkeeping", sec_types)
        self.assertIn("training", sec_types)

        # Verify exemplars attached to service sections
        retrieval_sections = [s for s in plan.sections if s.retrieval_context is not None]
        self.assertGreaterEqual(len(retrieval_sections), 2)
        for s in retrieval_sections:
            self.assertTrue(1 <= len(s.retrieval_context.exemplars) <= 3)
            roles = [ex.role for ex in s.retrieval_context.exemplars]
            self.assertIn("primary", roles)

    def test_scenario_8_audit_oversight_diagnostic(self):
        """
        Scenario 8: Audit Oversight & Internal Controls Diagnostic
        - Diagnostic focus on internal_controls and audit_readiness.
        - Approved compliance audit_support and diagnostic cleanup.
        - Precedence Priority 2 must trigger: ARCH_AUDIT_OVERSIGHT_TRANSFORMATION.
        """
        client_input = ClientInput(
            client_id="SCENARIO_008",
            organization=OrganizationInfo(
                name="Ontario Immigrant Support Services",
                organization_type="nonprofit",
                sector="social_services"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="comprehensive",
                diagnostic_focus=["internal_controls", "audit_readiness"]
            ),
            requested_scope=ScopeContainer(
                compliance=ComplianceScope(audit_support=True, audit_response_sla="1-2 business days"),
                bookkeeping=BookkeepingScope(cadence="monthly", catchup_cleanup=True)
            ),
            approved_scope=ScopeContainer(
                compliance=ComplianceScope(audit_support=True, audit_response_sla="1-2 business days"),
                bookkeeping=BookkeepingScope(cadence="monthly", catchup_cleanup=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="placeholder"
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.selected_archetype, "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION")
        sec_types = [s.section_type for s in plan.sections]
        self.assertIn("financial_management", sec_types)  # Diagnostic reconciliation tasks
        self.assertIn("compliance", sec_types)            # Audit readiness

    def test_scenario_9_commercial_social_enterprise_credentials_suppression(self):
        """
        Scenario 9: Commercial / For-Profit Social Enterprise (USD Currency)
        - Organization type: for_profit.
        - Verifies suppression of nonprofit/charity credentials in Why Us.
        - Verifies USD currency preservation.
        """
        client_input = ClientInput(
            client_id="SCENARIO_009",
            organization=OrganizationInfo(
                name="EcoTech Innovations Inc.",
                organization_type="for_profit",
                sector="environmental"
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="compact"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="monthly")
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="monthly")
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                currency="USD",
                monthly_retainer=2400.0
            ),
            preferences=Preferences(
                include_why_us=True,
                identity_credential_preference="none"
            )
        )

        plan = self.planner.plan(client_input)

        self.assertEqual(plan.commercial_summary["currency"], "USD")
        self.assertEqual(plan.commercial_summary["fee_items"][0]["amount"], 2400.0)
        self.assertEqual(plan.commercial_summary["fee_items"][0]["currency"], "USD")

        # Verify Why Us excludes nonprofit / charity bullets
        why_sec = next(s for s in plan.sections if s.section_type == "why_us")
        block_keys = [b["block_key"] for b in why_sec.reference_blocks]
        self.assertNotIn("REF_BLOCK_WHY_US_EXP_NONPROFIT", block_keys)
        self.assertNotIn("REF_BLOCK_WHY_US_EXP_CHARITY", block_keys)
        self.assertNotIn("REF_BLOCK_WHY_US_SECTOR_COMM_SOCIAL", block_keys)

    def test_scenario_10_minimum_viable_intake_edge_case(self):
        """
        Scenario 10: Minimum Viable Intake Edge Case
        - Minimal client input (missing optional fields, all defaults).
        - Must safely default without throwing exceptions.
        - Default archetype ARCH_COMPACT_BOOKKEEPING.
        - Emits structured pricing placeholders.
        """
        client_input = ClientInput(
            client_id="SCENARIO_010",
            organization=OrganizationInfo(
                name="Acme Org",
                organization_type="unspecified",
                sector="other"
            ),
            engagement=EngagementContext(),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope()
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope()
            ),
            commercial_terms=ApprovedCommercialInputs()
        )

        plan = self.planner.plan(client_input)

        self.assertTrue(plan.plan_id.startswith("plan_"))
        self.assertEqual(plan.selected_archetype, "ARCH_COMPACT_BOOKKEEPING")
        self.assertTrue(plan.commercial_summary["has_placeholders"])
        self.assertIn("PRICING_PLACEHOLDERS_ACTIVE", plan.confidence_metadata.flags)
        self.assertGreaterEqual(len(plan.sections), 2)

    def test_frozen_database_invariants_post_planner(self):
        """
        Verifies that running the planner made ZERO modifications to:
          - embeddings
          - retrieval benchmark
          - style rules
          - reference blocks
          - proposal documents & chunks
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

        self.assertEqual(docs_count, 7, "proposal_documents must remain 7")
        self.assertEqual(chunks_count, 71, "proposal_chunks must remain 71")
        self.assertEqual(imports_count, 7, "dataset_imports must remain 7")
        self.assertEqual(rules_count, 21, "sympl_style_rules must remain 21")
        self.assertEqual(refs_count, 13, "sympl_reference_blocks must remain 13")
        self.assertEqual(embedded_count, 47, "embedded chunks must remain exactly 47")
        self.assertEqual(unsafe_embedded, 0, "unsafe embedded must remain 0")


if __name__ == "__main__":
    unittest.main()

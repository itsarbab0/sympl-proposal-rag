#!/usr/bin/env python3
"""
Generates the canonical sample proposal_plan.json using the Sympl Proposal Planner.
"""

import json
import sys
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
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.engine import ProposalPlanner


def generate_canonical_plan():
    client_input = ClientInput(
        client_id="SAMPLE_INTAKE_001",
        organization=OrganizationInfo(
            name="Harbourfront Community & Arts Services",
            organization_type="nonprofit",
            sector="community_services",
            description="Multi-service community organization providing social programs and community arts workshops across Toronto.",
            current_systems=["QuickBooks Online", "Manual Timesheets"],
            target_systems=["QuickBooks Online", "Wagepoint", "Dext"]
        ),
        engagement=EngagementContext(
            engagement_type="recurring",
            complexity="comprehensive",
            diagnostic_focus=["workflow_efficiency"]
        ),
        requested_scope=ScopeContainer(
            bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True, expense_management=True),
            payroll=PayrollScope(
                cadence="semi_monthly",
                headcount_employees=14,
                headcount_contractors=4,
                migration_parallel_run=True,
                sympl_processes_payroll=True,
                manager_input_responsibility=True,
                hr_functions_excluded=True
            ),
            financial_reporting=ReportingScope(
                cadence="monthly",
                funder_tracking=True,
                class_department_tracking=True,
                board_package=True,
                budget_vs_actual=True
            ),
            compliance=ComplianceScope(
                gst_hst_filing=True,
                audit_support=True
            ),
            digital_transformation=TransformationScope(
                system_migrations=["Wagepoint Payroll Setup & Parallel Run", "Dext Expense Ingestion"],
                workflow_redesign=True
            )
        ),
        approved_scope=ScopeContainer(
            bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True, expense_management=True),
            payroll=PayrollScope(
                cadence="semi_monthly",
                headcount_employees=14,
                headcount_contractors=4,
                migration_parallel_run=True,
                sympl_processes_payroll=True,
                manager_input_responsibility=True,
                hr_functions_excluded=True
            ),
            financial_reporting=ReportingScope(
                cadence="monthly",
                funder_tracking=True,
                class_department_tracking=True,
                board_package=True,
                budget_vs_actual=True
            ),
            compliance=ComplianceScope(
                gst_hst_filing=True,
                audit_support=True
            ),
            digital_transformation=TransformationScope(
                system_migrations=["Wagepoint Payroll Setup & Parallel Run", "Dext Expense Ingestion"],
                workflow_redesign=True
            )
        ),
        commercial_terms=ApprovedCommercialInputs(
            pricing_model="fixed_retainer",
            currency="CAD",
            monthly_retainer=3650.0,
            setup_fee=1500.0,
            billing_schedule="Monthly retainer invoiced on the 1st of each service month.",
            approved_categories=["monthly_retainer", "setup_fee"],
            include_backlog_exclusion=True,
            software_fees_excluded=True
        ),
        preferences=Preferences(
            is_competitive_pitch=True,
            identity_credential_preference="community_social"
        )
    )

    planner = ProposalPlanner()
    plan = planner.plan(client_input)

    output_path = Path("proposal_plan.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(plan.to_json(indent=2, for_writer=True))

    print(f"Successfully generated canonical proposal plan: {output_path}")
    print(f"Plan ID:            {plan.plan_id}")
    print(f"Selected Archetype: {plan.selected_archetype}")
    print(f"Sections Count:     {len(plan.sections)}")
    print(f"Confidence Score:   {plan.confidence_metadata.overall_confidence}")
    print(f"Why Us Blocks:      {len(plan.reference_block_manifest)}")


if __name__ == "__main__":
    generate_canonical_plan()

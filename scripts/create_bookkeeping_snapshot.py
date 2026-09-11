#!/usr/bin/env python3
"""
Generate Bookkeeping Retrieval Regression Snapshot

Captures current retrieval outputs (proposal codes, section families, similarity ranking)
for benchmark bookkeeping profiles (TACT, RPFF, CAHOOTS, YPT, PIRS) BEFORE modifying retrieval.
Saves to tests/fixtures/bookkeeping_regression_snapshot.json.
"""

import sys
import os
import json
from pathlib import Path
import psycopg

# Add root directory to sys.path
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
    TransitionScope,
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.retrieval import ExemplarRetriever, DATABASE_URL

BENCHMARK_PROFILES = [
    {
        "id": "TACT",
        "archetype": "ARCH_COMPREHENSIVE_TRANSFORMATION",
        "client_input": ClientInput(
            client_id="BENCHMARK_TACT",
            organization=OrganizationInfo(
                name="The Autism Centre of Toronto",
                organization_type="nonprofit",
                sector="community_services",
                current_systems=["QuickBooks Desktop", "ADP"]
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="comprehensive"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                digital_transformation=TransformationScope(system_migrations=["QuickBooks Online", "WagePoint"], workflow_redesign=True),
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=19, migration_parallel_run=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True),
                compliance=ComplianceScope(gst_hst_filing=True, audit_support=True),
                transition=TransitionScope(onboarding_duration_weeks=6, handover_continuity=True)
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer")
        ),
        "families": [
            ("digital_transformation", "digital_transformation"),
            ("bookkeeping", "bookkeeping"),
            ("payroll", "payroll"),
            ("financial_reporting", "financial_reporting"),
            ("compliance", "compliance"),
            ("transition", "transition")
        ]
    },
    {
        "id": "RPFF",
        "archetype": "ARCH_STANDARD_NONPROFIT",
        "client_input": ClientInput(
            client_id="BENCHMARK_RPFF",
            organization=OrganizationInfo(
                name="Regent Park Film Festival",
                organization_type="charity",
                sector="arts_culture",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="standard"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="biweekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=4),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True),
                compliance=ComplianceScope(gst_hst_filing=True, audit_support=True)
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer")
        ),
        "families": [
            ("bookkeeping", "bookkeeping"),
            ("payroll", "payroll"),
            ("financial_reporting", "financial_reporting"),
            ("compliance", "compliance")
        ]
    },
    {
        "id": "CAHOOTS",
        "archetype": "ARCH_COMPACT_BOOKKEEPING",
        "client_input": ClientInput(
            client_id="BENCHMARK_CAHOOTS",
            organization=OrganizationInfo(
                name="Cahoots Theatre Company",
                organization_type="nonprofit",
                sector="arts_culture",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="compact"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="biweekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="semi_monthly", headcount_employees=3),
                compliance=ComplianceScope(gst_hst_filing=True)
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer")
        ),
        "families": [
            ("bookkeeping", "bookkeeping"),
            ("payroll", "payroll"),
            ("compliance", "compliance")
        ]
    },
    {
        "id": "YPT",
        "archetype": "ARCH_TRANSITION_INTERIM",
        "client_input": ClientInput(
            client_id="BENCHMARK_YPT",
            organization=OrganizationInfo(
                name="Young People's Theatre",
                organization_type="charity",
                sector="arts_culture",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="comprehensive"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="biweekly", headcount_employees=25),
                financial_reporting=ReportingScope(cadence="monthly", board_package=True),
                transition=TransitionScope(onboarding_duration_weeks=4, handover_continuity=True)
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer")
        ),
        "families": [
            ("bookkeeping", "bookkeeping"),
            ("payroll", "payroll"),
            ("financial_reporting", "financial_reporting"),
            ("transition", "transition")
        ]
    },
    {
        "id": "PIRS",
        "archetype": "ARCH_AUDIT_OVERSIGHT_TRANSFORMATION",
        "client_input": ClientInput(
            client_id="BENCHMARK_PIRS",
            organization=OrganizationInfo(
                name="Pacific Immigrant Resources Society",
                organization_type="nonprofit",
                sector="community_services",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(engagement_type="recurring", complexity="comprehensive"),
            requested_scope=ScopeContainer(),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                financial_reporting=ReportingScope(cadence="monthly", funder_tracking=True, board_package=True),
                compliance=ComplianceScope(gst_hst_filing=True, audit_support=True)
            ),
            commercial_terms=ApprovedCommercialInputs(pricing_model="fixed_retainer")
        ),
        "families": [
            ("bookkeeping", "bookkeeping"),
            ("financial_reporting", "financial_reporting"),
            ("compliance", "compliance")
        ]
    }
]

def generate_snapshot():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1] if DATABASE_URL else 'None'}")
    snapshot = {}

    with psycopg.connect(DATABASE_URL) as conn:
        for profile in BENCHMARK_PROFILES:
            pid = profile["id"]
            arch = profile["archetype"]
            c_input = profile["client_input"]
            snapshot[pid] = {
                "archetype": arch,
                "sections": {}
            }
            print(f"\nCapturing baseline for {pid} ({arch})...")

            for fam, sec_type in profile["families"]:
                ctx = ExemplarRetriever.attach_exemplars_to_section(
                    conn=conn,
                    service_family=fam,
                    section_type=sec_type,
                    target_archetype=arch,
                    client_input=c_input
                )

                if ctx and ctx.exemplars:
                    exemplars_summary = []
                    for ex in ctx.exemplars:
                        exemplars_summary.append({
                            "role": ex.role,
                            "proposal_code": ex.proposal_code,
                            "chunk_key": ex.chunk_key,
                            "section_type": ex.section_type,
                            "similarity_score": round(ex.similarity_score, 4)
                        })
                    snapshot[pid]["sections"][fam] = {
                        "section_type": sec_type,
                        "candidate_pool_size": ctx.candidate_pool_size,
                        "exemplars": exemplars_summary
                    }
                    codes = [e["proposal_code"] for e in exemplars_summary]
                    print(f"  [{fam}] -> {codes} (pool size: {ctx.candidate_pool_size})")
                else:
                    snapshot[pid]["sections"][fam] = None
                    print(f"  [{fam}] -> None")

    out_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "bookkeeping_regression_snapshot.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\nSnapshot successfully written to: {out_path}")

if __name__ == "__main__":
    generate_snapshot()

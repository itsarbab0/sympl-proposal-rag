"""
Tests Phase 2C Domain Narrative Decoupling & Dynamic Historical Benchmark Injection.

Verifies:
  A. Planner passes domain metadata:
     - service_category
     - generic_services
     - resolved domain information
     - approved_scope.generic_services
  B. Website prompt:
     - contains: CRAWFORD_2026 and website terminology
     - does NOT contain: QBO, Dext, Plooto, TACT, YPT, RPFF
  C. Data prompt:
     - contains: AKM_2026 and data terminology
     - does NOT contain: accounting workflows (AP/AR, month-end close, reconciliations, QBO, Dext, Plooto)
  D. Accounting prompt:
     - remains byte-identical to pre-Phase 2A baseline snapshot
  E. Executive summaries differ by domain:
     - Accounting: mentions bookkeeping/reporting
     - Website: mentions CMS, UX, collector journey
     - Data: mentions SQL warehouse, dashboards, ETL
     - Finance: mentions forecasting, budgeting, assumptions
     - Zero generic fallback accounting boilerplate in non-accounting proposals
"""

import os
import json
import pytest
from pathlib import Path

# Force offline mode for transformers/huggingface if imported transitively
os.environ["HF_HUB_OFFLINE"] = "1"

from sympl_planner.schema import (
    ClientInput,
    OrganizationInfo,
    EngagementContext,
    ScopeContainer,
    BookkeepingScope,
    PayrollScope,
    ReportingScope,
    ComplianceScope,
    GenericServiceScope,
    ApprovedCommercialInputs,
    Preferences
)
from sympl_planner.engine import ProposalPlanner
from sympl_writer.prompt_builder import PromptBuilder
from sympl_writer.writer import ProposalWriter
from sympl_writer.llm_client import MockLLMClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "prompt_snapshot_phase2a_baseline.json"


@pytest.fixture
def snapshot_data():
    """Loads pre-Phase 2A baseline prompt snapshot."""
    assert FIXTURE_PATH.exists(), f"Snapshot fixture missing at {FIXTURE_PATH}"
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestDomainNarrativeDecoupling:
    """Test suite for Phase 2C narrative decoupling and domain isolation."""

    # -------------------------------------------------------------------------
    # A. Planner passes domain metadata
    # -------------------------------------------------------------------------
    def test_planner_passes_domain_metadata_website(self):
        """Verify planner correctly extracts and serializes domain metadata for Website Development."""
        planner = ProposalPlanner()
        client_input = ClientInput(
            client_id="TEST_PLANNER_WEB",
            organization=OrganizationInfo(
                name="Crawford Contemporary Art",
                organization_type="commercial_creative",
                sector="arts_culture",
                current_systems=["Squarespace 7.0"]
            ),
            engagement=EngagementContext(
                engagement_type="project",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Website Development",
                        service_name="Website Redesign & CMS Architecture",
                        deliverables=["Mobile-responsive portfolio", "Headless CMS setup", "Collector inquiry pathway"],
                        requirements=["High-resolution artwork photography", "SEO metadata tagging"],
                        target_systems=["Squarespace", "Stripe"]
                    )
                ]
            ),
            approved_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Website Development",
                        service_name="Website Redesign & CMS Architecture",
                        deliverables=["Mobile-responsive portfolio", "Headless CMS setup", "Collector inquiry pathway"],
                        requirements=["High-resolution artwork photography", "SEO metadata tagging"],
                        target_systems=["Squarespace", "Stripe"]
                    )
                ]
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=3500.0
            ),
            service_category="Website Development"
        )

        plan = planner.plan(client_input)

        # 1. Top-level plan fields
        assert plan.service_category == "Website Development"
        assert plan.generic_services is not None
        assert len(plan.generic_services) == 1
        assert plan.generic_services[0]["service_category"] == "Website Development"
        assert plan.generic_services[0]["service_name"] == "Website Redesign & CMS Architecture"

        # 2. Approved scope and client context
        assert plan.client_context.get("service_category") == "Website Development"
        assert "generic_services" in plan.approved_scope
        assert len(plan.approved_scope["generic_services"]) == 1

        # 3. Serialization for writer
        writer_payload = plan.to_dict(for_writer=True)
        assert writer_payload["service_category"] == "Website Development"
        assert writer_payload["generic_services"] == plan.generic_services
        assert writer_payload["approved_scope"]["generic_services"] == plan.generic_services
        assert writer_payload["client_context"]["service_category"] == "Website Development"

    def test_planner_passes_domain_metadata_data_analytics(self):
        """Verify planner correctly extracts and serializes domain metadata for Data Analytics."""
        planner = ProposalPlanner()
        client_input = ClientInput(
            client_id="TEST_PLANNER_DATA",
            organization=OrganizationInfo(
                name="AKM Cultural Insights",
                organization_type="nonprofit",
                sector="arts_culture",
                current_systems=["AudienceView", "Mailchimp"]
            ),
            engagement=EngagementContext(
                engagement_type="project",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Data Analytics",
                        service_name="Data Warehouse Architecture & Dashboards",
                        deliverables=["SQL warehouse setup", "Automated ETL", "Power BI dashboards"],
                        target_systems=["PostgreSQL", "Power BI"]
                    )
                ]
            ),
            approved_scope=ScopeContainer(
                generic_services=[
                    GenericServiceScope(
                        service_category="Data Analytics",
                        service_name="Data Warehouse Architecture & Dashboards",
                        deliverables=["SQL warehouse setup", "Automated ETL", "Power BI dashboards"],
                        target_systems=["PostgreSQL", "Power BI"]
                    )
                ]
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=4200.0
            ),
            service_category="Data Analytics"
        )

        plan = planner.plan(client_input)
        writer_payload = plan.to_dict(for_writer=True)

        assert writer_payload["service_category"] == "Data Analytics"
        assert len(writer_payload["generic_services"]) == 1
        assert writer_payload["generic_services"][0]["service_category"] == "Data Analytics"
        assert writer_payload["approved_scope"]["generic_services"][0]["service_name"] == "Data Warehouse Architecture & Dashboards"

    def test_planner_preserves_accounting_payload(self):
        """Verify existing accounting payload remains unchanged."""
        planner = ProposalPlanner()
        client_input = ClientInput(
            client_id="TEST_PLANNER_ACCT",
            organization=OrganizationInfo(
                name="Heritage Foundation",
                organization_type="nonprofit",
                sector="community_services",
                current_systems=["QuickBooks Online"]
            ),
            engagement=EngagementContext(
                engagement_type="recurring",
                complexity="standard"
            ),
            requested_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="biweekly", headcount_employees=8, sympl_processes_payroll=True)
            ),
            approved_scope=ScopeContainer(
                bookkeeping=BookkeepingScope(cadence="weekly", ap_ar=True, reconciliations=True),
                payroll=PayrollScope(cadence="biweekly", headcount_employees=8, sympl_processes_payroll=True)
            ),
            commercial_terms=ApprovedCommercialInputs(
                pricing_model="fixed_retainer",
                monthly_retainer=2200.0
            )
        )

        plan = planner.plan(client_input)
        writer_payload = plan.to_dict(for_writer=True)

        assert "bookkeeping" in writer_payload["approved_scope"]
        assert "payroll" in writer_payload["approved_scope"]
        assert writer_payload["approved_scope"]["bookkeeping"]["ap_ar"] is True
        assert writer_payload["approved_scope"]["payroll"]["headcount_employees"] == 8

    # -------------------------------------------------------------------------
    # B. Website prompt isolation & benchmark injection
    # -------------------------------------------------------------------------
    def test_website_prompt_contains_benchmarks_and_no_accounting(self):
        """
        Website prompt MUST:
        - contain: CRAWFORD_2026, website terminology (Squarespace, collector, CMS, portfolio)
        - NOT contain: QBO, Dext, Plooto, TACT, YPT, RPFF, AP/bookkeeping examples
        """
        web_plan = {
            "client_name": "Gary Crawford Art Gallery",
            "service_category": "Website Development",
            "client_context": {
                "name": "Gary Crawford Art Gallery",
                "organization_type": "commercial_creative",
                "sector": "arts_culture",
                "current_systems": ["Squarespace 7.0"],
                "target_systems": ["Squarespace 7.1", "Stripe"],
                "engagement_type": "project",
                "complexity": "standard",
                "service_category": "Website Development"
            },
            "approved_scope": {
                "generic_services": [
                    {
                        "service_category": "Website Development",
                        "service_name": "Website Redesign & CMS Architecture",
                        "deliverables": ["Collector journey navigation", "Portfolio showcase", "Available Now catalog"]
                    }
                ]
            },
            "sections": [
                {
                    "section_id": "sec_1",
                    "section_title": "Website Redesign & CMS Architecture",
                    "section_type": "architecture",
                    "service_family": "website",
                    "structural_role": "modular_service",
                    "section_instructions": ["Focus on collector experience and CMS autonomy"],
                    "style_rules_applied": []
                }
            ],
            "pricing": {
                "pricing_model": "fixed_retainer",
                "fee_items": [
                    {
                        "category": "Project Fee",
                        "amount": 3500.0,
                        "currency": "CAD",
                        "billing_frequency": "one_time",
                        "description": "Website redesign as scoped.",
                        "is_placeholder": False
                    }
                ]
            }
        }

        sys_prompt, user_prompt = PromptBuilder.build_prompt(web_plan)
        combined_prompt = f"{sys_prompt}\n{user_prompt}"

        # Must contain
        assert "CRAWFORD_2026" in combined_prompt
        assert "Squarespace" in combined_prompt
        assert "collector" in combined_prompt.lower()
        assert "cms" in combined_prompt.lower()
        assert "portfolio" in combined_prompt.lower()
        assert "Collector Journey / CMS Architecture" in user_prompt

        # Must NOT contain accounting software / benchmarks / workflows
        assert "QBO" not in combined_prompt
        assert "Dext" not in combined_prompt
        assert "Plooto" not in combined_prompt
        assert "TACT" not in combined_prompt
        assert "YPT" not in combined_prompt
        assert "RPFF" not in combined_prompt
        assert "Accounts Payable & Vendor Disbursement Workflow" not in combined_prompt
        assert "bookkeeping" not in combined_prompt.lower()

    # -------------------------------------------------------------------------
    # C. Data prompt isolation & benchmark injection
    # -------------------------------------------------------------------------
    def test_data_prompt_contains_benchmarks_and_no_accounting(self):
        """
        Data prompt MUST:
        - contain: AKM_2026, data terminology (SQL, data warehouse, Power BI, ETL, dashboard)
        - NOT contain: accounting workflows (Accounts Payable, Accounts Receivable, month-end close, QBO, Dext, Plooto, TACT)
        """
        data_plan = {
            "client_name": "AKM Heritage Organization",
            "service_category": "Data Analytics",
            "client_context": {
                "name": "AKM Heritage Organization",
                "organization_type": "nonprofit",
                "sector": "arts_culture",
                "current_systems": ["AudienceView", "Raiser's Edge"],
                "target_systems": ["Azure Canada Central SQL", "Power BI"],
                "engagement_type": "project",
                "complexity": "standard",
                "service_category": "Data Analytics"
            },
            "approved_scope": {
                "generic_services": [
                    {
                        "service_category": "Data Analytics",
                        "service_name": "Data Architecture & Reporting Framework",
                        "deliverables": ["SQL data warehouse", "Automated ETL pipelines", "Executive Power BI dashboards"]
                    }
                ]
            },
            "sections": [
                {
                    "section_id": "sec_1",
                    "section_title": "Data Warehouse Architecture & Dashboards",
                    "section_type": "data_analytics",
                    "service_family": "data_analytics",
                    "structural_role": "modular_service",
                    "section_instructions": ["Centralize constituent databases"],
                    "style_rules_applied": []
                }
            ],
            "pricing": {
                "pricing_model": "fixed_retainer",
                "fee_items": [
                    {
                        "category": "Implementation Retainer",
                        "amount": 4500.0,
                        "currency": "CAD",
                        "billing_frequency": "monthly",
                        "description": "Data architecture and dashboard configuration.",
                        "is_placeholder": False
                    }
                ]
            }
        }

        sys_prompt, user_prompt = PromptBuilder.build_prompt(data_plan)
        combined_prompt = f"{sys_prompt}\n{user_prompt}"

        # Must contain
        assert "AKM_2026" in combined_prompt
        assert "SQL" in combined_prompt
        assert "data warehouse" in combined_prompt.lower()
        assert "Power BI" in combined_prompt
        assert "ETL" in combined_prompt
        assert "dashboard" in combined_prompt.lower()
        assert "Data Warehouse / Dashboard Architecture" in user_prompt

        # Must NOT contain accounting software / benchmarks / workflows
        assert "QBO" not in combined_prompt
        assert "Dext" not in combined_prompt
        assert "Plooto" not in combined_prompt
        assert "TACT" not in combined_prompt
        assert "YPT" not in combined_prompt
        assert "RPFF" not in combined_prompt
        assert "Accounts Payable" not in combined_prompt
        assert "Accounts Receivable" not in combined_prompt
        assert "month-end close" not in combined_prompt.lower()
        assert "bookkeeping" not in combined_prompt.lower()

    # -------------------------------------------------------------------------
    # D. Accounting prompt remains byte-identical
    # -------------------------------------------------------------------------
    def test_accounting_prompt_byte_identical(self, snapshot_data):
        """Verify accounting prompts match baseline snapshot character-for-character."""
        input_plan = snapshot_data["input_plan"]
        baseline_sys = snapshot_data["oldt_system_prompt"]
        baseline_user = snapshot_data["oldt_user_prompt"]

        current_sys, current_user = PromptBuilder.build_prompt(input_plan)

        assert current_sys == baseline_sys, "Accounting system prompt diverged from baseline snapshot!"
        assert current_user == baseline_user, "Accounting user prompt diverged from baseline snapshot!"
        assert PromptBuilder.SYSTEM_PROMPT == snapshot_data["system_prompt_raw"]

    # -------------------------------------------------------------------------
    # E. Executive summaries differ by domain
    # -------------------------------------------------------------------------
    def test_executive_summaries_differ_by_domain(self):
        """
        Verify generated executive summaries are tailored per domain:
        - Accounting mentions QBO/Dext/Plooto or bookkeeping/reporting
        - Website mentions CMS, UX, collector journey
        - Data mentions SQL warehouse, dashboards, ETL
        - Finance mentions forecasting, budgeting, assumptions
        - No generic boilerplate in non-accounting proposals
        """
        client = MockLLMClient()

        # Generate Website Proposal
        web_resp_raw = client.generate(
            prompt="title: Website Development Proposal for Crawford Gallery\nservice_category: Website Development\nCRAWFORD_2026\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"generic_services\": [{\"service_category\": \"Website Development\"}]}"
        )
        web_data = json.loads(web_resp_raw)
        web_exec = web_data["executive_summary"]

        # Generate Data Analytics Proposal
        data_resp_raw = client.generate(
            prompt="title: Data Analytics & Centralized Database Proposal for AKM Centre\nservice_category: Data Analytics\nAKM_2026\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"generic_services\": [{\"service_category\": \"Data Analytics\"}]}"
        )
        data_data = json.loads(data_resp_raw)
        data_exec = data_data["executive_summary"]

        # Generate Finance Transformation Proposal
        fin_resp_raw = client.generate(
            prompt="title: Budget Revamp & Financial Forecasting Proposal for Compass Centre\nservice_category: Finance Transformation\nCOMPASS_2026\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"generic_services\": [{\"service_category\": \"Finance Transformation\"}]}"
        )
        fin_data = json.loads(fin_resp_raw)
        fin_exec = fin_data["executive_summary"]

        # Generate Accounting Proposal
        acct_resp_raw = client.generate(
            prompt="title: Accounting & Bookkeeping Services Proposal for OldT Arts\nClient Name: OldT Arts\n--- APPROVED SERVICE SCOPE (AUTHORITATIVE & COMPLETE) ---\n{\"bookkeeping\": {\"cadence\": \"weekly\"}, \"payroll\": {\"cadence\": \"biweekly\"}}"
        )
        acct_data = json.loads(acct_resp_raw)
        acct_exec = acct_data["executive_summary"]

        # 1. All executive summaries are distinct
        assert len({web_exec, data_exec, fin_exec, acct_exec}) == 4

        # 2. Website domain vocabulary
        assert "cms" in web_exec.lower()
        assert "ux" in web_exec.lower()
        assert "collector" in web_exec.lower()

        # 3. Data Analytics domain vocabulary
        assert "sql warehouse" in data_exec.lower() or "sql" in data_exec.lower()
        assert "dashboard" in data_exec.lower()
        assert "etl" in data_exec.lower()

        # 4. Finance Transformation domain vocabulary
        assert "forecasting" in fin_exec.lower() or "forecast" in fin_exec.lower()
        assert "budget" in fin_exec.lower()
        assert "assumptions" in fin_exec.lower()

        # 5. Non-accounting summaries must NOT contain generic fallback boilerplate
        generic_boilerplate = "disciplined operational workflows, accurate deliverables, and structured reporting to establish transparent oversight"
        assert generic_boilerplate not in web_exec
        assert generic_boilerplate not in data_exec
        assert generic_boilerplate not in fin_exec

        # 6. Non-accounting summaries must not leak accounting tools
        for non_acct_exec in [web_exec, data_exec, fin_exec]:
            assert "qbo" not in non_acct_exec.lower()
            assert "dext" not in non_acct_exec.lower()
            assert "plooto" not in non_acct_exec.lower()
            assert "bookkeeping" not in non_acct_exec.lower()

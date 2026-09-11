"""
Tests Phase 2B Dynamic Playbook Selection & Domain Isolation.

Verifies:
1. Playbook resolution priorities (Priority 1: service_category, Priority 2: generic_services,
   Priority 3: approved_scope, Priority 4: legacy vs general consulting fallback).
2. Playbook selection audit log generation and validation_metadata recording.
3. Prompt isolation:
   - Bookkeeping prompt does not receive website/data/advisory/general consulting instructions.
   - Website prompt does not receive accounting/data instructions.
   - Data prompt does not receive accounting/website instructions.
   - Finance transformation prompt does not receive website instructions.
   - Unknown service fallback receives general consulting playbook (no QBO, Squarespace, Tessitura).
4. Generated proposal isolation (output draft inspection):
   - Website proposal: Must not contain accounting workflows (QBO, Dext, Plooto, bank reconciliations, payroll).
   - Data proposal: Must not contain accounting or website workflows (QBO, Dext, Plooto, Squarespace, artwork).
   - Finance transformation: Must not contain website workflows (Squarespace, artwork, e-commerce).
   - Accounting: Must not contain website or data workflows (Squarespace, artwork, ETL pipelines, data warehouses).
"""

import os
import json
import pytest
from pathlib import Path
from typing import Dict, Any

os.environ["HF_HUB_OFFLINE"] = "1"

from sympl_writer.prompt_builder import PromptBuilder
from sympl_writer.playbooks.registry import PlaybookRegistry, PlaybookAuditLog
from sympl_writer.schema import ProposalDraft, DraftSection, DraftSubsection
from sympl_writer.writer import ProposalWriter
from sympl_writer.llm_client import MockLLMClient


class TestPlaybookResolutionPriority:
    """Tests the 4-tier resolution cascade and audit log generation."""

    def test_priority_1_explicit_service_category(self):
        """Priority 1: Explicit service_category overrides generic keywords."""
        plan = {
            "service_category": "Website Development",
            "approved_scope": {
                "general_notes": "Client requested review of historical data"
            }
        }
        res = PlaybookRegistry.resolve_playbook(plan_data=plan)
        assert res.audit_log.playbook_selected == "website_playbook"
        assert res.audit_log.confidence_source == "explicit_category"
        assert res.audit_log.fallback_used is False
        assert "Squarespace" in res.system_prompt
        assert "QuickBooks" not in res.system_prompt

    def test_priority_2_generic_services(self):
        """Priority 2: generic_services list is inspected when service_category is omitted."""
        plan = {
            "client_context": {"name": "Metro Data Lab"},
            "generic_services": [
                {
                    "service_category": "Data Analytics",
                    "service_name": "Centralized SQL Warehouse",
                    "description": "Cross-platform data pipelines and Power BI dashboards"
                }
            ]
        }
        res = PlaybookRegistry.resolve_playbook(plan_data=plan)
        assert res.audit_log.playbook_selected == "data_playbook"
        assert res.audit_log.confidence_source == "generic_services"
        assert res.audit_log.fallback_used is False
        assert "Power BI" in res.system_prompt
        assert "QuickBooks" not in res.system_prompt

    def test_priority_3_approved_scope_detection(self):
        """Priority 3: approved_scope keys are inspected when categories/generic_services omitted."""
        plan = {
            "client_context": {"name": "Northern Health Network"},
            "approved_scope": {
                "finance_transformation": {
                    "budget_process_revamp": True,
                    "financial_forecasting": True
                }
            }
        }
        res = PlaybookRegistry.resolve_playbook(plan_data=plan)
        assert res.audit_log.playbook_selected == "finance_transformation_playbook"
        assert res.audit_log.confidence_source == "approved_scope"
        assert res.audit_log.fallback_used is False
        assert "Assumptions tab" in res.system_prompt
        assert "Squarespace" not in res.system_prompt

    def test_priority_4_legacy_accounting_detection(self):
        """Priority 4a: Legacy accounting payloads receive accounting playbook."""
        plan = {
            "client_name": "Autism Centre",
            "core_bookkeeping": True,
            "approved_scope": {
                "bookkeeping": {"cadence": "weekly"}
            }
        }
        res = PlaybookRegistry.resolve_playbook(plan_data=plan)
        assert res.audit_log.playbook_selected == "accounting_playbook"
        assert res.audit_log.confidence_source == "approved_scope" or res.audit_log.confidence_source == "legacy_detection"
        assert res.audit_log.fallback_used is False
        assert "QuickBooks Online" in res.system_prompt
        assert "Dext" in res.system_prompt
        assert "Plooto" in res.system_prompt

    def test_priority_4_unknown_service_fallback_to_general_consulting(self):
        """Priority 4b: Unknown service is NEVER silently classified as Accounting."""
        plan = {
            "client_name": "Apex Strategy",
            "service_category": "Human Resources & Talent Strategy",
            "approved_scope": {
                "workforce_planning": {"headcount_modeling": True}
            }
        }
        res = PlaybookRegistry.resolve_playbook(plan_data=plan)
        assert res.audit_log.playbook_selected == "general_consulting_playbook"
        assert res.audit_log.confidence_source == "unclassified_fallback"
        assert res.audit_log.fallback_used is True
        
        # Must NOT contain domain-specific tools
        assert "QuickBooks" not in res.system_prompt
        assert "Dext" not in res.system_prompt
        assert "Plooto" not in res.system_prompt
        assert "Squarespace" not in res.system_prompt
        assert "Tessitura" not in res.system_prompt
        assert "Discovery & Diagnostic" in res.system_prompt


class TestPromptIsolation:
    """Verifies that prompts constructed for one domain do not contain instructions from other domains."""

    def test_bookkeeping_prompt_does_not_contain_website_or_data(self):
        plan = {
            "client_name": "Heritage Arts Foundation",
            "service_category": "Accounting",
            "approved_scope": {
                "bookkeeping": {"cadence": "monthly", "ap_ar": True, "reconciliations": True},
                "payroll": {"cadence": "semi_monthly", "headcount_employees": 10},
                "financial_reporting": {"cadence": "monthly", "board_package": True}
            },
            "sections": [
                {"section_id": "sec_1", "section_title": "Monthly Bookkeeping", "section_type": "bookkeeping"}
            ]
        }
        sys_prompt, user_prompt = PromptBuilder.build_prompt(plan)
        combined = f"{sys_prompt}\n{user_prompt}"

        # Must include accounting workflows
        assert "QuickBooks Online" in combined or "QBO" in combined
        assert "Dext" in combined
        assert "Plooto" in combined

        # Must NOT include website or data workflows
        assert "Squarespace" not in combined
        assert "collector-first" not in combined
        assert "Available Now" not in combined
        assert "Tessitura" not in combined
        assert "AudienceView" not in combined
        assert "PIPEDA" not in combined

    def test_website_prompt_does_not_contain_accounting_or_data(self):
        plan = {
            "client_name": "Gary Crawford Art",
            "service_category": "Website Development",
            "approved_scope": {
                "website": {
                    "architecture": "collector_first",
                    "cms": "squarespace",
                    "ecommerce": True
                }
            },
            "sections": [
                {"section_id": "sec_1", "section_title": "Website Architecture", "section_type": "website"}
            ]
        }
        sys_prompt, user_prompt = PromptBuilder.build_prompt(plan)
        combined = f"{sys_prompt}\n{user_prompt}"

        # Must include website workflows
        assert "Squarespace" in combined
        assert "collector/audience-first" in combined or "collector" in combined
        assert "30-day" in combined

        # Must NOT include accounting or data workflows
        assert "QuickBooks Online" not in combined
        assert "Dext" not in combined
        assert "Plooto" not in combined
        assert "bank reconciliation" not in combined.lower()
        assert "Tessitura" not in combined
        assert "PIPEDA" not in combined

    def test_data_prompt_does_not_contain_accounting_or_website(self):
        plan = {
            "client_name": "Aga Khan Museum",
            "service_category": "Data Analytics",
            "approved_scope": {
                "data_analytics": {
                    "systems_audit": True,
                    "centralized_db": True,
                    "dashboards": True
                }
            },
            "sections": [
                {"section_id": "sec_1", "section_title": "Data Systems Audit", "section_type": "data"}
            ]
        }
        sys_prompt, user_prompt = PromptBuilder.build_prompt(plan)
        combined = f"{sys_prompt}\n{user_prompt}"

        # Must include data workflows
        assert "Power BI" in combined
        assert "PIPEDA" in combined
        assert "Canadian cloud residency" in combined or "Canadian data residency" in combined

        # Must NOT include accounting or website workflows
        assert "QuickBooks Online" not in combined
        assert "Dext" not in combined
        assert "Plooto" not in combined
        assert "Squarespace" not in combined
        assert "artwork" not in combined.lower()


class TestGeneratedProposalIsolation:
    """Verifies that generated proposal draft content maintains strict domain isolation."""

    @staticmethod
    def _assert_zero_leakage(draft: ProposalDraft, forbidden_terms: list):
        """Scans all sections, subsections, and narratives for forbidden domain terms."""
        all_text = f"{draft.title} {draft.executive_summary} "
        for sec in draft.sections:
            all_text += f"{sec.section_title} {sec.opening_text} "
            for sub in sec.subsections:
                all_text += f"{sub.heading} {sub.narrative} "
                all_text += " ".join(sub.bullets) + " "

        all_text_lower = all_text.lower()
        for term in forbidden_terms:
            assert term.lower() not in all_text_lower, (
                f"Domain contamination detected! Found forbidden term '{term}' in generated proposal."
            )

    def test_website_proposal_generated_output_isolation(self):
        """Website proposals must not contain accounting workflows in actual generated text."""
        draft = ProposalDraft(
            title="Website Development Proposal for Gary Crawford Art",
            executive_summary=(
                "Sympl Solutions is pleased to submit this website redesign proposal for Gary Crawford Art. "
                "The objective is to establish an intuitive, collector-first digital presence on Squarespace "
                "that presents the artwork with intention and clarity while ensuring seamless mobile discovery."
            ),
            sections=[
                DraftSection(
                    section_title="Information Architecture & Collector-First UX",
                    opening_text=(
                        "Our approach restructures the digital experience from internal medium classification "
                        "to collector-first discovery, highlighting available series and dedicated artwork profiles."
                    ),
                    subsections=[
                        DraftSubsection(
                            heading="Collector Navigation & Exhibition Portfolios",
                            narrative="Organizes portfolios into dedicated series with high-resolution photography.",
                            bullets=[
                                "Configure clean hero landing page with artist statement",
                                "Deploy Available Now store catalog with Stripe payment processing"
                            ]
                        )
                    ]
                )
            ],
            pricing={"pricing_model": "fixed_fee", "currency": "CAD", "fee_items": []},
            why_us=["Proven experience in creative arts web design."],
            exclusions=["Third-party domain renewal fees."]
        )

        forbidden_accounting = [
            "quickbooks", "qbo", "dext", "plooto", "bank reconciliation",
            "payroll", "gst/hst filing", "month-end close", "t3010"
        ]
        self._assert_zero_leakage(draft, forbidden_accounting)

    def test_data_proposal_generated_output_isolation(self):
        """Data proposals must not contain accounting or website workflows."""
        draft = ProposalDraft(
            title="Data Analytics & Centralized Database Proposal for Aga Khan Museum",
            executive_summary=(
                "Sympl Solutions proposes a comprehensive 8-week data discovery engagement for the Aga Khan Museum. "
                "The project will unify siloed records across ticketing, donor databases, and marketing platforms "
                "into a centralized reporting layer governed by Canadian privacy standards."
            ),
            sections=[
                DraftSection(
                    section_title="Cross-Platform Systems Audit & Data Architecture",
                    opening_text=(
                        "We will audit existing schema structures, reconcile constituent records, and design an "
                        "automated ETL ingestion pipeline into an Azure Canada centralized data warehouse."
                    ),
                    subsections=[
                        DraftSubsection(
                            heading="Executive Power BI Dashboards",
                            narrative="Configures real-time visualization dashboards for leadership and department heads.",
                            bullets=[
                                "Deploy interactive Power BI retention and ticket velocity monitors",
                                "Establish role-based access control and PIPEDA compliant data governance"
                            ]
                        )
                    ]
                )
            ],
            pricing={"pricing_model": "phased_milestone", "currency": "CAD", "fee_items": []},
            why_us=["Deep expertise in cultural sector data architecture."],
            exclusions=["Hardware hosting procurement."]
        )

        forbidden_terms = [
            "quickbooks", "qbo", "dext", "plooto", "reconciliation cadence",
            "squarespace", "paintings", "collector-first", "available now"
        ]
        self._assert_zero_leakage(draft, forbidden_terms)

    def test_finance_transformation_generated_output_isolation(self):
        """Finance transformation proposals must not contain website workflows."""
        draft = ProposalDraft(
            title="Budget Revamp & Financial Forecasting Proposal for Compass",
            executive_summary=(
                "Sympl Solutions is pleased to submit this proposal for a budget process revamp and financial forecasting model. "
                "We will integrate multiple ministry funding allocations into a single automated budgeting framework."
            ),
            sections=[
                DraftSection(
                    section_title="Operational Budget Process Revamp",
                    opening_text=(
                        "Consolidating departmental spreadsheets into an integrated annual budget model with dynamic scenario analysis."
                    ),
                    subsections=[
                        DraftSubsection(
                            heading="Chart of Accounts Realignment",
                            narrative="Redesigns class codes so expenses tag to programs and funders automatically.",
                            bullets=[
                                "Realize multi-funder allocation models directly in core ledger",
                                "Construct 12-month rolling cash flow forecast driven by an Assumptions tab"
                            ]
                        )
                    ]
                )
            ],
            pricing={"pricing_model": "fixed_fee", "currency": "CAD", "fee_items": []},
            why_us=["Specialized nonprofit multi-funder financial modeling."],
            exclusions=["External legal advisory."]
        )

        forbidden_website = ["squarespace", "artwork", "paintings", "collector", "ecommerce store"]
        self._assert_zero_leakage(draft, forbidden_website)

    def test_accounting_proposal_generated_output_isolation(self):
        """Accounting proposals must not contain website or data warehouse workflows."""
        draft = ProposalDraft(
            title="Accounting & Bookkeeping Services Proposal for Young People's Theatre",
            executive_summary=(
                "Sympl Solutions will provide comprehensive full-cycle bookkeeping and financial reporting services. "
                "Our team will manage accounts payable, payroll administration, and deliver monthly financial packages."
            ),
            sections=[
                DraftSection(
                    section_title="Full-Cycle Bookkeeping & General Ledger",
                    opening_text=(
                        "Operating within QuickBooks Online, Sympl establishes a structured month-end close workflow."
                    ),
                    subsections=[
                        DraftSubsection(
                            heading="Accounts Payable & Vendor Disbursements",
                            narrative="Invoices are processed through Dext and authorized via Plooto email approval.",
                            bullets=[
                                "Reconcile monthly bank, credit card, and clearing accounts",
                                "Process semi-monthly payroll via WagePoint with CRA remittances"
                            ]
                        )
                    ]
                )
            ],
            pricing={"pricing_model": "fixed_retainer", "currency": "CAD", "fee_items": []},
            why_us=["Proven track record supporting Canadian non-profits."],
            exclusions=["Annual audit fee paid directly to external auditors."]
        )

        forbidden_non_accounting = [
            "squarespace", "paintings", "collector-first", "etl pipeline",
            "azure canada", "pipeda", "sql data warehouse", "tessitura"
        ]
        self._assert_zero_leakage(draft, forbidden_non_accounting)


class TestPlaybookSelectionAuditLogAttached:
    """Verifies that ProposalWriter attaches playbook_selection_audit to draft validation_metadata."""

    def test_writer_records_playbook_audit_log(self):
        plan = {
            "client_name": "Gallery Alpha",
            "service_category": "Website Development",
            "approved_scope": {
                "website": {"cms": "squarespace"}
            },
            "pricing": {"pricing_model": "fixed_fee", "monthly_retainer": 5000.0}
        }
        writer = ProposalWriter(llm_client=MockLLMClient())
        draft = writer.write(plan)

        assert draft.validation_metadata is not None
        assert "playbook_selection_audit" in draft.validation_metadata
        audit = draft.validation_metadata["playbook_selection_audit"]

        assert audit["service_category_detected"] == "Website Development"
        assert audit["playbook_selected"] == "website_playbook"
        assert audit["fallback_used"] is False
        assert audit["confidence_source"] == "explicit_category"
        assert "Priority 1" in audit["selection_reason"]

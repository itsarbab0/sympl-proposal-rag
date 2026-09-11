"""
Sympl Solutions Proposal RAG — Playbook Registry & Dynamic Selector

Resolves the appropriate domain playbook based on:
  1. Priority 1: Explicit service_category from ProposalPlan (top-level or client_context)
  2. Priority 2: generic_services list/scopes
  3. Priority 3: approved_scope key and service module detection
  4. Priority 4: Fallback handling (legacy accounting vs. general consulting for unknown services)

Maintains an internal Playbook Selection Audit Log on every resolution to diagnose
selection decisions without modifying the proposal output structure.
"""

import re
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional, Tuple

from sympl_writer.playbooks.accounting_playbook import (
    ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM,
    ACCOUNTING_OPERATIONAL_PLAYBOOK_USER_LINES,
    BENCHMARK_REFERENCES as ACCOUNTING_BENCHMARKS,
    JSON_EXAMPLE_SUBHEADING as ACCOUNTING_SUBHEADING,
    EXECUTIVE_SUMMARY_GUIDANCE as ACCOUNTING_EXEC_GUIDANCE,
    DOMAIN_VOCABULARY as ACCOUNTING_VOCABULARY,
)
from sympl_writer.playbooks.website_playbook import (
    WEBSITE_OPERATIONAL_PLAYBOOK_SYSTEM,
    WEBSITE_OPERATIONAL_PLAYBOOK_USER_LINES,
    BENCHMARK_REFERENCES as WEBSITE_BENCHMARKS,
    JSON_EXAMPLE_SUBHEADING as WEBSITE_SUBHEADING,
    EXECUTIVE_SUMMARY_GUIDANCE as WEBSITE_EXEC_GUIDANCE,
    DOMAIN_VOCABULARY as WEBSITE_VOCABULARY,
)
from sympl_writer.playbooks.data_playbook import (
    DATA_OPERATIONAL_PLAYBOOK_SYSTEM,
    DATA_OPERATIONAL_PLAYBOOK_USER_LINES,
    BENCHMARK_REFERENCES as DATA_BENCHMARKS,
    JSON_EXAMPLE_SUBHEADING as DATA_SUBHEADING,
    EXECUTIVE_SUMMARY_GUIDANCE as DATA_EXEC_GUIDANCE,
    DOMAIN_VOCABULARY as DATA_VOCABULARY,
)
from sympl_writer.playbooks.finance_transformation_playbook import (
    FINANCE_TRANSFORMATION_PLAYBOOK_SYSTEM,
    FINANCE_TRANSFORMATION_PLAYBOOK_USER_LINES,
    BENCHMARK_REFERENCES as FINANCE_BENCHMARKS,
    JSON_EXAMPLE_SUBHEADING as FINANCE_SUBHEADING,
    EXECUTIVE_SUMMARY_GUIDANCE as FINANCE_EXEC_GUIDANCE,
    DOMAIN_VOCABULARY as FINANCE_VOCABULARY,
)
from sympl_writer.playbooks.general_consulting_playbook import (
    GENERAL_CONSULTING_PLAYBOOK_SYSTEM,
    GENERAL_CONSULTING_PLAYBOOK_USER_LINES,
    BENCHMARK_REFERENCES as GENERAL_BENCHMARKS,
    JSON_EXAMPLE_SUBHEADING as GENERAL_SUBHEADING,
    EXECUTIVE_SUMMARY_GUIDANCE as GENERAL_EXEC_GUIDANCE,
    DOMAIN_VOCABULARY as GENERAL_VOCABULARY,
)


@dataclass
class PlaybookAuditLog:
    """Internal diagnostic audit record for playbook selection."""
    service_category_detected: str
    playbook_selected: str
    selection_reason: str
    fallback_used: bool
    confidence_source: str  # "explicit_category" | "generic_services" | "approved_scope" | "legacy_detection" | "unclassified_fallback"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlaybookResolution:
    """Container for the resolved playbook prompts and audit metadata."""
    system_prompt: str
    user_lines: List[str]
    audit_log: PlaybookAuditLog
    benchmark_references: List[str] = field(default_factory=lambda: ["TACT", "YPT", "RPFF"])
    json_example_subheading: str = "Accounts Payable & Vendor Disbursement Workflow"
    executive_summary_guidance: str = ""
    domain_vocabulary: List[str] = field(default_factory=list)


class PlaybookRegistry:
    """
    Dynamic Playbook Selector enforcing the 4-tier resolution priority
    with strict unknown service fallback guardrails.
    """

    WEBSITE_KEYWORDS = [
        "website", "web design", "web development", "web redesign",
        "cms", "squarespace", "webflow", "wordpress", "ecommerce",
        "artist website", "portfolio website", "artwork"
    ]

    DATA_KEYWORDS = [
        "data analytics", "centralized database", "data warehouse", "database architecture",
        "power bi", "powerbi", "tableau", "bi dashboard", "bi dashboards",
        "etl pipeline", "data discovery", "kpi framework", "audience analytics",
        "patron analytics", "tessitura", "audienceview"
    ]

    ADVISORY_KEYWORDS = [
        "finance transformation", "budget process revamp", "financial forecasting",
        "budget model", "gl realignment", "chart of accounts realignment",
        "scenario modeling", "financial advisory", "multi funder"
    ]

    ACCOUNTING_KEYWORDS = [
        "accounting", "bookkeeping", "payroll", "ap ar", "reconciliations",
        "month end close", "qbo", "quickbooks", "dext", "plooto",
        "gst hst filing", "financial reporting package"
    ]

    @classmethod
    def _matches_any(cls, text: str, keywords: List[str]) -> bool:
        """Helper to test whole-word / phrase matching against text."""
        for kw in keywords:
            # Word boundary regex allowing spaces
            pattern = r"(?:\b|_)" + re.escape(kw).replace(r"\ ", r"[\s_]+") + r"(?:\b|_)"
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def _create_accounting_resolution(cls, detected_category: str, reason: str, confidence_source: str) -> PlaybookResolution:
        return PlaybookResolution(
            system_prompt=ACCOUNTING_OPERATIONAL_PLAYBOOK_SYSTEM,
            user_lines=ACCOUNTING_OPERATIONAL_PLAYBOOK_USER_LINES,
            audit_log=PlaybookAuditLog(
                service_category_detected=detected_category or "Accounting",
                playbook_selected="accounting_playbook",
                selection_reason=reason,
                fallback_used=False,
                confidence_source=confidence_source
            ),
            benchmark_references=ACCOUNTING_BENCHMARKS,
            json_example_subheading=ACCOUNTING_SUBHEADING,
            executive_summary_guidance=ACCOUNTING_EXEC_GUIDANCE,
            domain_vocabulary=ACCOUNTING_VOCABULARY,
        )

    @classmethod
    def _create_website_resolution(cls, detected_category: str, reason: str, confidence_source: str) -> PlaybookResolution:
        return PlaybookResolution(
            system_prompt=WEBSITE_OPERATIONAL_PLAYBOOK_SYSTEM,
            user_lines=WEBSITE_OPERATIONAL_PLAYBOOK_USER_LINES,
            audit_log=PlaybookAuditLog(
                service_category_detected=detected_category or "Website Development",
                playbook_selected="website_playbook",
                selection_reason=reason,
                fallback_used=False,
                confidence_source=confidence_source
            ),
            benchmark_references=WEBSITE_BENCHMARKS,
            json_example_subheading=WEBSITE_SUBHEADING,
            executive_summary_guidance=WEBSITE_EXEC_GUIDANCE,
            domain_vocabulary=WEBSITE_VOCABULARY,
        )

    @classmethod
    def _create_data_resolution(cls, detected_category: str, reason: str, confidence_source: str) -> PlaybookResolution:
        return PlaybookResolution(
            system_prompt=DATA_OPERATIONAL_PLAYBOOK_SYSTEM,
            user_lines=DATA_OPERATIONAL_PLAYBOOK_USER_LINES,
            audit_log=PlaybookAuditLog(
                service_category_detected=detected_category or "Data Analytics",
                playbook_selected="data_playbook",
                selection_reason=reason,
                fallback_used=False,
                confidence_source=confidence_source
            ),
            benchmark_references=DATA_BENCHMARKS,
            json_example_subheading=DATA_SUBHEADING,
            executive_summary_guidance=DATA_EXEC_GUIDANCE,
            domain_vocabulary=DATA_VOCABULARY,
        )

    @classmethod
    def _create_finance_resolution(cls, detected_category: str, reason: str, confidence_source: str) -> PlaybookResolution:
        return PlaybookResolution(
            system_prompt=FINANCE_TRANSFORMATION_PLAYBOOK_SYSTEM,
            user_lines=FINANCE_TRANSFORMATION_PLAYBOOK_USER_LINES,
            audit_log=PlaybookAuditLog(
                service_category_detected=detected_category or "Finance Transformation",
                playbook_selected="finance_transformation_playbook",
                selection_reason=reason,
                fallback_used=False,
                confidence_source=confidence_source
            ),
            benchmark_references=FINANCE_BENCHMARKS,
            json_example_subheading=FINANCE_SUBHEADING,
            executive_summary_guidance=FINANCE_EXEC_GUIDANCE,
            domain_vocabulary=FINANCE_VOCABULARY,
        )

    @classmethod
    def _create_general_resolution(cls, detected_category: str, reason: str, confidence_source: str) -> PlaybookResolution:
        return PlaybookResolution(
            system_prompt=GENERAL_CONSULTING_PLAYBOOK_SYSTEM,
            user_lines=GENERAL_CONSULTING_PLAYBOOK_USER_LINES,
            audit_log=PlaybookAuditLog(
                service_category_detected=detected_category or "Unclassified",
                playbook_selected="general_consulting_playbook",
                selection_reason=reason,
                fallback_used=True,
                confidence_source=confidence_source
            ),
            benchmark_references=GENERAL_BENCHMARKS,
            json_example_subheading=GENERAL_SUBHEADING,
            executive_summary_guidance=GENERAL_EXEC_GUIDANCE,
            domain_vocabulary=GENERAL_VOCABULARY,
        )

    @classmethod
    def resolve_playbook(
        cls,
        service_category: Optional[str] = None,
        approved_scope: Optional[Dict[str, Any]] = None,
        generic_services: Optional[List[Any]] = None,
        client_context: Optional[Dict[str, Any]] = None,
        plan_data: Optional[Dict[str, Any]] = None
    ) -> PlaybookResolution:
        """
        Executes the 4-tier playbook selection cascade:
          Priority 1: Explicit service_category from ProposalPlan
          Priority 2: generic_services inspection
          Priority 3: approved_scope detection
          Priority 4: Fallback handling (legacy accounting vs. general consulting)
        """
        # Guard against accidental positional argument pass where plan_data was passed as arg #1
        if isinstance(service_category, dict) and not plan_data:
            plan_data = service_category
            service_category = None

        plan_data = plan_data or {}
        approved_scope = approved_scope or plan_data.get("approved_scope") or {}
        client_context = client_context or plan_data.get("client_context") or {}

        # ------------------------------------------------------------------
        # Priority 1: Explicit service_category from ProposalPlan
        # ------------------------------------------------------------------
        raw_cat = (
            service_category
            or client_context.get("service_category")
            or plan_data.get("service_category")
            or plan_data.get("metadata", {}).get("service_category")
            or ""
        )
        detected_category = raw_cat.strip() if isinstance(raw_cat, str) else ""
        cat_normalized = detected_category.lower().replace("_", " ").replace("-", " ")

        if cat_normalized:
            if "accounting" in cat_normalized or "bookkeeping" in cat_normalized:
                return cls._create_accounting_resolution(
                    detected_category=detected_category,
                    reason=f"Priority 1: Explicit category '{detected_category}' matched Accounting",
                    confidence_source="explicit_category"
                )

            if "website" in cat_normalized or "web" in cat_normalized:
                return cls._create_website_resolution(
                    detected_category=detected_category,
                    reason=f"Priority 1: Explicit category '{detected_category}' matched Website Development",
                    confidence_source="explicit_category"
                )

            if "data" in cat_normalized or "analytics" in cat_normalized or "database" in cat_normalized:
                return cls._create_data_resolution(
                    detected_category=detected_category,
                    reason=f"Priority 1: Explicit category '{detected_category}' matched Data Analytics",
                    confidence_source="explicit_category"
                )

            if "finance transformation" in cat_normalized or "advisory" in cat_normalized or "budget" in cat_normalized:
                return cls._create_finance_resolution(
                    detected_category=detected_category,
                    reason=f"Priority 1: Explicit category '{detected_category}' matched Finance Transformation",
                    confidence_source="explicit_category"
                )

        # ------------------------------------------------------------------
        # Priority 2: generic_services inspection
        # ------------------------------------------------------------------
        gen_services_list = generic_services or plan_data.get("generic_services") or approved_scope.get("generic_services") or []
        if isinstance(gen_services_list, list) and len(gen_services_list) > 0:
            combined_gen_text = ""
            for gs in gen_services_list:
                if isinstance(gs, dict):
                    combined_gen_text += f" {gs.get('service_category', '')} {gs.get('service_name', '')} {gs.get('description', '')}"
                elif hasattr(gs, "service_category"):
                    combined_gen_text += f" {getattr(gs, 'service_category', '')} {getattr(gs, 'service_name', '')}"
                elif isinstance(gs, str):
                    combined_gen_text += f" {gs}"

            if cls._matches_any(combined_gen_text, cls.WEBSITE_KEYWORDS):
                return cls._create_website_resolution(
                    detected_category=detected_category or "Website Development (inferred)",
                    reason="Priority 2: Matched website keywords in generic_services",
                    confidence_source="generic_services"
                )

            if cls._matches_any(combined_gen_text, cls.DATA_KEYWORDS):
                return cls._create_data_resolution(
                    detected_category=detected_category or "Data Analytics (inferred)",
                    reason="Priority 2: Matched data analytics keywords in generic_services",
                    confidence_source="generic_services"
                )

            if cls._matches_any(combined_gen_text, cls.ADVISORY_KEYWORDS):
                return cls._create_finance_resolution(
                    detected_category=detected_category or "Finance Transformation (inferred)",
                    reason="Priority 2: Matched finance transformation keywords in generic_services",
                    confidence_source="generic_services"
                )

            if cls._matches_any(combined_gen_text, cls.ACCOUNTING_KEYWORDS):
                return cls._create_accounting_resolution(
                    detected_category=detected_category or "Accounting (inferred)",
                    reason="Priority 2: Matched accounting keywords in generic_services",
                    confidence_source="generic_services"
                )

        # ------------------------------------------------------------------
        # Priority 3: approved_scope detection
        # ------------------------------------------------------------------
        scope_keys = set(k.lower() for k in approved_scope.keys()) if isinstance(approved_scope, dict) else set()

        # 3a. Direct scope key match
        if any(k in scope_keys for k in ["website", "web_redesign", "cms_configuration"]):
            return cls._create_website_resolution(
                detected_category=detected_category or "Website Development (inferred)",
                reason="Priority 3: Detected website scope keys in approved_scope",
                confidence_source="approved_scope"
            )

        if any(k in scope_keys for k in ["data_analytics", "centralized_db", "data_assessment"]):
            return cls._create_data_resolution(
                detected_category=detected_category or "Data Analytics (inferred)",
                reason="Priority 3: Detected data analytics scope keys in approved_scope",
                confidence_source="approved_scope"
            )

        if any(k in scope_keys for k in ["finance_transformation", "budget_process_revamp", "financial_forecasting"]):
            return cls._create_finance_resolution(
                detected_category=detected_category or "Finance Transformation (inferred)",
                reason="Priority 3: Detected finance transformation scope keys in approved_scope",
                confidence_source="approved_scope"
            )

        if any(k in scope_keys for k in ["bookkeeping", "payroll", "financial_reporting", "compliance"]):
            return cls._create_accounting_resolution(
                detected_category=detected_category or "Accounting (inferred)",
                reason="Priority 3: Detected accounting/bookkeeping scope keys in approved_scope",
                confidence_source="approved_scope"
            )

        # 3b. Deep text scan of approved_scope content with word boundaries
        scope_str = " ".join(scope_keys)
        if isinstance(approved_scope, dict):
            for k, v in approved_scope.items():
                if isinstance(v, dict):
                    scope_str += " " + " ".join(str(sub_k) for sub_k in v.keys())
                    scope_str += " " + " ".join(str(sub_v) for sub_v in v.values() if isinstance(sub_v, (str, list)))

        if cls._matches_any(scope_str, cls.WEBSITE_KEYWORDS):
            return cls._create_website_resolution(
                detected_category=detected_category or "Website Development (inferred)",
                reason="Priority 3: Detected website keywords in approved_scope",
                confidence_source="approved_scope"
            )

        if cls._matches_any(scope_str, cls.DATA_KEYWORDS):
            return cls._create_data_resolution(
                detected_category=detected_category or "Data Analytics (inferred)",
                reason="Priority 3: Detected data keywords in approved_scope",
                confidence_source="approved_scope"
            )

        if cls._matches_any(scope_str, cls.ADVISORY_KEYWORDS):
            return cls._create_finance_resolution(
                detected_category=detected_category or "Finance Transformation (inferred)",
                reason="Priority 3: Detected advisory/transformation keywords in approved_scope",
                confidence_source="approved_scope"
            )

        if cls._matches_any(scope_str, cls.ACCOUNTING_KEYWORDS):
            return cls._create_accounting_resolution(
                detected_category=detected_category or "Accounting (inferred)",
                reason="Priority 3: Detected accounting keywords in approved_scope",
                confidence_source="approved_scope"
            )

        # ------------------------------------------------------------------
        # Priority 4: Fallback handling
        # ------------------------------------------------------------------
        is_legacy_accounting = (
            plan_data.get("core_bookkeeping") is True
            or any(k in scope_keys for k in ["bookkeeping", "payroll", "financial_reporting", "compliance"])
            or cls._matches_any(scope_str, ["qbo", "quickbooks", "dext", "plooto"])
        )

        if is_legacy_accounting:
            return cls._create_accounting_resolution(
                detected_category=detected_category or "Accounting (legacy)",
                reason="Priority 4: Legacy bookkeeping scope detected in payload",
                confidence_source="legacy_detection"
            )

        # UNKNOWN OR UNCLASSIFIED SERVICE:
        # Strictly route to General Consulting. NEVER silently classify as Accounting!
        return cls._create_general_resolution(
            detected_category=detected_category or "Unclassified",
            reason=f"Priority 4 Fallback: Service '{detected_category or 'unspecified'}' has no domain playbook. Routed to General Consulting.",
            confidence_source="unclassified_fallback"
        )

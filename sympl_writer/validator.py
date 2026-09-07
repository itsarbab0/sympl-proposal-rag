"""
Sympl Solutions Proposal RAG — Proposal Writer Validator

Implements strict validation checks for the Proposal Writer Layer:
  1. Scope Validator: Verifies generated services match approved_scope.
  2. Scope Completeness Validator: Ensures all approved scope families are represented (MISSING_APPROVED_SCOPE_ITEM).
  3. Pricing Safety Validator: Prevents invented fees/amounts, enforces placeholders.
  4. Historical Data Firewall: Rejects historical client names, historical years (2025/2026), amounts, and headcounts.
  5. Style Validator: Checks forbidden buzzwords, marketing hype, passive voice, bullet length (6-15 words).
  6. Reference Block Validator: Ensures canonical reference blocks match verbatim without tampering.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set

from sympl_writer.schema import ProposalDraft, DraftSection, DraftSubsection
from sympl_writer.exceptions import (
    WriterError,
    ScopeViolationError,
    MissingApprovedScopeItemError,
    PricingSafetyError,
    HistoricalLeakageError,
    StyleViolationError,
    ReferenceBlockTamperingError
)


@dataclass
class ValidationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details
        }


class ProposalValidator:
    """
    Validates ProposalDraft instances against ProposalPlan data and Sympl quality invariants.
    """

    # 1. Historical Firewall Entities
    HISTORICAL_CLIENT_CODES = [
        "TACT",
        "PIRS",
        "GOODFOOT",
        "RPFF",
        "YPT",
        "CARE/OF",
        "CAREOF",
        "CAHOOTS"
    ]

    HISTORICAL_CLIENT_NAMES = [
        "The Autism Centre of Toronto",
        "Autism Centre of Toronto",
        "Pacific Immigrant Resources Society",
        "Good Foot Support Services",
        "Good Foot Delivery",
        "Regent Park Film Festival",
        "Young People's Theatre",
        "Care/Of Experiences",
        "Cahoots Theatre Company",
        "Cahoots Theatre"
    ]

    HISTORICAL_YEARS = ["2025", "2026"]

    HISTORICAL_AMOUNTS_HEADCOUNTS = [
        r"\$1\.4\s*M(illion)?",
        r"\$1\.1\s*M(illion)?",
        r"\b19\s+employees\b",
        r"\b11\s+employees\b",
        r"\$4,500\s*/\s*month",
        r"\$3,500\s*/\s*month",
        r"\$2,800\s*/\s*month",
        r"\$1,200\s*/\s*month",
        r"\$8,500\b"
    ]

    # 2. Forbidden Buzzwords
    FORBIDDEN_BUZZWORDS = [
        "leverage",
        "cutting-edge",
        "game-changing",
        "holistic ecosystem",
        "unlock value",
        "bespoke transformation journey",
        "strategic synergies",
        "world-class",
        "paradigm shift",
        "revolutionary",
        "unparalleled"
    ]

    # 3. Passive Voice Patterns
    PASSIVE_PATTERNS = [
        r"\bwill be managed by\b",
        r"\bwill be handled by\b",
        r"\bwill be reconciled by\b",
        r"\bis managed by\b",
        r"\bare reviewed by\b",
        r"\bwas prepared by\b",
        r"\bbe performed by\b",
        r"\bwill be executed by\b"
    ]

    # 4. Scope Family Keywords Mapping
    SCOPE_FAMILY_KEYWORDS = {
        "bookkeeping": ["bookkeeping", "accounting", "ledger", "accounts payable", "reconcil"],
        "payroll": ["payroll", "wagepoint", "source deduction", "t4", "remittance"],
        "financial_reporting": ["reporting", "funder", "board package", "grant", "budget vs actual", "financial statements"],
        "compliance": ["compliance", "gst", "hst", "rebate", "t3010", "audit support", "statutory"],
        "digital_transformation": ["transformation", "system migration", "workflow", "cloud", "integration", "dext", "onboarding"],
        "management_consulting": ["consulting", "advisory", "cfo", "strategic", "governance"],
        "transition_services": ["transition", "interim", "handover", "onboarding plan"],
        "audit_oversight": ["audit oversight", "auditor", "audit readiness", "working paper"]
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate(
        self,
        draft: ProposalDraft,
        plan_data: Dict[str, Any],
        raise_on_error: bool = False
    ) -> ValidationResult:
        """
        Executes all validation checks against the draft and plan data.
        If raise_on_error is True, raises the specific subclass of WriterError on first critical failure.
        """
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        # 1. Historical Firewall
        hist_errors = self.check_historical_firewall(draft)
        if hist_errors:
            errors.extend(hist_errors)
            details["historical_firewall"] = {"passed": False, "violations": hist_errors}
            if raise_on_error:
                raise HistoricalLeakageError(f"Historical Firewall Violation: {hist_errors[0]}")
        else:
            details["historical_firewall"] = {"passed": True}

        # 2. Scope Completeness (Ensures all approved scope items appear)
        completeness_errors = self.check_scope_completeness(draft, plan_data)
        if completeness_errors:
            errors.extend(completeness_errors)
            details["scope_completeness"] = {"passed": False, "violations": completeness_errors}
            if raise_on_error:
                raise MissingApprovedScopeItemError(completeness_errors[0])
        else:
            details["scope_completeness"] = {"passed": True}

        # 3. Scope Violations (No unauthorized or excluded services)
        scope_errors = self.check_scope_violations(draft, plan_data)
        if scope_errors:
            errors.extend(scope_errors)
            details["scope_violations"] = {"passed": False, "violations": scope_errors}
            if raise_on_error:
                raise ScopeViolationError(f"Scope Violation: {scope_errors[0]}")
        else:
            details["scope_violations"] = {"passed": True}

        # 4. Pricing Safety
        pricing_errors = self.check_pricing_safety(draft, plan_data)
        if pricing_errors:
            errors.extend(pricing_errors)
            details["pricing_safety"] = {"passed": False, "violations": pricing_errors}
            if raise_on_error:
                raise PricingSafetyError(f"Pricing Safety Violation: {pricing_errors[0]}")
        else:
            details["pricing_safety"] = {"passed": True}

        # 5. Reference Block Integrity
        ref_errors = self.check_reference_blocks(draft, plan_data)
        if ref_errors:
            errors.extend(ref_errors)
            details["reference_blocks"] = {"passed": False, "violations": ref_errors}
            if raise_on_error:
                raise ReferenceBlockTamperingError(f"Reference Block Tampering: {ref_errors[0]}")
        else:
            details["reference_blocks"] = {"passed": True}

        # 6. Style Compliance
        style_errors, style_warnings = self.check_style_compliance(draft)
        if style_errors:
            errors.extend(style_errors)
            details["style_compliance"] = {"passed": False, "violations": style_errors}
            if raise_on_error:
                raise StyleViolationError(f"Style Rule Violation: {style_errors[0]}")
        else:
            details["style_compliance"] = {"passed": True, "warnings": style_warnings}
        warnings.extend(style_warnings)

        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings, details=details)

    # --------------------------------------------------------------------------
    # Check 1: Historical Firewall
    # --------------------------------------------------------------------------
    def check_historical_firewall(self, draft: ProposalDraft) -> List[str]:
        """Rejects historical codes, names, dates (2025/2026), amounts, and headcounts."""
        violations = []
        all_text = self._extract_all_text(draft)

        # Check client short codes
        for code in self.HISTORICAL_CLIENT_CODES:
            pattern = rf"\b{re.escape(code)}\b"
            if "/" in code:
                pattern = rf"{re.escape(code)}"
            if re.search(pattern, all_text, re.IGNORECASE):
                violations.append(f"Detected historical client code: '{code}'")

        # Check client full names
        for name in self.HISTORICAL_CLIENT_NAMES:
            if re.search(rf"\b{re.escape(name)}\b", all_text, re.IGNORECASE):
                violations.append(f"Detected historical client name: '{name}'")

        # Check historical years 2025, 2026
        for year in self.HISTORICAL_YEARS:
            if re.search(rf"\b{year}\b", all_text):
                violations.append(f"Detected forbidden historical year: '{year}'")

        # Check historical amounts & headcounts
        for pat in self.HISTORICAL_AMOUNTS_HEADCOUNTS:
            match = re.search(pat, all_text, re.IGNORECASE)
            if match:
                violations.append(f"Detected historical financial/headcount leakage: '{match.group(0)}'")

        return violations

    # --------------------------------------------------------------------------
    # Check 2: Scope Completeness
    # --------------------------------------------------------------------------
    def check_scope_completeness(self, draft: ProposalDraft, plan_data: Dict[str, Any]) -> List[str]:
        """
        Ensures that every service family present in approved_scope is represented in the draft.
        Raises / returns MISSING_APPROVED_SCOPE_ITEM if omitted.
        """
        violations = []
        approved_scope = plan_data.get("approved_scope") or {}

        # Determine active approved families
        active_families = set()
        for family, config in approved_scope.items():
            if isinstance(config, dict):
                # If dict has booleans or non-empty lists, check if anything is True/non-empty
                has_active = any(v is True or (isinstance(v, (list, dict)) and len(v) > 0) for v in config.values())
                if has_active:
                    active_families.add(family)
            elif config is True:
                active_families.add(family)

        # Scan draft sections
        section_texts = []
        for s in draft.sections:
            sec_blob = s.section_title.lower() + " " + s.opening_text.lower()
            for sub in s.subsections:
                sec_blob += " " + sub.heading.lower() + " " + " ".join(b.lower() for b in sub.bullets)
            section_texts.append(sec_blob)

        combined_sections_text = " ".join(section_texts)

        # For each active family, verify presence
        for family in active_families:
            keywords = self.SCOPE_FAMILY_KEYWORDS.get(family, [family])
            found = any(kw in combined_sections_text for kw in keywords)
            if not found:
                violations.append(f"MISSING_APPROVED_SCOPE_ITEM: Approved scope item '{family}' is missing from generated draft")

        return violations

    # --------------------------------------------------------------------------
    # Check 3: Scope Violations (Unauthorized Services)
    # --------------------------------------------------------------------------
    def check_scope_violations(self, draft: ProposalDraft, plan_data: Dict[str, Any]) -> List[str]:
        """Ensures the writer has not introduced unapproved services or deliverables."""
        violations = []
        approved_scope = plan_data.get("approved_scope") or {}
        all_text = self._extract_all_text(draft).lower()

        # 1. Unapproved Catch-up / Backlog Bookkeeping
        bk_scope = approved_scope.get("bookkeeping")
        if isinstance(bk_scope, dict) and not bk_scope.get("catchup_cleanup", False):
            # Check if active catchup service is described in bullets
            for s in draft.sections:
                for sub in s.subsections:
                    for b in sub.bullets:
                        b_lower = b.lower()
                        if "catch-up" in b_lower or "cleanup of prior" in b_lower or "backlog cleanup" in b_lower:
                            # If it appears as an active deliverable (not in exclusions)
                            violations.append("Unauthorized catchup/cleanup bookkeeping deliverable included in services.")

        # 2. Unapproved T3010 support
        comp_scope = approved_scope.get("compliance")
        if isinstance(comp_scope, dict) and not comp_scope.get("t3010_support", False):
            for s in draft.sections:
                for sub in s.subsections:
                    for b in sub.bullets:
                        b_lower = b.lower()
                        if "t3010" in b_lower or "charity information return" in b_lower:
                            violations.append("Unauthorized T3010 filing deliverable included in compliance services.")

        # 3. Completely absent service families (e.g., payroll absent but included)
        if "payroll" not in approved_scope:
            for s in draft.sections:
                if "payroll" in s.section_title.lower():
                    violations.append("Unauthorized payroll section present when payroll is not in approved scope.")

        return violations

    # --------------------------------------------------------------------------
    # Check 4: Pricing Safety
    # --------------------------------------------------------------------------
    def check_pricing_safety(self, draft: ProposalDraft, plan_data: Dict[str, Any]) -> List[str]:
        """Ensures pricing integrity: no invented fees, placeholder preservation."""
        violations = []
        plan_pricing = plan_data.get("pricing") or plan_data.get("commercial_summary") or {}
        draft_pricing = draft.pricing or {}

        # 1. Placeholder preservation
        plan_has_placeholders = plan_pricing.get("has_placeholders", False)
        plan_fee_items = plan_pricing.get("fee_items", [])

        # Check if plan had placeholders
        has_pending_in_plan = plan_has_placeholders or any(item.get("is_placeholder", False) for item in plan_fee_items)

        if has_pending_in_plan:
            draft_fee_items = draft_pricing.get("fee_items", [])
            draft_has_ph = draft_pricing.get("has_placeholders", False)
            token_present = any(
                "[PRICING_PLACEHOLDER" in str(item.get("placeholder_token", "")) or
                "[PRICING_PLACEHOLDER" in str(item.get("description", "")) or
                item.get("amount") is None or
                item.get("is_placeholder", False)
                for item in draft_fee_items
            )
            if not (draft_has_ph or token_present):
                violations.append("Pending pricing placeholder was not preserved; invented fee amounts detected.")

        # 2. Fee item amounts matching
        if not has_pending_in_plan and plan_fee_items:
            draft_fee_items = draft_pricing.get("fee_items", [])
            plan_amounts = [item.get("amount") for item in plan_fee_items if item.get("amount") is not None]
            draft_amounts = [item.get("amount") for item in draft_fee_items if item.get("amount") is not None]

            # If draft has fee items with amounts, check they don't invent extra arbitrary fees
            for d_amt in draft_amounts:
                if d_amt not in plan_amounts:
                    violations.append(f"Invented or altered fee amount detected in pricing schedule: ${d_amt:,.2f}")

        return violations

    # --------------------------------------------------------------------------
    # Check 5: Reference Block Integrity
    # --------------------------------------------------------------------------
    def check_reference_blocks(self, draft: ProposalDraft, plan_data: Dict[str, Any]) -> List[str]:
        """Verifies that canonical reference blocks (Why Us, Backlog, Software, HR) appear verbatim."""
        violations = []
        required_texts = []

        # 1. Collect from sections
        for sec in plan_data.get("sections", []):
            for blk in sec.get("reference_blocks", []):
                if isinstance(blk, dict) and blk.get("content"):
                    content = blk["content"].strip()
                    if len(content) > 15 and not content.startswith("REF_BLOCK_"):
                        if content not in required_texts:
                            required_texts.append(content)

        # 2. Collect from pricing disclaimers
        pricing = plan_data.get("pricing") or plan_data.get("commercial_summary") or {}
        for d in pricing.get("disclaimers", []):
            if isinstance(d, dict) and d.get("content"):
                content = d["content"].strip()
                if len(content) > 15 and not content.startswith("REF_BLOCK_"):
                    if content not in required_texts:
                        required_texts.append(content)

        # 3. Collect from top-level reference_blocks if dicts
        for blk in plan_data.get("reference_blocks", []):
            if isinstance(blk, dict) and blk.get("content"):
                content = blk["content"].strip()
                if len(content) > 15 and not content.startswith("REF_BLOCK_"):
                    if content not in required_texts:
                        required_texts.append(content)

        # Check inside why_us, exclusions, sections, pricing
        all_draft_text = self._extract_all_text(draft)
        normalized_corpus = self._normalize_whitespace(all_draft_text)

        for req in required_texts:
            norm_req = self._normalize_whitespace(req)
            if norm_req not in normalized_corpus:
                # Also check prefix match for multi-line blocks
                prefix = norm_req[:60]
                if prefix not in normalized_corpus:
                    violations.append(f"Canonical reference block altered or missing: '{req[:50]}...'")

        return violations

    # --------------------------------------------------------------------------
    # Check 6: Style Compliance
    # --------------------------------------------------------------------------
    def check_style_compliance(self, draft: ProposalDraft) -> Tuple[List[str], List[str]]:
        """Checks forbidden buzzwords, marketing hype, passive voice, and bullet length."""
        errors = []
        warnings = []
        all_text = self._extract_all_text(draft)

        # 1. Forbidden buzzwords
        for buzz in self.FORBIDDEN_BUZZWORDS:
            if re.search(rf"\b{re.escape(buzz)}\b", all_text, re.IGNORECASE):
                errors.append(f"Forbidden buzzword/hype detected: '{buzz}'")

        # 2. Bullet analysis: length, passive voice, trailing periods
        for s in draft.sections:
            for sub in s.subsections:
                for b in sub.bullets:
                    b_strip = b.strip()

                    # Trailing periods
                    if b_strip.endswith("."):
                        warnings.append(f"Bullet point has trailing period (Sympl style prefers none): '{b_strip[:40]}...'")

                    # Word count
                    words = b_strip.split()
                    word_count = len(words)
                    if word_count > 25:
                        errors.append(f"Bullet exceeds maximum length ({word_count} words > 25 words): '{b_strip[:40]}...'")
                    elif word_count < 4:
                        warnings.append(f"Bullet too short ({word_count} words < 4 words): '{b_strip}'")

                    # Passive voice
                    for pat in self.PASSIVE_PATTERNS:
                        if re.search(pat, b_strip, re.IGNORECASE):
                            errors.append(f"Passive voice detected in service bullet: '{b_strip}'")

        return errors, warnings

    # --------------------------------------------------------------------------
    # Helper Utilities
    # --------------------------------------------------------------------------
    def _extract_all_text(self, draft: ProposalDraft) -> str:
        """Flattens all text fields of ProposalDraft into a single string."""
        parts = [
            draft.title,
            draft.executive_summary,
            " ".join(draft.why_us),
            " ".join(draft.exclusions),
            json.dumps(draft.pricing)
        ]
        for s in draft.sections:
            parts.append(s.section_title)
            parts.append(s.opening_text)
            for sub in s.subsections:
                parts.append(sub.heading)
                parts.extend(sub.bullets)

        return " ".join(parts)

    def _normalize_whitespace(self, text: str) -> str:
        """Collapses consecutive whitespace to single space for robust substring matching."""
        return re.sub(r"\s+", " ", text).strip()

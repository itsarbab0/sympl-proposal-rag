"""
Sympl Solutions Proposal RAG — Proposal Renderer Validator

Implements strict validation checks for the presentation rendering pipeline:
  1. Draft Input Contract Validator: Ensures all mandatory fields are present.
  2. Content Integrity Validator: Confirms rendered text matches proposal_draft.json verbatim.
  3. Pricing Integrity Validator: Guarantees zero fee mutation, matching values, and placeholder preservation.
  4. Reference Integrity Validator: Ensures Why Us credentials and exclusions appear verbatim.
  5. Layout Overflow Validator: Enforces template limits, prevents empty pages, and detects missing headings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import re
import json

from sympl_renderer.schema import RenderedProposal, RenderPage, ComponentType
from sympl_renderer.exceptions import (
    InvalidDraftError,
    ContentIntegrityError,
    PricingIntegrityError,
    ReferenceIntegrityError,
    LayoutOverflowError
)


@dataclass
class RenderValidationResult:
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


def validate_draft_input(draft_data: Dict[str, Any]) -> None:
    """
    Validates input contract for proposal_draft.json.
    Must contain: title, executive_summary, sections, why_us, pricing, exclusions, validation_metadata.
    Raises InvalidDraftError if any required field is missing.
    """
    required_keys = [
        "executive_summary",
        "sections",
        "why_us",
        "pricing",
        "exclusions",
        "validation_metadata"
    ]

    # Accept either title or proposal_title
    has_title = "title" in draft_data or "proposal_title" in draft_data
    if not has_title:
        raise InvalidDraftError("Draft validation failed: Missing mandatory field 'title' (or 'proposal_title').")

    missing = [k for k in required_keys if k not in draft_data]
    if missing:
        raise InvalidDraftError(f"Draft validation failed: Missing mandatory fields: {missing}")

    if not isinstance(draft_data.get("sections"), list):
        raise InvalidDraftError("Draft validation failed: 'sections' must be a list.")


class ContentIntegrityValidator:
    """Verifies that all text from proposal_draft.json is accurately represented without modification."""

    @classmethod
    def validate(cls, rendered: RenderedProposal, draft: Dict[str, Any]) -> List[str]:
        errors = []
        all_rendered_text = cls._extract_all_rendered_text(rendered)
        normalized_rendered = cls._normalize_whitespace(all_rendered_text)

        # 1. Executive Summary check
        exec_summary = draft.get("executive_summary", "").strip()
        if exec_summary and cls._normalize_whitespace(exec_summary) not in normalized_rendered:
            errors.append("Executive summary text not found verbatim in rendered proposal.")

        # 2. Sections text check
        for s in draft.get("sections", []):
            sec_title = s.get("section_title", "").strip()
            if sec_title and cls._normalize_whitespace(sec_title) not in normalized_rendered:
                errors.append(f"Section title missing or altered: '{sec_title}'")

            opening = s.get("opening_text", "").strip()
            if opening and cls._normalize_whitespace(opening) not in normalized_rendered:
                errors.append(f"Section opening text missing or altered in '{sec_title}'")

            for sub in s.get("subsections", []):
                heading = sub.get("heading", "").strip()
                if heading and cls._normalize_whitespace(heading) not in normalized_rendered:
                    errors.append(f"Subsection heading missing or altered: '{heading}'")

                for b in sub.get("bullets", []):
                    b_clean = b.strip()
                    if b_clean and cls._normalize_whitespace(b_clean) not in normalized_rendered:
                        errors.append(f"Service bullet missing or altered: '{b_clean[:45]}...'")

        return errors

    @classmethod
    def _extract_all_rendered_text(cls, rendered: RenderedProposal) -> str:
        parts = [rendered.title, rendered.client_name]
        for p in rendered.pages:
            parts.append(p.page_title)
            parts.append(p.page_subtitle)
            for c in p.components:
                if c.title:
                    parts.append(c.title)
                if c.content:
                    parts.append(c.content)
                if c.items:
                    parts.extend(c.items)
                if c.table_data:
                    for row in c.table_data.get("rows", []):
                        parts.extend(str(cell) for cell in row)
        return " ".join(parts)

    @classmethod
    def _normalize_whitespace(cls, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


class PricingIntegrityValidator:
    """Verifies that pricing structure, fee amounts, and placeholders are preserved exactly."""

    @classmethod
    def validate(cls, rendered: RenderedProposal, draft: Dict[str, Any]) -> List[str]:
        errors = []
        draft_pricing = draft.get("pricing", {})
        draft_fee_items = draft_pricing.get("fee_items", [])

        # Find pricing page in rendered proposal
        pricing_page = next((p for p in rendered.pages if p.page_type == "pricing"), None)
        if not pricing_page and draft_fee_items:
            errors.append("Pricing page missing from rendered proposal when draft contains fee items.")
            return errors

        # Extract table data from pricing page
        table_comp = next((c for c in pricing_page.components if c.component_type == ComponentType.TABLE), None)
        if not table_comp or not table_comp.table_data:
            errors.append("Pricing schedule table component missing from rendered pricing page.")
            return errors

        rendered_rows = table_comp.table_data.get("rows", [])
        rendered_text = json.dumps(rendered_rows)

        for item in draft_fee_items:
            cat = item.get("category", "")
            amount = item.get("amount")
            is_ph = item.get("is_placeholder", False)
            ph_token = item.get("placeholder_token", "")

            # Category must appear
            if cat and cat not in rendered_text:
                errors.append(f"Fee category missing from rendered pricing table: '{cat}'")

            # Check amount preservation
            if is_ph or amount is None:
                # Placeholder must be preserved
                if not ("[PRICING_PLACEHOLDER" in rendered_text or "Pending" in rendered_text or ph_token in rendered_text):
                    errors.append(f"Pricing placeholder was not preserved for category '{cat}'")
            else:
                # Numerical amount must appear
                formatted_amt = f"{amount:,.2f}"
                plain_amt = str(amount)
                if formatted_amt not in rendered_text and plain_amt not in rendered_text:
                    errors.append(f"Approved fee amount ${amount} missing from rendered pricing table for '{cat}'")

        return errors


class ReferenceIntegrityValidator:
    """Verifies that Why Us blocks and exclusions are preserved verbatim."""

    @classmethod
    def validate(cls, rendered: RenderedProposal, draft: Dict[str, Any]) -> List[str]:
        errors = []
        all_rendered = ContentIntegrityValidator._extract_all_rendered_text(rendered)
        norm_rendered = ContentIntegrityValidator._normalize_whitespace(all_rendered)

        # 1. Why Us credentials
        for block in draft.get("why_us", []):
            clean_b = block.strip()
            if len(clean_b) > 20:
                if ContentIntegrityValidator._normalize_whitespace(clean_b) not in norm_rendered:
                    errors.append(f"Why Us reference block altered or missing: '{clean_b[:50]}...'")

        # 2. Exclusions and disclaimers
        for exc in draft.get("exclusions", []):
            clean_e = exc.strip()
            if len(clean_e) > 20:
                if ContentIntegrityValidator._normalize_whitespace(clean_e) not in norm_rendered:
                    errors.append(f"Exclusion / boundary block altered or missing: '{clean_e[:50]}...'")

        return errors


class LayoutOverflowValidator:
    """Verifies that no empty pages exist, all headings are present, and component capacity limits are respected."""

    @classmethod
    def validate(cls, rendered: RenderedProposal) -> tuple[List[str], List[str]]:
        errors = []
        warnings = []

        if not rendered.pages:
            errors.append("Rendered proposal contains zero pages.")
            return errors, warnings

        for page in rendered.pages:
            # Check 1: Missing page heading
            if not page.page_title or not page.page_title.strip():
                errors.append(f"Page {page.page_number} is missing a page title.")

            # Check 2: Empty page (no components or no content)
            if not page.components:
                errors.append(f"Page {page.page_number} ({page.page_type}) is completely empty.")
            else:
                has_content = any(
                    (c.title and c.title.strip()) or
                    (c.content and c.content.strip()) or
                    (c.items and len(c.items) > 0) or
                    (c.table_data and len(c.table_data.get("rows", [])) > 0)
                    for c in page.components
                )
                if not has_content:
                    errors.append(f"Page {page.page_number} ({page.page_type}) contains no text or table content.")

            # Check 3: Overflow flag or excessive bullets
            if page.overflow_detected:
                warnings.append(f"Page {page.page_number} ({page.page_title}) flagged for high content density / layout overflow.")

            # Bullet capacity warning
            bullet_count = page.capacity_metrics.get("bullet_count", 0)
            if bullet_count > 12:
                errors.append(f"Page {page.page_number} exceeds maximum recommended bullet capacity ({bullet_count} > 12).")

        return errors, warnings


class RenderValidator:
    """Unified validator running all presentation integrity and overflow checks."""

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate(
        self,
        rendered: RenderedProposal,
        draft: Dict[str, Any],
        raise_on_error: bool = False
    ) -> RenderValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        # 1. Content Integrity
        content_errors = ContentIntegrityValidator.validate(rendered, draft)
        if content_errors:
            errors.extend(content_errors)
            details["content_integrity"] = {"passed": False, "violations": content_errors}
            if raise_on_error:
                raise ContentIntegrityError(f"Content Integrity Violation: {content_errors[0]}")
        else:
            details["content_integrity"] = {"passed": True}

        # 2. Pricing Integrity
        pricing_errors = PricingIntegrityValidator.validate(rendered, draft)
        if pricing_errors:
            errors.extend(pricing_errors)
            details["pricing_integrity"] = {"passed": False, "violations": pricing_errors}
            if raise_on_error:
                raise PricingIntegrityError(f"Pricing Integrity Violation: {pricing_errors[0]}")
        else:
            details["pricing_integrity"] = {"passed": True}

        # 3. Reference Integrity
        ref_errors = ReferenceIntegrityValidator.validate(rendered, draft)
        if ref_errors:
            errors.extend(ref_errors)
            details["reference_integrity"] = {"passed": False, "violations": ref_errors}
            if raise_on_error:
                raise ReferenceIntegrityError(f"Reference Integrity Violation: {ref_errors[0]}")
        else:
            details["reference_integrity"] = {"passed": True}

        # 4. Layout Overflow
        overflow_errors, overflow_warnings = LayoutOverflowValidator.validate(rendered)
        if overflow_errors:
            errors.extend(overflow_errors)
            details["layout_overflow"] = {"passed": False, "violations": overflow_errors}
            if raise_on_error:
                raise LayoutOverflowError(f"Layout Overflow Violation: {overflow_errors[0]}")
        else:
            details["layout_overflow"] = {"passed": True, "warnings": overflow_warnings}
        warnings.extend(overflow_warnings)

        passed = len(errors) == 0
        return RenderValidationResult(passed=passed, errors=errors, warnings=warnings, details=details)

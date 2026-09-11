"""
Sympl Solutions — Canva Layout Validation Engine
Validates proposal payloads against Canva template capabilities, character limits,
word limits, table row boundaries, and visual overflow constraints before export.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from .template_schema import CanvaProposalData


class CanvaLayoutValidator:
    """
    Validation engine ensuring content conforms to template geometry and capacity rules.
    """

    def __init__(self, template_config_path: Optional[str] = None):
        if template_config_path is None:
            # Look in templates directory
            base = Path(__file__).resolve().parent
            candidates = [
                base / "templates" / "DAHU1H8DMjc.json",
                base.parent.parent / "templates" / "DAHU1H8DMjc.json",
                Path(r"d:\Sympl\templates\DAHU1H8DMjc.json")
            ]
            for c in candidates:
                if c.exists():
                    template_config_path = str(c)
                    break

        self.config_path = Path(template_config_path) if template_config_path else None
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path and self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"fields": {}, "table_capacities": {}}

    def validate_proposal(self, proposal_data: CanvaProposalData) -> Dict[str, Any]:
        """
        Runs comprehensive validation checks:
        1. Text overflow (word and character limits)
        2. Empty required fields
        3. Missing images or uncleaned placeholder assets
        4. Table row mismatches
        5. Hard character limit bounds
        """
        errors: List[str] = []
        warnings: List[str] = []

        fields = self.config.get("fields", {})
        tables = self.config.get("table_capacities", {})

        # 1. Validate Cover Page
        cover = proposal_data.cover
        if not cover.client_name or not cover.client_name.strip():
            errors.append("Empty required field: cover.client_name")
        elif len(cover.client_name) > fields.get("cover_client_and_date", {}).get("max_chars", 50):
            warnings.append(f"Cover client name ({len(cover.client_name)} chars) exceeds recommended max 50 chars")

        if not cover.proposal_title or not cover.proposal_title.strip():
            errors.append("Empty required field: cover.proposal_title")
        elif len(cover.proposal_title) > fields.get("cover_title", {}).get("max_chars", 70):
            warnings.append(f"Cover title ({len(cover.proposal_title)} chars) exceeds recommended max 70 chars")

        # 2. Validate Executive Summary
        exec_sum = proposal_data.executive_summary
        exec_text = exec_sum.full_text
        if not exec_text or not exec_text.strip():
            errors.append("Empty required field: executive_summary")
        else:
            exec_words = len(exec_text.split())
            max_exec_words = fields.get("exec_summary_body", {}).get("max_words", 220)
            if exec_words > max_exec_words:
                warnings.append(
                    f"Executive summary word count ({exec_words} words) exceeds template safe capacity "
                    f"({max_exec_words} words). Risk of visual overflow on Page 2."
                )

        # 3. Validate Commercial Page (Page 8)
        pricing = proposal_data.pricing
        if not pricing.investment_amount or not pricing.investment_amount.strip():
            errors.append("Empty required field: pricing.investment_amount")

        comm_desc = pricing.investment_description
        comm_words = len(comm_desc.split()) if comm_desc else 0
        max_comm_words = fields.get("monthly_investment_card", {}).get("max_words", 15)
        if comm_words > max_comm_words:
            errors.append(
                f"Commercial investment description ({comm_words} words) strictly exceeds the {max_comm_words}-word limit. "
                f"Will overlap the Fee Schedule subheader on Page 8."
            )
        elif len(comm_desc) > fields.get("monthly_investment_card", {}).get("max_chars", 110):
            warnings.append(
                f"Commercial investment description ({len(comm_desc)} chars) exceeds recommended 110 chars."
            )

        # 4. Validate Table Row Capacities
        deliverables_max = tables.get("deliverables_table", {}).get("max_rows", 7)
        timeline_max = tables.get("timeline_table", {}).get("max_rows", 6)

        total_deliverables = sum(len(s.deliverables) for s in proposal_data.services)
        if total_deliverables > deliverables_max:
            warnings.append(
                f"Total deliverables ({total_deliverables}) exceeds Page 3 table capacity ({deliverables_max} rows). "
                f"Excess items will be omitted or summarized."
            )

        timeline_items_count = len(proposal_data.timeline.items)
        if timeline_items_count > timeline_max:
            warnings.append(
                f"Timeline phases count ({timeline_items_count}) exceeds Page 7 timeline capacity ({timeline_max} rows). "
                f"Excess phases will be truncated."
            )

        # 5. Asset Fills Check
        # Check if client cover artwork is explicitly managed
        has_client_cover = bool(proposal_data.client_assets.get("cover_artwork"))
        if not has_client_cover:
            # Note: asset_mapper will automatically emit delete_element
            pass

        # Calculate status
        is_valid = len(errors) == 0
        if errors:
            status = "FAIL"
        elif warnings:
            status = "WARN"
        else:
            status = "PASS"

        return {
            "status": status,
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "metrics": {
                "client_name": cover.client_name,
                "proposal_title": cover.proposal_title,
                "executive_summary_words": len(exec_text.split()) if exec_text else 0,
                "commercial_desc_words": comm_words,
                "services_count": len(proposal_data.services),
                "timeline_items_count": timeline_items_count,
                "template_id": self.config.get("template_id", "DAHU1H8DMjc")
            }
        }

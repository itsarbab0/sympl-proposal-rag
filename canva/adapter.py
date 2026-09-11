"""
Sympl Solutions — Canva Operations Adapter Layer
Converts MasterTemplateMapper editing operations and CanvaProposalData
into Canva Connect API payloads (Autofill data dictionary and transaction operations).
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import CanvaEditingOperation
from .template_schema import CanvaProposalData


class CanvaOperationsAdapter:
    """
    Adapter converting 70 MasterTemplateMapper editing operations and structured
    proposal fields into Canva Connect API compatible payloads.
    """

    def __init__(self, template_config_path: Optional[str] = None):
        if template_config_path is None:
            base = Path(__file__).resolve().parent
            template_config_path = str(base / "templates" / "DAHU1H8DMjc.json")
        self.config_path = Path(template_config_path)
        self.element_to_field_map = self._build_element_field_map()

    def _build_element_field_map(self) -> Dict[str, str]:
        """Inverts the template config fields dictionary to map element_id -> field_name."""
        mapping = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    for field_name, field_info in cfg.get("fields", {}).items():
                        elem_id = field_info.get("element_id")
                        if elem_id:
                            mapping[elem_id] = field_name
            except Exception:
                pass
        return mapping

    def operations_to_autofill_dataset(
        self,
        operations: List[CanvaEditingOperation],
        cdata: Optional[CanvaProposalData] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Adapts the 70 operations into Canva's Autofill data dictionary format:
        {
           "<field_name>": { "type": "text", "text": "<value>" }
        }
        """
        dataset: Dict[str, Dict[str, Any]] = {}

        # 1. Map operations by recognized field name or element ID
        for op in operations:
            if isinstance(op, dict):
                text_val = op.get("text") or op.get("replace_text")
                elem_id = op.get("element_id")
            else:
                text_val = getattr(op, "text", None) or getattr(op, "replace_text", None)
                elem_id = getattr(op, "element_id", None)

            if text_val is None:
                continue

            # Check if this element ID has a recognized template field name
            field_name = self.element_to_field_map.get(elem_id) if elem_id else None

            if field_name:
                dataset[field_name] = {
                    "type": "text",
                    "text": str(text_val)
                }

            # Also provide element-keyed entry for direct element binding
            if elem_id:
                dataset[f"elem_{elem_id}"] = {
                    "type": "text",
                    "text": str(text_val)
                }

        # 2. Augment with structured proposal fields from CanvaProposalData if available
        if cdata:
            if hasattr(cdata, "cover") and cdata.cover:
                dataset["client_name"] = {"type": "text", "text": getattr(cdata.cover, "client_name", "")}
                dataset["proposal_title"] = {"type": "text", "text": getattr(cdata.cover, "proposal_title", "")}
                dataset["proposal_date"] = {"type": "text", "text": getattr(cdata.cover, "date", "")}
            if hasattr(cdata, "executive_summary") and cdata.executive_summary:
                exec_text = getattr(cdata.executive_summary, "full_text", "") or " ".join(getattr(cdata.executive_summary, "paragraphs", []))
                dataset["executive_summary"] = {"type": "text", "text": exec_text}
            if hasattr(cdata, "pricing") and cdata.pricing:
                dataset["total_investment"] = {"type": "text", "text": getattr(cdata.pricing, "investment_amount", "")}
                dataset["investment_description"] = {"type": "text", "text": getattr(cdata.pricing, "investment_description", "")}

        return dataset

    def operations_to_transaction_payload(
        self,
        operations: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Converts CanvaEditingOperation objects or dicts into serializable JSON dictionaries.
        """
        return [op.to_dict() if hasattr(op, "to_dict") else op for op in operations]

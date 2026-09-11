"""
Sympl Solutions — Canva Client
Provides high-level client interface for Canva template cloning, transaction editing,
bulk operation execution, and PDF export.
"""

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import (
    CanvaDesignMetadata,
    CanvaExportResult,
    CanvaEditingOperation,
)
from .template_mapper import MasterTemplateMapper


class CanvaClient:
    """
    Client for automating Canva template operations via Composio integration.
    Implements Strategy C: Design Duplication + Editing Transaction + PDF Export.
    """

    DEFAULT_MASTER_TEMPLATE_ID = "DAHU1H8DMjc"

    def __init__(self, master_template_id: Optional[str] = None):
        self.master_template_id = master_template_id or self.DEFAULT_MASTER_TEMPLATE_ID
        self.mapper = MasterTemplateMapper()

    def clone_design(self, source_design_id: Optional[str] = None, title: Optional[str] = None) -> CanvaDesignMetadata:
        """
        Creates an isolated duplicate of a Canva design using CANVA_POST_DESIGNS.
        Source design remains 100% untouched.
        """
        target_id = source_design_id or self.master_template_id
        # Note: Canva API requires only design_id and type='design' for design duplication
        payload = {
            "type": "design",
            "design_id": target_id
        }
        return payload

    def prepare_operations_from_draft(self, draft_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Translates a ProposalDraft dictionary into an array of Canva editing operations.
        """
        return self.mapper.map_proposal_to_operations(draft_dict)

    def execute_export(self, design_id: str, format_type: str = "pdf") -> Dict[str, Any]:
        """
        Constructs the export payload for CANVA_POST_EXPORTS.
        """
        return {
            "design_id": design_id,
            "format": {
                "type": format_type
            }
        }

    def download_pdf(self, download_url: str, output_path: str) -> str:
        """
        Downloads the generated Canva PDF file to a local destination.
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(download_url, str(out_file))
        return str(out_file)

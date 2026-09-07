"""
Sympl Solutions Proposal RAG — Proposal Renderer Layer

The ProposalRenderer coordinates the complete presentation compilation pipeline:
  1. Draft Input Contract Validation (rejects malformed drafts).
  2. Template Mapping & Dynamic Page Scaling (preserves all text, pricing, and blocks).
  3. Corporate Branding Injection (colors, typography, assets).
  4. Canva Integration (via CanvaConnectClient or MockCanvaClient).
  5. Presentation Integrity Validation (Content, Pricing, Reference, Layout Overflow).
  6. Output Adaptation & Serialization (JSON, Canva Payload, HTML/PDF, Markdown).
"""

import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from sympl_renderer.schema import (
    RenderedProposal,
    RenderPage,
    ExportStatus
)
from sympl_renderer.branding import SymplBranding, DEFAULT_BRANDING
from sympl_renderer.canva_client import CanvaClient, get_canva_client
from sympl_renderer.template_mapper import TemplateMapper
from sympl_renderer.validator import RenderValidator, validate_draft_input
from sympl_renderer.output_adapter import (
    JsonOutputAdapter,
    CanvaPayloadAdapter,
    HtmlPdfAdapter,
    MarkdownAdapter
)
from sympl_renderer.exceptions import RendererError, InvalidDraftError


class ProposalRenderer:
    """
    Presentation compilation engine for Sympl Solutions proposals.
    Transforms validated proposal_draft.json into presentation-ready output.
    """

    def __init__(
        self,
        canva_client: Optional[CanvaClient] = None,
        branding: Optional[SymplBranding] = None,
        template_mapper: Optional[TemplateMapper] = None,
        validator: Optional[RenderValidator] = None
    ):
        self.canva_client = canva_client or get_canva_client()
        self.branding = branding or DEFAULT_BRANDING
        self.template_mapper = template_mapper or TemplateMapper(branding=self.branding)
        self.validator = validator or RenderValidator()
        self.json_adapter = JsonOutputAdapter()
        self.canva_adapter = CanvaPayloadAdapter()
        self.html_adapter = HtmlPdfAdapter()
        self.markdown_adapter = MarkdownAdapter()

    def render(self, draft_input: Union[Dict[str, Any], str, Path]) -> RenderedProposal:
        """
        Main rendering pipeline: converts proposal_draft into presentation RenderedProposal.

        Args:
            draft_input: Dict, JSON string, or file path pointing to proposal_draft.json.

        Returns:
            Fully compiled, validated RenderedProposal.

        Raises:
            InvalidDraftError: If draft is missing required fields.
            ContentIntegrityError: If rendered text deviates from the approved draft.
            PricingIntegrityError: If fees or placeholders are altered.
            ReferenceIntegrityError: If reference blocks are altered.
            LayoutOverflowError: If page limits are exceeded or pages are empty.
            CanvaAPIError: If external Canva communications fail.
        """
        # 1. Ingest and parse draft data
        draft_dict = self._load_draft_data(draft_input)

        # 2. Validate input contract
        validate_draft_input(draft_dict)

        title = draft_dict.get("title") or draft_dict.get("proposal_title") or "Proposal Document"
        client_name = self.template_mapper._extract_client_name(title, draft_dict)

        # 3. Dynamic Template Mapping & Branding
        pages = self.template_mapper.map_draft_to_pages(draft_dict)

        # 4. Canva Integration (Create, Populate, Export)
        design_info = self.canva_client.create_design(title=title)
        design_id = design_info.get("design_id", "canva_des_unknown")

        # Convert pages to Canva autofill payload
        pages_payload = [p.to_dict() for p in pages]
        populate_resp = self.canva_client.populate_design(design_id=design_id, pages_data=pages_payload)
        pdf_url = self.canva_client.export_pdf(design_id=design_id)

        # 5. Assemble RenderedProposal data model
        sections_overview = [
            {
                "section_title": s.get("section_title", ""),
                "subsections_count": len(s.get("subsections", []))
            }
            for s in draft_dict.get("sections", [])
        ]

        rendered = RenderedProposal(
            design_id=design_id,
            title=title,
            client_name=client_name,
            page_count=len(pages),
            pages=pages,
            sections=sections_overview,
            export_status=ExportStatus.EXPORTED if pdf_url else ExportStatus.POPULATED,
            pdf_url=pdf_url,
            branding=self.branding.to_dict(),
            render_metadata={
                "engine": "sympl_renderer_v1",
                "canva_client": "mock" if self.canva_client.is_mock else "canva_connect_v1",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "template_id": design_info.get("template_id", "default_template")
            }
        )

        # 6. Strict Presentation Integrity Validation
        val_result = self.validator.validate(rendered, draft_dict, raise_on_error=True)
        rendered.render_metadata["validation_results"] = val_result.to_dict()

        return rendered

    def render_to_file(
        self,
        draft_input: Union[Dict[str, Any], str, Path],
        output_path: Union[str, Path] = "rendered_proposal.json",
        format: str = "json"
    ) -> Path:
        """
        Renders draft and writes output to disk in specified format ('json', 'html', 'markdown').
        """
        rendered = self.render(draft_input)
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fmt_lower = format.lower()
        if fmt_lower == "json":
            self.json_adapter.write_to_file(rendered, str(out_file))
        elif fmt_lower in ("html", "pdf"):
            html_content = self.html_adapter.adapt(rendered)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(html_content)
        elif fmt_lower in ("markdown", "md"):
            md_content = self.markdown_adapter.adapt(rendered)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(md_content)
        else:
            raise ValueError(f"Unsupported output format: '{format}'. Supported: 'json', 'html', 'markdown'.")

        return out_file

    # --------------------------------------------------------------------------
    # Private Helpers
    # --------------------------------------------------------------------------
    def _load_draft_data(self, draft_input: Union[Dict[str, Any], str, Path]) -> Dict[str, Any]:
        """Resolves input into a dictionary."""
        if hasattr(draft_input, "to_dict"):
            return draft_input.to_dict()

        if isinstance(draft_input, dict):
            return draft_input

        if isinstance(draft_input, (str, Path)):
            p = Path(draft_input)
            if p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            if isinstance(draft_input, str) and draft_input.strip().startswith("{"):
                return json.loads(draft_input)

        raise InvalidDraftError(f"Invalid draft input: expected dict, JSON string, or file path, got {type(draft_input)}")

"""
Sympl Solutions Proposal RAG — Proposal Renderer Output Adapters

Converts the internal RenderedProposal data model into target delivery formats:
  - JsonOutputAdapter: Serializes to canonical rendered_proposal.json / proposal_render.json
  - CanvaPayloadAdapter: Formats components into Canva Connect API autofill structures
  - HtmlPdfAdapter: Generates presentation HTML with inline Sympl CSS branding for PDF compilation
  - MarkdownAdapter: Generates high-fidelity structured markdown document
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

from sympl_renderer.schema import RenderedProposal, RenderPage, RenderComponent, ComponentType
from sympl_renderer.exceptions import AdapterError


class OutputAdapter(ABC):
    """Abstract base adapter for proposal rendering output formats."""

    @abstractmethod
    def adapt(self, proposal: RenderedProposal) -> Any:
        """Transforms RenderedProposal into target format representation."""
        pass


class JsonOutputAdapter(OutputAdapter):
    """Serializes RenderedProposal into standard JSON string or dictionary."""

    def adapt(self, proposal: RenderedProposal, indent: int = 2) -> str:
        try:
            return proposal.to_json(indent=indent)
        except Exception as e:
            raise AdapterError(f"Failed to adapt RenderedProposal to JSON: {e}") from e

    def write_to_file(self, proposal: RenderedProposal, file_path: str = "rendered_proposal.json") -> Path:
        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        json_str = self.adapt(proposal)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        return out_path


class CanvaPayloadAdapter(OutputAdapter):
    """Formats RenderedProposal into the exact data structure expected by Canva Connect API."""

    def adapt(self, proposal: RenderedProposal) -> Dict[str, Any]:
        try:
            pages_payload = []
            for page in proposal.pages:
                components_payload = {}
                for comp in page.components:
                    if comp.component_type == ComponentType.HEADING:
                        components_payload[f"{comp.component_id}_title"] = comp.title or ""
                        if comp.content:
                            components_payload[f"{comp.component_id}_content"] = comp.content
                    elif comp.component_type in (ComponentType.PARAGRAPH, ComponentType.CALLOUT):
                        components_payload[comp.component_id] = comp.content or ""
                    elif comp.component_type in (ComponentType.BULLET_LIST, ComponentType.CARD):
                        components_payload[comp.component_id] = {
                            "heading": comp.title or "",
                            "bullets": comp.items
                        }
                    elif comp.component_type == ComponentType.TABLE:
                        components_payload[comp.component_id] = comp.table_data or {}

                pages_payload.append({
                    "page_number": page.page_number,
                    "page_type": page.page_type,
                    "title": page.page_title,
                    "elements": components_payload
                })

            return {
                "design_id": proposal.design_id,
                "title": proposal.title,
                "client_name": proposal.client_name,
                "page_count": proposal.page_count,
                "pages": pages_payload
            }
        except Exception as e:
            raise AdapterError(f"Failed to adapt RenderedProposal to Canva payload: {e}") from e


class HtmlPdfAdapter(OutputAdapter):
    """Converts RenderedProposal into styled standalone HTML ready for PDF compilation."""

    def adapt(self, proposal: RenderedProposal) -> str:
        try:
            colors = proposal.branding.get("colors", {})
            primary = colors.get("primary", "#1A2E40")
            secondary = colors.get("secondary", "#008080")
            neutral_dark = colors.get("neutral_dark", "#2D3748")
            neutral_light = colors.get("neutral_light", "#F7FAFC")
            border = colors.get("border", "#E2E8F0")

            html_lines = [
                "<!DOCTYPE html>",
                "<html lang=\"en\">",
                "<head>",
                "  <meta charset=\"UTF-8\">",
                f"  <title>{proposal.title}</title>",
                "  <style>",
                "    @page { size: letter; margin: 0.8in; }",
                "    body { font-family: 'Inter', Arial, sans-serif; color: " + neutral_dark + "; line-height: 1.5; margin: 0; padding: 0; }",
                "    .page { page-break-after: always; padding: 20px 0; min-height: 900px; }",
                "    .page:last-child { page-break-after: avoid; }",
                "    h1 { font-family: 'Montserrat', sans-serif; color: " + primary + "; font-size: 26pt; margin-bottom: 8px; }",
                "    h2 { font-family: 'Montserrat', sans-serif; color: " + primary + "; font-size: 18pt; border-bottom: 2px solid " + secondary + "; padding-bottom: 6px; }",
                "    h3 { font-family: 'Montserrat', sans-serif; color: " + primary + "; font-size: 13pt; margin-top: 14px; margin-bottom: 6px; }",
                "    p { font-size: 10.5pt; color: " + neutral_dark + "; }",
                "    ul { margin: 6px 0 14px 20px; padding: 0; }",
                "    li { font-size: 10pt; margin-bottom: 4px; }",
                "    .card { background-color: " + neutral_light + "; border: 1px solid " + border + "; border-radius: 6px; padding: 14px; margin-bottom: 12px; }",
                "    .callout { background-color: #EFF6FF; border-left: 4px solid " + primary + "; padding: 10px 14px; margin-bottom: 10px; font-size: 9.5pt; }",
                "    table { width: 100%; border-collapse: collapse; margin: 14px 0; }",
                "    th { background-color: " + primary + "; color: #FFFFFF; font-size: 10pt; text-align: left; padding: 8px 10px; }",
                "    td { border-bottom: 1px solid " + border + "; font-size: 9.5pt; padding: 8px 10px; }",
                "    .footer { font-size: 8.5pt; color: #718096; margin-top: 30px; border-top: 1px solid " + border + "; padding-top: 8px; }",
                "  </style>",
                "</head>",
                "<body>"
            ]

            for page in proposal.pages:
                html_lines.append(f"  <div class=\"page\" id=\"page_{page.page_number}\">")
                html_lines.append(f"    <h2>{page.page_title}</h2>")
                if page.page_subtitle:
                    html_lines.append(f"    <p><em>{page.page_subtitle}</em></p>")

                for comp in page.components:
                    if comp.component_type == ComponentType.HEADING:
                        if comp.title:
                            html_lines.append(f"    <h3>{comp.title}</h3>")
                        if comp.content:
                            html_lines.append(f"    <p>{comp.content}</p>")
                    elif comp.component_type == ComponentType.PARAGRAPH:
                        if comp.title:
                            html_lines.append(f"    <h3>{comp.title}</h3>")
                        if comp.content:
                            html_lines.append(f"    <p>{comp.content}</p>")
                    elif comp.component_type == ComponentType.BULLET_LIST:
                        if comp.title:
                            html_lines.append(f"    <h3>{comp.title}</h3>")
                        html_lines.append("    <ul>")
                        for b in comp.items:
                            html_lines.append(f"      <li>{b}</li>")
                        html_lines.append("    </ul>")
                    elif comp.component_type == ComponentType.CARD:
                        html_lines.append("    <div class=\"card\">")
                        if comp.title:
                            html_lines.append(f"      <h3>{comp.title}</h3>")
                        html_lines.append("      <ul>")
                        for item in comp.items:
                            html_lines.append(f"        <li>{item}</li>")
                        html_lines.append("      </ul>")
                        html_lines.append("    </div>")
                    elif comp.component_type == ComponentType.CALLOUT:
                        html_lines.append(f"    <div class=\"callout\">{comp.content}</div>")
                    elif comp.component_type == ComponentType.TABLE and comp.table_data:
                        html_lines.append("    <table>")
                        html_lines.append("      <thead><tr>")
                        for h in comp.table_data.get("headers", []):
                            html_lines.append(f"        <th>{h}</th>")
                        html_lines.append("      </tr></thead>")
                        html_lines.append("      <tbody>")
                        for row in comp.table_data.get("rows", []):
                            html_lines.append("        <tr>")
                            for cell in row:
                                html_lines.append(f"          <td>{cell}</td>")
                            html_lines.append("        </tr>")
                        html_lines.append("      </tbody>")
                        html_lines.append("    </table>")
                    elif comp.component_type == ComponentType.FOOTER:
                        html_lines.append(f"    <div class=\"footer\">{comp.content}</div>")

                html_lines.append("  </div>")

            html_lines.append("</body>")
            html_lines.append("</html>")
            return "\n".join(html_lines)
        except Exception as e:
            raise AdapterError(f"Failed to adapt RenderedProposal to HTML: {e}") from e


class MarkdownAdapter(OutputAdapter):
    """Generates structured Markdown representation of the rendered proposal."""

    def adapt(self, proposal: RenderedProposal) -> str:
        lines = [
            f"# {proposal.title}",
            f"**Client:** {proposal.client_name}  ",
            f"**Design ID:** `{proposal.design_id}`  ",
            f"**Status:** {proposal.export_status} | **Pages:** {proposal.page_count}",
            "",
            "---",
            ""
        ]

        for page in proposal.pages:
            lines.append(f"## Page {page.page_number}: {page.page_title}")
            if page.page_subtitle:
                lines.append(f"*{page.page_subtitle}*")
            lines.append("")

            for comp in page.components:
                if comp.title:
                    lines.append(f"### {comp.title}")
                if comp.content:
                    lines.append(comp.content)
                    lines.append("")
                if comp.items:
                    for item in comp.items:
                        lines.append(f"- {item}")
                    lines.append("")
                if comp.table_data:
                    headers = comp.table_data.get("headers", [])
                    lines.append("| " + " | ".join(headers) + " |")
                    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                    for row in comp.table_data.get("rows", []):
                        lines.append("| " + " | ".join(str(c) for c in row) + " |")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class PdfOutputAdapter(OutputAdapter):
    """Compiles RenderedProposal into a styled binary vector PDF using ReportLab Platypus."""

    def __init__(self, pdf_service: Optional[Any] = None):
        from sympl_renderer.pdf_generator import PdfGenerationService
        self.pdf_service = pdf_service or PdfGenerationService()

    def adapt(self, proposal: RenderedProposal) -> bytes:
        try:
            return self.pdf_service.generate_pdf(proposal)
        except Exception as e:
            raise AdapterError(f"Failed to compile PDF from RenderedProposal: {e}") from e

    def write_to_file(self, proposal: RenderedProposal, file_path: Union[str, Path] = "proposal.pdf") -> Path:
        try:
            out_path = Path(file_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self.pdf_service.generate_pdf(proposal, output_path=out_path)
            return out_path
        except Exception as e:
            raise AdapterError(f"Failed to write PDF to file '{file_path}': {e}") from e


"""
Sympl Solutions Proposal RAG — Proposal Renderer Schemas

Data structures representing components, pages, export status, and the
fully assembled RenderedProposal document.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


class ComponentType:
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    BULLET_LIST = "bullet_list"
    TABLE = "table"
    CARD = "card"
    CALLOUT = "callout"
    DIVIDER = "divider"
    FOOTER = "footer"


class PageType:
    COVER = "cover"
    EXECUTIVE_SUMMARY = "executive_summary"
    SERVICES_OVERVIEW = "services_overview"
    SERVICE_DETAIL = "service_detail"
    TIMELINE = "timeline"
    WHY_US = "why_us"
    PRICING = "pricing"
    EXCLUSIONS = "exclusions"
    CLOSING = "closing"


class ExportStatus:
    DRAFT = "DRAFT"
    POPULATED = "POPULATED"
    EXPORTED = "EXPORTED"
    FAILED = "FAILED"


@dataclass
class RenderComponent:
    """Atomic presentation component within a proposal page."""
    component_id: str
    component_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    items: List[str] = field(default_factory=list)
    table_data: Optional[Dict[str, Any]] = None
    styling: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RenderPage:
    """A discrete presentation slide or page in the proposal document."""
    page_number: int
    page_type: str
    page_title: str
    page_subtitle: str = ""
    components: List[RenderComponent] = field(default_factory=list)
    overflow_detected: bool = False
    capacity_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["components"] = [c.to_dict() if hasattr(c, "to_dict") else c for c in self.components]
        return d


@dataclass
class RenderedProposal:
    """Fully compiled presentation proposal document."""
    design_id: str
    title: str
    client_name: str
    page_count: int
    pages: List[RenderPage] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    export_status: str = ExportStatus.DRAFT
    pdf_url: str = ""
    branding: Dict[str, Any] = field(default_factory=dict)
    render_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_id": self.design_id,
            "title": self.title,
            "client_name": self.client_name,
            "page_count": self.page_count,
            "pages": [p.to_dict() if hasattr(p, "to_dict") else p for p in self.pages],
            "sections": self.sections,
            "export_status": self.export_status,
            "pdf_url": self.pdf_url,
            "branding": self.branding,
            "render_metadata": self.render_metadata
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RenderedProposal":
        pages = []
        for p in data.get("pages", []):
            components = []
            for c in p.get("components", []):
                components.append(RenderComponent(
                    component_id=c.get("component_id", ""),
                    component_type=c.get("component_type", ""),
                    title=c.get("title"),
                    content=c.get("content"),
                    items=c.get("items", []),
                    table_data=c.get("table_data"),
                    styling=c.get("styling", {}),
                    metadata=c.get("metadata", {})
                ))
            pages.append(RenderPage(
                page_number=p.get("page_number", 1),
                page_type=p.get("page_type", ""),
                page_title=p.get("page_title", ""),
                page_subtitle=p.get("page_subtitle", ""),
                components=components,
                overflow_detected=p.get("overflow_detected", False),
                capacity_metrics=p.get("capacity_metrics", {}),
                metadata=p.get("metadata", {})
            ))

        return cls(
            design_id=data.get("design_id", ""),
            title=data.get("title", ""),
            client_name=data.get("client_name", ""),
            page_count=data.get("page_count", len(pages)),
            pages=pages,
            sections=data.get("sections", []),
            export_status=data.get("export_status", ExportStatus.DRAFT),
            pdf_url=data.get("pdf_url", ""),
            branding=data.get("branding", {}),
            render_metadata=data.get("render_metadata", {})
        )

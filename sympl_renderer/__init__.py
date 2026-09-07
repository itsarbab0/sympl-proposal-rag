"""
Sympl Solutions Proposal RAG — Proposal Renderer Package (Phase 5)

Presentation compilation layer that converts validated proposal_draft.json
into formatted Canva, PDF, and document representations.
"""

from sympl_renderer.schema import (
    RenderedProposal,
    RenderPage,
    RenderComponent,
    ComponentType,
    PageType,
    ExportStatus
)
from sympl_renderer.branding import (
    SymplBranding,
    DEFAULT_BRANDING,
    ColorPalette,
    Typography
)
from sympl_renderer.exceptions import (
    RendererError,
    InvalidDraftError,
    ContentIntegrityError,
    PricingIntegrityError,
    ReferenceIntegrityError,
    LayoutOverflowError,
    CanvaAPIError,
    AdapterError
)
from sympl_renderer.canva_client import (
    CanvaClient,
    CanvaConnectClient,
    MockCanvaClient,
    get_canva_client
)
from sympl_renderer.template_mapper import TemplateMapper
from sympl_renderer.validator import (
    RenderValidator,
    validate_draft_input,
    ContentIntegrityValidator,
    PricingIntegrityValidator,
    ReferenceIntegrityValidator,
    LayoutOverflowValidator,
    RenderValidationResult
)
from sympl_renderer.output_adapter import (
    OutputAdapter,
    JsonOutputAdapter,
    CanvaPayloadAdapter,
    HtmlPdfAdapter,
    MarkdownAdapter
)
from sympl_renderer.renderer import ProposalRenderer

__all__ = [
    "ProposalRenderer",
    "RenderedProposal",
    "RenderPage",
    "RenderComponent",
    "ComponentType",
    "PageType",
    "ExportStatus",
    "SymplBranding",
    "DEFAULT_BRANDING",
    "ColorPalette",
    "Typography",
    "TemplateMapper",
    "CanvaClient",
    "CanvaConnectClient",
    "MockCanvaClient",
    "get_canva_client",
    "RenderValidator",
    "validate_draft_input",
    "ContentIntegrityValidator",
    "PricingIntegrityValidator",
    "ReferenceIntegrityValidator",
    "LayoutOverflowValidator",
    "RenderValidationResult",
    "OutputAdapter",
    "JsonOutputAdapter",
    "CanvaPayloadAdapter",
    "HtmlPdfAdapter",
    "MarkdownAdapter",
    "RendererError",
    "InvalidDraftError",
    "ContentIntegrityError",
    "PricingIntegrityError",
    "ReferenceIntegrityError",
    "LayoutOverflowError",
    "CanvaAPIError",
    "AdapterError"
]

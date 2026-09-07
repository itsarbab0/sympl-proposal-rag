"""
Sympl Solutions Proposal RAG — Proposal Renderer Exceptions

Custom domain exceptions for draft validation, content integrity, pricing safety,
reference block preservation, layout overflow, and Canva API interactions.
"""


class RendererError(Exception):
    """Base exception for all Proposal Renderer errors."""
    pass


class InvalidDraftError(RendererError):
    """Raised when proposal_draft.json is missing required fields or has invalid structure."""
    pass


class ContentIntegrityError(RendererError):
    """Raised when rendered text deviates from or modifies the approved proposal_draft.json content."""
    pass


class PricingIntegrityError(RendererError):
    """Raised when pricing fee items, amounts, frequencies, or placeholders are altered in rendering."""
    pass


class ReferenceIntegrityError(RendererError):
    """Raised when canonical reference blocks (Why Us, Backlog, Software, HR Boundary) are altered."""
    pass


class LayoutOverflowError(RendererError):
    """Raised when page content exceeds template component capacity or contains empty pages."""
    pass


class CanvaAPIError(RendererError):
    """Raised on Canva Connect API communication, authentication, or payload validation failures."""
    pass


class AdapterError(RendererError):
    """Raised when output adapter conversion or document export fails."""
    pass

"""
Sympl Solutions Proposal RAG — Proposal Writer Exceptions

Custom domain exceptions for safety firewall, scope compliance, pricing safety,
historical leakage, and style validation failures in the Proposal Writer layer.
"""


class WriterError(Exception):
    """Base exception for all Proposal Writer errors."""
    pass


class ScopeFirewallError(WriterError):
    """Raised when an uncurated plan contains requested_scope or unapproved_requested_scope."""
    pass


class ScopeViolationError(WriterError):
    """Raised when the writer introduces a service or task not in approved_scope."""
    pass


class MissingApprovedScopeItemError(WriterError):
    """Raised when an approved scope item is missing from the generated proposal."""
    pass


class HistoricalLeakageError(WriterError):
    """Raised when historical client names, dates, amounts, or employee counts are detected."""
    pass


class PricingSafetyError(WriterError):
    """Raised when unauthorized fees, invented amounts, or unapproved pricing categories appear."""
    pass


class StyleViolationError(WriterError):
    """Raised when forbidden buzzwords, marketing hype, or severe style rules are violated."""
    pass


class ReferenceBlockTamperingError(WriterError):
    """Raised when canonical reference blocks (Why Us, Backlog, Software exclusions, HR boundary) are altered."""
    pass


class RegenerationExhaustedError(WriterError):
    """Raised when validation failures persist after the maximum regeneration retry attempts (2 retries)."""
    pass

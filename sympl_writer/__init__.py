"""
Sympl Solutions Proposal RAG — Proposal Writer Package (Phase 4)

Provides the controlled narrative generation layer that receives proposal_plan.json
and generates validated proposal_draft.json.
"""

from sympl_writer.schema import (
    ProposalDraft,
    DraftSection,
    DraftSubsection,
    ValidationMetadata
)
from sympl_writer.exceptions import (
    WriterError,
    ScopeFirewallError,
    ScopeViolationError,
    MissingApprovedScopeItemError,
    HistoricalLeakageError,
    PricingSafetyError,
    StyleViolationError,
    ReferenceBlockTamperingError,
    RegenerationExhaustedError
)
from sympl_writer.llm_client import (
    LLMClient,
    OpenRouterClient,
    OllamaClient,
    MockLLMClient,
    get_llm_client
)
from sympl_writer.prompt_builder import PromptBuilder
from sympl_writer.validator import ProposalValidator, ValidationResult
from sympl_writer.writer import ProposalWriter

__all__ = [
    "ProposalWriter",
    "ProposalDraft",
    "DraftSection",
    "DraftSubsection",
    "ValidationMetadata",
    "ProposalValidator",
    "ValidationResult",
    "PromptBuilder",
    "LLMClient",
    "OpenRouterClient",
    "OllamaClient",
    "MockLLMClient",
    "get_llm_client",
    "WriterError",
    "ScopeFirewallError",
    "ScopeViolationError",
    "MissingApprovedScopeItemError",
    "HistoricalLeakageError",
    "PricingSafetyError",
    "StyleViolationError",
    "ReferenceBlockTamperingError",
    "RegenerationExhaustedError"
]

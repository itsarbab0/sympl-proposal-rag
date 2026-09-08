"""
Sympl Solutions Proposal RAG — Proposal Writer Schemas

Defines the output schema (proposal_draft.json) for the Proposal Writer Layer:
  - Title & Executive Summary
  - Sections with opening narrative and bulleted subsections
  - Canonical Why Us statements
  - Pricing schedule / placeholders
  - Exclusions & boundary statements
  - Comprehensive Validation Metadata
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class DraftSubsection:
    heading: str
    bullets: List[str] = field(default_factory=list)
    narrative: Optional[str] = None


@dataclass
class DraftSection:
    section_title: str
    opening_text: str
    subsections: List[DraftSubsection] = field(default_factory=list)


@dataclass
class ValidationMetadata:
    passed: bool
    scope_verification: Dict[str, Any] = field(default_factory=dict)
    pricing_safety: Dict[str, Any] = field(default_factory=dict)
    historical_firewall: Dict[str, Any] = field(default_factory=dict)
    style_compliance: Dict[str, Any] = field(default_factory=dict)
    reference_block_integrity: Dict[str, Any] = field(default_factory=dict)
    retries_count: int = 0
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""


@dataclass
class ProposalDraft:
    title: str
    executive_summary: str
    sections: List[DraftSection] = field(default_factory=list)
    why_us: List[str] = field(default_factory=list)
    pricing: Dict[str, Any] = field(default_factory=dict)
    exclusions: List[str] = field(default_factory=list)
    validation_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def proposal_title(self) -> str:
        """Alias for title for backwards/renderer compatibility."""
        return self.title

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["proposal_title"] = self.title
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProposalDraft":
        title = data.get("title") or data.get("proposal_title") or "Accounting & Bookkeeping Services Proposal"
        exec_summary = data.get("executive_summary") or ""

        sections = []
        for s in data.get("sections", []):
            subsections = []
            for sub in s.get("subsections", []):
                subsections.append(DraftSubsection(
                    heading=sub.get("heading", ""),
                    bullets=sub.get("bullets", []),
                    narrative=sub.get("narrative")
                ))
            sections.append(DraftSection(
                section_title=s.get("section_title", ""),
                opening_text=s.get("opening_text", ""),
                subsections=subsections
            ))

        return cls(
            title=title,
            executive_summary=exec_summary,
            sections=sections,
            why_us=data.get("why_us", []),
            pricing=data.get("pricing", {}),
            exclusions=data.get("exclusions", []),
            validation_metadata=data.get("validation_metadata", {})
        )

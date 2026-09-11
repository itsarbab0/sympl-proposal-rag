"""
Sympl Solutions — Canva Integration Models
Defines data structures for Canva template mapping, editing operations, and export results.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional


class CanvaOperationType(str, Enum):
    REPLACE_TEXT = "replace_text"
    FIND_AND_REPLACE_TEXT = "find_and_replace_text"
    UPDATE_FILL = "update_fill"
    UPDATE_TITLE = "update_title"
    INSERT_FILL = "insert_fill"
    DELETE_ELEMENT = "delete_element"
    FORMAT_TEXT = "format_text"


@dataclass
class CanvaEditingOperation:
    """Represents a single editing operation in a Canva editing transaction."""
    type: CanvaOperationType
    element_id: Optional[str] = None
    text: Optional[str] = None
    find_text: Optional[str] = None
    replace_text: Optional[str] = None
    title: Optional[str] = None
    asset_id: Optional[str] = None
    asset_type: Optional[str] = None
    alt_text: Optional[str] = None
    page_id: Optional[str] = None
    formatting: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": self.type.value if isinstance(self.type, CanvaOperationType) else self.type}
        if self.element_id is not None:
            d["element_id"] = self.element_id
        if self.text is not None:
            d["text"] = self.text
        if self.find_text is not None:
            d["find_text"] = self.find_text
        if self.replace_text is not None:
            d["replace_text"] = self.replace_text
        if self.title is not None:
            d["title"] = self.title
        if self.asset_id is not None:
            d["asset_id"] = self.asset_id
        if self.asset_type is not None:
            d["asset_type"] = self.asset_type
        if self.alt_text is not None:
            d["alt_text"] = self.alt_text
        if self.page_id is not None:
            d["page_id"] = self.page_id
        if self.formatting is not None:
            d["formatting"] = self.formatting
        return d


@dataclass
class CanvaDesignMetadata:
    """Metadata representing a Canva design."""
    design_id: str
    title: str
    page_count: int = 11
    edit_url: str = ""
    view_url: str = ""
    created_at: int = 0
    updated_at: int = 0
    is_template_duplicated: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanvaDesignMetadata":
        design = data.get("design", data)
        urls = design.get("urls", {})
        return cls(
            design_id=design.get("id", ""),
            title=design.get("title", ""),
            page_count=design.get("page_count", 11),
            edit_url=urls.get("edit_url", ""),
            view_url=urls.get("view_url", ""),
            created_at=design.get("created_at", 0),
            updated_at=design.get("updated_at", 0),
        )


@dataclass
class CanvaExportResult:
    """Status and URLs resulting from a Canva export job."""
    export_id: str
    status: str
    download_urls: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class ElementCapacity:
    """Text capacity bounds for a template element."""
    current_word_count: int
    max_recommended_words: int
    current_char_count: int
    max_recommended_chars: int


@dataclass
class TemplateElementMapping:
    """Configuration mapping for a specific element in the Canva master template."""
    element_id: str
    element_type: str
    current_text: str
    replacement_field: str
    editable: bool = True
    dynamic_replacement_feasible: bool = True
    capacity: Optional[ElementCapacity] = None
    notes: str = ""

"""Structured document outline types — hierarchical TOC structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OutlineEntry:
    """Hierarchical TOC entry."""

    title: str
    level: int
    page: Optional[str] = None
    entry_type: Optional[str] = None
    children: List["OutlineEntry"] = field(default_factory=list)

    def with_type(self, entry_type: str) -> "OutlineEntry":
        from dataclasses import replace
        return replace(self, entry_type=entry_type)

    def with_children(self, children: List["OutlineEntry"]) -> "OutlineEntry":
        from dataclasses import replace
        return replace(self, children=list(children))

    def add_child(self, child: "OutlineEntry") -> None:
        self.children.append(child)

    def flatten(self) -> List["FlatOutlineEntry"]:
        results: List[FlatOutlineEntry] = []
        self._flatten_recursive([], results)
        return results

    def _flatten_recursive(
        self, path: List[str], results: List["FlatOutlineEntry"]
    ) -> None:
        current_path = path + [self.title]
        results.append(
            FlatOutlineEntry(
                title=self.title,
                level=self.level,
                page=self.page,
                entry_type=self.entry_type,
                path=list(current_path),
            )
        )
        for child in self.children:
            child._flatten_recursive(current_path, results)


@dataclass
class FlatOutlineEntry:
    """Flattened outline entry with full hierarchical path."""

    title: str
    level: int
    path: List[str] = field(default_factory=list)
    page: Optional[str] = None
    entry_type: Optional[str] = None


@dataclass
class OutlineMetadata:
    """Statistics about a document outline."""

    total_entries: int = 0
    levels: int = 0
    has_leaders: bool = False
    numbering_style: Optional[str] = None
    page_style: Optional[str] = None
    structure_type: Optional[str] = None


class ListingOutline:
    """Complete TOC / listing outline for a document."""

    def __init__(self) -> None:
        self.document_title: Optional[str] = None
        self.entries: List[OutlineEntry] = []
        self.confidence: float = 1.0
        self.metadata: OutlineMetadata = OutlineMetadata()

    def flatten(self) -> List[FlatOutlineEntry]:
        results: List[FlatOutlineEntry] = []
        for entry in self.entries:
            results.extend(entry.flatten())
        return results

    def entries_at_level(self, level: int) -> List[OutlineEntry]:
        def collect(entries: List[OutlineEntry]) -> List[OutlineEntry]:
            found = []
            for e in entries:
                if e.level == level:
                    found.append(e)
                found.extend(collect(e.children))
            return found
        return collect(self.entries)

    def max_depth(self) -> int:
        def depth(entry: OutlineEntry) -> int:
            if not entry.children:
                return entry.level
            return max(depth(c) for c in entry.children)
        if not self.entries:
            return 0
        return max(depth(e) for e in self.entries)


def generate_outline_schema() -> Dict[str, Any]:
    """Return JSON Schema for ListingOutline."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Table of Contents",
        "type": "object",
        "properties": {
            "document_title": {"type": ["string", "null"]},
            "entries": {
                "type": "array",
                "items": {"$ref": "#/definitions/OutlineEntry"},
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "metadata": {"$ref": "#/definitions/OutlineMetadata"},
        },
        "required": ["entries", "confidence"],
        "definitions": {
            "OutlineEntry": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "page": {"type": ["string", "null"]},
                    "level": {"type": "integer", "minimum": 0, "maximum": 10},
                    "entry_type": {"type": ["string", "null"]},
                    "children": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/OutlineEntry"},
                    },
                },
                "required": ["title", "level"],
            },
            "OutlineMetadata": {
                "type": "object",
                "properties": {
                    "numbering_style": {"type": ["string", "null"]},
                    "has_leaders": {"type": "boolean"},
                    "page_style": {"type": ["string", "null"]},
                    "total_entries": {"type": "integer", "minimum": 0},
                    "levels": {"type": "integer", "minimum": 1, "maximum": 10},
                    "structure_type": {"type": ["string", "null"]},
                },
                "required": ["has_leaders", "total_entries", "levels"],
            },
        },
    }

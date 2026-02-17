"""Source location and node provenance mapping utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceSpan:
    """Represents a source range in 1-based coordinates."""

    file: str
    line: int
    column: int
    end_line: int
    end_column: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the span to a JSON-compatible mapping."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass
class SourceMapEntry:
    """Maps a graph node to source code provenance metadata."""

    node_id: str
    span: SourceSpan
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the source map entry."""
        return {
            "node_id": self.node_id,
            "span": self.span.to_dict(),
            "note": self.note,
        }


@dataclass
class SourceMap:
    """Tracks source provenance for graph nodes."""

    entries: list[SourceMapEntry] = field(default_factory=list)

    def add(self, node_id: str, span: SourceSpan, note: str = "") -> None:
        """Append an entry mapping node_id to source span."""
        self.entries.append(SourceMapEntry(node_id=node_id, span=span, note=note))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full source map."""
        return {
            "schema_version": "1.0",
            "entries": [entry.to_dict() for entry in self.entries],
        }

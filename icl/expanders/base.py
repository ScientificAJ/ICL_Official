"""Base abstractions for target language expanders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from icl.graph import IntentGraph


@dataclass
class ExpansionContext:
    """Compilation context passed into backend emitters."""

    target: str
    debug: bool = False
    metadata: dict[str, Any] | None = None


class BackendEmitter(ABC):
    """Abstract target language backend contract."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend target name."""

    @abstractmethod
    def emit_module(self, graph: IntentGraph, context: ExpansionContext) -> str:
        """Emit full source text for a module graph."""

    @staticmethod
    def indent(text: str, level: int, unit: str = "    ") -> str:
        """Indent all non-empty lines by level."""
        prefix = unit * level
        lines = text.splitlines()
        return "\n".join((prefix + line) if line.strip() else line for line in lines)

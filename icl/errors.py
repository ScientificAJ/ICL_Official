"""Structured compiler diagnostics and exception hierarchy for ICL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from icl.source_map import SourceSpan


@dataclass(frozen=True)
class Diagnostic:
    """Machine-readable diagnostic emitted by compiler phases."""

    code: str
    message: str
    span: SourceSpan | None = None
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the diagnostic for JSON output."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
        }
        if self.span is not None:
            payload["span"] = self.span.to_dict()
        return payload


class CompilerError(Exception):
    """Base compiler error carrying a code and optional source span."""

    def __init__(self, code: str, message: str, span: SourceSpan | None = None, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.span = span
        self.hint = hint

    def to_diagnostic(self) -> Diagnostic:
        """Convert exception into serializable diagnostic."""
        return Diagnostic(code=self.code, message=self.message, span=self.span, hint=self.hint)

    def __str__(self) -> str:
        if self.span is None:
            return f"[{self.code}] {self.message}"
        return (
            f"[{self.code}] {self.message} "
            f"({self.span.file}:{self.span.line}:{self.span.column})"
        )


class LexError(CompilerError):
    """Raised by lexical analysis failures."""


class ParseError(CompilerError):
    """Raised by parser failures."""


class SemanticError(CompilerError):
    """Raised by semantic analysis failures."""


class ExpansionError(CompilerError):
    """Raised by backend expansion failures."""


class CLIError(CompilerError):
    """Raised by CLI usage or orchestration failures."""


def format_diagnostic(diag: Diagnostic) -> str:
    """Format diagnostic into a stable human-readable line."""
    if diag.span is None:
        suffix = ""
    else:
        suffix = f" {diag.span.file}:{diag.span.line}:{diag.span.column}"
    hint = f" Hint: {diag.hint}" if diag.hint else ""
    return f"{diag.code}{suffix}: {diag.message}{hint}"

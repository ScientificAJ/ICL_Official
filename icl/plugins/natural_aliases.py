"""Natural-language alias syntax plugin for ICL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from icl.alias_map import alias_lookup, validate_alias_mode
from icl.plugin import PluginManager, SyntaxPlugin


@dataclass(frozen=True)
class AliasReplacement:
    """One alias replacement event with source location."""

    alias: str
    canonical: str
    line: int
    column: int


class NaturalAliasPlugin(SyntaxPlugin):
    """Pre-lexer source normalizer for natural alias forms."""

    def __init__(self, mode: str = "core") -> None:
        self._mode = validate_alias_mode(mode)
        self._lookup = alias_lookup(self._mode)
        self._replacements: list[AliasReplacement] = []
        self._changed = False

    @property
    def name(self) -> str:
        return "natural_aliases"

    def preprocess_source(self, source: str) -> str:
        normalized, replacements = normalize_aliases(source, self._lookup)
        self._replacements = replacements
        self._changed = normalized != source
        return normalized

    def metadata(self) -> dict[str, Any]:
        """Return metadata for latest preprocess pass."""
        return {
            "mode": self._mode,
            "changed": self._changed,
            "count": len(self._replacements),
            "replacements": [asdict(item) for item in self._replacements],
        }


_IDENTIFIER_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_IDENTIFIER_CONT = _IDENTIFIER_START | set("0123456789")


def normalize_aliases(source: str, lookup: dict[str, str]) -> tuple[str, list[AliasReplacement]]:
    """Normalize alias identifiers while preserving strings/comments."""
    out: list[str] = []
    replacements: list[AliasReplacement] = []

    idx = 0
    line = 1
    col = 1

    def bump(ch: str) -> tuple[int, int]:
        if ch == "\n":
            return line + 1, 1
        return line, col + 1

    while idx < len(source):
        ch = source[idx]

        if ch == '"':
            start = idx
            idx += 1
            line, col = bump(ch)
            while idx < len(source):
                cur = source[idx]
                idx += 1
                line, col = bump(cur)
                if cur == "\\":
                    if idx < len(source):
                        escaped = source[idx]
                        idx += 1
                        line, col = bump(escaped)
                    continue
                if cur == '"':
                    break
            out.append(source[start:idx])
            continue

        if ch == "/" and idx + 1 < len(source) and source[idx + 1] == "/":
            start = idx
            idx += 2
            line, col = bump("/")
            line, col = bump("/")
            while idx < len(source) and source[idx] != "\n":
                idx += 1
                line, col = bump("x")
            out.append(source[start:idx])
            continue

        if ch in _IDENTIFIER_START:
            start_idx = idx
            start_line = line
            start_col = col

            idx += 1
            line, col = bump(ch)
            while idx < len(source) and source[idx] in _IDENTIFIER_CONT:
                idx += 1
                line, col = bump("x")

            word = source[start_idx:idx]
            canonical = lookup.get(word)
            if canonical is None:
                out.append(word)
            else:
                out.append(canonical)
                replacements.append(
                    AliasReplacement(
                        alias=word,
                        canonical=canonical,
                        line=start_line,
                        column=start_col,
                    )
                )
            continue

        out.append(ch)
        idx += 1
        line, col = bump(ch)

    return "".join(out), replacements


def register(manager: PluginManager, mode: str = "core") -> None:
    """Register natural alias plugin into a plugin manager."""
    manager.register_syntax(NaturalAliasPlugin(mode=mode))

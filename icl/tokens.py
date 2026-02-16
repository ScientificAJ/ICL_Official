"""Token definitions for ICL lexical analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from icl.source_map import SourceSpan


class TokenType(Enum):
    """Finite token categories used by lexer and parser."""

    IDENT = auto()
    NUMBER = auto()
    STRING = auto()

    FN = auto()
    IF = auto()
    LOOP = auto()
    IN = auto()
    RET = auto()
    TRUE = auto()
    FALSE = auto()

    ASSIGN = auto()  # :=
    COLON = auto()  # :
    ARROW = auto()  # =>
    QUESTION = auto()  # ?
    RANGE = auto()  # ..

    COMMA = auto()
    SEMICOLON = auto()
    LPAR = auto()
    RPAR = auto()
    LBRACE = auto()
    RBRACE = auto()

    AT = auto()  # @
    HASH = auto()  # #

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

    EQ = auto()  # ==
    NE = auto()  # !=
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    AND = auto()  # &&
    OR = auto()  # ||
    NOT = auto()  # !

    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "fn": TokenType.FN,
    "if": TokenType.IF,
    "loop": TokenType.LOOP,
    "in": TokenType.IN,
    "ret": TokenType.RET,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
}


@dataclass(frozen=True)
class Token:
    """A single lexical token with original source span."""

    token_type: TokenType
    value: str
    span: SourceSpan

    def __str__(self) -> str:
        return f"{self.token_type.name}({self.value!r})@{self.span.line}:{self.span.column}"

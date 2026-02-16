"""AST model for ICL source programs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from icl.source_map import SourceSpan


@dataclass
class AstNode:
    """Base class for AST nodes with provenance span."""

    span: SourceSpan


@dataclass
class Expr(AstNode):
    """Base class for expression nodes."""


@dataclass
class Stmt(AstNode):
    """Base class for statement nodes."""


@dataclass
class Param:
    """Function parameter definition."""

    name: str
    type_hint: str | None = None


@dataclass
class Program(AstNode):
    """Root AST node representing a full ICL module."""

    statements: list[Stmt] = field(default_factory=list)


@dataclass
class AssignmentStmt(Stmt):
    """Variable assignment with optional type annotation."""

    name: str
    value: Expr
    type_hint: str | None = None


@dataclass
class ExpressionStmt(Stmt):
    """Expression used as a statement."""

    expr: Expr


@dataclass
class IfStmt(Stmt):
    """Conditional statement with required then and optional else blocks."""

    condition: Expr
    then_block: list[Stmt]
    else_block: list[Stmt]


@dataclass
class LoopStmt(Stmt):
    """Range loop statement: loop <iter> in <start>..<end> { ... }"""

    iterator: str
    start: Expr
    end: Expr
    body: list[Stmt]


@dataclass
class FunctionDefStmt(Stmt):
    """Function definition with either block body or expression body."""

    name: str
    params: list[Param]
    body: list[Stmt]
    expr_body: Expr | None = None
    return_type: str | None = None


@dataclass
class ReturnStmt(Stmt):
    """Return statement, optionally returning a value."""

    value: Expr | None = None


@dataclass
class MacroStmt(Stmt):
    """Macro invocation statement to be expanded by macro plugins."""

    name: str
    args: list[Expr]


@dataclass
class IdentifierExpr(Expr):
    """Identifier reference expression."""

    name: str


@dataclass
class LiteralExpr(Expr):
    """Literal value expression (number/string/bool)."""

    value: Any


@dataclass
class UnaryExpr(Expr):
    """Unary operator expression."""

    operator: str
    operand: Expr


@dataclass
class BinaryExpr(Expr):
    """Binary operator expression."""

    left: Expr
    operator: str
    right: Expr


@dataclass
class CallExpr(Expr):
    """Function call expression."""

    callee: Expr
    args: list[Expr]
    at_prefixed: bool = False

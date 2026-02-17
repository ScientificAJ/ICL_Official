"""Standard macro plugins for ICL."""

from __future__ import annotations

from icl.ast import CallExpr, ExpressionStmt, IdentifierExpr, LiteralExpr, MacroStmt
from icl.errors import SemanticError
from icl.plugin import MacroPlugin, PluginManager


class EchoMacro(MacroPlugin):
    """`#echo(expr)` -> `@print(expr)`"""

    @property
    def name(self) -> str:
        return "echo"

    def expand(self, stmt: MacroStmt) -> list[ExpressionStmt]:
        if len(stmt.args) != 1:
            raise SemanticError(
                code="PLG101",
                message="#echo expects exactly one argument.",
                span=stmt.span,
                hint="Use #echo(value).",
            )
        call = CallExpr(
            span=stmt.span,
            callee=IdentifierExpr(span=stmt.span, name="print"),
            args=[stmt.args[0]],
            at_prefixed=True,
        )
        return [ExpressionStmt(span=stmt.span, expr=call)]


class DbgMacro(MacroPlugin):
    """`#dbg(expr)` -> `@print("dbg:"); @print(expr)`"""

    @property
    def name(self) -> str:
        return "dbg"

    def expand(self, stmt: MacroStmt) -> list[ExpressionStmt]:
        if len(stmt.args) != 1:
            raise SemanticError(
                code="PLG102",
                message="#dbg expects exactly one argument.",
                span=stmt.span,
                hint="Use #dbg(value).",
            )
        label = ExpressionStmt(
            span=stmt.span,
            expr=CallExpr(
                span=stmt.span,
                callee=IdentifierExpr(span=stmt.span, name="print"),
                args=[LiteralExpr(span=stmt.span, value="dbg:")],
                at_prefixed=True,
            ),
        )
        value = ExpressionStmt(
            span=stmt.span,
            expr=CallExpr(
                span=stmt.span,
                callee=IdentifierExpr(span=stmt.span, name="print"),
                args=[stmt.args[0]],
                at_prefixed=True,
            ),
        )
        return [label, value]


def register(manager: PluginManager) -> None:
    """Register standard macro plugins into a plugin manager."""
    manager.register_macro(EchoMacro())
    manager.register_macro(DbgMacro())

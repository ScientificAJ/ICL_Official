"""Target-agnostic Intermediate Representation (IR) for ICL v2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from icl.ast import (
    AssignmentStmt,
    BinaryExpr,
    CallExpr,
    Expr,
    ExpressionStmt,
    FunctionDefStmt,
    IdentifierExpr,
    IfStmt,
    LambdaExpr,
    LiteralExpr,
    LoopStmt,
    MacroStmt,
    Param,
    Program,
    ReturnStmt,
    Stmt,
    UnaryExpr,
)
from icl.semantic import SemanticResult
from icl.source_map import SourceSpan


IR_SCHEMA_VERSION = "2.0"


@dataclass
class IRNode:
    """Base IR node with optional source span provenance."""

    ir_id: str
    span: SourceSpan | None


@dataclass
class IRExpr(IRNode):
    """Base expression node for IR."""

    expr_type: str | None = None


@dataclass
class IRStmt(IRNode):
    """Base statement node for IR."""


@dataclass
class IRParam:
    """Normalized function parameter."""

    name: str
    type_hint: str | None = None


@dataclass
class IRModule(IRNode):
    """Top-level module IR container."""

    schema_version: str
    statements: list[IRStmt]
    inferred_types: dict[str, str]


@dataclass
class IRAssignment(IRStmt):
    name: str
    type_hint: str | None
    value: IRExpr


@dataclass
class IRExpressionStmt(IRStmt):
    expr: IRExpr


@dataclass
class IRIf(IRStmt):
    condition: IRExpr
    then_block: list[IRStmt]
    else_block: list[IRStmt]


@dataclass
class IRLoop(IRStmt):
    iterator: str
    start: IRExpr
    end: IRExpr
    body: list[IRStmt]


@dataclass
class IRFunction(IRStmt):
    name: str
    params: list[IRParam]
    body: list[IRStmt]
    expr_body: IRExpr | None
    return_type: str | None


@dataclass
class IRReturn(IRStmt):
    value: IRExpr | None


@dataclass
class IRLiteral(IRExpr):
    value: Any = None


@dataclass
class IRRef(IRExpr):
    name: str = ""


@dataclass
class IRUnary(IRExpr):
    operator: str = ""
    operand: IRExpr | None = None


@dataclass
class IRBinary(IRExpr):
    left: IRExpr | None = None
    operator: str = ""
    right: IRExpr | None = None


@dataclass
class IRCall(IRExpr):
    callee: IRExpr | None = None
    args: list[IRExpr] | None = None
    at_prefixed: bool = False


@dataclass
class IRLambda(IRExpr):
    params: list[IRParam] | None = None
    body: IRExpr | None = None
    return_type: str | None = None


class IRBuilder:
    """Lowers AST into target-agnostic IR."""

    def __init__(self, semantic: SemanticResult | None = None) -> None:
        self._semantic = semantic
        self._counter = 0

    def build(self, program: Program) -> IRModule:
        """Create an IR module from parsed AST."""
        statements = [self._build_stmt(stmt) for stmt in program.statements]

        inferred: dict[str, str] = {}
        if self._semantic is not None:
            for expr_id, type_name in self._semantic.inferred_expr_types.items():
                inferred[str(expr_id)] = type_name

        return IRModule(
            ir_id=self._new_id("mod"),
            span=program.span,
            schema_version=IR_SCHEMA_VERSION,
            statements=statements,
            inferred_types=inferred,
        )

    def _build_stmt(self, stmt: Stmt) -> IRStmt:
        if isinstance(stmt, AssignmentStmt):
            return IRAssignment(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                name=stmt.name,
                type_hint=stmt.type_hint,
                value=self._build_expr(stmt.value),
            )

        if isinstance(stmt, ExpressionStmt):
            return IRExpressionStmt(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                expr=self._build_expr(stmt.expr),
            )

        if isinstance(stmt, IfStmt):
            return IRIf(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                condition=self._build_expr(stmt.condition),
                then_block=[self._build_stmt(item) for item in stmt.then_block],
                else_block=[self._build_stmt(item) for item in stmt.else_block],
            )

        if isinstance(stmt, LoopStmt):
            return IRLoop(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                iterator=stmt.iterator,
                start=self._build_expr(stmt.start),
                end=self._build_expr(stmt.end),
                body=[self._build_stmt(item) for item in stmt.body],
            )

        if isinstance(stmt, FunctionDefStmt):
            params = [IRParam(name=param.name, type_hint=param.type_hint) for param in stmt.params]
            return IRFunction(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                name=stmt.name,
                params=params,
                body=[self._build_stmt(item) for item in stmt.body],
                expr_body=self._build_expr(stmt.expr_body) if stmt.expr_body is not None else None,
                return_type=stmt.return_type,
            )

        if isinstance(stmt, ReturnStmt):
            return IRReturn(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                value=self._build_expr(stmt.value) if stmt.value is not None else None,
            )

        if isinstance(stmt, MacroStmt):
            # Macros should be fully expanded before IR build.
            return IRExpressionStmt(
                ir_id=self._new_id("stmt"),
                span=stmt.span,
                expr=IRCall(
                    ir_id=self._new_id("expr"),
                    span=stmt.span,
                    expr_type="Any",
                    callee=IRRef(
                        ir_id=self._new_id("expr"),
                        span=stmt.span,
                        expr_type="Fn",
                        name=f"__macro_{stmt.name}",
                    ),
                    args=[self._build_expr(arg) for arg in stmt.args],
                    at_prefixed=True,
                ),
            )

        raise TypeError(f"Unsupported AST statement in IRBuilder: {type(stmt).__name__}")

    def _build_expr(self, expr: Expr | None) -> IRExpr:
        if expr is None:
            return IRLiteral(ir_id=self._new_id("expr"), span=None, expr_type="Void", value=None)

        inferred_type = None
        if self._semantic is not None:
            inferred_type = self._semantic.inferred_expr_types.get(id(expr))

        if isinstance(expr, LiteralExpr):
            return IRLiteral(
                ir_id=self._new_id("expr"),
                span=expr.span,
                expr_type=inferred_type,
                value=expr.value,
            )

        if isinstance(expr, IdentifierExpr):
            return IRRef(
                ir_id=self._new_id("expr"),
                span=expr.span,
                expr_type=inferred_type,
                name=expr.name,
            )

        if isinstance(expr, UnaryExpr):
            return IRUnary(
                ir_id=self._new_id("expr"),
                span=expr.span,
                expr_type=inferred_type,
                operator=expr.operator,
                operand=self._build_expr(expr.operand),
            )

        if isinstance(expr, BinaryExpr):
            return IRBinary(
                ir_id=self._new_id("expr"),
                span=expr.span,
                expr_type=inferred_type,
                left=self._build_expr(expr.left),
                operator=expr.operator,
                right=self._build_expr(expr.right),
            )

        if isinstance(expr, CallExpr):
            return IRCall(
                ir_id=self._new_id("expr"),
                span=expr.span,
                expr_type=inferred_type,
                callee=self._build_expr(expr.callee),
                args=[self._build_expr(arg) for arg in expr.args],
                at_prefixed=expr.at_prefixed,
            )

        if isinstance(expr, LambdaExpr):
            return IRLambda(
                ir_id=self._new_id("expr"),
                span=expr.span,
                expr_type=inferred_type,
                params=[IRParam(name=param.name, type_hint=param.type_hint) for param in expr.params],
                body=self._build_expr(expr.body),
                return_type=expr.return_type,
            )

        raise TypeError(f"Unsupported AST expression in IRBuilder: {type(expr).__name__}")

    def _new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"


def ir_to_dict(node: Any) -> Any:
    """Serialize IR dataclasses recursively into JSON-compatible mappings."""
    if isinstance(node, list):
        return [ir_to_dict(item) for item in node]
    if isinstance(node, dict):
        return {str(key): ir_to_dict(value) for key, value in node.items()}
    if isinstance(node, SourceSpan):
        return node.to_dict()
    if is_dataclass(node):
        payload = asdict(node)
        payload["node_type"] = type(node).__name__
        return ir_to_dict(payload)
    return node


def param_from_ast(param: Param) -> IRParam:
    """Legacy helper for single-parameter conversions."""
    return IRParam(name=param.name, type_hint=param.type_hint)

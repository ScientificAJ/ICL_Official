"""IR lowering and lowered-form utilities for target emission."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from icl.errors import ExpansionError
from icl.graph import IntentGraph
from icl.ir import (
    IRAssignment,
    IRBinary,
    IRCall,
    IRExpr,
    IRExpressionStmt,
    IRFunction,
    IRIf,
    IRLambda,
    IRLiteral,
    IRLoop,
    IRModule,
    IRRef,
    IRReturn,
    IRStmt,
    IRUnary,
)
from icl.source_map import SourceSpan


@dataclass
class LoweredNode:
    """Base lowered node with deterministic id."""

    lowered_id: str
    span: SourceSpan | None


@dataclass
class LoweredExpr(LoweredNode):
    """Base lowered expression."""

    expr_type: str | None = None


@dataclass
class LoweredStmt(LoweredNode):
    """Base lowered statement."""


@dataclass
class LoweredModule(LoweredNode):
    """Target-shaped lowered module ready for emission."""

    ir_schema_version: str
    target: str
    statements: list[LoweredStmt]
    required_helpers: list[str]
    diagnostics: list[str]


@dataclass
class LoweredAssignment(LoweredStmt):
    name: str
    type_hint: str | None
    value: LoweredExpr


@dataclass
class LoweredExpressionStmt(LoweredStmt):
    expr: LoweredExpr


@dataclass
class LoweredIf(LoweredStmt):
    condition: LoweredExpr
    then_block: list[LoweredStmt]
    else_block: list[LoweredStmt]


@dataclass
class LoweredLoop(LoweredStmt):
    iterator: str
    start: LoweredExpr
    end: LoweredExpr
    body: list[LoweredStmt]


@dataclass
class LoweredFunction(LoweredStmt):
    name: str
    params: list[dict[str, str | None]]
    return_type: str | None
    body: list[LoweredStmt]


@dataclass
class LoweredReturn(LoweredStmt):
    value: LoweredExpr | None


@dataclass
class LoweredLiteral(LoweredExpr):
    value: Any = None


@dataclass
class LoweredRef(LoweredExpr):
    name: str = ""


@dataclass
class LoweredUnary(LoweredExpr):
    operator: str = ""
    operand: LoweredExpr | None = None


@dataclass
class LoweredBinary(LoweredExpr):
    left: LoweredExpr | None = None
    operator: str = ""
    right: LoweredExpr | None = None


@dataclass
class LoweredCall(LoweredExpr):
    callee: LoweredExpr | None = None
    args: list[LoweredExpr] | None = None


@dataclass
class LoweredLambda(LoweredExpr):
    params: list[dict[str, str | None]] | None = None
    body: LoweredExpr | None = None
    return_type: str | None = None


class Lowerer:
    """Lowers canonical IR into target-shaped lowered nodes."""

    def __init__(self) -> None:
        self._counter = 0

    def lower(self, module: IRModule, *, target: str, feature_coverage: dict[str, bool] | None = None) -> LoweredModule:
        """Lower IR module for a specific target."""
        feature_coverage = feature_coverage or {}
        diagnostics: list[str] = []

        features = collect_ir_features(module)
        missing = sorted(feature for feature in features if not feature_coverage.get(feature, True))
        if missing:
            raise ExpansionError(
                code="LOW001",
                message=f"Target '{target}' does not support required features: {', '.join(missing)}.",
                span=module.span,
                hint="Choose a compatible target or reduce source feature usage.",
            )

        statements = [self._lower_stmt(stmt, target=target, diagnostics=diagnostics) for stmt in module.statements]
        helpers = self._required_helpers(statements, target=target)

        return LoweredModule(
            lowered_id=self._new_id("lmod"),
            span=module.span,
            ir_schema_version=module.schema_version,
            target=target,
            statements=statements,
            required_helpers=helpers,
            diagnostics=diagnostics,
        )

    def _lower_stmt(self, stmt: IRStmt, *, target: str, diagnostics: list[str]) -> LoweredStmt:
        if isinstance(stmt, IRAssignment):
            return LoweredAssignment(
                lowered_id=self._new_id("lstmt"),
                span=stmt.span,
                name=stmt.name,
                type_hint=stmt.type_hint,
                value=self._lower_expr(stmt.value, target=target, diagnostics=diagnostics),
            )

        if isinstance(stmt, IRExpressionStmt):
            return LoweredExpressionStmt(
                lowered_id=self._new_id("lstmt"),
                span=stmt.span,
                expr=self._lower_expr(stmt.expr, target=target, diagnostics=diagnostics),
            )

        if isinstance(stmt, IRIf):
            return LoweredIf(
                lowered_id=self._new_id("lstmt"),
                span=stmt.span,
                condition=self._lower_expr(stmt.condition, target=target, diagnostics=diagnostics),
                then_block=[self._lower_stmt(item, target=target, diagnostics=diagnostics) for item in stmt.then_block],
                else_block=[self._lower_stmt(item, target=target, diagnostics=diagnostics) for item in stmt.else_block],
            )

        if isinstance(stmt, IRLoop):
            return LoweredLoop(
                lowered_id=self._new_id("lstmt"),
                span=stmt.span,
                iterator=stmt.iterator,
                start=self._lower_expr(stmt.start, target=target, diagnostics=diagnostics),
                end=self._lower_expr(stmt.end, target=target, diagnostics=diagnostics),
                body=[self._lower_stmt(item, target=target, diagnostics=diagnostics) for item in stmt.body],
            )

        if isinstance(stmt, IRFunction):
            body = [self._lower_stmt(item, target=target, diagnostics=diagnostics) for item in stmt.body]
            if stmt.expr_body is not None:
                body.append(
                    LoweredReturn(
                        lowered_id=self._new_id("lstmt"),
                        span=stmt.expr_body.span,
                        value=self._lower_expr(stmt.expr_body, target=target, diagnostics=diagnostics),
                    )
                )
            params = [{"name": param.name, "type_hint": param.type_hint} for param in stmt.params]
            return LoweredFunction(
                lowered_id=self._new_id("lstmt"),
                span=stmt.span,
                name=stmt.name,
                params=params,
                return_type=stmt.return_type,
                body=body,
            )

        if isinstance(stmt, IRReturn):
            return LoweredReturn(
                lowered_id=self._new_id("lstmt"),
                span=stmt.span,
                value=self._lower_expr(stmt.value, target=target, diagnostics=diagnostics) if stmt.value else None,
            )

        raise ExpansionError(
            code="LOW002",
            message=f"Unsupported IR statement in lowering: '{type(stmt).__name__}'.",
            span=getattr(stmt, "span", None),
            hint="Extend lowering rules or disable unsupported language features for this target.",
        )

    def _lower_expr(self, expr: IRExpr, *, target: str, diagnostics: list[str]) -> LoweredExpr:
        if isinstance(expr, IRLiteral):
            return LoweredLiteral(
                lowered_id=self._new_id("lexpr"),
                span=expr.span,
                expr_type=expr.expr_type,
                value=expr.value,
            )

        if isinstance(expr, IRRef):
            return LoweredRef(
                lowered_id=self._new_id("lexpr"),
                span=expr.span,
                expr_type=expr.expr_type,
                name=expr.name,
            )

        if isinstance(expr, IRUnary):
            return LoweredUnary(
                lowered_id=self._new_id("lexpr"),
                span=expr.span,
                expr_type=expr.expr_type,
                operator=expr.operator,
                operand=self._lower_expr(expr.operand, target=target, diagnostics=diagnostics),
            )

        if isinstance(expr, IRBinary):
            return LoweredBinary(
                lowered_id=self._new_id("lexpr"),
                span=expr.span,
                expr_type=expr.expr_type,
                left=self._lower_expr(expr.left, target=target, diagnostics=diagnostics),
                operator=expr.operator,
                right=self._lower_expr(expr.right, target=target, diagnostics=diagnostics),
            )

        if isinstance(expr, IRCall):
            return LoweredCall(
                lowered_id=self._new_id("lexpr"),
                span=expr.span,
                expr_type=expr.expr_type,
                callee=self._lower_expr(expr.callee, target=target, diagnostics=diagnostics),
                args=[self._lower_expr(arg, target=target, diagnostics=diagnostics) for arg in (expr.args or [])],
            )

        if isinstance(expr, IRLambda):
            return LoweredLambda(
                lowered_id=self._new_id("lexpr"),
                span=expr.span,
                expr_type=expr.expr_type,
                params=[{"name": param.name, "type_hint": param.type_hint} for param in (expr.params or [])],
                body=self._lower_expr(expr.body, target=target, diagnostics=diagnostics),
                return_type=expr.return_type,
            )

        raise ExpansionError(
            code="LOW003",
            message=f"Unsupported IR expression in lowering: '{type(expr).__name__}'.",
            span=getattr(expr, "span", None),
            hint="Extend expression lowering support for this target.",
        )

    def _required_helpers(self, statements: list[LoweredStmt], *, target: str) -> list[str]:
        helpers: set[str] = set()
        if target in {"web", "js", "typescript"}:
            if _contains_print_call(statements):
                helpers.add("print")
        return sorted(helpers)

    def _new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"


def _contains_print_call(statements: list[LoweredStmt]) -> bool:
    for stmt in statements:
        if isinstance(stmt, LoweredExpressionStmt):
            if _expr_has_print(stmt.expr):
                return True
        elif isinstance(stmt, LoweredIf):
            if _contains_print_call(stmt.then_block) or _contains_print_call(stmt.else_block):
                return True
        elif isinstance(stmt, LoweredLoop):
            if _contains_print_call(stmt.body):
                return True
        elif isinstance(stmt, LoweredFunction):
            if _contains_print_call(stmt.body):
                return True
        elif isinstance(stmt, LoweredReturn) and stmt.value is not None:
            if _expr_has_print(stmt.value):
                return True
        elif isinstance(stmt, LoweredAssignment):
            if _expr_has_print(stmt.value):
                return True
    return False


def _expr_has_print(expr: LoweredExpr) -> bool:
    if isinstance(expr, LoweredCall):
        callee = expr.callee
        if isinstance(callee, LoweredRef) and callee.name == "print":
            return True
        if callee is not None and _expr_has_print(callee):
            return True
        return any(_expr_has_print(arg) for arg in (expr.args or []))

    if isinstance(expr, LoweredUnary) and expr.operand is not None:
        return _expr_has_print(expr.operand)

    if isinstance(expr, LoweredBinary):
        left_has = expr.left is not None and _expr_has_print(expr.left)
        right_has = expr.right is not None and _expr_has_print(expr.right)
        return left_has or right_has

    if isinstance(expr, LoweredLambda) and expr.body is not None:
        return _expr_has_print(expr.body)

    return False


def collect_ir_features(module: IRModule) -> set[str]:
    """Collect declared features required by IR module."""

    features: set[str] = set()

    def walk_stmt(stmt: IRStmt) -> None:
        if isinstance(stmt, IRAssignment):
            features.add("assignment")
            if stmt.type_hint is not None:
                features.add("typed_annotation")
            walk_expr(stmt.value)
            return

        if isinstance(stmt, IRExpressionStmt):
            features.add("expression_stmt")
            walk_expr(stmt.expr)
            return

        if isinstance(stmt, IRIf):
            features.add("if")
            walk_expr(stmt.condition)
            for item in stmt.then_block:
                walk_stmt(item)
            for item in stmt.else_block:
                walk_stmt(item)
            return

        if isinstance(stmt, IRLoop):
            features.add("loop")
            walk_expr(stmt.start)
            walk_expr(stmt.end)
            for item in stmt.body:
                walk_stmt(item)
            return

        if isinstance(stmt, IRFunction):
            features.add("function")
            for item in stmt.body:
                walk_stmt(item)
            if stmt.expr_body is not None:
                walk_expr(stmt.expr_body)
            return

        if isinstance(stmt, IRReturn):
            features.add("return")
            if stmt.value is not None:
                walk_expr(stmt.value)
            return

    def walk_expr(expr: IRExpr) -> None:
        if isinstance(expr, IRLiteral):
            features.add("literal")
            return

        if isinstance(expr, IRRef):
            features.add("reference")
            return

        if isinstance(expr, IRUnary):
            features.add("unary")
            walk_expr(expr.operand)
            return

        if isinstance(expr, IRBinary):
            if expr.operator in {"&&", "||"}:
                features.add("logic")
            elif expr.operator in {"==", "!=", "<", "<=", ">", ">="}:
                features.add("comparison")
            else:
                features.add("arithmetic")
            walk_expr(expr.left)
            walk_expr(expr.right)
            return

        if isinstance(expr, IRCall):
            features.add("call")
            if expr.at_prefixed:
                features.add("at_call")
            walk_expr(expr.callee)
            for arg in (expr.args or []):
                walk_expr(arg)
            return

        if isinstance(expr, IRLambda):
            features.add("lambda")
            if expr.body is not None:
                walk_expr(expr.body)
            return

    for stmt in module.statements:
        walk_stmt(stmt)

    return features


def lowered_to_graph(module: LoweredModule) -> IntentGraph:
    """Convert lowered module into IntentGraph for emitters/optimizers."""

    graph = IntentGraph()
    counter = 0

    def new_node_id() -> str:
        nonlocal counter
        counter += 1
        return f"n{counter}"

    module_id = new_node_id()
    graph.add_node(node_id=module_id, kind="ModuleIntent", attrs={"name": "module", "target": module.target})
    graph.root_id = module_id

    def build_stmt(stmt: LoweredStmt, parent_id: str, edge_type: str, order: int) -> None:
        if isinstance(stmt, LoweredAssignment):
            node_id = new_node_id()
            graph.add_node(
                node_id=node_id,
                kind="AssignmentIntent",
                attrs={"name": stmt.name, "type_hint": stmt.type_hint},
            )
            value_id = build_expr(stmt.value)
            graph.add_edge(node_id, value_id, "value", order=0)

        elif isinstance(stmt, LoweredExpressionStmt):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="ExpressionIntent", attrs={})
            expr_id = build_expr(stmt.expr)
            graph.add_edge(node_id, expr_id, "expr", order=0)

        elif isinstance(stmt, LoweredIf):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="ControlIntent", attrs={"control": "if"})
            cond_id = build_expr(stmt.condition)
            graph.add_edge(node_id, cond_id, "condition", order=0)
            for idx, then_stmt in enumerate(stmt.then_block):
                build_stmt(then_stmt, node_id, "contains_then", idx)
            for idx, else_stmt in enumerate(stmt.else_block):
                build_stmt(else_stmt, node_id, "contains_else", idx)

        elif isinstance(stmt, LoweredLoop):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="LoopIntent", attrs={"iterator": stmt.iterator})
            start_id = build_expr(stmt.start)
            end_id = build_expr(stmt.end)
            graph.add_edge(node_id, start_id, "start", order=0)
            graph.add_edge(node_id, end_id, "end", order=1)
            for idx, body_stmt in enumerate(stmt.body):
                build_stmt(body_stmt, node_id, "contains_body", idx)

        elif isinstance(stmt, LoweredFunction):
            node_id = new_node_id()
            graph.add_node(
                node_id=node_id,
                kind="FuncIntent",
                attrs={
                    "name": stmt.name,
                    "params": stmt.params,
                    "return_type": stmt.return_type,
                    "expr_body": False,
                },
            )
            for idx, body_stmt in enumerate(stmt.body):
                build_stmt(body_stmt, node_id, "contains_body", idx)

        elif isinstance(stmt, LoweredReturn):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="ReturnIntent", attrs={})
            if stmt.value is not None:
                value_id = build_expr(stmt.value)
                graph.add_edge(node_id, value_id, "value", order=0)

        else:
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="UnknownIntent", attrs={"stmt": type(stmt).__name__})

        graph.add_edge(parent_id, node_id, edge_type=edge_type, order=order)

    def build_expr(expr: LoweredExpr) -> str:
        if isinstance(expr, LoweredLiteral):
            node_id = new_node_id()
            graph.add_node(
                node_id=node_id,
                kind="LiteralIntent",
                attrs={"value": expr.value, "value_type": type(expr.value).__name__},
            )
            return node_id

        if isinstance(expr, LoweredRef):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="RefIntent", attrs={"name": expr.name})
            return node_id

        if isinstance(expr, LoweredUnary):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="OperationIntent", attrs={"operator": expr.operator, "arity": 1})
            operand_id = build_expr(expr.operand)
            graph.add_edge(node_id, operand_id, "operand", order=0)
            return node_id

        if isinstance(expr, LoweredBinary):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="OperationIntent", attrs={"operator": expr.operator, "arity": 2})
            left_id = build_expr(expr.left)
            right_id = build_expr(expr.right)
            graph.add_edge(node_id, left_id, "operand", order=0)
            graph.add_edge(node_id, right_id, "operand", order=1)
            return node_id

        if isinstance(expr, LoweredCall):
            node_id = new_node_id()
            graph.add_node(node_id=node_id, kind="CallIntent", attrs={})
            if isinstance(expr.callee, LoweredRef):
                graph.nodes[node_id].attrs["callee_name"] = expr.callee.name
            elif expr.callee is not None:
                callee_id = build_expr(expr.callee)
                graph.add_edge(node_id, callee_id, "callee", order=0)
            for idx, arg in enumerate(expr.args or []):
                arg_id = build_expr(arg)
                graph.add_edge(node_id, arg_id, "arg", order=idx)
            return node_id

        if isinstance(expr, LoweredLambda):
            node_id = new_node_id()
            graph.add_node(
                node_id=node_id,
                kind="LambdaIntent",
                attrs={
                    "params": expr.params or [],
                    "return_type": expr.return_type,
                },
            )
            if expr.body is not None:
                body_id = build_expr(expr.body)
                graph.add_edge(node_id, body_id, "body", order=0)
            return node_id

        node_id = new_node_id()
        graph.add_node(node_id=node_id, kind="UnknownExprIntent", attrs={"expr": type(expr).__name__})
        return node_id

    for idx, stmt in enumerate(module.statements):
        build_stmt(stmt, module_id, "contains", idx)

    return graph


def lowered_to_dict(node: Any) -> Any:
    """Serialize lowered dataclasses recursively into JSON-compatible mapping."""
    if isinstance(node, list):
        return [lowered_to_dict(item) for item in node]
    if isinstance(node, dict):
        return {str(key): lowered_to_dict(value) for key, value in node.items()}
    if isinstance(node, SourceSpan):
        return node.to_dict()
    if is_dataclass(node):
        payload = asdict(node)
        payload["node_type"] = type(node).__name__
        return lowered_to_dict(payload)
    return node

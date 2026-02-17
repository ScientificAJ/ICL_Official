"""Intent Graph model and AST-to-graph builder for ICL."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    Program,
    ReturnStmt,
    Stmt,
    UnaryExpr,
)
from icl.source_map import SourceMap, SourceSpan


@dataclass
class IntentNode:
    """A typed semantic node in the Intent Graph."""

    node_id: str
    kind: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentEdge:
    """A directed relation between graph nodes."""

    source: str
    target: str
    edge_type: str
    order: int | None = None


@dataclass
class IntentDiff:
    """Structural diff output between two intent graphs."""

    added_nodes: list[str]
    removed_nodes: list[str]
    changed_nodes: list[str]
    added_edges: list[tuple[str, str, str, int | None]]
    removed_edges: list[tuple[str, str, str, int | None]]


@dataclass
class IntentGraph:
    """Directed graph representing normalized intent semantics."""

    nodes: dict[str, IntentNode] = field(default_factory=dict)
    edges: list[IntentEdge] = field(default_factory=list)
    root_id: str | None = None

    def add_node(self, kind: str, attrs: dict[str, Any] | None = None, node_id: str | None = None) -> str:
        """Add a new node and return its node id."""
        if node_id is None:
            node_id = f"n{len(self.nodes) + 1}"
            while node_id in self.nodes:
                node_id = f"n{len(self.nodes) + 1}"
        self.nodes[node_id] = IntentNode(node_id=node_id, kind=kind, attrs=attrs or {})
        return node_id

    def add_edge(self, source: str, target: str, edge_type: str, order: int | None = None) -> None:
        """Add a directed typed edge."""
        self.edges.append(IntentEdge(source=source, target=target, edge_type=edge_type, order=order))

    def outgoing(self, source: str, edge_type: str | None = None) -> list[IntentEdge]:
        """Return outgoing edges from source, optionally filtered by type."""
        edges = [edge for edge in self.edges if edge.source == source]
        if edge_type is not None:
            edges = [edge for edge in edges if edge.edge_type == edge_type]
        return sorted(edges, key=lambda e: (e.order is None, e.order if e.order is not None else 0))

    def incoming(self, target: str, edge_type: str | None = None) -> list[IntentEdge]:
        """Return incoming edges to target, optionally filtered by type."""
        edges = [edge for edge in self.edges if edge.target == target]
        if edge_type is not None:
            edges = [edge for edge in edges if edge.edge_type == edge_type]
        return edges

    def child_ids(self, source: str, edge_type: str) -> list[str]:
        """Return target node ids for ordered outgoing edge type."""
        return [edge.target for edge in self.outgoing(source, edge_type=edge_type)]

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all edges touching it."""
        if node_id in self.nodes:
            del self.nodes[node_id]
        self.edges = [edge for edge in self.edges if edge.source != node_id and edge.target != node_id]

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph as JSON-compatible mapping."""
        return {
            "schema_version": "1.0",
            "root_id": self.root_id,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind,
                    "attrs": node.attrs,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "edge_type": edge.edge_type,
                    "order": edge.order,
                }
                for edge in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntentGraph":
        """Construct graph from serialized mapping."""
        graph = cls()
        graph.root_id = data.get("root_id")
        for node in data.get("nodes", []):
            graph.nodes[node["node_id"]] = IntentNode(
                node_id=node["node_id"],
                kind=node["kind"],
                attrs=dict(node.get("attrs", {})),
            )
        for edge in data.get("edges", []):
            graph.edges.append(
                IntentEdge(
                    source=edge["source"],
                    target=edge["target"],
                    edge_type=edge["edge_type"],
                    order=edge.get("order"),
                )
            )
        return graph


class IntentGraphBuilder:
    """Builds Intent Graph plus source map from AST."""

    def __init__(self, source_map: SourceMap | None = None) -> None:
        self._counter = 0
        self._source_map = source_map or SourceMap()

    @property
    def source_map(self) -> SourceMap:
        """Return source map populated during build."""
        return self._source_map

    def build(self, program: Program) -> IntentGraph:
        """Convert a program AST into an IntentGraph."""
        graph = IntentGraph()
        module_id = self._new_node_id()
        graph.add_node(node_id=module_id, kind="ModuleIntent", attrs={"name": "module"})
        graph.root_id = module_id
        self._record_span(module_id, program.span, note="module")

        for idx, stmt in enumerate(program.statements):
            self._build_stmt(graph, stmt, parent_id=module_id, edge_type="contains", order=idx)
        return graph

    def _build_stmt(
        self,
        graph: IntentGraph,
        stmt: Stmt,
        parent_id: str,
        edge_type: str,
        order: int,
    ) -> str:
        if isinstance(stmt, AssignmentStmt):
            node_id = self._create_node(
                graph,
                kind="AssignmentIntent",
                attrs={"name": stmt.name, "type_hint": stmt.type_hint},
                span=stmt.span,
            )
            value_id = self._build_expr(graph, stmt.value)
            graph.add_edge(node_id, value_id, "value", order=0)

        elif isinstance(stmt, ExpressionStmt):
            node_id = self._create_node(
                graph,
                kind="ExpressionIntent",
                attrs={},
                span=stmt.span,
            )
            expr_id = self._build_expr(graph, stmt.expr)
            graph.add_edge(node_id, expr_id, "expr", order=0)

        elif isinstance(stmt, IfStmt):
            node_id = self._create_node(
                graph,
                kind="ControlIntent",
                attrs={"control": "if"},
                span=stmt.span,
            )
            cond_id = self._build_expr(graph, stmt.condition)
            graph.add_edge(node_id, cond_id, "condition", order=0)
            for idx, then_stmt in enumerate(stmt.then_block):
                self._build_stmt(graph, then_stmt, parent_id=node_id, edge_type="contains_then", order=idx)
            for idx, else_stmt in enumerate(stmt.else_block):
                self._build_stmt(graph, else_stmt, parent_id=node_id, edge_type="contains_else", order=idx)

        elif isinstance(stmt, LoopStmt):
            node_id = self._create_node(
                graph,
                kind="LoopIntent",
                attrs={"iterator": stmt.iterator},
                span=stmt.span,
            )
            start_id = self._build_expr(graph, stmt.start)
            end_id = self._build_expr(graph, stmt.end)
            graph.add_edge(node_id, start_id, "start", order=0)
            graph.add_edge(node_id, end_id, "end", order=1)
            for idx, body_stmt in enumerate(stmt.body):
                self._build_stmt(graph, body_stmt, parent_id=node_id, edge_type="contains_body", order=idx)

        elif isinstance(stmt, FunctionDefStmt):
            node_id = self._create_node(
                graph,
                kind="FuncIntent",
                attrs={
                    "name": stmt.name,
                    "params": [
                        {"name": param.name, "type_hint": param.type_hint}
                        for param in stmt.params
                    ],
                    "return_type": stmt.return_type,
                    "expr_body": stmt.expr_body is not None,
                },
                span=stmt.span,
            )
            if stmt.expr_body is not None:
                expr_id = self._build_expr(graph, stmt.expr_body)
                graph.add_edge(node_id, expr_id, "return_expr", order=0)
            else:
                for idx, body_stmt in enumerate(stmt.body):
                    self._build_stmt(graph, body_stmt, parent_id=node_id, edge_type="contains_body", order=idx)

        elif isinstance(stmt, ReturnStmt):
            node_id = self._create_node(
                graph,
                kind="ReturnIntent",
                attrs={},
                span=stmt.span,
            )
            if stmt.value is not None:
                value_id = self._build_expr(graph, stmt.value)
                graph.add_edge(node_id, value_id, "value", order=0)

        elif isinstance(stmt, MacroStmt):
            node_id = self._create_node(
                graph,
                kind="ExpansionIntent",
                attrs={"macro": stmt.name, "args": len(stmt.args)},
                span=stmt.span,
            )
            for idx, arg in enumerate(stmt.args):
                arg_id = self._build_expr(graph, arg)
                graph.add_edge(node_id, arg_id, "arg", order=idx)

        else:
            node_id = self._create_node(
                graph,
                kind="UnknownIntent",
                attrs={"stmt": type(stmt).__name__},
                span=stmt.span,
            )

        graph.add_edge(parent_id, node_id, edge_type=edge_type, order=order)
        return node_id

    def _build_expr(self, graph: IntentGraph, expr: Expr) -> str:
        if isinstance(expr, LiteralExpr):
            return self._create_node(
                graph,
                kind="LiteralIntent",
                attrs={"value": expr.value, "value_type": type(expr.value).__name__},
                span=expr.span,
            )

        if isinstance(expr, IdentifierExpr):
            return self._create_node(
                graph,
                kind="RefIntent",
                attrs={"name": expr.name},
                span=expr.span,
            )

        if isinstance(expr, UnaryExpr):
            node_id = self._create_node(
                graph,
                kind="OperationIntent",
                attrs={"operator": expr.operator, "arity": 1},
                span=expr.span,
            )
            operand_id = self._build_expr(graph, expr.operand)
            graph.add_edge(node_id, operand_id, "operand", order=0)
            return node_id

        if isinstance(expr, BinaryExpr):
            node_id = self._create_node(
                graph,
                kind="OperationIntent",
                attrs={"operator": expr.operator, "arity": 2},
                span=expr.span,
            )
            left_id = self._build_expr(graph, expr.left)
            right_id = self._build_expr(graph, expr.right)
            graph.add_edge(node_id, left_id, "operand", order=0)
            graph.add_edge(node_id, right_id, "operand", order=1)
            return node_id

        if isinstance(expr, CallExpr):
            attrs: dict[str, Any] = {"at_prefixed": expr.at_prefixed}
            node_id = self._create_node(
                graph,
                kind="CallIntent",
                attrs=attrs,
                span=expr.span,
            )
            if isinstance(expr.callee, IdentifierExpr):
                graph.nodes[node_id].attrs["callee_name"] = expr.callee.name
            else:
                callee_id = self._build_expr(graph, expr.callee)
                graph.add_edge(node_id, callee_id, "callee", order=0)
            for idx, arg in enumerate(expr.args):
                arg_id = self._build_expr(graph, arg)
                graph.add_edge(node_id, arg_id, "arg", order=idx)
            return node_id

        if isinstance(expr, LambdaExpr):
            node_id = self._create_node(
                graph,
                kind="LambdaIntent",
                attrs={
                    "params": [
                        {"name": param.name, "type_hint": param.type_hint}
                        for param in expr.params
                    ],
                    "return_type": expr.return_type,
                },
                span=expr.span,
            )
            body_id = self._build_expr(graph, expr.body)
            graph.add_edge(node_id, body_id, "body", order=0)
            return node_id

        return self._create_node(
            graph,
            kind="UnknownExprIntent",
            attrs={"expr": type(expr).__name__},
            span=expr.span,
        )

    def _create_node(self, graph: IntentGraph, kind: str, attrs: dict[str, Any], span: SourceSpan) -> str:
        node_id = self._new_node_id()
        graph.add_node(node_id=node_id, kind=kind, attrs=attrs)
        self._record_span(node_id, span, note=kind)
        return node_id

    def _new_node_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def _record_span(self, node_id: str, span: SourceSpan, note: str) -> None:
        self._source_map.add(node_id=node_id, span=span, note=note)


def diff_graphs(before: IntentGraph, after: IntentGraph) -> IntentDiff:
    """Compute a structural diff between two IntentGraph snapshots."""
    before_ids = set(before.nodes.keys())
    after_ids = set(after.nodes.keys())

    added_nodes = sorted(after_ids - before_ids)
    removed_nodes = sorted(before_ids - after_ids)

    changed_nodes: list[str] = []
    for node_id in sorted(before_ids & after_ids):
        left = before.nodes[node_id]
        right = after.nodes[node_id]
        if left.kind != right.kind or left.attrs != right.attrs:
            changed_nodes.append(node_id)

    before_edges = {(e.source, e.target, e.edge_type, e.order) for e in before.edges}
    after_edges = {(e.source, e.target, e.edge_type, e.order) for e in after.edges}

    added_edges = sorted(after_edges - before_edges)
    removed_edges = sorted(before_edges - after_edges)

    return IntentDiff(
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        changed_nodes=changed_nodes,
        added_edges=added_edges,
        removed_edges=removed_edges,
    )

"""Graph-level optimization passes for ICL Intent Graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import copy

from icl.graph import IntentGraph


@dataclass
class OptimizationReport:
    """Summary of optimization actions applied to a graph."""

    folded_operations: int = 0
    removed_assignments: int = 0
    notes: list[str] = field(default_factory=list)


class GraphOptimizer:
    """Applies deterministic optimization passes to an IntentGraph."""

    def optimize(self, graph: IntentGraph) -> tuple[IntentGraph, OptimizationReport]:
        """Run optimization passes and return optimized graph + report."""
        optimized = copy.deepcopy(graph)
        report = OptimizationReport()

        self._constant_fold(optimized, report)
        self._remove_dead_assignments(optimized, report)
        self._prune_orphans(optimized)

        return optimized, report

    def _constant_fold(self, graph: IntentGraph, report: OptimizationReport) -> None:
        for node_id, node in list(graph.nodes.items()):
            if node.kind != "OperationIntent":
                continue

            operands = [graph.nodes[edge.target] for edge in graph.outgoing(node_id, edge_type="operand")]
            if not operands or any(op.kind != "LiteralIntent" for op in operands):
                continue

            values = [op.attrs.get("value") for op in operands]
            operator = node.attrs.get("operator")

            try:
                folded = self._eval_operator(operator, values)
            except Exception:
                continue

            node.kind = "LiteralIntent"
            node.attrs = {
                "value": folded,
                "value_type": type(folded).__name__,
                "folded_from": operator,
            }
            graph.edges = [
                edge
                for edge in graph.edges
                if not (edge.source == node_id and edge.edge_type == "operand")
            ]
            report.folded_operations += 1
            report.notes.append(f"Folded operation node {node_id} ({operator}).")

    def _remove_dead_assignments(self, graph: IntentGraph, report: OptimizationReport) -> None:
        referenced_names = {
            node.attrs.get("name")
            for node in graph.nodes.values()
            if node.kind == "RefIntent" and node.attrs.get("name")
        }

        for node_id, node in list(graph.nodes.items()):
            if node.kind != "AssignmentIntent":
                continue
            name = node.attrs.get("name")
            if name in referenced_names:
                continue

            graph.remove_node(node_id)
            report.removed_assignments += 1
            report.notes.append(f"Removed dead assignment node {node_id} ({name}).")

    def _prune_orphans(self, graph: IntentGraph) -> None:
        changed = True
        while changed:
            changed = False
            for node_id in list(graph.nodes.keys()):
                if node_id == graph.root_id:
                    continue
                if graph.incoming(node_id):
                    continue
                graph.remove_node(node_id)
                changed = True

    @staticmethod
    def _eval_operator(operator: str, values: list[Any]) -> Any:
        if operator == "+":
            return values[0] + values[1]
        if operator == "-":
            if len(values) == 1:
                return -values[0]
            return values[0] - values[1]
        if operator == "*":
            return values[0] * values[1]
        if operator == "/":
            return values[0] / values[1]
        if operator == "%":
            return values[0] % values[1]
        if operator == "==":
            return values[0] == values[1]
        if operator == "!=":
            return values[0] != values[1]
        if operator == "<":
            return values[0] < values[1]
        if operator == "<=":
            return values[0] <= values[1]
        if operator == ">":
            return values[0] > values[1]
        if operator == ">=":
            return values[0] >= values[1]
        if operator == "&&":
            return values[0] and values[1]
        if operator == "||":
            return values[0] or values[1]
        if operator == "!":
            return not values[0]
        if operator == "+u":
            return +values[0]
        raise ValueError(f"Unsupported operator for folding: {operator}")

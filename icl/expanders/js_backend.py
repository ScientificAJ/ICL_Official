"""JavaScript backend emitter for ICL Intent Graph."""

from __future__ import annotations

import json

from icl.expanders.base import BackendEmitter, ExpansionContext
from icl.graph import IntentGraph


class JavaScriptBackend(BackendEmitter):
    """Expands Intent Graph into executable JavaScript source."""

    @property
    def name(self) -> str:
        return "js"

    def emit_module(self, graph: IntentGraph, context: ExpansionContext) -> str:
        self._declared: set[str] = set()
        if graph.root_id is None:
            return ""
        lines: list[str] = []
        for stmt_id in graph.child_ids(graph.root_id, "contains"):
            lines.extend(self._emit_stmt(graph, stmt_id, indent=0))
        return "\n".join(lines).rstrip() + "\n"

    def _emit_stmt(self, graph: IntentGraph, node_id: str, indent: int) -> list[str]:
        node = graph.nodes[node_id]
        kind = node.kind

        if kind == "AssignmentIntent":
            value_id = graph.child_ids(node_id, "value")[0]
            value_src = self._emit_expr(graph, value_id)
            name = str(node.attrs["name"])
            if name in self._declared:
                return [self.indent(f"{name} = {value_src};", indent)]
            self._declared.add(name)
            return [self.indent(f"let {name} = {value_src};", indent)]

        if kind == "ExpressionIntent":
            expr_id = graph.child_ids(node_id, "expr")[0]
            return [self.indent(f"{self._emit_expr(graph, expr_id)};", indent)]

        if kind == "ControlIntent":
            cond_id = graph.child_ids(node_id, "condition")[0]
            cond_src = self._emit_expr(graph, cond_id)
            lines = [self.indent(f"if ({cond_src}) {{", indent)]
            then_ids = graph.child_ids(node_id, "contains_then")
            if then_ids:
                for then_id in then_ids:
                    lines.extend(self._emit_stmt(graph, then_id, indent + 1))
            lines.append(self.indent("}", indent))

            else_ids = graph.child_ids(node_id, "contains_else")
            if else_ids:
                lines[-1] = self.indent("} else {", indent)
                for else_id in else_ids:
                    lines.extend(self._emit_stmt(graph, else_id, indent + 1))
                lines.append(self.indent("}", indent))
            return lines

        if kind == "LoopIntent":
            start_id = graph.child_ids(node_id, "start")[0]
            end_id = graph.child_ids(node_id, "end")[0]
            start_src = self._emit_expr(graph, start_id)
            end_src = self._emit_expr(graph, end_id)
            it = str(node.attrs["iterator"])
            lines = [
                self.indent(
                    f"for (let {it} = {start_src}; {it} < {end_src}; {it}++) {{",
                    indent,
                )
            ]
            body_ids = graph.child_ids(node_id, "contains_body")
            for body_id in body_ids:
                lines.extend(self._emit_stmt(graph, body_id, indent + 1))
            lines.append(self.indent("}", indent))
            return lines

        if kind == "FuncIntent":
            params = node.attrs.get("params", [])
            param_src = ", ".join(param["name"] for param in params)
            lines = [self.indent(f"function {node.attrs['name']}({param_src}) {{", indent)]
            if node.attrs.get("expr_body"):
                expr_id = graph.child_ids(node_id, "return_expr")[0]
                lines.append(self.indent(f"return {self._emit_expr(graph, expr_id)};", indent + 1))
                lines.append(self.indent("}", indent))
                return lines

            body_ids = graph.child_ids(node_id, "contains_body")
            if body_ids:
                for body_id in body_ids:
                    lines.extend(self._emit_stmt(graph, body_id, indent + 1))
            lines.append(self.indent("}", indent))
            return lines

        if kind == "ReturnIntent":
            value_ids = graph.child_ids(node_id, "value")
            if value_ids:
                return [self.indent(f"return {self._emit_expr(graph, value_ids[0])};", indent)]
            return [self.indent("return;", indent)]

        if kind == "ExpansionIntent":
            return [self.indent(f"// expansion macro: {node.attrs.get('macro', 'unknown')}", indent)]

        return [self.indent(f"// unsupported intent: {kind}", indent)]

    def _emit_expr(self, graph: IntentGraph, node_id: str) -> str:
        node = graph.nodes[node_id]
        kind = node.kind

        if kind == "LiteralIntent":
            value = node.attrs.get("value")
            if isinstance(value, bool):
                return "true" if value else "false"
            return json.dumps(value)

        if kind == "RefIntent":
            return str(node.attrs.get("name"))

        if kind == "OperationIntent":
            operator = str(node.attrs.get("operator"))
            operands = [self._emit_expr(graph, child_id) for child_id in graph.child_ids(node_id, "operand")]
            if len(operands) == 1:
                return f"({operator}{operands[0]})"
            return f"({operands[0]} {operator} {operands[1]})"

        if kind == "CallIntent":
            callee = node.attrs.get("callee_name")
            if callee is None:
                callee_ids = graph.child_ids(node_id, "callee")
                callee = self._emit_expr(graph, callee_ids[0]) if callee_ids else "unknown"
            args = [self._emit_expr(graph, arg_id) for arg_id in graph.child_ids(node_id, "arg")]
            return f"{callee}({', '.join(args)})"

        return "null"

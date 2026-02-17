"""Python backend emitter for ICL Intent Graph."""

from __future__ import annotations

from icl.expanders.base import BackendEmitter, ExpansionContext
from icl.graph import IntentGraph


class PythonBackend(BackendEmitter):
    """Expands Intent Graph into executable Python source."""

    @property
    def name(self) -> str:
        return "python"

    def emit_module(self, graph: IntentGraph, context: ExpansionContext) -> str:
        if graph.root_id is None:
            return ""
        statement_ids = graph.child_ids(graph.root_id, "contains")
        lines: list[str] = []
        for stmt_id in statement_ids:
            lines.extend(self._emit_stmt(graph, stmt_id, indent=0))
        return "\n".join(lines).rstrip() + "\n"

    def _emit_stmt(self, graph: IntentGraph, node_id: str, indent: int) -> list[str]:
        node = graph.nodes[node_id]
        kind = node.kind

        if kind == "AssignmentIntent":
            value_id = graph.child_ids(node_id, "value")[0]
            value_src = self._emit_expr(graph, value_id)
            return [self.indent(f"{node.attrs['name']} = {value_src}", indent)]

        if kind == "ExpressionIntent":
            expr_id = graph.child_ids(node_id, "expr")[0]
            return [self.indent(self._emit_expr(graph, expr_id), indent)]

        if kind == "ControlIntent":
            cond_id = graph.child_ids(node_id, "condition")[0]
            cond_src = self._emit_expr(graph, cond_id)
            lines = [self.indent(f"if {cond_src}:", indent)]

            then_ids = graph.child_ids(node_id, "contains_then")
            if then_ids:
                for then_id in then_ids:
                    lines.extend(self._emit_stmt(graph, then_id, indent + 1))
            else:
                lines.append(self.indent("pass", indent + 1))

            else_ids = graph.child_ids(node_id, "contains_else")
            if else_ids:
                lines.append(self.indent("else:", indent))
                for else_id in else_ids:
                    lines.extend(self._emit_stmt(graph, else_id, indent + 1))
            return lines

        if kind == "LoopIntent":
            start_id = graph.child_ids(node_id, "start")[0]
            end_id = graph.child_ids(node_id, "end")[0]
            start_src = self._emit_expr(graph, start_id)
            end_src = self._emit_expr(graph, end_id)
            lines = [
                self.indent(
                    f"for {node.attrs['iterator']} in range({start_src}, {end_src}):",
                    indent,
                )
            ]
            body_ids = graph.child_ids(node_id, "contains_body")
            if body_ids:
                for body_id in body_ids:
                    lines.extend(self._emit_stmt(graph, body_id, indent + 1))
            else:
                lines.append(self.indent("pass", indent + 1))
            return lines

        if kind == "FuncIntent":
            params = node.attrs.get("params", [])
            param_src = ", ".join(param["name"] for param in params)
            lines = [self.indent(f"def {node.attrs['name']}({param_src}):", indent)]

            if node.attrs.get("expr_body"):
                expr_id = graph.child_ids(node_id, "return_expr")[0]
                expr_src = self._emit_expr(graph, expr_id)
                lines.append(self.indent(f"return {expr_src}", indent + 1))
                return lines

            body_ids = graph.child_ids(node_id, "contains_body")
            if body_ids:
                for body_id in body_ids:
                    lines.extend(self._emit_stmt(graph, body_id, indent + 1))
            else:
                lines.append(self.indent("pass", indent + 1))
            return lines

        if kind == "ReturnIntent":
            value_ids = graph.child_ids(node_id, "value")
            if value_ids:
                return [self.indent(f"return {self._emit_expr(graph, value_ids[0])}", indent)]
            return [self.indent("return", indent)]

        if kind == "ExpansionIntent":
            return [self.indent(f"# expansion macro: {node.attrs.get('macro', 'unknown')}", indent)]

        return [self.indent(f"# unsupported intent: {kind}", indent)]

    def _emit_expr(self, graph: IntentGraph, node_id: str) -> str:
        node = graph.nodes[node_id]
        kind = node.kind

        if kind == "LiteralIntent":
            return repr(node.attrs.get("value"))

        if kind == "RefIntent":
            return str(node.attrs.get("name"))

        if kind == "OperationIntent":
            operator = str(node.attrs.get("operator"))
            operands = [self._emit_expr(graph, child_id) for child_id in graph.child_ids(node_id, "operand")]
            if len(operands) == 1:
                if operator == "!":
                    return f"(not {operands[0]})"
                return f"({operator}{operands[0]})"

            mapped_op = {"&&": "and", "||": "or"}.get(operator, operator)
            return f"({operands[0]} {mapped_op} {operands[1]})"

        if kind == "CallIntent":
            callee = node.attrs.get("callee_name")
            if callee is None:
                callee_ids = graph.child_ids(node_id, "callee")
                callee = self._emit_expr(graph, callee_ids[0]) if callee_ids else "unknown"
            args = [self._emit_expr(graph, arg_id) for arg_id in graph.child_ids(node_id, "arg")]
            return f"{callee}({', '.join(args)})"

        if kind == "LambdaIntent":
            params = node.attrs.get("params", [])
            body_ids = graph.child_ids(node_id, "body")
            body_src = self._emit_expr(graph, body_ids[0]) if body_ids else "None"
            param_src = ", ".join(param["name"] for param in params)
            return f"(lambda {param_src}: {body_src})"

        return "None"

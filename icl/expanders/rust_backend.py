"""Rust backend emitter for ICL Intent Graph."""

from __future__ import annotations

import json

from icl.expanders.base import BackendEmitter, ExpansionContext
from icl.graph import IntentGraph


class RustBackend(BackendEmitter):
    """Expands Intent Graph into runnable Rust source for core ICL constructs."""

    @property
    def name(self) -> str:
        return "rust"

    def emit_module(self, graph: IntentGraph, context: ExpansionContext) -> str:
        if graph.root_id is None:
            return ""

        self._function_return_types: dict[str, str] = {}
        self._function_param_types: dict[str, list[str]] = {}
        self._scope_stack: list[dict[str, str]] = []
        self._current_function_return: str | None = None

        function_ids: list[str] = []
        main_ids: list[str] = []
        for stmt_id in graph.child_ids(graph.root_id, "contains"):
            node = graph.nodes[stmt_id]
            if node.kind == "FuncIntent":
                function_ids.append(stmt_id)
            else:
                main_ids.append(stmt_id)

        self._collect_function_signatures(graph, function_ids)

        lines: list[str] = []
        for fn_id in function_ids:
            lines.extend(self._emit_function(graph, fn_id, indent=0))
            lines.append("")

        lines.append("fn main() {")
        self._push_scope()
        if main_ids:
            for stmt_id in main_ids:
                stmt_lines, _ = self._emit_stmt(graph, stmt_id, indent=1)
                lines.extend(stmt_lines)
        else:
            lines.append(self.indent("// empty", 1))
        self._pop_scope()
        lines.append("}")

        return "\n".join(lines).rstrip() + "\n"

    def _collect_function_signatures(self, graph: IntentGraph, function_ids: list[str]) -> None:
        for fn_id in function_ids:
            node = graph.nodes[fn_id]
            name = str(node.attrs.get("name", "func"))
            params = node.attrs.get("params", [])
            param_types = [self._symbolic_to_rust(param.get("type_hint")) for param in params]
            return_type = self._symbolic_to_rust(node.attrs.get("return_type"))
            self._function_param_types[name] = param_types
            self._function_return_types[name] = return_type

    def _emit_function(self, graph: IntentGraph, node_id: str, indent: int) -> list[str]:
        node = graph.nodes[node_id]
        name = str(node.attrs.get("name", "func"))
        params = node.attrs.get("params", [])
        return_type = self._function_return_types.get(name, "f64")

        rendered_params: list[str] = []
        for idx, param in enumerate(params):
            p_name = str(param.get("name"))
            p_type = self._function_param_types.get(name, ["f64"] * len(params))[idx]
            rendered_params.append(f"{p_name}: {p_type}")

        lines = [self.indent(f"fn {name}({', '.join(rendered_params)}) -> {return_type} {{", indent)]

        self._push_scope()
        for idx, param in enumerate(params):
            p_name = str(param.get("name"))
            p_type = self._function_param_types.get(name, ["f64"] * len(params))[idx]
            self._define_symbol(p_name, p_type)

        prev_return = self._current_function_return
        self._current_function_return = return_type

        saw_return = False
        body_ids = graph.child_ids(node_id, "contains_body")
        if body_ids:
            for body_id in body_ids:
                stmt_lines, returned = self._emit_stmt(graph, body_id, indent + 1)
                lines.extend(stmt_lines)
                saw_return = saw_return or returned

        if not saw_return:
            lines.append(self.indent(f"return {self._default_value(return_type)};", indent + 1))

        self._current_function_return = prev_return
        self._pop_scope()
        lines.append(self.indent("}", indent))
        return lines

    def _emit_stmt(self, graph: IntentGraph, node_id: str, indent: int) -> tuple[list[str], bool]:
        node = graph.nodes[node_id]
        kind = node.kind

        if kind == "AssignmentIntent":
            value_id = graph.child_ids(node_id, "value")[0]
            value_src, value_ty = self._emit_expr(graph, value_id)
            name = str(node.attrs["name"])

            existing_ty = self._resolve_symbol(name)
            if existing_ty is not None:
                if existing_ty == "Fn":
                    return [self.indent(f"{name} = {value_src};", indent)], False
                coerced = self._coerce(value_src, value_ty, existing_ty)
                return [self.indent(f"{name} = {coerced};", indent)], False

            inferred = self._normalize_decl_type(value_ty)
            self._define_symbol(name, inferred)
            if inferred == "Fn":
                return [self.indent(f"let mut {name} = {value_src};", indent)], False
            coerced = self._coerce(value_src, value_ty, inferred)
            return [self.indent(f"let mut {name}: {inferred} = {coerced};", indent)], False

        if kind == "ExpressionIntent":
            expr_id = graph.child_ids(node_id, "expr")[0]
            expr_node = graph.nodes[expr_id]
            if expr_node.kind == "CallIntent" and expr_node.attrs.get("callee_name") == "print":
                args = [self._emit_expr(graph, arg_id)[0] for arg_id in graph.child_ids(expr_id, "arg")]
                arg = args[0] if args else '""'
                return [self.indent(f"println!(\"{{:?}}\", {arg});", indent)], False

            expr_src, _ = self._emit_expr(graph, expr_id)
            return [self.indent(f"{expr_src};", indent)], False

        if kind == "ControlIntent":
            cond_id = graph.child_ids(node_id, "condition")[0]
            cond_src, cond_ty = self._emit_expr(graph, cond_id)
            cond_src = self._coerce(cond_src, cond_ty, "bool")
            lines = [self.indent(f"if {cond_src} {{", indent)]

            self._push_scope()
            then_returned = False
            for then_id in graph.child_ids(node_id, "contains_then"):
                then_lines, returned = self._emit_stmt(graph, then_id, indent + 1)
                lines.extend(then_lines)
                then_returned = then_returned or returned
            self._pop_scope()
            lines.append(self.indent("}", indent))

            else_ids = graph.child_ids(node_id, "contains_else")
            else_returned = False
            if else_ids:
                lines[-1] = self.indent("} else {", indent)
                self._push_scope()
                for else_id in else_ids:
                    else_lines, returned = self._emit_stmt(graph, else_id, indent + 1)
                    lines.extend(else_lines)
                    else_returned = else_returned or returned
                self._pop_scope()
                lines.append(self.indent("}", indent))

            return lines, bool(else_ids) and then_returned and else_returned

        if kind == "LoopIntent":
            start_id = graph.child_ids(node_id, "start")[0]
            end_id = graph.child_ids(node_id, "end")[0]
            start_src, start_ty = self._emit_expr(graph, start_id)
            end_src, end_ty = self._emit_expr(graph, end_id)
            it = str(node.attrs["iterator"])

            start_i64 = self._coerce(start_src, start_ty, "i64")
            end_i64 = self._coerce(end_src, end_ty, "i64")

            lines = [self.indent(f"for {it} in ({start_i64})..({end_i64}) {{", indent)]
            self._push_scope()
            self._define_symbol(it, "i64")
            for body_id in graph.child_ids(node_id, "contains_body"):
                body_lines, _ = self._emit_stmt(graph, body_id, indent + 1)
                lines.extend(body_lines)
            self._pop_scope()
            lines.append(self.indent("}", indent))
            return lines, False

        if kind == "FuncIntent":
            return self._emit_function(graph, node_id, indent), False

        if kind == "ReturnIntent":
            value_ids = graph.child_ids(node_id, "value")
            target_ty = self._current_function_return or "f64"
            if value_ids:
                value_src, value_ty = self._emit_expr(graph, value_ids[0])
                coerced = self._coerce(value_src, value_ty, target_ty)
                return [self.indent(f"return {coerced};", indent)], True
            if target_ty == "()":
                return [self.indent("return;", indent)], True
            return [self.indent(f"return {self._default_value(target_ty)};", indent)], True

        if kind == "ExpansionIntent":
            return [self.indent(f"// expansion macro: {node.attrs.get('macro', 'unknown')}", indent)], False

        return [self.indent(f"// unsupported intent: {kind}", indent)], False

    def _emit_expr(self, graph: IntentGraph, node_id: str) -> tuple[str, str]:
        node = graph.nodes[node_id]
        kind = node.kind

        if kind == "LiteralIntent":
            value = node.attrs.get("value")
            if isinstance(value, bool):
                return ("true" if value else "false"), "bool"
            if isinstance(value, str):
                return f"{json.dumps(value)}.to_string()", "String"
            return self._render_number(value), "f64"

        if kind == "RefIntent":
            name = str(node.attrs.get("name"))
            return name, self._resolve_symbol(name) or "f64"

        if kind == "OperationIntent":
            operator = str(node.attrs.get("operator"))
            operands = [self._emit_expr(graph, child_id) for child_id in graph.child_ids(node_id, "operand")]

            if len(operands) == 1:
                operand_src, operand_ty = operands[0]
                if operator == "!":
                    operand_src = self._coerce(operand_src, operand_ty, "bool")
                    return f"(!{operand_src})", "bool"
                operand_src = self._coerce(operand_src, operand_ty, "f64")
                return f"({operator}{operand_src})", "f64"

            left_src, left_ty = operands[0]
            right_src, right_ty = operands[1]

            if operator in {"+", "-", "*", "/", "%"}:
                if operator == "+" and (left_ty == "String" or right_ty == "String"):
                    left_str = self._to_string_expr(left_src, left_ty)
                    right_str = self._to_string_expr(right_src, right_ty)
                    return f"format!(\"{{}}{{}}\", {left_str}, {right_str})", "String"
                left_num = self._coerce(left_src, left_ty, "f64")
                right_num = self._coerce(right_src, right_ty, "f64")
                if operator == "%":
                    return f"({left_num} % {right_num})", "f64"
                return f"({left_num} {operator} {right_num})", "f64"

            if operator in {"==", "!="}:
                if left_ty == "String" and right_ty != "String":
                    right_src = self._to_string_expr(right_src, right_ty)
                    right_ty = "String"
                if right_ty == "String" and left_ty != "String":
                    left_src = self._to_string_expr(left_src, left_ty)
                    left_ty = "String"
                if self._is_numeric(left_ty) and self._is_numeric(right_ty):
                    left_src = self._coerce(left_src, left_ty, "f64")
                    right_src = self._coerce(right_src, right_ty, "f64")
                return f"({left_src} {operator} {right_src})", "bool"

            if operator in {"<", "<=", ">", ">="}:
                left_num = self._coerce(left_src, left_ty, "f64")
                right_num = self._coerce(right_src, right_ty, "f64")
                return f"({left_num} {operator} {right_num})", "bool"

            if operator in {"&&", "||"}:
                left_bool = self._coerce(left_src, left_ty, "bool")
                right_bool = self._coerce(right_src, right_ty, "bool")
                return f"({left_bool} {operator} {right_bool})", "bool"

            return "0.0", "f64"

        if kind == "CallIntent":
            callee = node.attrs.get("callee_name")
            if callee is None:
                callee_ids = graph.child_ids(node_id, "callee")
                callee, _ = self._emit_expr(graph, callee_ids[0]) if callee_ids else ("unknown", "Fn")
            else:
                callee = str(callee)

            args_src: list[str] = []
            arg_ids = graph.child_ids(node_id, "arg")
            expected_arg_types = self._function_param_types.get(callee, ["f64"] * len(arg_ids))
            for idx, arg_id in enumerate(arg_ids):
                arg_src, arg_ty = self._emit_expr(graph, arg_id)
                target_ty = expected_arg_types[idx] if idx < len(expected_arg_types) else arg_ty
                args_src.append(self._coerce(arg_src, arg_ty, target_ty))

            return_type = self._function_return_types.get(callee, "f64")
            return f"{callee}({', '.join(args_src)})", return_type

        if kind == "LambdaIntent":
            params = node.attrs.get("params", [])
            body_ids = graph.child_ids(node_id, "body")

            rendered_params: list[str] = []
            self._push_scope()
            for param in params:
                param_name = str(param.get("name"))
                param_type = self._symbolic_to_rust(param.get("type_hint"))
                self._define_symbol(param_name, param_type)
                rendered_params.append(param_name)

            body_src = "0.0"
            if body_ids:
                body_src, _ = self._emit_expr(graph, body_ids[0])
            self._pop_scope()

            return f"|{', '.join(rendered_params)}| {body_src}", "Fn"

        return "0.0", "f64"

    def _push_scope(self) -> None:
        self._scope_stack.append({})

    def _pop_scope(self) -> None:
        self._scope_stack.pop()

    def _define_symbol(self, name: str, rust_type: str) -> None:
        if not self._scope_stack:
            self._push_scope()
        self._scope_stack[-1][name] = rust_type

    def _resolve_symbol(self, name: str) -> str | None:
        for scope in reversed(self._scope_stack):
            if name in scope:
                return scope[name]
        return None

    @staticmethod
    def _symbolic_to_rust(type_hint: str | None) -> str:
        mapping = {
            None: "f64",
            "Any": "f64",
            "Num": "f64",
            "Bool": "bool",
            "Str": "String",
            "Void": "()",
            "Fn": "f64",
        }
        return mapping.get(type_hint, "f64")

    @staticmethod
    def _normalize_decl_type(inferred: str) -> str:
        if inferred in {"f64", "i64", "bool", "String", "()", "Fn"}:
            return inferred
        return "f64"

    def _coerce(self, expr_src: str, from_ty: str, to_ty: str) -> str:
        if to_ty == from_ty:
            return expr_src

        if from_ty == "Fn" or to_ty == "Fn":
            return expr_src

        if to_ty == "f64" and from_ty == "i64":
            return f"({expr_src} as f64)"
        if to_ty == "i64" and from_ty == "f64":
            return f"({expr_src} as i64)"

        if to_ty == "f64" and from_ty == "bool":
            return f"(if {expr_src} {{ 1.0 }} else {{ 0.0 }})"
        if to_ty == "bool" and from_ty == "f64":
            return f"({expr_src} != 0.0)"
        if to_ty == "bool" and from_ty == "i64":
            return f"({expr_src} != 0)"

        if to_ty == "bool" and from_ty == "String":
            return f"(!{expr_src}.is_empty())"

        if to_ty == "String":
            return self._to_string_expr(expr_src, from_ty)

        return expr_src

    @staticmethod
    def _is_numeric(ty: str) -> bool:
        return ty in {"f64", "i64"}

    @staticmethod
    def _to_string_expr(expr_src: str, from_ty: str) -> str:
        if from_ty == "String":
            return expr_src
        if from_ty == "bool":
            return f"({expr_src}).to_string()"
        if from_ty in {"f64", "i64"}:
            return f"({expr_src}).to_string()"
        return f"format!(\"{{:?}}\", {expr_src})"

    @staticmethod
    def _default_value(rust_type: str) -> str:
        if rust_type == "bool":
            return "false"
        if rust_type == "String":
            return "String::new()"
        if rust_type == "()":
            return "()"
        if rust_type == "i64":
            return "0"
        return "0.0"

    @staticmethod
    def _render_number(value: object) -> str:
        if isinstance(value, bool):
            return "1.0" if value else "0.0"
        if isinstance(value, int):
            return f"{value}.0"
        if isinstance(value, float):
            text = f"{value}"
            if "." not in text:
                text += ".0"
            return text
        return "0.0"

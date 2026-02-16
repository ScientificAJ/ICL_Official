"""Top-level compiler orchestration for ICL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
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
    LiteralExpr,
    LoopStmt,
    MacroStmt,
    Program,
    ReturnStmt,
    Stmt,
    UnaryExpr,
)
from icl.expanders.base import ExpansionContext
from icl.expanders.js_backend import JavaScriptBackend
from icl.expanders.python_backend import PythonBackend
from icl.expanders.rust_backend import RustBackend
from icl.graph import IntentGraph, IntentGraphBuilder
from icl.lexer import Lexer
from icl.optimize import GraphOptimizer, OptimizationReport
from icl.parser import Parser
from icl.plugin import PluginManager, load_plugins
from icl.semantic import SemanticAnalyzer, SemanticResult
from icl.serialization import write_graph, write_source_map
from icl.source_map import SourceMap
from icl.tokens import Token


@dataclass
class CompileArtifacts:
    """Full compiler artifacts for debugging and downstream tooling."""

    tokens: list[Token]
    program: Program
    semantic: SemanticResult
    graph: IntentGraph
    source_map: SourceMap
    code: str
    optimization: OptimizationReport | None = None


def default_plugin_manager() -> PluginManager:
    """Create plugin manager with built-in backends."""
    manager = PluginManager()
    manager.register_backend("python", PythonBackend())
    manager.register_backend("js", JavaScriptBackend())
    manager.register_backend("rust", RustBackend())
    return manager


def build_plugin_manager(plugin_specs: list[str] | None = None) -> PluginManager:
    """Create default manager and apply optional plugin specs."""
    manager = default_plugin_manager()
    if plugin_specs:
        load_plugins(manager, plugin_specs)
    return manager


def compile_source(
    source: str,
    *,
    filename: str = "<input>",
    target: str = "python",
    plugin_manager: PluginManager | None = None,
    optimize: bool = False,
    debug: bool = False,
    emit_graph_path: str | Path | None = None,
    emit_sourcemap_path: str | Path | None = None,
) -> CompileArtifacts:
    """Compile source text into target code and intermediate artifacts."""
    manager = plugin_manager or default_plugin_manager()
    prepared_source = manager.preprocess_source(source)

    tokens = Lexer(prepared_source, filename=filename).tokenize()
    program = Parser(tokens).parse_program()
    program = manager.transform_program(program)
    program = manager.expand_macros(program)

    semantic = SemanticAnalyzer().analyze(program)

    graph_builder = IntentGraphBuilder()
    graph = graph_builder.build(program)
    source_map = graph_builder.source_map

    optimization_report: OptimizationReport | None = None
    if optimize:
        graph, optimization_report = GraphOptimizer().optimize(graph)

    backend = manager.get_backend(target)
    code = backend.emit_module(graph, ExpansionContext(target=target, debug=debug, metadata={"filename": filename}))

    if emit_graph_path is not None:
        write_graph(graph, emit_graph_path)
    if emit_sourcemap_path is not None:
        write_source_map(source_map, emit_sourcemap_path)

    return CompileArtifacts(
        tokens=tokens,
        program=program,
        semantic=semantic,
        graph=graph,
        source_map=source_map,
        code=code,
        optimization=optimization_report,
    )


def compile_file(
    input_path: str | Path,
    *,
    target: str,
    output_path: str | Path | None = None,
    plugin_manager: PluginManager | None = None,
    optimize: bool = False,
    debug: bool = False,
    emit_graph_path: str | Path | None = None,
    emit_sourcemap_path: str | Path | None = None,
) -> CompileArtifacts:
    """Compile an input `.icl` file."""
    path = Path(input_path)
    source = path.read_text(encoding="utf-8")
    artifacts = compile_source(
        source,
        filename=str(path),
        target=target,
        plugin_manager=plugin_manager,
        optimize=optimize,
        debug=debug,
        emit_graph_path=emit_graph_path,
        emit_sourcemap_path=emit_sourcemap_path,
    )

    if output_path is not None:
        Path(output_path).write_text(artifacts.code, encoding="utf-8")
    return artifacts


def check_source(
    source: str,
    *,
    filename: str = "<input>",
    plugin_manager: PluginManager | None = None,
) -> CompileArtifacts:
    """Run compiler pipeline through graph build without target emission selection."""
    return compile_source(source, filename=filename, target="python", plugin_manager=plugin_manager)


def explain_source(
    source: str,
    *,
    filename: str = "<input>",
    plugin_manager: PluginManager | None = None,
) -> dict[str, Any]:
    """Return a JSON-compatible explanation payload with AST + graph."""
    artifacts = compile_source(source, filename=filename, target="python", plugin_manager=plugin_manager)
    return {
        "ast": ast_to_dict(artifacts.program),
        "graph": artifacts.graph.to_dict(),
        "source_map": artifacts.source_map.to_dict(),
    }


def compress_source(source: str, *, filename: str = "<input>") -> str:
    """Canonical compact ICL pretty-printer for compression mode."""
    tokens = Lexer(source, filename=filename).tokenize()
    program = Parser(tokens).parse_program()
    return _emit_program_compact(program)


def _emit_program_compact(program: Program) -> str:
    return "\n".join(_emit_stmt_compact(stmt) for stmt in program.statements).strip() + "\n"


def _emit_stmt_compact(stmt: Stmt) -> str:
    if isinstance(stmt, AssignmentStmt):
        if stmt.type_hint:
            return f"{stmt.name}:{stmt.type_hint}:={_emit_expr_compact(stmt.value)}"
        return f"{stmt.name}:={_emit_expr_compact(stmt.value)}"

    if isinstance(stmt, ExpressionStmt):
        return _emit_expr_compact(stmt.expr)

    if isinstance(stmt, ReturnStmt):
        if stmt.value is None:
            return "ret"
        return f"ret {_emit_expr_compact(stmt.value)}"

    if isinstance(stmt, LoopStmt):
        body = ";".join(_emit_stmt_compact(item) for item in stmt.body)
        return f"loop {stmt.iterator} in {_emit_expr_compact(stmt.start)}..{_emit_expr_compact(stmt.end)}{{{body}}}"

    if isinstance(stmt, IfStmt):
        then_part = ";".join(_emit_stmt_compact(item) for item in stmt.then_block)
        else_part = ";".join(_emit_stmt_compact(item) for item in stmt.else_block)
        if else_part:
            return f"if {_emit_expr_compact(stmt.condition)}?{{{then_part}}}:{{{else_part}}}"
        return f"if {_emit_expr_compact(stmt.condition)}?{{{then_part}}}"

    if isinstance(stmt, FunctionDefStmt):
        params = ",".join(
            f"{p.name}:{p.type_hint}" if p.type_hint else p.name
            for p in stmt.params
        )
        suffix = f":{stmt.return_type}" if stmt.return_type else ""
        if stmt.expr_body is not None:
            return f"fn {stmt.name}({params}){suffix}=>{_emit_expr_compact(stmt.expr_body)}"
        body = ";".join(_emit_stmt_compact(item) for item in stmt.body)
        return f"fn {stmt.name}({params}){suffix}{{{body}}}"

    if isinstance(stmt, MacroStmt):
        args = ",".join(_emit_expr_compact(arg) for arg in stmt.args)
        return f"#{stmt.name}({args})"

    return "/*unsupported*/"


def _emit_expr_compact(expr: Expr) -> str:
    if isinstance(expr, LiteralExpr):
        if isinstance(expr.value, bool):
            return "true" if expr.value else "false"
        if isinstance(expr.value, str):
            return f'"{expr.value}"'
        return str(expr.value)

    if isinstance(expr, IdentifierExpr):
        return expr.name

    if isinstance(expr, UnaryExpr):
        return f"{expr.operator}{_emit_expr_compact(expr.operand)}"

    if isinstance(expr, BinaryExpr):
        return f"({_emit_expr_compact(expr.left)}{expr.operator}{_emit_expr_compact(expr.right)})"

    if isinstance(expr, CallExpr):
        callee = _emit_expr_compact(expr.callee)
        prefix = "@" if expr.at_prefixed and isinstance(expr.callee, IdentifierExpr) else ""
        args = ",".join(_emit_expr_compact(arg) for arg in expr.args)
        return f"{prefix}{callee}({args})"

    return "?"


def ast_to_dict(node: Any) -> Any:
    """Serialize AST dataclasses recursively into JSON-compatible dicts."""
    if isinstance(node, list):
        return [ast_to_dict(item) for item in node]
    if hasattr(node, "__dataclass_fields__"):
        payload = asdict(node)
        payload["node_type"] = type(node).__name__
        return payload
    return node

if __name__ == "__main__":
    from icl.cli import run

    raise SystemExit(run())

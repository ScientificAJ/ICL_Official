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
from icl.graph import IntentGraph, IntentGraphBuilder
from icl.ir import IRBuilder, IRModule, ir_to_dict
from icl.language_pack import EmissionContext, OutputBundle, PackRegistry, load_pack_specs
from icl.lexer import Lexer
from icl.lowering import LoweredModule, Lowerer, lowered_to_dict, lowered_to_graph
from icl.optimize import GraphOptimizer, OptimizationReport
from icl.packs import build_builtin_pack_registry
from icl.parser import Parser
from icl.plugin import PluginManager, load_plugins
from icl.scaffolder import scaffold_output, write_bundle
from icl.semantic import SemanticAnalyzer, SemanticResult
from icl.serialization import write_graph, write_source_map
from icl.source_map import SourceMap
from icl.tokens import Token


@dataclass
class FrontendArtifacts:
    """Pipeline output from source through semantic analysis."""

    tokens: list[Token]
    program: Program
    semantic: SemanticResult
    ir: IRModule
    source_map: SourceMap


@dataclass
class TargetArtifacts:
    """Single-target lowering, emission, and scaffolding output."""

    target: str
    lowered: LoweredModule
    graph: IntentGraph
    code: str
    bundle: OutputBundle
    optimization: OptimizationReport | None = None


@dataclass
class CompileArtifacts:
    """Full compiler artifacts for debugging and downstream tooling."""

    tokens: list[Token]
    program: Program
    semantic: SemanticResult
    ir: IRModule
    lowered: LoweredModule
    graph: IntentGraph
    source_map: SourceMap
    code: str
    bundle: OutputBundle
    optimization: OptimizationReport | None = None


@dataclass
class MultiTargetArtifacts:
    """Shared frontend + many target emissions from one source."""

    tokens: list[Token]
    program: Program
    semantic: SemanticResult
    ir: IRModule
    source_map: SourceMap
    targets: dict[str, TargetArtifacts]


def default_plugin_manager() -> PluginManager:
    """Create plugin manager with built-in backends."""
    manager = PluginManager()
    # Backend registrations remain for backward-compatible plugin extensibility.
    from icl.expanders.js_backend import JavaScriptBackend
    from icl.expanders.python_backend import PythonBackend
    from icl.expanders.rust_backend import RustBackend

    manager.register_backend("python", PythonBackend())
    manager.register_backend("js", JavaScriptBackend())
    manager.register_backend("rust", RustBackend())
    return manager


def default_pack_registry() -> PackRegistry:
    """Create registry with built-in stable + experimental packs."""
    return build_builtin_pack_registry()


def build_plugin_manager(plugin_specs: list[str] | None = None) -> PluginManager:
    """Create default plugin manager and apply plugin specs."""
    manager = default_plugin_manager()
    if plugin_specs:
        load_plugins(manager, plugin_specs)
    return manager


def build_pack_registry(pack_specs: list[str] | None = None) -> PackRegistry:
    """Create default pack registry and apply custom pack specs."""
    registry = default_pack_registry()
    if pack_specs:
        load_pack_specs(registry, pack_specs)
    return registry


def compile_source(
    source: str,
    *,
    filename: str = "<input>",
    target: str = "python",
    plugin_manager: PluginManager | None = None,
    plugin_specs: list[str] | None = None,
    pack_registry: PackRegistry | None = None,
    pack_specs: list[str] | None = None,
    optimize: bool = False,
    debug: bool = False,
    emit_graph_path: str | Path | None = None,
    emit_sourcemap_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> CompileArtifacts:
    """Compile source text into one target using v2 frontend + lowering pipeline."""

    multi = compile_targets(
        source,
        filename=filename,
        targets=[target],
        plugin_manager=plugin_manager,
        plugin_specs=plugin_specs,
        pack_registry=pack_registry,
        pack_specs=pack_specs,
        optimize=optimize,
        debug=debug,
    )

    target_artifacts = multi.targets[target]

    if emit_graph_path is not None:
        write_graph(target_artifacts.graph, emit_graph_path)
    if emit_sourcemap_path is not None:
        write_source_map(multi.source_map, emit_sourcemap_path)

    if output_path is not None:
        write_bundle(target_artifacts.bundle, output_path)

    return CompileArtifacts(
        tokens=multi.tokens,
        program=multi.program,
        semantic=multi.semantic,
        ir=multi.ir,
        lowered=target_artifacts.lowered,
        graph=target_artifacts.graph,
        source_map=multi.source_map,
        code=target_artifacts.code,
        bundle=target_artifacts.bundle,
        optimization=target_artifacts.optimization,
    )


def compile_targets(
    source: str,
    *,
    filename: str = "<input>",
    targets: list[str],
    plugin_manager: PluginManager | None = None,
    plugin_specs: list[str] | None = None,
    pack_registry: PackRegistry | None = None,
    pack_specs: list[str] | None = None,
    optimize: bool = False,
    debug: bool = False,
) -> MultiTargetArtifacts:
    """Compile source once and emit for multiple targets."""

    manager = plugin_manager or build_plugin_manager(plugin_specs)
    registry = pack_registry or build_pack_registry(pack_specs)

    frontend = _run_frontend(source, filename=filename, plugin_manager=manager)

    target_results: dict[str, TargetArtifacts] = {}
    lowerer = Lowerer()
    for target in targets:
        pack = registry.get(target)
        lowered = lowerer.lower(
            frontend.ir,
            target=pack.manifest.target,
            feature_coverage=pack.manifest.feature_coverage,
        )

        graph = lowered_to_graph(lowered)
        optimization_report: OptimizationReport | None = None
        if optimize:
            graph, optimization_report = GraphOptimizer().optimize(graph)

        code = pack.emit(
            lowered,
            EmissionContext(
                target=pack.manifest.target,
                debug=debug,
                metadata={"filename": filename, "source_target": target},
            ),
        )
        bundle = scaffold_output(pack, code, target=pack.manifest.target, debug=debug)

        target_results[target] = TargetArtifacts(
            target=target,
            lowered=lowered,
            graph=graph,
            code=bundle.code,
            bundle=bundle,
            optimization=optimization_report,
        )

    return MultiTargetArtifacts(
        tokens=frontend.tokens,
        program=frontend.program,
        semantic=frontend.semantic,
        ir=frontend.ir,
        source_map=frontend.source_map,
        targets=target_results,
    )


def compile_file(
    input_path: str | Path,
    *,
    target: str,
    output_path: str | Path | None = None,
    plugin_manager: PluginManager | None = None,
    plugin_specs: list[str] | None = None,
    pack_registry: PackRegistry | None = None,
    pack_specs: list[str] | None = None,
    optimize: bool = False,
    debug: bool = False,
    emit_graph_path: str | Path | None = None,
    emit_sourcemap_path: str | Path | None = None,
) -> CompileArtifacts:
    """Compile an input `.icl` file for one target."""
    path = Path(input_path)
    source = path.read_text(encoding="utf-8")
    return compile_source(
        source,
        filename=str(path),
        target=target,
        output_path=output_path,
        plugin_manager=plugin_manager,
        plugin_specs=plugin_specs,
        pack_registry=pack_registry,
        pack_specs=pack_specs,
        optimize=optimize,
        debug=debug,
        emit_graph_path=emit_graph_path,
        emit_sourcemap_path=emit_sourcemap_path,
    )


def check_source(
    source: str,
    *,
    filename: str = "<input>",
    plugin_manager: PluginManager | None = None,
    plugin_specs: list[str] | None = None,
    pack_registry: PackRegistry | None = None,
) -> CompileArtifacts:
    """Run compiler pipeline through lowering for default python target."""
    return compile_source(
        source,
        filename=filename,
        target="python",
        plugin_manager=plugin_manager,
        plugin_specs=plugin_specs,
        pack_registry=pack_registry,
        optimize=False,
        debug=False,
    )


def explain_source(
    source: str,
    *,
    filename: str = "<input>",
    target: str = "python",
    plugin_manager: PluginManager | None = None,
    plugin_specs: list[str] | None = None,
    pack_registry: PackRegistry | None = None,
    pack_specs: list[str] | None = None,
) -> dict[str, Any]:
    """Return a JSON-compatible explanation payload with AST, IR, and graphs."""

    artifacts = compile_source(
        source,
        filename=filename,
        target=target,
        plugin_manager=plugin_manager,
        plugin_specs=plugin_specs,
        pack_registry=pack_registry,
        pack_specs=pack_specs,
        optimize=False,
        debug=False,
    )

    return {
        "ast": ast_to_dict(artifacts.program),
        "ir": ir_to_dict(artifacts.ir),
        "lowered": lowered_to_dict(artifacts.lowered),
        "graph": artifacts.graph.to_dict(),
        "source_map": artifacts.source_map.to_dict(),
    }


def compress_source(source: str, *, filename: str = "<input>") -> str:
    """Canonical compact ICL pretty-printer for compression mode."""
    tokens = Lexer(source, filename=filename).tokenize()
    program = Parser(tokens).parse_program()
    return _emit_program_compact(program)


def _run_frontend(source: str, *, filename: str, plugin_manager: PluginManager) -> FrontendArtifacts:
    prepared_source = plugin_manager.preprocess_source(source)

    tokens = Lexer(prepared_source, filename=filename).tokenize()
    program = Parser(tokens).parse_program()
    program = plugin_manager.transform_program(program)
    program = plugin_manager.expand_macros(program)

    semantic = SemanticAnalyzer().analyze(program)

    graph_builder = IntentGraphBuilder()
    graph_builder.build(program)
    source_map = graph_builder.source_map

    ir = IRBuilder(semantic).build(program)

    return FrontendArtifacts(tokens=tokens, program=program, semantic=semantic, ir=ir, source_map=source_map)


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
        params = ",".join(f"{p.name}:{p.type_hint}" if p.type_hint else p.name for p in stmt.params)
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
    if hasattr(node, "to_dict"):
        try:
            return node.to_dict()
        except TypeError:
            pass
    if hasattr(node, "__dataclass_fields__"):
        payload = asdict(node)
        payload["node_type"] = type(node).__name__
        return payload
    return node


if __name__ == "__main__":
    from icl.cli import run

    raise SystemExit(run())

"""Machine-oriented service layer for ICL integrations.

This module provides a stable request/response API used by HTTP and stdio
adapters so non-human clients can call compiler capabilities deterministically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from icl.errors import CLIError, CompilerError
from icl.graph import IntentGraph, diff_graphs
from icl.main import build_plugin_manager, compile_source, compress_source, explain_source
from icl.serialization import graph_from_json


def compile_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile source payload into target code and optional artifacts."""
    source, filename = _resolve_source_payload(payload)
    target = str(payload.get("target", "python"))
    optimize = bool(payload.get("optimize", False))
    debug = bool(payload.get("debug", False))
    include_graph = bool(payload.get("include_graph", False))
    include_source_map = bool(payload.get("include_source_map", False))
    plugins = _normalize_plugins(payload.get("plugins"))

    manager = build_plugin_manager(plugins)
    artifacts = compile_source(
        source,
        filename=filename,
        target=target,
        plugin_manager=manager,
        optimize=optimize,
        debug=debug,
    )

    result: dict[str, Any] = {
        "target": target,
        "code": artifacts.code,
        "metrics": {
            "tokens": len(artifacts.tokens),
            "nodes": len(artifacts.graph.nodes),
            "edges": len(artifacts.graph.edges),
        },
    }
    if include_graph:
        result["graph"] = artifacts.graph.to_dict()
    if include_source_map:
        result["source_map"] = artifacts.source_map.to_dict()
    if artifacts.optimization is not None:
        result["optimization"] = {
            "folded_operations": artifacts.optimization.folded_operations,
            "removed_assignments": artifacts.optimization.removed_assignments,
            "notes": artifacts.optimization.notes,
        }
    return result


def check_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate source payload via parse + semantic phases."""
    source, filename = _resolve_source_payload(payload)
    plugins = _normalize_plugins(payload.get("plugins"))

    manager = build_plugin_manager(plugins)
    artifacts = compile_source(source, filename=filename, target="python", plugin_manager=manager)

    return {
        "ok": True,
        "metrics": {
            "tokens": len(artifacts.tokens),
            "nodes": len(artifacts.graph.nodes),
            "edges": len(artifacts.graph.edges),
        },
    }


def explain_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Return AST, graph, and source map for given payload."""
    source, filename = _resolve_source_payload(payload)
    plugins = _normalize_plugins(payload.get("plugins"))

    manager = build_plugin_manager(plugins)
    return explain_source(source, filename=filename, plugin_manager=manager)


def compress_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Return canonical compact form for source payload."""
    source, filename = _resolve_source_payload(payload)
    return {
        "compressed": compress_source(source, filename=filename),
    }


def diff_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Return structural diff between two graphs."""
    before_graph = _resolve_graph(payload, key_prefix="before")
    after_graph = _resolve_graph(payload, key_prefix="after")
    diff = diff_graphs(before_graph, after_graph)
    return {
        "added_nodes": diff.added_nodes,
        "removed_nodes": diff.removed_nodes,
        "changed_nodes": diff.changed_nodes,
        "added_edges": diff.added_edges,
        "removed_edges": diff.removed_edges,
    }


def capabilities_request(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return service capability metadata for automation clients."""
    manager = build_plugin_manager([])
    return {
        "service": "icl",
        "version": "0.1.0",
        "methods": ["compile", "check", "explain", "compress", "diff", "capabilities"],
        "targets": manager.available_backends(),
    }


_METHODS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "compile": compile_request,
    "check": check_request,
    "explain": explain_request,
    "compress": compress_request,
    "diff": diff_request,
    "capabilities": capabilities_request,
}


def dispatch(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dispatch a method call for integration adapters."""
    fn = _METHODS.get(method)
    if fn is None:
        raise CLIError(
            code="SRV001",
            message=f"Unknown service method '{method}'.",
            span=None,
            hint=f"Available methods: {', '.join(sorted(_METHODS.keys()))}",
        )
    return fn(payload or {})


def _resolve_source_payload(payload: dict[str, Any]) -> tuple[str, str]:
    source = payload.get("source")
    input_path = payload.get("input_path")

    if source is not None and input_path is not None:
        raise CLIError(
            code="SRV002",
            message="Provide only one of 'source' or 'input_path'.",
            span=None,
            hint="Use inline source for API calls or file path for local source files.",
        )

    if input_path is not None:
        path = Path(str(input_path))
        try:
            return path.read_text(encoding="utf-8"), str(path)
        except FileNotFoundError as exc:
            raise CLIError(
                code="SRV003",
                message=f"Input file not found: {path}",
                span=None,
                hint="Check input_path and file permissions.",
            ) from exc

    if source is not None:
        return str(source), str(payload.get("filename", "<inline>"))

    raise CLIError(
        code="SRV004",
        message="Missing source input.",
        span=None,
        hint="Provide 'source' or 'input_path'.",
    )


def _resolve_graph(payload: dict[str, Any], key_prefix: str) -> IntentGraph:
    graph_obj = payload.get(f"{key_prefix}_graph")
    graph_path = payload.get(f"{key_prefix}_path")

    if graph_obj is not None and graph_path is not None:
        raise CLIError(
            code="SRV005",
            message=f"Provide only one of '{key_prefix}_graph' or '{key_prefix}_path'.",
            span=None,
            hint="Pass serialized graph object or file path, not both.",
        )

    if graph_obj is not None:
        if not isinstance(graph_obj, dict):
            raise CLIError(
                code="SRV006",
                message=f"'{key_prefix}_graph' must be a JSON object.",
                span=None,
                hint="Use graph.to_dict() payload format.",
            )
        return IntentGraph.from_dict(graph_obj)

    if graph_path is not None:
        path = Path(str(graph_path))
        try:
            payload_text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise CLIError(
                code="SRV007",
                message=f"Graph file not found: {path}",
                span=None,
                hint="Check graph path and file permissions.",
            ) from exc
        return graph_from_json(payload_text)

    raise CLIError(
        code="SRV008",
        message=f"Missing graph input for '{key_prefix}'.",
        span=None,
        hint=f"Provide '{key_prefix}_graph' or '{key_prefix}_path'.",
    )


def _normalize_plugins(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            normalized.append(str(item))
        return normalized
    raise CLIError(
        code="SRV009",
        message="'plugins' must be a string or list of strings.",
        span=None,
        hint="Use plugins: ['module:register']",
    )


def safe_dispatch(method: str, payload: dict[str, Any] | None = None) -> tuple[bool, dict[str, Any]]:
    """Dispatch method and normalize errors for integration transport layers."""
    try:
        return True, dispatch(method, payload)
    except CompilerError as err:
        return False, {"error": err.to_diagnostic().to_dict()}
    except Exception as err:  # pragma: no cover - defensive fallback
        return False, {
            "error": {
                "code": "SRV999",
                "message": f"Internal service error: {err}",
                "hint": "Inspect server logs for details.",
            }
        }

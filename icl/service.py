"""Machine-oriented service layer for ICL integrations.

This module provides a stable request/response API used by HTTP and stdio
adapters so non-human clients can call compiler capabilities deterministically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from icl.errors import CLIError, CompilerError
from icl.graph import IntentGraph, diff_graphs
from icl.main import (
    build_pack_registry,
    build_plugin_manager,
    compile_source,
    compile_targets,
    compress_source,
    default_pack_registry,
    explain_source,
)
from icl.serialization import graph_from_json


def compile_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile source payload into target code and optional artifacts."""
    source, filename = _resolve_source_payload(payload)
    targets = _resolve_targets(payload)

    optimize = bool(payload.get("optimize", False))
    debug = bool(payload.get("debug", False))
    include_graph = bool(payload.get("include_graph", False))
    include_source_map = bool(payload.get("include_source_map", False))
    include_ir = bool(payload.get("include_ir", False))
    include_lowered = bool(payload.get("include_lowered", False))
    include_bundle = bool(payload.get("include_bundle", False))
    plugins = _normalize_plugins(payload.get("plugins"))
    packs = _normalize_plugins(payload.get("packs"))

    manager = build_plugin_manager(plugins)
    pack_registry = build_pack_registry(packs)

    multi = compile_targets(
        source,
        filename=filename,
        targets=targets,
        plugin_manager=manager,
        pack_registry=pack_registry,
        optimize=optimize,
        debug=debug,
    )

    if len(targets) == 1:
        target = targets[0]
        emitted = multi.targets[target]
        result: dict[str, Any] = {
            "target": target,
            "code": emitted.code,
            "metrics": {
                "tokens": len(multi.tokens),
                "nodes": len(emitted.graph.nodes),
                "edges": len(emitted.graph.edges),
            },
        }
        if include_graph:
            result["graph"] = emitted.graph.to_dict()
        if include_source_map:
            result["source_map"] = multi.source_map.to_dict()
        if include_ir:
            from icl.ir import ir_to_dict

            result["ir"] = ir_to_dict(multi.ir)
        if include_lowered:
            from icl.lowering import lowered_to_dict

            result["lowered"] = lowered_to_dict(emitted.lowered)
        if include_bundle:
            result["bundle"] = {
                "primary_path": emitted.bundle.primary_path,
                "files": emitted.bundle.files,
            }
        if emitted.optimization is not None:
            result["optimization"] = {
                "folded_operations": emitted.optimization.folded_operations,
                "removed_assignments": emitted.optimization.removed_assignments,
                "notes": emitted.optimization.notes,
            }
        return result

    outputs: dict[str, Any] = {}
    for target in targets:
        emitted = multi.targets[target]
        payload_item: dict[str, Any] = {
            "code": emitted.code,
            "metrics": {
                "nodes": len(emitted.graph.nodes),
                "edges": len(emitted.graph.edges),
            },
            "bundle": {
                "primary_path": emitted.bundle.primary_path,
                "files": emitted.bundle.files,
            },
        }
        if include_graph:
            payload_item["graph"] = emitted.graph.to_dict()
        if include_lowered:
            from icl.lowering import lowered_to_dict

            payload_item["lowered"] = lowered_to_dict(emitted.lowered)
        if emitted.optimization is not None:
            payload_item["optimization"] = {
                "folded_operations": emitted.optimization.folded_operations,
                "removed_assignments": emitted.optimization.removed_assignments,
                "notes": emitted.optimization.notes,
            }
        outputs[target] = payload_item

    response: dict[str, Any] = {
        "targets": targets,
        "outputs": outputs,
        "metrics": {
            "tokens": len(multi.tokens),
        },
    }
    if include_source_map:
        response["source_map"] = multi.source_map.to_dict()
    if include_ir:
        from icl.ir import ir_to_dict

        response["ir"] = ir_to_dict(multi.ir)
    return response


def check_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate source payload via parse + semantic phases."""
    source, filename = _resolve_source_payload(payload)
    plugins = _normalize_plugins(payload.get("plugins"))
    packs = _normalize_plugins(payload.get("packs"))

    artifacts = compile_source(
        source,
        filename=filename,
        target="python",
        plugin_specs=plugins,
        pack_specs=packs,
    )

    return {
        "ok": True,
        "metrics": {
            "tokens": len(artifacts.tokens),
            "nodes": len(artifacts.graph.nodes),
            "edges": len(artifacts.graph.edges),
        },
    }


def explain_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Return AST, IR, lowered, graph, and source map for given payload."""
    source, filename = _resolve_source_payload(payload)
    plugins = _normalize_plugins(payload.get("plugins"))
    packs = _normalize_plugins(payload.get("packs"))
    target = str(payload.get("target", "python"))

    manager = build_plugin_manager(plugins)
    pack_registry = build_pack_registry(packs)
    return explain_source(source, filename=filename, target=target, plugin_manager=manager, pack_registry=pack_registry)


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
    registry = default_pack_registry()
    return {
        "service": "icl",
        "version": "2.0.0",
        "methods": [
            "compile",
            "check",
            "explain",
            "compress",
            "diff",
            "capabilities",
        ],
        "targets": registry.targets(stability="stable"),
        "experimental_targets": sorted(
            target
            for target in registry.targets(stability="experimental")
            if target not in registry.targets(stability="stable")
        ),
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


def _resolve_targets(payload: dict[str, Any]) -> list[str]:
    target = payload.get("target")
    targets = payload.get("targets")

    if target is not None and targets is not None:
        raise CLIError(
            code="SRV010",
            message="Provide only one of 'target' or 'targets'.",
            span=None,
            hint="Use target for single output, targets for multi-target compile.",
        )

    if targets is not None:
        if not isinstance(targets, list):
            raise CLIError(
                code="SRV011",
                message="'targets' must be a list of target names.",
                span=None,
                hint="Example: targets=['python','js']",
            )
        normalized = [str(item) for item in targets if str(item).strip()]
        if not normalized:
            raise CLIError(
                code="SRV012",
                message="'targets' cannot be empty.",
                span=None,
                hint="Provide at least one target.",
            )
        return normalized

    if target is not None:
        normalized_target = str(target).strip()
        if not normalized_target:
            raise CLIError(code="SRV013", message="'target' cannot be empty.", span=None, hint="Set target value.")
        return [normalized_target]

    return ["python"]


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
        message="'plugins'/'packs' must be a string or list of strings.",
        span=None,
        hint="Use ['module:register']",
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

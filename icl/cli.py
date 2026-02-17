"""Command-line interface for the ICL compiler."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from icl.contract_tests import run_contract_suite
from icl.errors import CompilerError, Diagnostic, format_diagnostic
from icl.graph import IntentGraph, diff_graphs
from icl.main import (
    build_pack_registry,
    build_plugin_manager,
    compile_file,
    compile_source,
    compile_targets,
    compress_source,
    explain_source,
)
from icl.scaffolder import write_bundle
from icl.serialization import graph_from_json


def build_parser() -> argparse.ArgumentParser:
    """Build argparse command tree for ICL CLI."""
    parser = argparse.ArgumentParser(prog="icl", description="ICL compiler and tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="Compile ICL source to one or many target languages")
    compile_parser.add_argument("input", nargs="?", help="Input .icl file")
    compile_parser.add_argument("--code", help="Inline ICL source string")
    compile_parser.add_argument("--target", help="Single target backend name (e.g. python/js/rust/web)")
    compile_parser.add_argument(
        "--targets",
        action="append",
        default=[],
        help="Target backend list (repeatable or comma-separated): --targets python,js --targets rust",
    )
    compile_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )
    compile_parser.add_argument(
        "--pack",
        action="append",
        default=[],
        help="Custom language pack spec in module[:symbol] format; can be repeated.",
    )
    compile_parser.add_argument("-o", "--output", help="Output file path (single target) or directory (multi-target)")
    compile_parser.add_argument("--emit-graph", help="Write intent graph JSON (single target only)")
    compile_parser.add_argument("--emit-sourcemap", help="Write source map JSON")
    compile_parser.add_argument("--optimize", action="store_true", help="Enable graph optimizations")
    compile_parser.add_argument("--debug", action="store_true", help="Emit debug info to stderr")
    compile_parser.add_argument("--natural", action="store_true", help="Enable natural alias normalization.")
    compile_parser.add_argument(
        "--alias-mode",
        choices=["core", "extended"],
        default="core",
        help="Alias normalization mode when --natural is set.",
    )

    check_parser = subparsers.add_parser("check", help="Validate source through semantic analysis")
    check_parser.add_argument("input", nargs="?", help="Input .icl file")
    check_parser.add_argument("--code", help="Inline ICL source string")
    check_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )
    check_parser.add_argument("--natural", action="store_true", help="Enable natural alias normalization.")
    check_parser.add_argument(
        "--alias-mode",
        choices=["core", "extended"],
        default="core",
        help="Alias normalization mode when --natural is set.",
    )

    explain_parser = subparsers.add_parser("explain", help="Print AST + IR + lowered + Intent Graph JSON")
    explain_parser.add_argument("input", nargs="?", help="Input .icl file")
    explain_parser.add_argument("--code", help="Inline ICL source string")
    explain_parser.add_argument("--target", default="python", help="Target for lowering preview")
    explain_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )
    explain_parser.add_argument(
        "--pack",
        action="append",
        default=[],
        help="Custom language pack spec in module[:symbol] format; can be repeated.",
    )
    explain_parser.add_argument("--natural", action="store_true", help="Enable natural alias normalization.")
    explain_parser.add_argument(
        "--alias-mode",
        choices=["core", "extended"],
        default="core",
        help="Alias normalization mode when --natural is set.",
    )
    explain_parser.add_argument("--alias-trace", action="store_true", help="Include applied alias replacements.")

    compress_parser = subparsers.add_parser("compress", help="Print canonical compact ICL encoding")
    compress_parser.add_argument("input", nargs="?", help="Input .icl file")
    compress_parser.add_argument("--code", help="Inline ICL source string")

    diff_parser = subparsers.add_parser("diff", help="Diff two serialized Intent Graph JSON files")
    diff_parser.add_argument("before", help="Path to previous graph JSON")
    diff_parser.add_argument("after", help="Path to next graph JSON")

    pack_parser = subparsers.add_parser("pack", help="Manage language packs")
    pack_subparsers = pack_parser.add_subparsers(dest="pack_command", required=True)

    pack_list_parser = pack_subparsers.add_parser("list", help="List available language packs")
    pack_list_parser.add_argument("--stability", choices=["stable", "beta", "experimental"], help="Filter by stability")
    pack_list_parser.add_argument(
        "--pack",
        action="append",
        default=[],
        help="Custom language pack spec in module[:symbol] format; can be repeated.",
    )

    pack_validate_parser = pack_subparsers.add_parser("validate", help="Validate pack manifests")
    pack_validate_parser.add_argument("--target", help="Validate a single pack target")
    pack_validate_parser.add_argument(
        "--pack",
        action="append",
        default=[],
        help="Custom language pack spec in module[:symbol] format; can be repeated.",
    )

    contract_parser = subparsers.add_parser("contract", help="Run language contract test suite")
    contract_subparsers = contract_parser.add_subparsers(dest="contract_command", required=True)

    contract_test_parser = contract_subparsers.add_parser("test", help="Run canonical contract compile checks")
    contract_test_parser.add_argument("--target", action="append", default=[], help="Target to test (repeatable)")
    contract_test_parser.add_argument("--all", action="store_true", help="Include experimental targets")
    contract_test_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )
    contract_test_parser.add_argument(
        "--pack",
        action="append",
        default=[],
        help="Custom language pack spec in module[:symbol] format; can be repeated.",
    )

    alias_parser = subparsers.add_parser("alias", help="Inspect natural alias mapping catalog")
    alias_subparsers = alias_parser.add_subparsers(dest="alias_command", required=True)
    alias_list_parser = alias_subparsers.add_parser("list", help="List natural alias mappings")
    alias_list_parser.add_argument("--mode", choices=["core", "extended"], default="core", help="Alias mode view")
    alias_list_parser.add_argument("--json", action="store_true", help="Emit JSON payload")

    serve_parser = subparsers.add_parser("serve", help="Run HTTP API server for AI/tool integrations")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    serve_parser.add_argument("--port", type=int, default=8080, help="Bind port")

    subparsers.add_parser("agent", help="Run stdio JSON adapter for AI/tool integrations")
    mcp_parser = subparsers.add_parser("mcp", help="Run MCP stdio server")
    mcp_parser.add_argument("--root", help="Allowed root directory for MCP file path operations")

    return parser


def run(argv: list[str] | None = None) -> int:
    """Run CLI and return shell exit code."""
    args = build_parser().parse_args(argv)

    try:
        if args.command == "compile":
            source, filename = _resolve_source(args.input, args.code)
            if args.input and args.code:
                raise argparse.ArgumentTypeError("Provide either file input or --code, not both.")

            targets = _resolve_compile_targets(args.target, args.targets)
            manager = build_plugin_manager(
                args.plugin,
                natural_aliases=args.natural,
                alias_mode=args.alias_mode,
            )
            pack_registry = build_pack_registry(args.pack)

            if len(targets) == 1:
                target = targets[0]
                if args.input:
                    artifacts = compile_file(
                        args.input,
                        target=target,
                        output_path=args.output,
                        plugin_manager=manager,
                        pack_registry=pack_registry,
                        optimize=args.optimize,
                        debug=args.debug,
                        emit_graph_path=args.emit_graph,
                        emit_sourcemap_path=args.emit_sourcemap,
                    )
                else:
                    artifacts = compile_source(
                        source,
                        filename=filename,
                        target=target,
                        plugin_manager=manager,
                        pack_registry=pack_registry,
                        optimize=args.optimize,
                        debug=args.debug,
                        emit_graph_path=args.emit_graph,
                        emit_sourcemap_path=args.emit_sourcemap,
                        output_path=args.output,
                    )

                if args.debug:
                    token_count = len(artifacts.tokens)
                    node_count = len(artifacts.graph.nodes)
                    edge_count = len(artifacts.graph.edges)
                    print(
                        f"debug: tokens={token_count} nodes={node_count} edges={edge_count}",
                        file=sys.stderr,
                    )
                    if artifacts.optimization is not None:
                        print(
                            "debug: folded="
                            f"{artifacts.optimization.folded_operations} "
                            f"dead_assignments={artifacts.optimization.removed_assignments}",
                            file=sys.stderr,
                        )

                if not args.output:
                    sys.stdout.write(artifacts.code)
                return 0

            if args.emit_graph:
                raise argparse.ArgumentTypeError("--emit-graph supports single target only.")

            multi = compile_targets(
                source,
                filename=filename,
                targets=targets,
                plugin_manager=manager,
                pack_registry=pack_registry,
                optimize=args.optimize,
                debug=args.debug,
            )

            if args.emit_sourcemap:
                Path(args.emit_sourcemap).write_text(
                    json.dumps(multi.source_map.to_dict(), indent=2, sort_keys=True),
                    encoding="utf-8",
                )

            if args.output:
                out_dir = Path(args.output)
                out_dir.mkdir(parents=True, exist_ok=True)
                for target in targets:
                    target_dir = out_dir / target
                    write_bundle(multi.targets[target].bundle, target_dir)
                if args.debug:
                    print(f"debug: wrote multi-target outputs to {out_dir}", file=sys.stderr)
            else:
                payload = {
                    target: {
                        "primary_path": multi.targets[target].bundle.primary_path,
                        "files": multi.targets[target].bundle.files,
                    }
                    for target in targets
                }
                print(json.dumps(payload, indent=2, sort_keys=True))

            return 0

        if args.command == "check":
            source, filename = _resolve_source(args.input, args.code)
            manager = build_plugin_manager(
                args.plugin,
                natural_aliases=args.natural,
                alias_mode=args.alias_mode,
            )
            compile_source(source, filename=filename, target="python", plugin_manager=manager)
            print("OK")
            return 0

        if args.command == "explain":
            source, filename = _resolve_source(args.input, args.code)
            manager = build_plugin_manager(
                args.plugin,
                natural_aliases=args.natural,
                alias_mode=args.alias_mode,
            )
            registry = build_pack_registry(args.pack)
            payload = explain_source(
                source,
                filename=filename,
                target=args.target,
                plugin_manager=manager,
                pack_registry=registry,
            )
            if args.alias_trace:
                payload["alias_trace"] = _alias_trace_from_metadata(manager.metadata_snapshot())
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        if args.command == "compress":
            source, filename = _resolve_source(args.input, args.code)
            print(compress_source(source, filename=filename), end="")
            return 0

        if args.command == "diff":
            before_graph = _load_graph(Path(args.before))
            after_graph = _load_graph(Path(args.after))
            diff = diff_graphs(before_graph, after_graph)
            print(
                json.dumps(
                    {
                        "added_nodes": diff.added_nodes,
                        "removed_nodes": diff.removed_nodes,
                        "changed_nodes": diff.changed_nodes,
                        "added_edges": diff.added_edges,
                        "removed_edges": diff.removed_edges,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "pack":
            registry = build_pack_registry(getattr(args, "pack", []))

            if args.pack_command == "list":
                manifests = registry.manifests(stability=args.stability)
                payload = [manifest.to_dict() for manifest in manifests]
                print(json.dumps(payload, indent=2, sort_keys=True))
                return 0

            if args.pack_command == "validate":
                results = registry.validate(target=args.target)
                payload = [
                    {"target": result.target, "ok": result.ok, "errors": result.errors}
                    for result in results
                ]
                print(json.dumps(payload, indent=2, sort_keys=True))
                return 0 if all(item["ok"] for item in payload) else 1

            raise argparse.ArgumentTypeError(f"Unsupported pack command '{args.pack_command}'.")

        if args.command == "contract":
            if args.contract_command == "test":
                registry = build_pack_registry(args.pack)
                report = run_contract_suite(
                    targets=args.target or None,
                    stable_only=not args.all,
                    plugin_specs=args.plugin,
                    registry=registry,
                )
                print(json.dumps(report, indent=2, sort_keys=True))

                return 0 if report.get("ok", False) else 1

            raise argparse.ArgumentTypeError(f"Unsupported contract command '{args.contract_command}'.")

        if args.command == "alias":
            from icl.alias_map import alias_catalog

            if args.alias_command == "list":
                catalog = alias_catalog(args.mode)
                if args.json:
                    print(json.dumps(catalog, indent=2, sort_keys=True))
                else:
                    for entry in catalog:
                        aliases = ", ".join(entry["aliases"])
                        print(
                            f"{entry['canonical']:<8} [{entry['category']}] {entry['description']} | aliases: {aliases}"
                        )
                return 0

            raise argparse.ArgumentTypeError(f"Unsupported alias command '{args.alias_command}'.")

        if args.command == "serve":
            from icl.api_server import run_http_api

            return run_http_api(host=args.host, port=args.port)

        if args.command == "agent":
            from icl.agent_stdio import run_stdio

            return run_stdio()

        if args.command == "mcp":
            from icl.mcp_server import run as run_mcp

            mcp_args: list[str] = []
            if args.root:
                mcp_args.extend(["--root", args.root])
            return run_mcp(mcp_args)

        raise argparse.ArgumentTypeError(f"Unsupported command '{args.command}'.")

    except CompilerError as err:
        diag = err.to_diagnostic()
        print(format_diagnostic(diag), file=sys.stderr)
        return 1
    except argparse.ArgumentTypeError as err:
        diag = Diagnostic(code="CLI001", message=str(err), span=None, hint="Run icl --help for usage.")
        print(format_diagnostic(diag), file=sys.stderr)
        return 2
    except Exception as err:  # pragma: no cover - defensive fallback
        diag = Diagnostic(code="CLI999", message=f"Internal error: {err}", span=None, hint="Run with --debug")
        print(format_diagnostic(diag), file=sys.stderr)
        return 3


def _resolve_compile_targets(target: str | None, targets_args: list[str]) -> list[str]:
    targets: list[str] = []
    if target:
        targets.append(target)
    for item in targets_args:
        chunks = [chunk.strip() for chunk in item.split(",")]
        targets.extend(chunk for chunk in chunks if chunk)

    if not targets:
        raise argparse.ArgumentTypeError("No target provided. Use --target or --targets.")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in targets:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _alias_trace_from_metadata(metadata: dict[str, object]) -> dict[str, object]:
    payload = metadata.get("natural_aliases")
    if not isinstance(payload, dict):
        return {"enabled": False, "changed": False, "count": 0, "replacements": []}
    return {
        "enabled": True,
        "mode": payload.get("mode", "core"),
        "changed": bool(payload.get("changed", False)),
        "count": int(payload.get("count", 0)),
        "replacements": list(payload.get("replacements", [])),
    }


def _resolve_source(input_path: str | None, inline_code: str | None) -> tuple[str, str]:
    if input_path and inline_code:
        raise argparse.ArgumentTypeError("Use either input file path or --code, not both.")
    if input_path:
        path = Path(input_path)
        return path.read_text(encoding="utf-8"), str(path)
    if inline_code is not None:
        return inline_code, "<inline>"
    raise argparse.ArgumentTypeError("No source provided. Pass input file path or --code.")


def _load_graph(path: Path) -> IntentGraph:
    payload = path.read_text(encoding="utf-8")
    return graph_from_json(payload)


if __name__ == "__main__":
    raise SystemExit(run())

"""Command-line interface for the ICL compiler."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from icl.errors import CompilerError, Diagnostic, format_diagnostic
from icl.graph import IntentGraph, diff_graphs
from icl.main import build_plugin_manager, compile_file, compile_source, compress_source, explain_source
from icl.serialization import graph_from_json


def build_parser() -> argparse.ArgumentParser:
    """Build argparse command tree for ICL CLI."""
    parser = argparse.ArgumentParser(prog="icl", description="ICL compiler and tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="Compile ICL source to a target language")
    compile_parser.add_argument("input", nargs="?", help="Input .icl file")
    compile_parser.add_argument("--code", help="Inline ICL source string")
    compile_parser.add_argument("--target", required=True, help="Target backend name (e.g. python/js/rust)")
    compile_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )
    compile_parser.add_argument("-o", "--output", help="Output file path")
    compile_parser.add_argument("--emit-graph", help="Write intent graph JSON")
    compile_parser.add_argument("--emit-sourcemap", help="Write source map JSON")
    compile_parser.add_argument("--optimize", action="store_true", help="Enable graph optimizations")
    compile_parser.add_argument("--debug", action="store_true", help="Emit debug info to stderr")

    check_parser = subparsers.add_parser("check", help="Validate source through semantic analysis")
    check_parser.add_argument("input", nargs="?", help="Input .icl file")
    check_parser.add_argument("--code", help="Inline ICL source string")
    check_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )

    explain_parser = subparsers.add_parser("explain", help="Print AST + Intent Graph JSON")
    explain_parser.add_argument("input", nargs="?", help="Input .icl file")
    explain_parser.add_argument("--code", help="Inline ICL source string")
    explain_parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin spec in module[:symbol] format; can be repeated.",
    )

    compress_parser = subparsers.add_parser("compress", help="Print canonical compact ICL encoding")
    compress_parser.add_argument("input", nargs="?", help="Input .icl file")
    compress_parser.add_argument("--code", help="Inline ICL source string")

    diff_parser = subparsers.add_parser("diff", help="Diff two serialized Intent Graph JSON files")
    diff_parser.add_argument("before", help="Path to previous graph JSON")
    diff_parser.add_argument("after", help="Path to next graph JSON")

    return parser


def run(argv: list[str] | None = None) -> int:
    """Run CLI and return shell exit code."""
    args = build_parser().parse_args(argv)

    try:
        if args.command == "compile":
            source, filename = _resolve_source(args.input, args.code)
            if args.input and args.code:
                raise argparse.ArgumentTypeError("Provide either file input or --code, not both.")
            manager = build_plugin_manager(args.plugin)

            if args.input:
                artifacts = compile_file(
                    args.input,
                    target=args.target,
                    plugin_manager=manager,
                    output_path=args.output,
                    optimize=args.optimize,
                    debug=args.debug,
                    emit_graph_path=args.emit_graph,
                    emit_sourcemap_path=args.emit_sourcemap,
                )
            else:
                artifacts = compile_source(
                    source,
                    filename=filename,
                    target=args.target,
                    plugin_manager=manager,
                    optimize=args.optimize,
                    debug=args.debug,
                    emit_graph_path=args.emit_graph,
                    emit_sourcemap_path=args.emit_sourcemap,
                )
                if args.output:
                    Path(args.output).write_text(artifacts.code, encoding="utf-8")

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

        if args.command == "check":
            source, filename = _resolve_source(args.input, args.code)
            manager = build_plugin_manager(args.plugin)
            compile_source(source, filename=filename, target="python", plugin_manager=manager)
            print("OK")
            return 0

        if args.command == "explain":
            source, filename = _resolve_source(args.input, args.code)
            manager = build_plugin_manager(args.plugin)
            payload = explain_source(source, filename=filename, plugin_manager=manager)
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

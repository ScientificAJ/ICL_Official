"""Catalog metadata for ICL MCP tools, resources, and prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from icl.mcp_errors import MCP_POLICY_ERROR, PolicyError


@dataclass(frozen=True)
class ResourceEntry:
    """Readable resource exposed via MCP resource API."""

    uri: str
    name: str
    description: str
    mime_type: str
    path: Path


def tools_list() -> list[dict[str, Any]]:
    """Return MCP tool metadata."""
    return [
        {
            "name": "icl_capabilities",
            "description": "Return service capability metadata (methods, targets, version).",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "icl_compile",
            "description": "Compile ICL source to one target or multiple language packs with runnable bundles.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "input_path": {"type": "string"},
                    "filename": {"type": "string"},
                    "target": {"type": "string"},
                    "targets": {"type": "array", "items": {"type": "string"}},
                    "optimize": {"type": "boolean"},
                    "debug": {"type": "boolean"},
                    "include_graph": {"type": "boolean"},
                    "include_source_map": {"type": "boolean"},
                    "include_ir": {"type": "boolean"},
                    "include_lowered": {"type": "boolean"},
                    "include_bundle": {"type": "boolean"},
                    "plugins": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                    "packs": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                },
                "anyOf": [{"required": ["target"]}, {"required": ["targets"]}],
                "additionalProperties": False,
            },
        },
        {
            "name": "icl_check",
            "description": "Validate ICL source (parse + semantic).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "input_path": {"type": "string"},
                    "filename": {"type": "string"},
                    "plugins": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "icl_explain",
            "description": "Return AST + IR + lowered + graph + source map for ICL source.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "input_path": {"type": "string"},
                    "filename": {"type": "string"},
                    "target": {"type": "string"},
                    "plugins": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                    "packs": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "icl_compress",
            "description": "Return canonical compact ICL text.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "input_path": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "icl_diff",
            "description": "Diff two intent graphs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "before_graph": {"type": "object"},
                    "before_path": {"type": "string"},
                    "after_graph": {"type": "object"},
                    "after_path": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    ]


def resources_list(root: Path) -> list[dict[str, Any]]:
    """Return list of available MCP resources."""
    entries = _resource_entries(root)
    return [
        {
            "uri": entry.uri,
            "name": entry.name,
            "description": entry.description,
            "mimeType": entry.mime_type,
        }
        for entry in entries.values()
    ]


def read_resource(uri: str, root: Path) -> dict[str, Any]:
    """Read a resource by URI."""
    entries = _resource_entries(root)
    entry = entries.get(uri)
    if entry is None:
        raise PolicyError(
            code=MCP_POLICY_ERROR,
            message=f"Unknown resource URI: {uri}",
            data={"uri": uri},
        )

    text = entry.path.read_text(encoding="utf-8")
    return {
        "contents": [
            {
                "uri": entry.uri,
                "mimeType": entry.mime_type,
                "text": text,
            }
        ]
    }


def prompts_list() -> list[dict[str, Any]]:
    """Return list of MCP prompt templates."""
    return [
        {
            "name": "icl_teach_beginner",
            "description": "Generate a beginner-oriented ICL teaching walkthrough by topic.",
            "arguments": [
                {
                    "name": "topic",
                    "description": "One of: assignment, if, loop, function",
                    "required": True,
                },
                {
                    "name": "targets",
                    "description": (
                        "Comma-separated targets. Stable: python/js/rust/web. "
                        "Experimental: typescript/go/java/csharp/cpp/php/ruby/kotlin/swift/lua/dart."
                    ),
                    "required": False,
                }
            ],
        },
        {
            "name": "icl_compile_review",
            "description": "Guide an agent to check, explain, compile, and summarize ICL source.",
            "arguments": [
                {
                    "name": "source",
                    "description": "ICL source text to process.",
                    "required": True,
                },
                {
                    "name": "target",
                    "description": (
                        "Target language pack. Stable: python/js/rust/web. "
                        "Experimental: typescript/go/java/csharp/cpp/php/ruby/kotlin/swift/lua/dart."
                    ),
                    "required": True,
                },
            ],
        },
        {
            "name": "icl_backend_extension_guide",
            "description": "Checklist prompt for implementing a new ICL backend safely.",
            "arguments": [
                {
                    "name": "backend_name",
                    "description": "Name of backend to implement.",
                    "required": True,
                }
            ],
        },
    ]


def get_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Render a prompt template by name."""
    args = arguments or {}

    if name == "icl_teach_beginner":
        topic = str(args.get("topic", "assignment"))
        targets = str(args.get("targets", "python,js,rust,web"))
        text = (
            "Teach ICL beginner topic with concrete compiler-aligned examples using the universal workflow.\n"
            f"Topic: {topic}\n"
            f"Targets: {targets}\n"
            "Required structure:\n"
            "1) ICL snippet\n2) AST->IR->Lowered summary\n3) multi-target output snippets\n4) semantic parity notes\n"
            "Stable targets: python/js/rust/web.\n"
            "Experimental targets: typescript/go/java/csharp/cpp/php/ruby/kotlin/swift/lua/dart.\n"
            "If a required language runtime/compiler is not installed, install it when permissions allow.\n"
            "If installation is blocked, ask your mentor to install or approve it.\n"
            "Use strict semantics from ICL_SEMANTICS_GUIDE.md."
        )
    elif name == "icl_compile_review":
        source = str(args.get("source", ""))
        target = str(args.get("target", "python"))
        text = (
            "Run the universal-language workflow:\n"
            "1) check source\n"
            "2) explain source (AST, IR, lowered, graph)\n"
            f"3) compile source to {target}\n"
            "4) if needed, compile to additional targets for parity comparison\n"
            "5) summarize diagnostics and result.\n"
            "Stable targets: python/js/rust/web.\n"
            "Experimental targets: typescript/go/java/csharp/cpp/php/ruby/kotlin/swift/lua/dart.\n"
            "If a required language runtime/compiler is not installed, install it when permissions allow.\n"
            "If installation is blocked, ask your mentor to install or approve it.\n"
            f"Source:\n{source}"
        )
    elif name == "icl_backend_extension_guide":
        backend_name = str(args.get("backend_name", "new_backend"))
        text = (
            f"Implement language pack '{backend_name}' with this checklist:\n"
            "- Add pack manifest + emit/scaffold implementation\n"
            "- Follow pipeline: Source -> AST -> IR -> Lowered -> Emit -> Scaffold\n"
            "- Register pack in pack registry\n"
            "- Add contract and integration tests\n"
            "- Keep language-contract semantic compatibility\n"
            "- Declare stable vs experimental support clearly\n"
            "- If required language toolchain/runtime is missing, install it when allowed or ask your mentor\n"
            "- Update docs and CLI examples\n"
        )
    else:
        raise PolicyError(
            code=MCP_POLICY_ERROR,
            message=f"Unknown prompt: {name}",
            data={"name": name},
        )

    return {
        "description": f"ICL prompt template: {name}",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": text,
                },
            }
        ],
    }


def _resource_entries(root: Path) -> dict[str, ResourceEntry]:
    entries: dict[str, ResourceEntry] = {}

    def add(uri: str, rel_path: str, name: str, description: str) -> None:
        path = (root / rel_path).resolve()
        if not path.exists():
            return
        entries[uri] = ResourceEntry(
            uri=uri,
            name=name,
            description=description,
            mime_type="text/markdown" if path.suffix.lower() == ".md" else "text/plain",
            path=path,
        )

    add("icl://docs/standards", "ICL_STANDARDS.md", "ICL Standards", "Coding standards and contributor rules.")
    add("icl://docs/semantics", "ICL_SEMANTICS_GUIDE.md", "ICL Semantics", "Compiler-accurate semantic specification.")
    add("icl://docs/teaching", "ICL_TEACHING_MANUAL.md", "ICL Teaching", "Teaching and onboarding manual.")
    add("icl://docs/language_spec", "docs/language_spec.md", "Language Spec", "Language reference document.")
    add("icl://docs/architecture", "docs/compiler_architecture.md", "Architecture", "Compiler architecture and adapters.")
    add("icl://docs/cli", "docs/cli_guide.md", "CLI Guide", "CLI and integration usage.")
    add("icl://docs/mcp", "docs/mcp_tool_docs.md", "MCP Tool Docs", "MCP server methods and tool docs.")
    add(
        "icl://docs/pack_guide",
        "docs/language_pack_creation_guide.md",
        "Pack Creation Guide",
        "How to create and validate custom language packs.",
    )
    add(
        "icl://docs/v2_plan",
        "ICL_2.0_UNIVERSAL_TRANSLATION_ARCHITECTURE_PLAN.md",
        "V2 Plan",
        "ICL v2 universal translation plan.",
    )
    add(
        "icl://docs/language_contract",
        "ICL_LANGUAGE_CONTRACT.md",
        "Language Contract",
        "Normative language contract for all language packs.",
    )
    add(
        "icl://docs/pack_spec",
        "LANGUAGE_PACK_SPEC.md",
        "Language Pack Spec",
        "Pack manifest and emission/scaffolding contract.",
    )
    add(
        "icl://docs/migration_v2",
        "MIGRATION_NOTES_v2.md",
        "Migration Notes v2",
        "Release notes and migration details for ICL v2.0.",
    )

    examples_dir = (root / "examples").resolve()
    if examples_dir.exists():
        for path in sorted(examples_dir.glob("*.icl")):
            entries[f"icl://examples/{path.name}"] = ResourceEntry(
                uri=f"icl://examples/{path.name}",
                name=path.name,
                description="ICL example source",
                mime_type="text/plain",
                path=path,
            )

    generated_dir = (root / "examples" / "generated").resolve()
    if generated_dir.exists():
        for path in sorted(generated_dir.glob("*")):
            if path.is_file():
                entries[f"icl://examples/generated/{path.name}"] = ResourceEntry(
                    uri=f"icl://examples/generated/{path.name}",
                    name=path.name,
                    description="Generated backend output",
                    mime_type="text/plain",
                    path=path,
                )

    return entries

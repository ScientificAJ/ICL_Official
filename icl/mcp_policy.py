"""Strict policy checks for ICL MCP tool execution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

from icl.mcp_errors import MCP_POLICY_ERROR, PolicyError


_DEFAULT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class MCPPolicyConfig:
    """Policy configuration for MCP server runtime."""

    root: Path
    plugin_allowlist: set[str]


def load_policy_config(root: Path | None = None) -> MCPPolicyConfig:
    """Load strict policy config from args/env with secure defaults."""
    root_env = os.getenv("ICL_MCP_ROOT")
    chosen_root = root or (Path(root_env).resolve() if root_env else _DEFAULT_ROOT.resolve())

    allow_env = os.getenv("ICL_MCP_PLUGIN_ALLOWLIST", "")
    plugin_allowlist = {item.strip() for item in allow_env.split(",") if item.strip()}

    return MCPPolicyConfig(root=chosen_root, plugin_allowlist=plugin_allowlist)


def validate_tool_call(tool_name: str, arguments: dict[str, Any], config: MCPPolicyConfig) -> dict[str, Any]:
    """Validate and sanitize MCP tool call arguments under strict policy."""
    if not isinstance(arguments, dict):
        raise PolicyError(
            code=MCP_POLICY_ERROR,
            message="Tool arguments must be an object.",
            data={"tool": tool_name},
        )

    sanitized = dict(arguments)

    _validate_paths(tool_name=tool_name, arguments=sanitized, config=config)
    _validate_plugins(arguments=sanitized, config=config)

    return sanitized


def _validate_paths(tool_name: str, arguments: dict[str, Any], config: MCPPolicyConfig) -> None:
    per_tool_keys: dict[str, tuple[str, ...]] = {
        "icl_compile": ("input_path",),
        "icl_check": ("input_path",),
        "icl_explain": ("input_path",),
        "icl_compress": ("input_path",),
        "icl_diff": ("before_path", "after_path"),
    }
    keys = per_tool_keys.get(tool_name, ())

    for key in keys:
        value = arguments.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise PolicyError(
                code=MCP_POLICY_ERROR,
                message=f"'{key}' must be a non-empty string.",
                data={"tool": tool_name, "field": key},
            )

        resolved = Path(value).expanduser().resolve()
        if not _is_under_root(resolved, config.root):
            raise PolicyError(
                code=MCP_POLICY_ERROR,
                message=f"Path for '{key}' is outside allowed root.",
                data={
                    "tool": tool_name,
                    "field": key,
                    "path": str(resolved),
                    "allowed_root": str(config.root),
                },
            )
        arguments[key] = str(resolved)


def _validate_plugins(arguments: dict[str, Any], config: MCPPolicyConfig) -> None:
    plugins = arguments.get("plugins")
    if plugins is None:
        return

    if isinstance(plugins, str):
        normalized = [plugins]
    elif isinstance(plugins, list):
        normalized = [str(item) for item in plugins]
    else:
        raise PolicyError(
            code=MCP_POLICY_ERROR,
            message="'plugins' must be a string or list of strings.",
            data={"field": "plugins"},
        )

    if not normalized:
        arguments["plugins"] = []
        return

    if not config.plugin_allowlist:
        raise PolicyError(
            code=MCP_POLICY_ERROR,
            message="Plugins are disabled by MCP policy.",
            data={"field": "plugins"},
        )

    denied = [plugin for plugin in normalized if plugin not in config.plugin_allowlist]
    if denied:
        raise PolicyError(
            code=MCP_POLICY_ERROR,
            message="One or more plugins are not allowlisted.",
            data={
                "denied": denied,
                "allowlist": sorted(config.plugin_allowlist),
            },
        )

    arguments["plugins"] = normalized


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

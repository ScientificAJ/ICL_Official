"""Error helpers for ICL MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603
MCP_TOOL_ERROR = -32010
MCP_POLICY_ERROR = -32020


@dataclass
class MCPError(Exception):
    """Represents a structured MCP/JSON-RPC error."""

    code: int
    message: str
    data: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class PolicyError(MCPError):
    """Policy violation error in MCP server."""


def error_payload(code: int, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build JSON-RPC error payload."""
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    return payload


def success_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Build JSON-RPC success envelope."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def error_response(
    request_id: Any,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build JSON-RPC error envelope."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error_payload(code=code, message=message, data=data),
    }

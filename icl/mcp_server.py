"""MCP stdio server for ICL tools, resources, and prompts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, BinaryIO

from icl.mcp_catalog import get_prompt, prompts_list, read_resource, resources_list, tools_list
from icl.mcp_errors import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    MCP_TOOL_ERROR,
    MCPError,
    PolicyError,
    error_response,
    success_response,
)
from icl.mcp_policy import MCPPolicyConfig, load_policy_config, validate_tool_call
from icl.service import safe_dispatch


PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "icl-mcp", "version": "2.0.0"}
SERVER_CAPABILITIES = {
    "tools": {"listChanged": False},
    "resources": {"subscribe": False, "listChanged": False},
    "prompts": {"listChanged": False},
}


class ICLMCPServer:
    """Handles JSON-RPC MCP requests for ICL."""

    def __init__(self, policy: MCPPolicyConfig) -> None:
        self.policy = policy
        self._tool_to_method = {
            "icl_capabilities": "capabilities",
            "icl_compile": "compile",
            "icl_check": "check",
            "icl_explain": "explain",
            "icl_compress": "compress",
            "icl_diff": "diff",
        }

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a single JSON-RPC request object."""
        if not isinstance(request, dict):
            raise MCPError(
                code=JSONRPC_INVALID_REQUEST,
                message="Request must be a JSON object.",
            )

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not isinstance(method, str) or not method:
            raise MCPError(
                code=JSONRPC_INVALID_REQUEST,
                message="Missing or invalid method.",
            )

        if not isinstance(params, dict):
            raise MCPError(
                code=JSONRPC_INVALID_PARAMS,
                message="Params must be an object.",
            )

        if method == "notifications/initialized":
            return None

        if method == "ping":
            return success_response(request_id, {})

        if method == "initialize":
            return success_response(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": SERVER_CAPABILITIES,
                    "serverInfo": SERVER_INFO,
                },
            )

        if method == "tools/list":
            return success_response(request_id, {"tools": tools_list()})

        if method == "tools/call":
            return success_response(request_id, self._handle_tools_call(params))

        if method == "resources/list":
            return success_response(request_id, {"resources": resources_list(self.policy.root)})

        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str) or not uri:
                raise MCPError(code=JSONRPC_INVALID_PARAMS, message="resources/read requires string 'uri'.")
            return success_response(request_id, read_resource(uri=uri, root=self.policy.root))

        if method == "prompts/list":
            return success_response(request_id, {"prompts": prompts_list()})

        if method == "prompts/get":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not name:
                raise MCPError(code=JSONRPC_INVALID_PARAMS, message="prompts/get requires string 'name'.")
            if not isinstance(arguments, dict):
                raise MCPError(code=JSONRPC_INVALID_PARAMS, message="prompts/get 'arguments' must be an object.")
            return success_response(request_id, get_prompt(name=name, arguments=arguments))

        raise MCPError(code=JSONRPC_METHOD_NOT_FOUND, message=f"Method not found: {method}")

    def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not isinstance(name, str) or not name:
            raise MCPError(code=JSONRPC_INVALID_PARAMS, message="tools/call requires string 'name'.")
        if not isinstance(arguments, dict):
            raise MCPError(code=JSONRPC_INVALID_PARAMS, message="tools/call 'arguments' must be an object.")

        service_method = self._tool_to_method.get(name)
        if service_method is None:
            raise MCPError(code=JSONRPC_INVALID_PARAMS, message=f"Unknown tool '{name}'.")

        validated_args = validate_tool_call(tool_name=name, arguments=arguments, config=self.policy)
        ok, payload = safe_dispatch(service_method, validated_args)

        if ok:
            return {
                "isError": False,
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    }
                ],
                "structuredContent": payload,
            }

        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True, sort_keys=True),
                }
            ],
            "structuredContent": payload,
        }


def run_stdio_server(
    server: ICLMCPServer,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
) -> int:
    """Run MCP server with Content-Length framed stdio messages."""
    input_stream = input_stream or sys.stdin.buffer
    output_stream = output_stream or sys.stdout.buffer

    while True:
        try:
            request = _read_message(input_stream)
        except EOFError:
            break
        except MCPError as err:
            _write_message(
                output_stream,
                error_response(
                    request_id=None,
                    code=err.code,
                    message=err.message,
                    data=err.data,
                ),
            )
            continue
        except Exception as err:  # pragma: no cover
            _write_message(
                output_stream,
                error_response(
                    request_id=None,
                    code=JSONRPC_PARSE_ERROR,
                    message=f"Failed to parse MCP message: {err}",
                ),
            )
            continue

        request_id = request.get("id") if isinstance(request, dict) else None
        try:
            response = server.handle_request(request)
            if response is not None:
                _write_message(output_stream, response)
        except PolicyError as err:
            _write_message(output_stream, error_response(request_id, err.code, err.message, err.data))
        except MCPError as err:
            _write_message(output_stream, error_response(request_id, err.code, err.message, err.data))
        except Exception as err:  # pragma: no cover
            _write_message(
                output_stream,
                error_response(
                    request_id,
                    JSONRPC_INTERNAL_ERROR,
                    f"Internal MCP server error: {err}",
                ),
            )

    return 0


def _read_message(stream: BinaryIO) -> dict[str, Any]:
    headers: dict[str, str] = {}

    while True:
        line = stream.readline()
        if line == b"":
            if not headers:
                raise EOFError()
            raise MCPError(code=JSONRPC_PARSE_ERROR, message="Unexpected EOF while reading headers.")

        stripped = line.strip(b"\r\n")
        if not stripped:
            break

        try:
            key_bytes, value_bytes = stripped.split(b":", 1)
        except ValueError as exc:
            raise MCPError(code=JSONRPC_PARSE_ERROR, message="Malformed header line.") from exc
        headers[key_bytes.decode("utf-8").strip().lower()] = value_bytes.decode("utf-8").strip()

    raw_len = headers.get("content-length")
    if raw_len is None:
        raise MCPError(code=JSONRPC_PARSE_ERROR, message="Missing Content-Length header.")

    try:
        content_length = int(raw_len)
    except ValueError as exc:
        raise MCPError(code=JSONRPC_PARSE_ERROR, message="Invalid Content-Length value.") from exc

    body = stream.read(content_length)
    if len(body) != content_length:
        raise MCPError(code=JSONRPC_PARSE_ERROR, message="Unexpected EOF while reading body.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise MCPError(code=JSONRPC_PARSE_ERROR, message="Body is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise MCPError(code=JSONRPC_INVALID_REQUEST, message="Top-level request must be an object.")

    if payload.get("jsonrpc") != "2.0":
        raise MCPError(code=JSONRPC_INVALID_REQUEST, message="jsonrpc must be '2.0'.")

    return payload


def _write_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    encoded = json.dumps(message, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii")
    stream.write(header)
    stream.write(encoded)
    stream.flush()


def run(argv: list[str] | None = None) -> int:
    """CLI entrypoint for MCP server."""
    parser = argparse.ArgumentParser(prog="icl-mcp", description="ICL MCP stdio server")
    parser.add_argument(
        "--root",
        help="Allowed root directory for MCP file path operations (default: repo root or ICL_MCP_ROOT).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else None
    policy = load_policy_config(root=root)
    server = ICLMCPServer(policy=policy)
    return run_stdio_server(server=server)


if __name__ == "__main__":
    raise SystemExit(run())

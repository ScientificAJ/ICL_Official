from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _encode_messages(messages: list[dict[str, object]]) -> bytes:
    chunks: list[bytes] = []
    for message in messages:
        body = json.dumps(message, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        chunks.append(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
        chunks.append(body)
    return b"".join(chunks)


def _decode_messages(raw: bytes) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    index = 0

    while index < len(raw):
        header_end = raw.find(b"\r\n\r\n", index)
        if header_end < 0:
            raise AssertionError("Missing MCP header terminator.")

        headers = raw[index:header_end].split(b"\r\n")
        index = header_end + 4

        content_length: int | None = None
        for header in headers:
            if not header:
                continue
            key, value = header.split(b":", 1)
            if key.strip().lower() == b"content-length":
                content_length = int(value.strip().decode("ascii"))
                break

        if content_length is None:
            raise AssertionError("Missing Content-Length header in response.")

        body = raw[index : index + content_length]
        if len(body) != content_length:
            raise AssertionError("Truncated MCP response body.")
        index += content_length

        parsed = json.loads(body.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise AssertionError("Response body is not a JSON object.")
        messages.append(parsed)

    return messages


def _run_mcp(messages: list[dict[str, object]], *, env: dict[str, str] | None = None) -> list[dict[str, object]]:
    payload = _encode_messages(messages)
    proc = subprocess.run(
        [sys.executable, "-m", "icl.mcp_server", "--root", str(PROJECT_ROOT)],
        cwd=PROJECT_ROOT,
        input=payload,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise AssertionError(f"mcp server exited with {proc.returncode}: {proc.stderr.decode('utf-8')}")
    return _decode_messages(proc.stdout)


class MCPServerTests(unittest.TestCase):
    def test_initialize_and_tools_list(self) -> None:
        responses = _run_mcp(
            [
                {"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}},
            ]
        )
        self.assertEqual(len(responses), 2)

        init = responses[0]
        self.assertEqual(init["id"], "init")
        init_result = init["result"]
        self.assertEqual(init_result["protocolVersion"], "2024-11-05")
        self.assertEqual(init_result["serverInfo"]["name"], "icl-mcp")

        tools = responses[1]
        self.assertEqual(tools["id"], "tools")
        tool_names = {entry["name"] for entry in tools["result"]["tools"]}
        self.assertIn("icl_compile", tool_names)
        self.assertIn("icl_check", tool_names)
        self.assertIn("icl_diff", tool_names)

    def test_tools_call_compile(self) -> None:
        responses = _run_mcp(
            [
                {
                    "jsonrpc": "2.0",
                    "id": "compile",
                    "method": "tools/call",
                    "params": {
                        "name": "icl_compile",
                        "arguments": {
                            "source": "x := 1 + 2;",
                            "target": "python",
                            "include_graph": True,
                        },
                    },
                }
            ]
        )
        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertEqual(response["id"], "compile")
        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertIn("x = (1 + 2)", result["structuredContent"]["code"])
        self.assertIn("graph", result["structuredContent"])

    def test_policy_blocks_paths_outside_root(self) -> None:
        responses = _run_mcp(
            [
                {
                    "jsonrpc": "2.0",
                    "id": "blocked-path",
                    "method": "tools/call",
                    "params": {
                        "name": "icl_check",
                        "arguments": {"input_path": "/etc/passwd"},
                    },
                }
            ]
        )
        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertEqual(response["id"], "blocked-path")
        self.assertEqual(response["error"]["code"], -32020)
        self.assertIn("outside allowed root", response["error"]["message"])

    def test_policy_blocks_plugins_when_allowlist_absent(self) -> None:
        responses = _run_mcp(
            [
                {
                    "jsonrpc": "2.0",
                    "id": "blocked-plugin",
                    "method": "tools/call",
                    "params": {
                        "name": "icl_compile",
                        "arguments": {
                            "source": "#echo(1);",
                            "target": "python",
                            "plugins": ["icl.plugins.std_macros"],
                        },
                    },
                }
            ]
        )
        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertEqual(response["id"], "blocked-plugin")
        self.assertEqual(response["error"]["code"], -32020)
        self.assertIn("Plugins are disabled", response["error"]["message"])

    def test_resources_and_prompts(self) -> None:
        responses = _run_mcp(
            [
                {"jsonrpc": "2.0", "id": "res", "method": "resources/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": "prompt",
                    "method": "prompts/get",
                    "params": {"name": "icl_teach_beginner", "arguments": {"topic": "if"}},
                },
            ]
        )
        self.assertEqual(len(responses), 2)

        resources = responses[0]["result"]["resources"]
        uris = {entry["uri"] for entry in resources}
        self.assertIn("icl://docs/semantics", uris)

        prompt_text = responses[1]["result"]["messages"][0]["content"]["text"]
        self.assertIn("Topic: if", prompt_text)

    def test_cli_mcp_subcommand(self) -> None:
        payload = _encode_messages(
            [
                {"jsonrpc": "2.0", "id": "ping", "method": "ping", "params": {}},
            ]
        )
        proc = subprocess.run(
            [sys.executable, "-m", "icl.cli", "mcp", "--root", str(PROJECT_ROOT)],
            cwd=PROJECT_ROOT,
            input=payload,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        responses = _decode_messages(proc.stdout)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["id"], "ping")
        self.assertEqual(responses[0]["result"], {})


if __name__ == "__main__":
    unittest.main()

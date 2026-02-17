"""Line-delimited JSON stdio adapter for AI agent integrations."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from icl.service import safe_dispatch


def run_stdio(input_stream: Any = None, output_stream: Any = None) -> int:
    """Run the stdio JSON-RPC-like server.

    Request format (one JSON object per line):
    {
      "id": "req-1",
      "method": "compile",
      "params": {"source": "x := 1;", "target": "python"}
    }

    Response format:
    {
      "id": "req-1",
      "ok": true,
      "result": {...}
    }
    """
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout

    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue

        response = _handle_line(line)
        output_stream.write(json.dumps(response, ensure_ascii=True, separators=(",", ":")) + "\n")
        output_stream.flush()

    return 0


def _handle_line(line: str) -> dict[str, Any]:
    request_id: Any = None
    try:
        obj = json.loads(line)
    except Exception:
        return {
            "id": None,
            "ok": False,
            "error": {
                "code": "AGT400",
                "message": "Invalid JSON request line.",
                "hint": "Send one JSON object per line.",
            },
        }

    if not isinstance(obj, dict):
        return {
            "id": None,
            "ok": False,
            "error": {
                "code": "AGT401",
                "message": "Request must be a JSON object.",
                "hint": "Use {'id','method','params'} object format.",
            },
        }

    request_id = obj.get("id")
    method = obj.get("method")
    params = obj.get("params", {})

    if not isinstance(method, str) or not method:
        return {
            "id": request_id,
            "ok": False,
            "error": {
                "code": "AGT402",
                "message": "Missing or invalid 'method'.",
                "hint": "Set method to compile/check/explain/compress/diff/capabilities.",
            },
        }

    if not isinstance(params, dict):
        return {
            "id": request_id,
            "ok": False,
            "error": {
                "code": "AGT403",
                "message": "'params' must be a JSON object.",
                "hint": "Set params to an object, even if empty.",
            },
        }

    ok, payload = safe_dispatch(method, params)
    if ok:
        return {
            "id": request_id,
            "ok": True,
            "result": payload,
        }

    return {
        "id": request_id,
        "ok": False,
        **payload,
    }


def run(argv: list[str] | None = None) -> int:
    """CLI entrypoint for stdio adapter."""
    parser = argparse.ArgumentParser(prog="icl-agent", description="ICL stdio agent adapter")
    parser.parse_args(argv)
    return run_stdio()


if __name__ == "__main__":
    raise SystemExit(run())

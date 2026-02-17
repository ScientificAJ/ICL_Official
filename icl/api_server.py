"""HTTP API adapter for ICL service methods."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from icl.service import safe_dispatch


class ICLAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler exposing ICL service methods over JSON."""

    server_version = "ICLHTTP/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json(HTTPStatus.OK, {"ok": True, "service": "icl", "transport": "http"})
            return
        if self.path == "/v1/capabilities":
            ok, payload = safe_dispatch("capabilities", {})
            if ok:
                self._write_json(HTTPStatus.OK, {"ok": True, "result": payload})
            else:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, **payload})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": {"code": "HTTP404", "message": "Not found"}})

    def do_POST(self) -> None:  # noqa: N802
        method = self._method_from_path(self.path)
        if method is None:
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": {"code": "HTTP404", "message": "Not found"}})
            return

        payload = self._read_json_payload()
        if payload is None:
            return

        ok, result = safe_dispatch(method, payload)
        if ok:
            self._write_json(HTTPStatus.OK, {"ok": True, "result": result})
            return

        status = HTTPStatus.BAD_REQUEST
        error_code = result.get("error", {}).get("code", "")
        if error_code == "SRV999":
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        self._write_json(status, {"ok": False, **result})

    def _read_json_payload(self) -> dict[str, Any] | None:
        length_raw = self.headers.get("Content-Length")
        if length_raw is None:
            self._write_json(
                HTTPStatus.LENGTH_REQUIRED,
                {"ok": False, "error": {"code": "HTTP411", "message": "Missing Content-Length"}},
            )
            return None

        try:
            length = int(length_raw)
        except ValueError:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": {"code": "HTTP400", "message": "Invalid Content-Length"}},
            )
            return None

        body = self.rfile.read(length)
        try:
            decoded = body.decode("utf-8")
            obj = json.loads(decoded)
        except Exception:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": {"code": "HTTP400", "message": "Invalid JSON body"}},
            )
            return None

        if not isinstance(obj, dict):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": {"code": "HTTP400", "message": "JSON payload must be an object"}},
            )
            return None

        return obj

    @staticmethod
    def _method_from_path(path: str) -> str | None:
        if not path.startswith("/v1/"):
            return None
        method = path[len("/v1/") :].strip()
        if not method:
            return None
        return method

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep HTTP adapter quiet by default for tool/AI usage.
        return


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    """Create an ICL API HTTP server instance."""
    return ThreadingHTTPServer((host, port), ICLAPIHandler)


def run_http_api(host: str = "127.0.0.1", port: int = 8080) -> int:
    """Run the ICL HTTP API server."""
    server = create_server(host=host, port=port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def run(argv: list[str] | None = None) -> int:
    """CLI entrypoint for running HTTP API service."""
    parser = argparse.ArgumentParser(prog="icl-api", description="ICL HTTP API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    return run_http_api(host=args.host, port=args.port)


if __name__ == "__main__":
    raise SystemExit(run())

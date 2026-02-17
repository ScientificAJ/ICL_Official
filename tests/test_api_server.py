from __future__ import annotations

import json
import threading
import unittest
from urllib.request import Request, urlopen

from icl.api_server import create_server


class APIServerTests(unittest.TestCase):
    def test_health_and_compile_endpoint(self) -> None:
        try:
            server = create_server(host="127.0.0.1", port=0)
        except PermissionError:
            self.skipTest("Socket binding is not permitted in this environment.")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        host, port = server.server_address
        base = f"http://{host}:{port}"

        try:
            with urlopen(f"{base}/health") as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(payload["ok"])

            req_payload = json.dumps({"source": "x := 1 + 2;", "target": "python"}).encode("utf-8")
            req = Request(
                f"{base}/v1/compile",
                data=req_payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(result["ok"])
            self.assertIn("x = (1 + 2)", result["result"]["code"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AgentStdioTests(unittest.TestCase):
    def test_compile_request_line(self) -> None:
        req = {
            "id": "1",
            "method": "compile",
            "params": {"source": "x := 1;", "target": "python"},
        }
        proc = subprocess.run(
            [sys.executable, "-m", "icl.agent_stdio"],
            cwd=PROJECT_ROOT,
            input=json.dumps(req) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        line = proc.stdout.strip().splitlines()[0]
        payload = json.loads(line)
        self.assertEqual(payload["id"], "1")
        self.assertTrue(payload["ok"])
        self.assertIn("x = 1", payload["result"]["code"])

    def test_invalid_json_line(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "icl.agent_stdio"],
            cwd=PROJECT_ROOT,
            input="not-json\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout.strip().splitlines()[0])
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "AGT400")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from icl.contract_tests import run_contract_suite
from icl.main import build_pack_registry, compile_source, compile_targets


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class V2PipelineTests(unittest.TestCase):
    def test_compile_targets_multi(self) -> None:
        artifacts = compile_targets("x := 1 + 2;", targets=["python", "js"])
        self.assertIn("python", artifacts.targets)
        self.assertIn("js", artifacts.targets)
        self.assertIn("x = (1 + 2)", artifacts.targets["python"].code)
        self.assertIn("let x = (1 + 2);", artifacts.targets["js"].code)

    def test_web_target_scaffold(self) -> None:
        artifacts = compile_source("@print(1);", target="web")
        self.assertIn("index.html", artifacts.bundle.files)
        self.assertIn("styles.css", artifacts.bundle.files)
        self.assertIn("app.js", artifacts.bundle.files)
        self.assertIn("function print(value)", artifacts.code)

    def test_experimental_pack_available(self) -> None:
        registry = build_pack_registry()
        experimental_targets = registry.targets(stability="experimental")
        self.assertIn("typescript", experimental_targets)
        artifacts = compile_source("x := 1;", target="typescript", pack_registry=registry)
        self.assertIn("experimental ICL pack", artifacts.code)

    def test_contract_suite_stable(self) -> None:
        report = run_contract_suite(stable_only=True)
        for result in report["results"]:
            self.assertTrue(result["ok"], msg=json.dumps(result))


class V2CLITests(unittest.TestCase):
    def test_compile_multi_targets_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "icl.cli",
                "compile",
                "--code",
                "x := 1;",
                "--targets",
                "python,js",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("python", payload)
        self.assertIn("js", payload)
        self.assertIn("primary_path", payload["python"])
        self.assertIn("files", payload["python"])
        self.assertIn("main.py", payload["python"]["files"])
        self.assertIn("main.js", payload["js"]["files"])


if __name__ == "__main__":
    unittest.main()

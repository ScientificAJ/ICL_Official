from __future__ import annotations

import unittest

from icl.main import explain_source
from icl.service import capabilities_request, compile_request, diff_request


class ServiceTests(unittest.TestCase):
    def test_compile_request_python(self) -> None:
        result = compile_request({"source": "x := 1 + 2;", "target": "python"})
        self.assertIn("x = (1 + 2)", result["code"])
        self.assertEqual(result["target"], "python")
        self.assertGreater(result["metrics"]["tokens"], 0)

    def test_compile_request_with_macro_plugin(self) -> None:
        result = compile_request(
            {
                "source": "#echo(5);",
                "target": "js",
                "plugins": ["icl.plugins.std_macros"],
            }
        )
        self.assertIn("print(5);", result["code"])

    def test_capabilities_request(self) -> None:
        caps = capabilities_request({})
        self.assertIn("compile", caps["methods"])
        self.assertIn("python", caps["targets"])
        self.assertIn("js", caps["targets"])
        self.assertIn("rust", caps["targets"])

    def test_diff_request_from_graph_objects(self) -> None:
        before = explain_source("x := 1;")["graph"]
        after = explain_source("x := 2;")["graph"]
        diff = diff_request({"before_graph": before, "after_graph": after})
        self.assertTrue(diff["changed_nodes"])


if __name__ == "__main__":
    unittest.main()

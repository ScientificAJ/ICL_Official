from __future__ import annotations

import unittest

from icl.main import compile_source


class IntegrationTests(unittest.TestCase):
    def test_compile_and_execute_python(self) -> None:
        source = 'fn add(a, b):Num => a + b; x := @add(2, 3);'
        artifacts = compile_source(source, target='python')
        namespace: dict[str, object] = {}
        exec(artifacts.code, namespace, namespace)
        self.assertEqual(namespace['x'], 5)

    def test_optimization_constant_folding(self) -> None:
        source = 'x := 1 + 2; y := x;'
        artifacts = compile_source(source, target='python', optimize=True)
        folded_nodes = [
            node
            for node in artifacts.graph.nodes.values()
            if node.kind == 'LiteralIntent' and node.attrs.get('folded_from') == '+'
        ]
        self.assertTrue(folded_nodes)


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import unittest

from icl.graph import IntentGraphBuilder, diff_graphs
from icl.lexer import Lexer
from icl.parser import Parser


def build_graph(source: str):
    program = Parser(Lexer(source).tokenize()).parse_program()
    builder = IntentGraphBuilder()
    graph = builder.build(program)
    return graph, builder.source_map


class GraphTests(unittest.TestCase):
    def test_graph_builder_creates_root_and_nodes(self) -> None:
        graph, source_map = build_graph('x := 1; y := x + 2;')
        self.assertIsNotNone(graph.root_id)
        assert graph.root_id is not None
        self.assertEqual(graph.nodes[graph.root_id].kind, 'ModuleIntent')
        self.assertGreaterEqual(len(graph.nodes), 5)
        self.assertEqual(len(source_map.entries), len(graph.nodes))

    def test_graph_diff_detects_literal_change(self) -> None:
        before, _ = build_graph('x := 1;')
        after, _ = build_graph('x := 2;')
        diff = diff_graphs(before, after)
        self.assertTrue(diff.changed_nodes)


if __name__ == '__main__':
    unittest.main()

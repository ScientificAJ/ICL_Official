from __future__ import annotations

import unittest

from icl.ast import AssignmentStmt, FunctionDefStmt, IfStmt, LoopStmt
from icl.errors import ParseError
from icl.lexer import Lexer
from icl.parser import Parser


def parse_source(source: str):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse_program()


class ParserTests(unittest.TestCase):
    def test_function_and_assignment(self) -> None:
        program = parse_source('fn add(a,b):Num => a + b; result := @add(2, 3);')
        self.assertEqual(len(program.statements), 2)
        self.assertIsInstance(program.statements[0], FunctionDefStmt)
        self.assertIsInstance(program.statements[1], AssignmentStmt)

    def test_nested_conditional_in_loop(self) -> None:
        source = (
            'loop i in 0..3 { '
            'if i > 1 ? { x := i; } : { x := 0; } '
            '}'
        )
        program = parse_source(source)
        self.assertEqual(len(program.statements), 1)
        loop_stmt = program.statements[0]
        self.assertIsInstance(loop_stmt, LoopStmt)
        self.assertIsInstance(loop_stmt.body[0], IfStmt)

    def test_invalid_syntax_raises(self) -> None:
        with self.assertRaises(ParseError):
            parse_source('if true ? { x := 1; ')


if __name__ == '__main__':
    unittest.main()

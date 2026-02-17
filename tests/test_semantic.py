from __future__ import annotations

import unittest

from icl.errors import SemanticError
from icl.lexer import Lexer
from icl.parser import Parser
from icl.semantic import SemanticAnalyzer


def analyze(source: str) -> None:
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    SemanticAnalyzer().analyze(program)


class SemanticTests(unittest.TestCase):
    def test_undefined_symbol(self) -> None:
        with self.assertRaises(SemanticError) as ctx:
            analyze('x := y;')
        self.assertEqual(ctx.exception.code, 'SEM011')

    def test_return_outside_function(self) -> None:
        with self.assertRaises(SemanticError) as ctx:
            analyze('ret 1;')
        self.assertEqual(ctx.exception.code, 'SEM008')

    def test_function_arity_mismatch(self) -> None:
        with self.assertRaises(SemanticError) as ctx:
            analyze('fn add(a, b) => a + b; x := @add(1);')
        self.assertEqual(ctx.exception.code, 'SEM019')

    def test_type_mismatch(self) -> None:
        with self.assertRaises(SemanticError) as ctx:
            analyze('x:Num := "hello";')
        self.assertEqual(ctx.exception.code, 'SEM002')

    def test_lambda_value_is_callable(self) -> None:
        analyze('inc := lam(n:Num):Num => n + 1; out := inc(2);')

    def test_lambda_return_type_mismatch(self) -> None:
        with self.assertRaises(SemanticError) as ctx:
            analyze('bad := lam(n:Num):Bool => n + 1;')
        self.assertEqual(ctx.exception.code, 'SEM021')


if __name__ == '__main__':
    unittest.main()

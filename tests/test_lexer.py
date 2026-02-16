from __future__ import annotations

import unittest

from icl.errors import LexError
from icl.lexer import Lexer
from icl.tokens import TokenType


class LexerTests(unittest.TestCase):
    def test_tokenizes_assignment_and_call(self) -> None:
        source = 'x:Num := @add(1, 2);'
        tokens = Lexer(source).tokenize()
        kinds = [token.token_type for token in tokens]
        self.assertEqual(
            kinds[:11],
            [
                TokenType.IDENT,
                TokenType.COLON,
                TokenType.IDENT,
                TokenType.ASSIGN,
                TokenType.AT,
                TokenType.IDENT,
                TokenType.LPAR,
                TokenType.NUMBER,
                TokenType.COMMA,
                TokenType.NUMBER,
                TokenType.RPAR,
            ],
        )

    def test_handles_comments_and_strings(self) -> None:
        source = '// comment\nmsg := "hi";'
        tokens = Lexer(source).tokenize()
        self.assertEqual(tokens[0].token_type, TokenType.IDENT)
        self.assertEqual(tokens[0].value, 'msg')
        self.assertEqual(tokens[2].token_type, TokenType.STRING)
        self.assertEqual(tokens[2].value, 'hi')

    def test_rejects_unexpected_character(self) -> None:
        with self.assertRaises(LexError) as ctx:
            Lexer('x := 1 $ 2').tokenize()
        self.assertEqual(ctx.exception.code, 'LEX001')


if __name__ == '__main__':
    unittest.main()

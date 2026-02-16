"""ICL lexical analyzer."""

from __future__ import annotations

from typing import Final

from icl.errors import LexError
from icl.source_map import SourceSpan
from icl.tokens import KEYWORDS, Token, TokenType


_SINGLE_CHAR_TOKENS: Final[dict[str, TokenType]] = {
    ":": TokenType.COLON,
    "?": TokenType.QUESTION,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
    "(": TokenType.LPAR,
    ")": TokenType.RPAR,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "@": TokenType.AT,
    "#": TokenType.HASH,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "!": TokenType.NOT,
}


class Lexer:
    """Converts ICL source text into a token stream."""

    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source = source
        self.filename = filename
        self.index = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        """Tokenize full source and return the token stream."""
        tokens: list[Token] = []

        while not self._is_eof():
            ch = self._peek()
            if ch in " \t\r\n":
                self._consume_whitespace()
                continue

            if ch == "/" and self._peek(1) == "/":
                self._consume_comment()
                continue

            if ch.isalpha() or ch == "_":
                tokens.append(self._lex_identifier())
                continue

            if ch.isdigit():
                tokens.append(self._lex_number())
                continue

            if ch == '"':
                tokens.append(self._lex_string())
                continue

            multi = self._lex_multi_char_operator()
            if multi is not None:
                tokens.append(multi)
                continue

            token_type = _SINGLE_CHAR_TOKENS.get(ch)
            if token_type is not None:
                start_line, start_col = self.line, self.column
                self._advance()
                span = self._span(start_line, start_col, self.line, self.column)
                tokens.append(Token(token_type=token_type, value=ch, span=span))
                continue

            raise LexError(
                code="LEX001",
                message=f"Unexpected character {ch!r}.",
                span=self._span(self.line, self.column, self.line, self.column + 1),
                hint="Remove the character or escape it inside a string literal.",
            )

        eof_span = self._span(self.line, self.column, self.line, self.column)
        tokens.append(Token(token_type=TokenType.EOF, value="", span=eof_span))
        return tokens

    def _lex_multi_char_operator(self) -> Token | None:
        start_line, start_col = self.line, self.column
        pair = self._peek() + self._peek(1)
        mapping: dict[str, TokenType] = {
            ":=": TokenType.ASSIGN,
            "=>": TokenType.ARROW,
            "..": TokenType.RANGE,
            "==": TokenType.EQ,
            "!=": TokenType.NE,
            "<=": TokenType.LE,
            ">=": TokenType.GE,
            "&&": TokenType.AND,
            "||": TokenType.OR,
        }
        token_type = mapping.get(pair)
        if token_type is None:
            return None
        self._advance()
        self._advance()
        span = self._span(start_line, start_col, self.line, self.column)
        return Token(token_type=token_type, value=pair, span=span)

    def _lex_identifier(self) -> Token:
        start_line, start_col = self.line, self.column
        value_chars: list[str] = []
        while not self._is_eof() and (self._peek().isalnum() or self._peek() == "_"):
            value_chars.append(self._advance())
        value = "".join(value_chars)
        token_type = KEYWORDS.get(value, TokenType.IDENT)
        span = self._span(start_line, start_col, self.line, self.column)
        return Token(token_type=token_type, value=value, span=span)

    def _lex_number(self) -> Token:
        start_line, start_col = self.line, self.column
        value_chars: list[str] = []
        seen_dot = False

        while not self._is_eof():
            ch = self._peek()
            if ch.isdigit():
                value_chars.append(self._advance())
                continue
            if ch == "." and not seen_dot and self._peek(1).isdigit():
                seen_dot = True
                value_chars.append(self._advance())
                continue
            break

        value = "".join(value_chars)
        span = self._span(start_line, start_col, self.line, self.column)
        return Token(token_type=TokenType.NUMBER, value=value, span=span)

    def _lex_string(self) -> Token:
        start_line, start_col = self.line, self.column
        self._advance()  # opening quote
        value_chars: list[str] = []

        while not self._is_eof():
            ch = self._advance()
            if ch == '"':
                span = self._span(start_line, start_col, self.line, self.column)
                return Token(token_type=TokenType.STRING, value="".join(value_chars), span=span)
            if ch == "\\":
                if self._is_eof():
                    break
                esc = self._advance()
                escapes = {
                    "n": "\n",
                    "t": "\t",
                    '"': '"',
                    "\\": "\\",
                }
                value_chars.append(escapes.get(esc, esc))
                continue
            value_chars.append(ch)

        raise LexError(
            code="LEX002",
            message="Unterminated string literal.",
            span=self._span(start_line, start_col, self.line, self.column),
            hint="Close the string with a double quote.",
        )

    def _consume_whitespace(self) -> None:
        while not self._is_eof() and self._peek() in " \t\r\n":
            self._advance()

    def _consume_comment(self) -> None:
        while not self._is_eof() and self._peek() != "\n":
            self._advance()

    def _peek(self, offset: int = 0) -> str:
        idx = self.index + offset
        if idx >= len(self.source):
            return "\0"
        return self.source[idx]

    def _advance(self) -> str:
        ch = self.source[self.index]
        self.index += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _is_eof(self) -> bool:
        return self.index >= len(self.source)

    def _span(
        self,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int,
    ) -> SourceSpan:
        return SourceSpan(
            file=self.filename,
            line=start_line,
            column=start_col,
            end_line=end_line,
            end_column=end_col,
        )

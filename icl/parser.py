"""ICL parser producing a typed AST."""

from __future__ import annotations

from dataclasses import dataclass

from icl.ast import (
    AssignmentStmt,
    BinaryExpr,
    CallExpr,
    Expr,
    ExpressionStmt,
    FunctionDefStmt,
    IdentifierExpr,
    IfStmt,
    LambdaExpr,
    LiteralExpr,
    LoopStmt,
    MacroStmt,
    Param,
    Program,
    ReturnStmt,
    Stmt,
    UnaryExpr,
)
from icl.errors import ParseError
from icl.source_map import SourceSpan
from icl.tokens import Token, TokenType


_PRECEDENCE: dict[TokenType, int] = {
    TokenType.OR: 1,
    TokenType.AND: 2,
    TokenType.EQ: 3,
    TokenType.NE: 3,
    TokenType.LT: 4,
    TokenType.LE: 4,
    TokenType.GT: 4,
    TokenType.GE: 4,
    TokenType.PLUS: 5,
    TokenType.MINUS: 5,
    TokenType.STAR: 6,
    TokenType.SLASH: 6,
    TokenType.PERCENT: 6,
}


@dataclass
class Parser:
    """Recursive-descent + Pratt parser for ICL."""

    tokens: list[Token]

    def __post_init__(self) -> None:
        self.pos = 0

    def parse_program(self) -> Program:
        """Parse full token stream into a program AST."""
        statements: list[Stmt] = []
        errors: list[ParseError] = []

        while not self._is_at_end():
            self._consume_optional_semicolons()
            if self._is_at_end():
                break
            try:
                stmt = self._parse_statement()
                statements.append(stmt)
                self._consume_optional_semicolons()
            except ParseError as err:
                errors.append(err)
                self._synchronize()

        if errors:
            if len(errors) == 1:
                raise errors[0]
            first = errors[0]
            raise ParseError(
                code=first.code,
                message=f"{first.message} (plus {len(errors) - 1} additional parse error(s)).",
                span=first.span,
                hint=first.hint,
            )

        if statements:
            span = self._merge_spans(statements[0].span, statements[-1].span)
        else:
            span = self._peek().span
        return Program(span=span, statements=statements)

    def _parse_statement(self) -> Stmt:
        if self._match(TokenType.FN):
            return self._parse_function_def(self._previous())
        if self._match(TokenType.IF):
            return self._parse_if_stmt(self._previous())
        if self._match(TokenType.LOOP):
            return self._parse_loop_stmt(self._previous())
        if self._match(TokenType.RET):
            return self._parse_return_stmt(self._previous())
        if self._match(TokenType.HASH):
            return self._parse_macro_stmt(self._previous())
        if self._is_assignment_start():
            return self._parse_assignment_stmt()

        expr = self._parse_expression()
        return ExpressionStmt(span=expr.span, expr=expr)

    def _parse_assignment_stmt(self) -> AssignmentStmt:
        name_tok = self._consume(TokenType.IDENT, "Expected identifier in assignment.")
        type_hint: str | None = None

        if self._match(TokenType.COLON):
            type_tok = self._consume(TokenType.IDENT, "Expected type name after ':'.")
            type_hint = type_tok.value

        self._consume(TokenType.ASSIGN, "Expected ':=' in assignment.")
        value = self._parse_expression()
        span = self._merge_spans(name_tok.span, value.span)
        return AssignmentStmt(span=span, name=name_tok.value, value=value, type_hint=type_hint)

    def _parse_function_def(self, fn_token: Token) -> FunctionDefStmt:
        name_tok = self._consume(TokenType.IDENT, "Expected function name after 'fn'.")
        self._consume(TokenType.LPAR, "Expected '(' after function name.")
        params: list[Param] = []

        if not self._check(TokenType.RPAR):
            while True:
                param_name = self._consume(TokenType.IDENT, "Expected parameter name.")
                param_type: str | None = None
                if self._match(TokenType.COLON):
                    param_type_tok = self._consume(TokenType.IDENT, "Expected parameter type after ':'.")
                    param_type = param_type_tok.value
                params.append(Param(name=param_name.value, type_hint=param_type))
                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RPAR, "Expected ')' after function parameters.")

        return_type: str | None = None
        if self._match(TokenType.COLON):
            return_type_tok = self._consume(TokenType.IDENT, "Expected return type after ':'.")
            return_type = return_type_tok.value

        if self._match(TokenType.ARROW):
            expr = self._parse_expression()
            span = self._merge_spans(fn_token.span, expr.span)
            return FunctionDefStmt(
                span=span,
                name=name_tok.value,
                params=params,
                body=[],
                expr_body=expr,
                return_type=return_type,
            )

        body, block_span = self._parse_block()
        span = self._merge_spans(fn_token.span, block_span)
        return FunctionDefStmt(
            span=span,
            name=name_tok.value,
            params=params,
            body=body,
            expr_body=None,
            return_type=return_type,
        )

    def _parse_if_stmt(self, if_token: Token) -> IfStmt:
        condition = self._parse_expression()
        self._consume(TokenType.QUESTION, "Expected '?' after if condition.")
        then_block, then_span = self._parse_block()

        else_block: list[Stmt] = []
        end_span = then_span
        if self._match(TokenType.COLON):
            else_block, else_span = self._parse_block()
            end_span = else_span

        span = self._merge_spans(if_token.span, end_span)
        return IfStmt(span=span, condition=condition, then_block=then_block, else_block=else_block)

    def _parse_loop_stmt(self, loop_token: Token) -> LoopStmt:
        iterator_tok = self._consume(TokenType.IDENT, "Expected loop iterator name after 'loop'.")
        self._consume(TokenType.IN, "Expected 'in' in loop header.")
        start_expr = self._parse_expression()
        self._consume(TokenType.RANGE, "Expected '..' in loop range.")
        end_expr = self._parse_expression()
        body, body_span = self._parse_block()

        span = self._merge_spans(loop_token.span, body_span)
        return LoopStmt(
            span=span,
            iterator=iterator_tok.value,
            start=start_expr,
            end=end_expr,
            body=body,
        )

    def _parse_return_stmt(self, ret_token: Token) -> ReturnStmt:
        if self._check(TokenType.SEMICOLON) or self._check(TokenType.RBRACE) or self._check(TokenType.EOF):
            return ReturnStmt(span=ret_token.span, value=None)
        value = self._parse_expression()
        span = self._merge_spans(ret_token.span, value.span)
        return ReturnStmt(span=span, value=value)

    def _parse_macro_stmt(self, hash_token: Token) -> MacroStmt:
        name_tok = self._consume(TokenType.IDENT, "Expected macro name after '#'.")
        self._consume(TokenType.LPAR, "Expected '(' after macro name.")
        args: list[Expr] = []
        if not self._check(TokenType.RPAR):
            while True:
                args.append(self._parse_expression())
                if not self._match(TokenType.COMMA):
                    break
        end_tok = self._consume(TokenType.RPAR, "Expected ')' after macro arguments.")
        span = self._merge_spans(hash_token.span, end_tok.span)
        return MacroStmt(span=span, name=name_tok.value, args=args)

    def _parse_block(self) -> tuple[list[Stmt], SourceSpan]:
        lbrace = self._consume(TokenType.LBRACE, "Expected '{' to start block.")
        statements: list[Stmt] = []
        self._consume_optional_semicolons()

        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._parse_statement()
            statements.append(stmt)
            self._consume_optional_semicolons()

        rbrace = self._consume(TokenType.RBRACE, "Expected '}' to close block.")
        return statements, self._merge_spans(lbrace.span, rbrace.span)

    def _parse_expression(self, min_prec: int = 1) -> Expr:
        expr = self._parse_unary()

        while True:
            tok = self._peek()
            prec = _PRECEDENCE.get(tok.token_type)
            if prec is None or prec < min_prec:
                break

            op = self._advance()
            right = self._parse_expression(prec + 1)
            span = self._merge_spans(expr.span, right.span)
            expr = BinaryExpr(span=span, left=expr, operator=op.value, right=right)

        return expr

    def _parse_unary(self) -> Expr:
        if self._match(TokenType.NOT, TokenType.MINUS, TokenType.PLUS):
            op = self._previous()
            operand = self._parse_unary()
            span = self._merge_spans(op.span, operand.span)
            return UnaryExpr(span=span, operator=op.value, operand=operand)
        return self._parse_postfix()

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()
        while self._match(TokenType.LPAR):
            args: list[Expr] = []
            if not self._check(TokenType.RPAR):
                while True:
                    args.append(self._parse_expression())
                    if not self._match(TokenType.COMMA):
                        break
            rpar = self._consume(TokenType.RPAR, "Expected ')' after call arguments.")
            span = self._merge_spans(expr.span, rpar.span)
            expr = CallExpr(span=span, callee=expr, args=args, at_prefixed=False)
        return expr

    def _parse_primary(self) -> Expr:
        if self._match(TokenType.NUMBER):
            tok = self._previous()
            value: int | float
            value = float(tok.value) if "." in tok.value else int(tok.value)
            return LiteralExpr(span=tok.span, value=value)

        if self._match(TokenType.STRING):
            tok = self._previous()
            return LiteralExpr(span=tok.span, value=tok.value)

        if self._match(TokenType.TRUE):
            tok = self._previous()
            return LiteralExpr(span=tok.span, value=True)

        if self._match(TokenType.FALSE):
            tok = self._previous()
            return LiteralExpr(span=tok.span, value=False)

        if self._match(TokenType.LAM):
            return self._parse_lambda_expr(self._previous())

        if self._match(TokenType.IDENT):
            tok = self._previous()
            return IdentifierExpr(span=tok.span, name=tok.value)

        if self._match(TokenType.AT):
            at_tok = self._previous()
            callee_tok = self._consume(TokenType.IDENT, "Expected callee identifier after '@'.")
            self._consume(TokenType.LPAR, "Expected '(' after @callee.")
            args: list[Expr] = []
            if not self._check(TokenType.RPAR):
                while True:
                    args.append(self._parse_expression())
                    if not self._match(TokenType.COMMA):
                        break
            end_tok = self._consume(TokenType.RPAR, "Expected ')' after call arguments.")
            callee = IdentifierExpr(span=callee_tok.span, name=callee_tok.value)
            span = self._merge_spans(at_tok.span, end_tok.span)
            return CallExpr(span=span, callee=callee, args=args, at_prefixed=True)

        if self._match(TokenType.LPAR):
            expr = self._parse_expression()
            self._consume(TokenType.RPAR, "Expected ')' to close grouped expression.")
            return expr

        tok = self._peek()
        raise ParseError(
            code="PAR001",
            message=f"Unexpected token {tok.token_type.name} in expression.",
            span=tok.span,
            hint="Use literals, identifiers, calls, or parenthesized expressions.",
        )

    def _parse_lambda_expr(self, lam_token: Token) -> LambdaExpr:
        self._consume(TokenType.LPAR, "Expected '(' after 'lam'.")
        params: list[Param] = []

        if not self._check(TokenType.RPAR):
            while True:
                param_name = self._consume(TokenType.IDENT, "Expected lambda parameter name.")
                param_type: str | None = None
                if self._match(TokenType.COLON):
                    param_type_tok = self._consume(TokenType.IDENT, "Expected parameter type after ':'.")
                    param_type = param_type_tok.value
                params.append(Param(name=param_name.value, type_hint=param_type))
                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RPAR, "Expected ')' after lambda parameters.")

        return_type: str | None = None
        if self._match(TokenType.COLON):
            return_type_tok = self._consume(TokenType.IDENT, "Expected lambda return type after ':'.")
            return_type = return_type_tok.value

        self._consume(TokenType.ARROW, "Expected '=>' in lambda expression.")
        body = self._parse_expression()
        span = self._merge_spans(lam_token.span, body.span)
        return LambdaExpr(span=span, params=params, body=body, return_type=return_type)

    def _is_assignment_start(self) -> bool:
        if not self._check(TokenType.IDENT):
            return False
        if self._peek(1).token_type == TokenType.ASSIGN:
            return True
        return (
            self._peek(1).token_type == TokenType.COLON
            and self._peek(2).token_type == TokenType.IDENT
            and self._peek(3).token_type == TokenType.ASSIGN
        )

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        tok = self._peek()
        raise ParseError(code="PAR002", message=message, span=tok.span, hint="Adjust token order to match grammar.")

    def _match(self, *token_types: TokenType) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        return self._peek().token_type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.pos += 1
        return self._previous()

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def _is_at_end(self) -> bool:
        return self._peek().token_type == TokenType.EOF

    def _consume_optional_semicolons(self) -> None:
        while self._match(TokenType.SEMICOLON):
            pass

    def _synchronize(self) -> None:
        while not self._is_at_end():
            if self._previous().token_type in {TokenType.SEMICOLON, TokenType.RBRACE}:
                return
            if self._peek().token_type in {TokenType.FN, TokenType.IF, TokenType.LOOP, TokenType.RET}:
                return
            self._advance()

    @staticmethod
    def _merge_spans(start: SourceSpan, end: SourceSpan) -> SourceSpan:
        return SourceSpan(
            file=start.file,
            line=start.line,
            column=start.column,
            end_line=end.end_line,
            end_column=end.end_column,
        )

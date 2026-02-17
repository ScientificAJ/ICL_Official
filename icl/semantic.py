"""Semantic analysis and type inference for ICL AST."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    Program,
    ReturnStmt,
    Stmt,
    UnaryExpr,
)
from icl.errors import SemanticError
from icl.source_map import SourceSpan


TYPE_ANY = "Any"
TYPE_NUM = "Num"
TYPE_STR = "Str"
TYPE_BOOL = "Bool"
TYPE_VOID = "Void"
TYPE_FN = "Fn"


@dataclass
class SymbolInfo:
    """Symbol table entry for variables and functions."""

    name: str
    type_name: str
    is_function: bool = False
    arity: int | None = None
    return_type: str | None = None
    param_types: list[str] = field(default_factory=list)


@dataclass
class Scope:
    """Lexical scope with parent chaining."""

    parent: "Scope | None" = None
    symbols: dict[str, SymbolInfo] = field(default_factory=dict)

    def define(self, symbol: SymbolInfo) -> None:
        """Define symbol in current scope."""
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> SymbolInfo | None:
        """Resolve a symbol in current or parent scopes."""
        scope: Scope | None = self
        while scope is not None:
            found = scope.symbols.get(name)
            if found is not None:
                return found
            scope = scope.parent
        return None


@dataclass
class SemanticResult:
    """Semantic model output used by later compiler stages."""

    global_scope: Scope
    inferred_expr_types: dict[int, str]


class SemanticAnalyzer:
    """Performs scope, binding, and type checks."""

    def __init__(self) -> None:
        self._expr_types: dict[int, str] = {}

    def analyze(self, program: Program) -> SemanticResult:
        """Run semantic analysis for a full AST."""
        global_scope = Scope(parent=None)
        self._define_builtins(global_scope)

        for stmt in program.statements:
            if isinstance(stmt, FunctionDefStmt):
                self._register_function_signature(global_scope, stmt)

        for stmt in program.statements:
            self._analyze_stmt(stmt, global_scope, in_function=False, expected_return_type=None)

        return SemanticResult(global_scope=global_scope, inferred_expr_types=dict(self._expr_types))

    def _define_builtins(self, scope: Scope) -> None:
        scope.define(
            SymbolInfo(
                name="print",
                type_name=TYPE_FN,
                is_function=True,
                arity=1,
                return_type=TYPE_VOID,
                param_types=[TYPE_ANY],
            )
        )

    def _register_function_signature(self, scope: Scope, stmt: FunctionDefStmt) -> None:
        if scope.resolve(stmt.name) and stmt.name in scope.symbols:
            raise SemanticError(
                code="SEM001",
                message=f"Function '{stmt.name}' is already defined in this scope.",
                span=stmt.span,
                hint="Use a unique function name or rename the existing function.",
            )
        param_types = [param.type_hint or TYPE_ANY for param in stmt.params]
        scope.define(
            SymbolInfo(
                name=stmt.name,
                type_name=TYPE_FN,
                is_function=True,
                arity=len(stmt.params),
                return_type=stmt.return_type or TYPE_ANY,
                param_types=param_types,
            )
        )

    def _analyze_stmt(
        self,
        stmt: Stmt,
        scope: Scope,
        in_function: bool,
        expected_return_type: str | None,
    ) -> bool:
        if isinstance(stmt, AssignmentStmt):
            value_type = self._infer_expr_type(stmt.value, scope)
            target_type = stmt.type_hint or value_type
            if stmt.type_hint and not self._is_compatible(stmt.type_hint, value_type):
                raise SemanticError(
                    code="SEM002",
                    message=(
                        f"Cannot assign value of type '{value_type}' "
                        f"to '{stmt.name}' annotated as '{stmt.type_hint}'."
                    ),
                    span=stmt.span,
                    hint="Align annotation with expression type or cast in source.",
                )
            scope.define(SymbolInfo(name=stmt.name, type_name=target_type))
            return False

        if isinstance(stmt, ExpressionStmt):
            self._infer_expr_type(stmt.expr, scope)
            return False

        if isinstance(stmt, IfStmt):
            cond_type = self._infer_expr_type(stmt.condition, scope)
            if cond_type not in {TYPE_BOOL, TYPE_ANY}:
                raise SemanticError(
                    code="SEM003",
                    message=f"If condition expects Bool, got '{cond_type}'.",
                    span=stmt.condition.span,
                    hint="Use comparison/logical expressions for conditions.",
                )

            then_scope = Scope(parent=scope)
            else_scope = Scope(parent=scope)
            then_returns = False
            else_returns = False
            for then_stmt in stmt.then_block:
                then_returns = self._analyze_stmt(
                    then_stmt,
                    then_scope,
                    in_function=in_function,
                    expected_return_type=expected_return_type,
                ) or then_returns
            for else_stmt in stmt.else_block:
                else_returns = self._analyze_stmt(
                    else_stmt,
                    else_scope,
                    in_function=in_function,
                    expected_return_type=expected_return_type,
                ) or else_returns
            return then_returns and else_returns and bool(stmt.else_block)

        if isinstance(stmt, LoopStmt):
            start_type = self._infer_expr_type(stmt.start, scope)
            end_type = self._infer_expr_type(stmt.end, scope)
            if start_type not in {TYPE_NUM, TYPE_ANY} or end_type not in {TYPE_NUM, TYPE_ANY}:
                raise SemanticError(
                    code="SEM004",
                    message="Loop bounds must evaluate to Num.",
                    span=stmt.span,
                    hint="Convert loop bound expressions to numbers.",
                )
            loop_scope = Scope(parent=scope)
            loop_scope.define(SymbolInfo(name=stmt.iterator, type_name=TYPE_NUM))
            for loop_stmt in stmt.body:
                self._analyze_stmt(
                    loop_stmt,
                    loop_scope,
                    in_function=in_function,
                    expected_return_type=expected_return_type,
                )
            return False

        if isinstance(stmt, FunctionDefStmt):
            fn_symbol = scope.resolve(stmt.name)
            if fn_symbol is None or not fn_symbol.is_function:
                raise SemanticError(
                    code="SEM005",
                    message=f"Function signature for '{stmt.name}' is missing.",
                    span=stmt.span,
                    hint="Function signatures must be registered before body analysis.",
                )
            fn_scope = Scope(parent=scope)
            for idx, param in enumerate(stmt.params):
                fn_scope.define(
                    SymbolInfo(
                        name=param.name,
                        type_name=fn_symbol.param_types[idx],
                    )
                )

            if stmt.expr_body is not None:
                expr_type = self._infer_expr_type(stmt.expr_body, fn_scope)
                if stmt.return_type and not self._is_compatible(stmt.return_type, expr_type):
                    raise SemanticError(
                        code="SEM006",
                        message=(
                            f"Function '{stmt.name}' returns '{expr_type}' "
                            f"but is annotated as '{stmt.return_type}'."
                        ),
                        span=stmt.expr_body.span,
                        hint="Adjust return annotation or expression type.",
                    )
                return False

            found_return = False
            for body_stmt in stmt.body:
                found_return = self._analyze_stmt(
                    body_stmt,
                    fn_scope,
                    in_function=True,
                    expected_return_type=stmt.return_type,
                ) or found_return

            if stmt.return_type and stmt.return_type != TYPE_VOID and not found_return:
                raise SemanticError(
                    code="SEM007",
                    message=f"Function '{stmt.name}' is missing a return value.",
                    span=stmt.span,
                    hint="Add a ret statement in all execution paths.",
                )
            return False

        if isinstance(stmt, ReturnStmt):
            if not in_function:
                raise SemanticError(
                    code="SEM008",
                    message="Return statements are only valid inside functions.",
                    span=stmt.span,
                    hint="Move ret into a fn block or remove it.",
                )
            value_type = TYPE_VOID
            if stmt.value is not None:
                value_type = self._infer_expr_type(stmt.value, scope)
            if expected_return_type and not self._is_compatible(expected_return_type, value_type):
                raise SemanticError(
                    code="SEM009",
                    message=(
                        f"Return type '{value_type}' does not satisfy "
                        f"expected '{expected_return_type}'."
                    ),
                    span=stmt.span,
                    hint="Change ret expression or function return annotation.",
                )
            return True

        if isinstance(stmt, MacroStmt):
            raise SemanticError(
                code="SEM010",
                message=f"Unexpanded macro '#{stmt.name}' reached semantic analysis.",
                span=stmt.span,
                hint="Register a macro plugin for this macro or remove it.",
            )

        raise SemanticError(
            code="SEM099",
            message=f"Unsupported statement type '{type(stmt).__name__}'.",
            span=stmt.span,
            hint="Extend semantic analyzer for this statement kind.",
        )

    def _infer_expr_type(self, expr: Expr, scope: Scope) -> str:
        if isinstance(expr, LiteralExpr):
            if isinstance(expr.value, bool):
                return self._record(expr, TYPE_BOOL)
            if isinstance(expr.value, (int, float)):
                return self._record(expr, TYPE_NUM)
            if isinstance(expr.value, str):
                return self._record(expr, TYPE_STR)
            return self._record(expr, TYPE_ANY)

        if isinstance(expr, IdentifierExpr):
            symbol = scope.resolve(expr.name)
            if symbol is None:
                raise SemanticError(
                    code="SEM011",
                    message=f"Undefined symbol '{expr.name}'.",
                    span=expr.span,
                    hint="Declare the variable or function before use.",
                )
            if symbol.is_function:
                return self._record(expr, TYPE_FN)
            return self._record(expr, symbol.type_name)

        if isinstance(expr, UnaryExpr):
            operand_type = self._infer_expr_type(expr.operand, scope)
            if expr.operator == "!":
                if operand_type not in {TYPE_BOOL, TYPE_ANY}:
                    raise SemanticError(
                        code="SEM012",
                        message=f"Unary '!' expects Bool, got '{operand_type}'.",
                        span=expr.span,
                        hint="Use '!' with boolean expressions.",
                    )
                return self._record(expr, TYPE_BOOL)
            if expr.operator in {"+", "-"}:
                if operand_type not in {TYPE_NUM, TYPE_ANY}:
                    raise SemanticError(
                        code="SEM013",
                        message=f"Unary '{expr.operator}' expects Num, got '{operand_type}'.",
                        span=expr.span,
                        hint="Use numeric expressions with unary +/-.",
                    )
                return self._record(expr, TYPE_NUM)
            return self._record(expr, TYPE_ANY)

        if isinstance(expr, BinaryExpr):
            left = self._infer_expr_type(expr.left, scope)
            right = self._infer_expr_type(expr.right, scope)
            op = expr.operator

            if op in {"+", "-", "*", "/", "%"}:
                if op == "+" and left == TYPE_STR and right == TYPE_STR:
                    return self._record(expr, TYPE_STR)
                if left in {TYPE_NUM, TYPE_ANY} and right in {TYPE_NUM, TYPE_ANY}:
                    return self._record(expr, TYPE_NUM)
                raise SemanticError(
                    code="SEM014",
                    message=f"Operator '{op}' requires numeric operands.",
                    span=expr.span,
                    hint="Use Num operands or convert expression types.",
                )

            if op in {"==", "!="}:
                return self._record(expr, TYPE_BOOL)

            if op in {"<", "<=", ">", ">="}:
                if left not in {TYPE_NUM, TYPE_ANY} or right not in {TYPE_NUM, TYPE_ANY}:
                    raise SemanticError(
                        code="SEM015",
                        message=f"Comparison '{op}' requires Num-compatible operands.",
                        span=expr.span,
                        hint="Compare numeric values for ordering operators.",
                    )
                return self._record(expr, TYPE_BOOL)

            if op in {"&&", "||"}:
                if left not in {TYPE_BOOL, TYPE_ANY} or right not in {TYPE_BOOL, TYPE_ANY}:
                    raise SemanticError(
                        code="SEM016",
                        message=f"Logical operator '{op}' requires Bool operands.",
                        span=expr.span,
                        hint="Use logical operators with boolean expressions.",
                    )
                return self._record(expr, TYPE_BOOL)

            return self._record(expr, TYPE_ANY)

        if isinstance(expr, LambdaExpr):
            lambda_scope = Scope(parent=scope)
            for param in expr.params:
                lambda_scope.define(SymbolInfo(name=param.name, type_name=param.type_hint or TYPE_ANY))

            body_type = self._infer_expr_type(expr.body, lambda_scope)
            if expr.return_type and not self._is_compatible(expr.return_type, body_type):
                raise SemanticError(
                    code="SEM021",
                    message=(
                        f"Lambda returns '{body_type}' "
                        f"but is annotated as '{expr.return_type}'."
                    ),
                    span=expr.span,
                    hint="Adjust lambda return annotation or expression type.",
                )
            return self._record(expr, TYPE_FN)

        if isinstance(expr, CallExpr):
            for arg in expr.args:
                self._infer_expr_type(arg, scope)

            callee_type = self._infer_expr_type(expr.callee, scope)
            if isinstance(expr.callee, IdentifierExpr):
                symbol = scope.resolve(expr.callee.name)
                if symbol is None:
                    raise SemanticError(
                        code="SEM017",
                        message=f"Call target '{expr.callee.name}' is undefined.",
                        span=expr.span,
                        hint="Define function before calling it.",
                    )
                if symbol.is_function:
                    if symbol.arity is not None and symbol.arity != len(expr.args):
                        raise SemanticError(
                            code="SEM019",
                            message=(
                                f"Function '{expr.callee.name}' expects {symbol.arity} args, "
                                f"got {len(expr.args)}."
                            ),
                            span=expr.span,
                            hint="Adjust call argument count.",
                        )
                    return self._record(expr, symbol.return_type or TYPE_ANY)

                if symbol.type_name in {TYPE_FN, TYPE_ANY}:
                    return self._record(expr, TYPE_ANY)

                raise SemanticError(
                    code="SEM018",
                    message=f"Symbol '{expr.callee.name}' is not callable.",
                    span=expr.span,
                    hint="Only function symbols or Fn-typed values can be invoked.",
                )

            if callee_type not in {TYPE_FN, TYPE_ANY}:
                raise SemanticError(
                    code="SEM020",
                    message="Call expression target is not callable.",
                    span=expr.span,
                    hint="Use identifier/function references as call targets.",
                )
            return self._record(expr, TYPE_ANY)

        raise SemanticError(
            code="SEM098",
            message=f"Unsupported expression type '{type(expr).__name__}'.",
            span=getattr(expr, "span", None),
            hint="Extend semantic inference for this expression kind.",
        )

    def _record(self, expr: Expr, inferred: str) -> str:
        self._expr_types[id(expr)] = inferred
        return inferred

    @staticmethod
    def _is_compatible(expected: str, actual: str) -> bool:
        if expected == TYPE_ANY or actual == TYPE_ANY:
            return True
        if expected == actual:
            return True
        if expected == TYPE_VOID and actual == TYPE_VOID:
            return True
        return False


def span_or_none(node: Any) -> SourceSpan | None:
    """Best-effort span extraction helper for diagnostics."""
    return getattr(node, "span", None)

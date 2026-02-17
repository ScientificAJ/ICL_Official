# ICL Semantics Guide (v2)

This guide summarizes active compiler behavior. The normative source is `ICL_LANGUAGE_CONTRACT.md`.

## Semantic Core
- Lexical scoping with parent chaining.
- Symbolic type model (`Num`, `Str`, `Bool`, `Any`, `Fn`, `Void`).
- Deterministic operator precedence and statement ordering.
- Function signatures pre-registered before body analysis.
- `lam(...) => expr` values are first-class `Fn` expressions.
- `Fn`-typed symbols are callable (with dynamic return type unless statically declared).

## Condition and Loop Rules
- `if` conditions require `Bool` or `Any`.
- `loop` bounds require `Num` or `Any`.

## Return Rules
- `ret` allowed only inside functions.
- Annotated function returns must satisfy annotation compatibility.

## Macro Rules
- Macro statements must be expanded before semantic phase.
- Unexpanded macro at semantic phase is an error.

## Pipeline Context
`Source -> AST -> IR -> Lowered -> Pack Emit -> Scaffold`

## Diagnostics
- Lex: `LEX*`
- Parse: `PAR*`
- Semantic: `SEM*`
- Lowering: `LOW*`
- Pack: `PACK*`
- CLI/service: `CLI*`, `SRV*`

## Debug Workflow
- `icl check` for semantic validity.
- `icl explain` for AST/IR/lowered/graph inspection.
- `icl contract test` for cross-target contract validation.

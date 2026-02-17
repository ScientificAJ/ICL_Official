# ICL Coding Standards (v2)

## 1. Architectural Boundaries
- Parser/semantic define language behavior.
- IR/lowering define target-agnostic and target-shaped semantics.
- Language packs define syntax/scaffolding only.
- Do not move semantic rules into emitters.

## 2. Naming Rules
- AST statements end with `Stmt`; expressions end with `Expr`.
- IR nodes use `IR*` prefixes.
- Lowered nodes use `Lowered*` prefixes.
- Pack IDs must be globally unique (`icl.<scope>.<target>`).

## 3. Compatibility Rules
- Stable packs must satisfy language contract semantics.
- Experimental packs must fail explicitly for unsupported features.
- Feature support must be declared in `feature_coverage`.

## 4. Change Protocol
For grammar changes:
- update lexer/parser
- update `ICL_LANGUAGE_CONTRACT.md`
- update docs and tests

For semantic changes:
- update semantic analyzer
- update IR/lowering mapping
- update contract tests and target expectations

For pack changes:
- update pack manifest coverage
- validate with `icl pack validate`
- run `icl contract test`

## 5. Error Discipline
- Use phase-owned error families (`LEX*`, `PAR*`, `SEM*`, `LOW*`, `PACK*`, `CLI*`, `SRV*`).
- Never silently drop unsupported constructs.

## 6. Test Discipline
- Run full test suite before merge.
- Stable pack changes require contract suite pass.
- Regressions in existing examples are disallowed.

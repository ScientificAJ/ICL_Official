# ICL Language Contract (v2.0)

This file is the normative source of truth for compiler core and language packs.

## 1. Construct Inventory
### Statements
- Assignment: `name := expr` or `name:Type := expr`
- Function definition:
  - expression body: `fn name(args):Type => expr`
  - block body: `fn name(args):Type { ... }`
- Conditional: `if expr ? { ... } : { ... }`
- Loop: `loop i in start..end { ... }`
- Return: `ret` or `ret expr`
- Macro invocation statement: `#name(args)` (must expand before semantic pass)
- Expression statement: `expr`

### Expressions
- Literals: number, string, `true`, `false`
- Identifier reference
- Unary ops: `!`, `+`, `-`
- Binary ops: `+ - * / % == != < <= > >= && ||`
- Lambda: `lam(args):Type => expr`
- Calls: `name(args)` and `@name(args)`
- Grouping: `(expr)`

## 2. Semantic Behavior
- Assignments infer RHS type first, then validate annotation compatibility.
- Top-level function signatures are registered before body analysis.
- `if` condition must be `Bool` or `Any`.
- `loop` bounds must be `Num` or `Any`.
- `ret` is legal only in function scope.
- Function return annotations must be satisfied by return expressions.
- Unexpanded macros are semantic errors.

## 3. Scope Rules
- Lexical scoping with parent chain.
- Function parameters are function-local.
- Loop iterator is loop-local.
- Branch-local assignments do not leak to parent scope.

## 4. Expression Evaluation Rules
- Operator precedence is deterministic:
  - `||`
  - `&&`
  - equality
  - comparison
  - `+ -`
  - `* / %`
  - unary
  - postfix call
- Binary operations are left-associative under Pratt precedence implementation.
- Function calls evaluate callee then args in source order.
- Lambda expressions capture lexical scope and evaluate as first-class `Fn` values.

## 5. Truthiness Model
- Contract-level condition type is `Bool` (or unresolved `Any` prior to specialization).
- No implicit compile-time truthiness coercion is injected by core pipeline.
- If an `Any` reaches target emission, runtime truth semantics are target-native and must be documented by the pack.

## 6. Type Model
- Symbolic core types: `Num`, `Str`, `Bool`, `Any`, `Fn`, `Void`.
- `Any` is top-compatibility type.
- Type annotations constrain inferred values.
- Call arity is checked for resolved function symbols.
- `lam` expressions infer as `Fn`; annotated lambda return types must match inferred body type.
- `Fn`-typed values are callable; unresolved callable metadata returns `Any`.
- Cross-target stable guarantee is semantic parity, not identical native type syntax.

## 7. Error Model
### Phase-Owned Error Families
- Lex errors: `LEX*`
- Parse errors: `PAR*`
- Semantic errors: `SEM*`
- Plugin/pack errors: `PLG*`, `PACK*`
- Lowering errors: `LOW*`
- CLI/service/internal orchestration: `CLI*`, `SRV*`

### Required Behavior
- Errors must provide: code, message, optional span, optional hint.
- Unsupported stable-contract feature in a target must fail explicitly (no silent drop).
- Experimental packs may emit best-effort output only when feature coverage declares support.

## 8. Compatibility Classes
- `required-core`: must work in all stable packs.
- `required-stable`: must work in each stable pack marked compatible.
- `optional-pack`: pack may support with explicit declaration.
- `unsupported-must-error`: must produce explicit compile error.

## 9. Contract Gate for Stability
A pack cannot be marked `stable` unless contract test cases pass at 100% for all features declared as required-stable.

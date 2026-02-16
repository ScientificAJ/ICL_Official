# ICL Coding Standards

This standard is implementation-aligned with the current compiler in `icl/`.
It defines contributor rules, style rules, and compatibility rules that preserve parser, semantic, and backend behavior.

## 1. Naming Conventions

### 1.1 Source Identifier Naming
- Valid identifier regex: `^[A-Za-z_][A-Za-z0-9_]*$`.
- Keywords are reserved and cannot be identifiers:
- `fn`, `if`, `loop`, `in`, `ret`, `true`, `false`
- Recommended style for user code:
- Variables/functions: `snake_case`
- Type annotation labels: `PascalCase` symbolic labels (`Num`, `Str`, `Bool`, `Any`, `Void`)

### 1.2 Token Naming Rules
- `TokenType` enum names must be all-caps with underscores (`ASSIGN`, `QUESTION`, `LBRACE`).
- Keyword token names are upper-case keyword aliases (`FN`, `IF`, `LOOP`, etc.).
- Multi-character symbols must be explicit in lexer mapping (`:=`, `=>`, `..`, `==`, `!=`, `<=`, `>=`, `&&`, `||`).

### 1.3 AST and Intent Naming Rules
- AST statement classes must end with `Stmt` (`AssignmentStmt`, `IfStmt`, `LoopStmt`).
- AST expression classes must end with `Expr` (`BinaryExpr`, `CallExpr`).
- Intent graph node kinds must end with `Intent` (`ControlIntent`, `OperationIntent`).
- Edge names are lower snake-case semantic relations (`contains_then`, `return_expr`, `operand`).

### 1.4 Backend Naming Rules
- Backend emitter class names follow `<Target>Backend` (`PythonBackend`, `JavaScriptBackend`, `RustBackend`).
- Backend `name` values are stable CLI target ids:
- `python`, `js`, `rust`
- Backend modules use snake case under `icl/expanders/`.

### 1.5 File and Module Naming Structure
- Core modules remain flat under `icl/`.
- Backends belong in `icl/expanders/`.
- Built-in plugins belong in `icl/plugins/`.
- Tests mirror behavior by concern under `tests/`.

## 2. Structural Rules

### 2.1 Statement Formatting
- Compiler accepts optional semicolons and whitespace-insensitive layout.
- Project standard: one statement per line in authored `.icl` files.
- Use semicolons consistently when writing compact single-line code.

### 2.2 Block and Arrow Usage
- `if` and `loop` always require `{ ... }` blocks.
- `fn` may use:
- expression body: `fn name(args) => expr`
- block body: `fn name(args) { ... }`
- `=>` is only for expression-bodied function definitions.

### 2.3 Whitespace and Comments
- Whitespace has no semantic meaning except token separation.
- Newlines do not terminate statements by themselves.
- Only line comments are supported: `// ...`.
- No block comment syntax exists.

### 2.4 Call Forms
- Two valid forms:
- `@name(arg1, arg2)`
- `name(arg1, arg2)`
- Use `@name(...)` for intent-forward DSL style consistency in examples and docs.

## 3. Intent Clarity Rules

### 3.1 Avoid Ambiguous Compression
- Do not remove structural delimiters (`?`, `{}`, `..`, `:=`) for stylistic compression.
- Prefer explicit grouping with parentheses in mixed-precedence expressions.

### 3.2 Expand vs Compress Guidance
- Authoring mode: readable canonical forms with clear spacing.
- Compression mode (`icl compress`): for transport/caching/model IO, not primary teaching format.

### 3.3 Explicit vs Inferred Declarations
- Inference is default and valid.
- Add type annotations when:
- API boundaries depend on stable symbolic type intent.
- function return behavior should be enforced (`fn ... :Num`).
- cross-backend readability matters.

### 3.4 Scope Clarity
- Variables assigned inside `if`/`loop` are scoped to nested semantic scopes.
- Do not rely on branch/body assignments to define symbols for outer-scope semantic use.

## 4. Backend Compatibility Rules

### 4.1 Target-Agnostic Source Rule
- ICL source must avoid target-specific syntax assumptions.
- Use only language-level constructs represented in AST/IntentGraph.

### 4.2 No Backend-Dependent Tokens
- Do not introduce tokens that encode one backend runtime directly.
- Backend-specific behavior belongs in emitter logic, not lexer/parser grammar.

### 4.3 Template Isolation Requirements
- Backend emitters must only consume IntentGraph node kinds/edges/attrs.
- Backend emitters must not read raw source text.
- Shared compile semantics remain in lexer/parser/semantic graph phases.

### 4.4 Cross-Backend Robustness Practice
- Declare variables outside conditionals if reused across branches.
- Rationale: JS backend declaration tracking is flow-insensitive and first-assignment based.

## 5. Contributor Rules

### 5.1 Grammar Change Protocol
For any syntax change:
- Update parser rules in `icl/parser.py`.
- Update lexical tokenization in `icl/tokens.py` and `icl/lexer.py`.
- Update formal grammar docs (`ICL_SEMANTICS_GUIDE.md` + `docs/language_spec.md`).
- Add parser and CLI tests.

### 5.2 AST Change Protocol
For any AST node addition/change:
- Update AST dataclasses in `icl/ast.py`.
- Update semantic analyzer in `icl/semantic.py`.
- Update graph builder in `icl/graph.py`.
- Update all backends in `icl/expanders/`.
- Update compact serializer in `icl/main.py` (`_emit_stmt_compact` / `_emit_expr_compact`).

### 5.3 Token Addition Protocol
For any token addition:
- Add `TokenType` enum member.
- Add lexing rules (`_lex_multi_char_operator` or `_SINGLE_CHAR_TOKENS`).
- Add parser consumption/matching logic.
- Add lexer/parser tests.

### 5.4 Semantic Safety Protocol
- New AST forms must not bypass semantic validation.
- Unexpanded macros must not reach semantic phase.
- Type and scope checks must remain deterministic.

### 5.5 Intent Graph Contract Protocol
- New semantic constructs require explicit node kind and edge typing.
- Maintain ordered edges (`order`) where sequence matters.
- Preserve `SourceMap` provenance for each created node.

### 5.6 CLI and Error Stability
- Keep diagnostic code-style stable (`LEX*`, `PAR*`, `SEM*`, `PLG*`, `CLI*`).
- Preserve exit code semantics:
- `0` success
- `1` compiler error (`CompilerError`)
- `2` CLI usage error
- `3` internal error

## 6. AI Training Data Rules

### 6.1 Canonicalization
- For model training corpora, canonicalize source with `icl compress` only when compact format is required.
- Keep a readable canonical source copy for human audit.

### 6.2 Artifact Pairing
- Pair each training sample with:
- original ICL source
- emitted target code
- intent graph JSON
- source map JSON

### 6.3 Plugin Reproducibility
- If samples depend on plugins, record exact plugin specs (`module[:symbol]`).
- Do not treat plugin-expanded syntax as core grammar unless added to parser/lexer.

### 6.4 Deterministic Evaluation Setup
- Keep compiler flags explicit in dataset generation (`target`, `--optimize`, plugin set).
- Avoid mixing optimized and non-optimized graph artifacts in one label set without annotation.

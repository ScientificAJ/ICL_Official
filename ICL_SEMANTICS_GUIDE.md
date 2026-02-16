# ICL Semantic Specification

This specification is reverse-engineered from the active implementation in:
- `icl/tokens.py`
- `icl/lexer.py`
- `icl/parser.py`
- `icl/semantic.py`
- `icl/graph.py`
- `icl/main.py`
- `icl/cli.py`
- `icl/plugin.py`

## 1. Formal Grammar (EBNF)

The grammar below matches parser behavior, including optional semicolons and expression precedence.

```ebnf
program          = { opt_semicolons, statement, opt_semicolons }, EOF ;
opt_semicolons   = { ";" } ;

statement        = function_def
                 | if_stmt
                 | loop_stmt
                 | return_stmt
                 | macro_stmt
                 | assignment
                 | expression_stmt ;

assignment       = IDENT, [ ":", IDENT ], ":=", expression ;

function_def     = "fn", IDENT, "(", [ params ], ")", [ ":", IDENT ],
                   ( "=>", expression | block ) ;
params           = param, { ",", param } ;
param            = IDENT, [ ":", IDENT ] ;

if_stmt          = "if", expression, "?", block, [ ":", block ] ;

loop_stmt        = "loop", IDENT, "in", expression, "..", expression, block ;

return_stmt      = "ret", [ expression ] ;

macro_stmt       = "#", IDENT, "(", [ arguments ], ")" ;
arguments        = expression, { ",", expression } ;

expression_stmt  = expression ;

block            = "{", opt_semicolons,
                   { statement, opt_semicolons },
                   "}" ;

expression       = logical_or ;
logical_or       = logical_and, { "||", logical_and } ;
logical_and      = equality, { "&&", equality } ;
equality         = comparison, { ( "==" | "!=" ), comparison } ;
comparison       = term, { ( "<" | "<=" | ">" | ">=" ), term } ;
term             = factor, { ( "+" | "-" ), factor } ;
factor           = unary, { ( "*" | "/" | "%" ), unary } ;
unary            = ( "!" | "-" | "+" ), unary | postfix ;
postfix          = primary, { "(", [ arguments ], ")" } ;

primary          = NUMBER
                 | STRING
                 | "true"
                 | "false"
                 | IDENT
                 | "@", IDENT, "(", [ arguments ], ")"
                 | "(", expression, ")" ;
```

### Lexical Constraints
- Identifier start: letter or `_`
- Identifier continuation: alnum or `_`
- Number literals: integer or decimal (single decimal point)
- String delimiters: `"..."`
- Supported escapes in strings: `\n`, `\t`, `\"`, `\\`
- Comment syntax: `//` to end-of-line
- Whitespace is ignored except as token separator

### Reserved Keywords
- `fn`, `if`, `loop`, `in`, `ret`, `true`, `false`

## 2. Execution Model

ICL compiler behavior is a deterministic transformation pipeline:

```text
Source Text
  -> Lexer (Token stream)
  -> Parser (AST)
  -> Syntax plugins (optional preprocess/transform)
  -> Macro expansion plugins
  -> Semantic analysis (scope + types)
  -> Intent Graph build + source map
  -> Optional graph optimization
  -> Backend expansion (python/js/rust)
```

### 2.1 Assignment Binding
- Assignment syntax: `name := expr` or `name:Type := expr`.
- Semantic rule:
- RHS is type-inferred first.
- If type annotation exists, inferred type must be compatible.
- Symbol is defined in current scope after RHS analysis.

### 2.2 Scope Resolution
- Lexical scope with parent chaining.
- Global scope includes built-in function `print` with arity `1` and return `Void`.
- Function parameters define function-local symbols.
- `if` branches and `loop` body each analyze in child scopes.
- Symbols defined in nested scopes are not exported to parent scope.

### 2.3 Control Flow Interpretation
- `if` condition must infer to `Bool` or `Any`.
- `loop` bounds must infer to `Num` or `Any`.
- Return statements are legal only inside function bodies.

### 2.4 Function Semantics
- All top-level function signatures are pre-registered before statement analysis.
- This allows calls to functions declared later in the file.
- Function return annotation check:
- expression-bodied `fn ... => expr` must match declared return type.
- block-bodied function with declared non-`Void` return must have at least one statically recognized return-guaranteeing statement.

### 2.5 Determinism Guarantees
- Parser precedence and associativity are fixed.
- Graph node IDs are assigned sequentially (`n1`, `n2`, ...).
- Edge ordering is explicit via `order` and read through sorted traversal.
- Backends emit by ordered `contains` traversal from graph root.

## 3. Intent Graph Specification

## 3.1 Graph Data Model
- Graph type: directed typed multigraph.
- Root node: `ModuleIntent` (`root_id`).
- Node fields: `node_id`, `kind`, `attrs`.
- Edge fields: `source`, `target`, `edge_type`, `order`.

## 3.2 Node Types (Implementation Names + Canonical Labels)

| Canonical label | Implemented `kind` |
|---|---|
| ControlNode | `ControlIntent` |
| OperationNode | `OperationIntent` |
| AssignmentNode | `AssignmentIntent` |
| ExpansionNode | `ExpansionIntent` |
| ModuleNode | `ModuleIntent` |
| LoopNode | `LoopIntent` |
| FunctionNode | `FuncIntent` |
| CallNode | `CallIntent` |
| ReturnNode | `ReturnIntent` |
| LiteralNode | `LiteralIntent` |
| ReferenceNode | `RefIntent` |
| ExpressionNode | `ExpressionIntent` |

## 3.3 Edge Types
- Structural:
- `contains`, `contains_then`, `contains_else`, `contains_body`
- Data and control operands:
- `value`, `expr`, `condition`, `start`, `end`, `operand`, `arg`, `callee`, `return_expr`

## 3.4 Graph Constraints
- Graph built by `IntentGraphBuilder` is acyclic by construction.
- No cycle validation is enforced at `IntentGraph` API level.
- Execution order model:
- For module-level and block-level sequencing, use edges with `order`.
- `child_ids(source, edge_type)` returns children sorted by `order`.

## 3.5 Parent-Child Semantics
- Each top-level statement is linked from root by `contains` with statement index order.
- Compound statements own body/branch statements through specialized `contains_*` edges.
- Expression subtrees are connected from statement or expression owner nodes via relation-specific edges.

## 4. Error Model

## 4.1 Diagnostic Shape
- All compiler errors derive from `CompilerError` and can be converted to:
- code
- message
- optional source span (`file`, `line`, `column`, `end_line`, `end_column`)
- optional hint

## 4.2 Lexical Errors (`LEX*`)
- `LEX001`: unexpected character
- `LEX002`: unterminated string literal

## 4.3 Parse Errors (`PAR*`)
- `PAR001`: unexpected token in expression
- `PAR002`: expected token/form mismatch
- Parser may aggregate multiple parse errors into one raised `ParseError` message.

## 4.4 Semantic Errors (`SEM*`)
- `SEM001` duplicate function in same scope
- `SEM002` assignment annotation/type mismatch
- `SEM003` non-boolean `if` condition
- `SEM004` non-numeric loop bounds
- `SEM005` missing function signature during body analysis
- `SEM006` function expression-body return mismatch
- `SEM007` missing required function return
- `SEM008` `ret` outside function
- `SEM009` return expression type mismatch
- `SEM010` unexpanded macro reached semantic stage
- `SEM011` undefined symbol
- `SEM012` invalid unary `!` operand type
- `SEM013` invalid unary `+`/`-` operand type
- `SEM014` invalid arithmetic operand types
- `SEM015` invalid comparison operand types
- `SEM016` invalid logical operand types
- `SEM017` call target undefined
- `SEM018` call target not callable
- `SEM019` call arity mismatch
- `SEM020` dynamic call target not callable
- `SEM098` unsupported expression type
- `SEM099` unsupported statement type

## 4.5 Plugin Errors (`PLG*`)
- `PLG001` unknown backend target
- `PLG002` macro missing plugin
- `PLG003` plugin symbol not found
- `PLG004` empty plugin spec
- `PLG005` plugin import failure
- `PLG006` unsupported plugin export type
- `PLG007` unsupported plugin callable signature
- `PLG008` plugin callable runtime failure
- Built-in macro plugin errors:
- `PLG101` invalid `#echo` arg count
- `PLG102` invalid `#dbg` arg count

## 4.6 Expansion and CLI Errors
- `ExpansionError` class exists for backend expansion failures but is not emitted by built-in backends currently.
- CLI-specific diagnostics:
- `CLI001` usage/argument error
- `CLI999` internal unhandled error

CLI exit codes:
- `0` success
- `1` compiler error (`CompilerError`)
- `2` CLI usage error
- `3` internal error

## 5. Backend Expansion Structure

### 5.1 Emitter Contract
- All backends implement `BackendEmitter`.
- Required interface:
- `name` property (CLI target id)
- `emit_module(graph, context) -> str`
- Shared helper:
- `BackendEmitter.indent(text, level, unit="    ")`

### 5.2 Built-in Backend Behaviors
- `python`:
- Emits top-level statements in graph `contains` order.
- Maps `&&`/`||` to `and`/`or`.
- `js`:
- Tracks first assignment names and emits `let` on first assignment only.
- Emits C-style `for` loops from `LoopIntent`.
- `rust` (scaffold):
- Emits function nodes before `main`.
- Uses `f64` function params and `let mut` assignments.
- Rewrites `print(...)` call intents to `println!(...)` statements in expression context.

### 5.3 Expansion Input Guarantees
- Backends receive semantically validated graph when compile flow succeeds.
- Backends do not perform source parsing or type inference.
- Source-map generation occurs before backend emission and is backend-independent.

## 6. CLI Behavior Specification

Commands:
- `compile`
- `check`
- `explain`
- `compress`
- `diff`

`compile`:
- input from file or `--code` (mutually exclusive)
- requires `--target`
- optional: `--plugin`, `--emit-graph`, `--emit-sourcemap`, `--optimize`, `--debug`

`check`:
- runs parse+semantic pipeline (target fixed to `python` internally)
- prints `OK` on success

`explain`:
- prints JSON payload with `ast`, `graph`, `source_map`

`compress`:
- prints canonical compact ICL serialization

`diff`:
- compares two serialized intent graphs and prints structural diff JSON

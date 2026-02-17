# ICL Language Specification (v1)

## 1. Philosophy
ICL (Intent Compression Language) is an AI-native symbolic intent language that compresses high-level programming intent into a deterministic intermediate representation.

Design constraints:
- Minimal syntax with canonical statement forms.
- Deterministic parse and semantic behavior.
- Extensible through plugin hooks.
- Reversible where practical via source-map provenance.
- Token-efficient while preserving human recoverability.

ICL differs from machine-oriented IRs (LLVM IR, bytecode) by preserving intent semantics (control intent, assignment intent, expansion intent) instead of low-level execution primitives.

## 2. Lexical Rules
- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`
- Number literals: integer or decimal (`12`, `3.14`)
- String literals: double-quoted with escapes (`\n`, `\t`, `\"`, `\\`)
- Comments: line comments with `//`
- Keywords: `fn`, `if`, `loop`, `in`, `ret`, `true`, `false`

Symbols/operators:
- Assignment: `:=`
- Type annotation separator: `:`
- Expression function body: `=>`
- Conditional marker: `?`
- Range marker: `..`
- Call prefix: `@`
- Macro prefix: `#`
- Binary ops: `+ - * / % == != < <= > >= && ||`
- Unary ops: `! + -`

## 3. Grammar (EBNF)
```ebnf
program         = { statement [ ";" ] } ;

statement       = assignment
                | function_def
                | conditional
                | loop
                | return_stmt
                | macro_stmt
                | expr_stmt
                ;

assignment      = identifier [ ":" type_name ] ":=" expression ;

function_def    = "fn" identifier "(" [ params ] ")"
                  [ ":" type_name ]
                  ( "=>" expression | block ) ;

params          = param { "," param } ;
param           = identifier [ ":" type_name ] ;

type_name       = identifier ;

conditional     = "if" expression "?" block [ ":" block ] ;

loop            = "loop" identifier "in" expression ".." expression block ;

return_stmt     = "ret" [ expression ] ;

macro_stmt      = "#" identifier "(" [ arguments ] ")" ;

expr_stmt       = expression ;

block           = "{" { statement [ ";" ] } "}" ;

arguments       = expression { "," expression } ;

expression      = logical_or ;
logical_or      = logical_and { "||" logical_and } ;
logical_and     = equality { "&&" equality } ;
equality        = comparison { ("==" | "!=") comparison } ;
comparison      = term { ("<" | "<=" | ">" | ">=") term } ;
term            = factor { ("+" | "-") factor } ;
factor          = unary { ("*" | "/" | "%") unary } ;
unary           = [ "!" | "+" | "-" ] unary | postfix ;
postfix         = primary { "(" [ arguments ] ")" } ;

primary         = number
                | string
                | "true"
                | "false"
                | identifier
                | "@" identifier "(" [ arguments ] ")"
                | "(" expression ")"
                ;

identifier      = letter { letter | digit | "_" } ;
number          = digit { digit } [ "." digit { digit } ] ;
string          = '"' { character | escape } '"' ;
```

## 4. Semantic Model

### 4.1 Intent Nodes
Primary node kinds:
- `ModuleIntent`
- `AssignmentIntent`
- `OperationIntent`
- `ControlIntent`
- `LoopIntent`
- `FuncIntent`
- `CallIntent`
- `ReturnIntent`
- `LiteralIntent`
- `RefIntent`
- `ExpansionIntent`

### 4.2 Intent Graph
The compiler lowers AST into a directed typed graph:
- Control/containment edges: `contains`, `contains_then`, `contains_else`, `contains_body`
- Data edges: `value`, `operand`, `arg`, `condition`, `start`, `end`, `return_expr`
- Edges include ordering metadata for deterministic traversal.

### 4.3 Type System
ICL v1 uses inferred types with optional annotations:
- Built-in symbolic types: `Num`, `Str`, `Bool`, `Any`, `Fn`, `Void`
- Annotations constrain inferred types.
- Type mismatches are compile-time errors.

### 4.4 Scope and Binding
- Lexical scoping with parent chained symbol tables.
- Functions introduce parameter scope.
- Loop iterators are loop-local symbols.
- Return statements are valid only within function scope.

## 5. Evaluation and Expansion Model
1. Lex source into tokens.
2. Parse tokens into AST.
3. Expand macros/syntax plugins.
4. Perform semantic validation and inference.
5. Build Intent Graph with source provenance.
6. Optional graph optimization passes.
7. Expand graph to target code (Python, JavaScript, or Rust scaffold backend).

## 6. Reversibility Artifacts
ICL v1 emits practical reverse metadata:
- Intent Graph JSON
- Node-level source map entries (`node_id -> source span`)

These artifacts support tracing generated code intent back to source, graph diffing, and future reverse compilation tooling.

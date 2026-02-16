# ICL Teaching & Onboarding Manual

This manual teaches ICL exactly as implemented in the current compiler.

## 1. Philosophy

### 1.1 Why ICL Exists
ICL is a symbolic intent layer between human intent and target code generation.
It is designed to preserve structure while reducing verbosity.

### 1.2 Why It Is AI-Native
- Deterministic grammar and fixed token set.
- Explicit intent graph (`ModuleIntent`, `ControlIntent`, `OperationIntent`, etc.).
- Stable reversible artifacts (graph JSON + source map).
- Compact canonical form (`icl compress`) for token-efficient model workflows.

### 1.3 How It Differs from Python
- ICL is not executed directly; it is compiled into backend code.
- ICL uses symbolic constructs (`:=`, `?`, `..`, optional `@callee`).
- Semantics are validated before backend emission (scope and symbolic type checks).
- One ICL source can target multiple emitters (`python`, `js`, `rust`).

## 2. Core Mental Model

```text
Intent Text (ICL)
   |
   v
AST (typed syntax tree)
   |
   v
Intent Graph (semantic IR)
   |
   v
Backend Expansion
   |
   +--> Python code
   +--> JavaScript code
   +--> Rust scaffold code
```

Rules of thumb:
- Write intent first.
- Validate with `icl check`.
- Inspect graph with `icl explain` when behavior is unclear.
- Compile to one or more targets.

## 3. Beginner Examples

All outputs below are exact current backend behavior.

## 3.1 Assignment

### ICL Code
```icl
x := 1 + 2;
```

### Intent Graph Representation
```text
Nodes:
n1 ModuleIntent {name: module}
n2 AssignmentIntent {name: x, type_hint: null}
n3 OperationIntent {operator: +, arity: 2}
n4 LiteralIntent {value: 1}
n5 LiteralIntent {value: 2}

Edges:
n1 -[contains:0]-> n2
n2 -[value:0]-> n3
n3 -[operand:0]-> n4
n3 -[operand:1]-> n5
```

### Python Output
```python
x = (1 + 2)
```

### JavaScript Output
```javascript
let x = (1 + 2);
```

## 3.2 Conditional

### ICL Code
```icl
if true ? { x := 1; } : { x := 2; }
```

### Intent Graph Representation
```text
Nodes:
n1 ModuleIntent
n2 ControlIntent {control: if}
n3 LiteralIntent {value: True}
n4 AssignmentIntent {name: x}
n5 LiteralIntent {value: 1}
n6 AssignmentIntent {name: x}
n7 LiteralIntent {value: 2}

Edges:
n1 -[contains:0]-> n2
n2 -[condition:0]-> n3
n2 -[contains_then:0]-> n4
n4 -[value:0]-> n5
n2 -[contains_else:0]-> n6
n6 -[value:0]-> n7
```

### Python Output
```python
if True:
    x = 1
else:
    x = 2
```

### JavaScript Output
```javascript
if (true) {
    let x = 1;
} else {
    x = 2;
}
```

## 3.3 Loop

### ICL Code
```icl
sum := 0;
loop i in 0..3 { sum := sum + i; }
```

### Intent Graph Representation
```text
Nodes:
n1 ModuleIntent
n2 AssignmentIntent {name: sum}
n3 LiteralIntent {value: 0}
n4 LoopIntent {iterator: i}
n5 LiteralIntent {value: 0}
n6 LiteralIntent {value: 3}
n7 AssignmentIntent {name: sum}
n8 OperationIntent {operator: +}
n9 RefIntent {name: sum}
n10 RefIntent {name: i}

Edges:
n1 -[contains:0]-> n2
n2 -[value:0]-> n3
n1 -[contains:1]-> n4
n4 -[start:0]-> n5
n4 -[end:1]-> n6
n4 -[contains_body:0]-> n7
n7 -[value:0]-> n8
n8 -[operand:0]-> n9
n8 -[operand:1]-> n10
```

### Python Output
```python
sum = 0
for i in range(0, 3):
    sum = (sum + i)
```

### JavaScript Output
```javascript
let sum = 0;
for (let i = 0; i < 3; i++) {
    sum = (sum + i);
}
```

## 3.4 Function

### ICL Code
```icl
fn add(a, b):Num => a + b;
result := @add(3, 4);
```

### Intent Graph Representation
```text
Nodes:
n1 ModuleIntent
n2 FuncIntent {name: add, return_type: Num, expr_body: true}
n3 OperationIntent {operator: +}
n4 RefIntent {name: a}
n5 RefIntent {name: b}
n6 AssignmentIntent {name: result}
n7 CallIntent {callee_name: add, at_prefixed: true}
n8 LiteralIntent {value: 3}
n9 LiteralIntent {value: 4}

Edges:
n1 -[contains:0]-> n2
n2 -[return_expr:0]-> n3
n3 -[operand:0]-> n4
n3 -[operand:1]-> n5
n1 -[contains:1]-> n6
n6 -[value:0]-> n7
n7 -[arg:0]-> n8
n7 -[arg:1]-> n9
```

### Python Output
```python
def add(a, b):
    return (a + b)
result = add(3, 4)
```

### JavaScript Output
```javascript
function add(a, b) {
    return (a + b);
}
let result = add(3, 4);
```

## 4. Advanced Topics

## 4.1 Writing a Custom Backend
Contract:
- Implement `BackendEmitter`.
- Provide `name` and `emit_module(graph, context)`.
- Register via plugin manager.

Minimal pattern:
```python
from icl.expanders.base import BackendEmitter

class MyBackend(BackendEmitter):
    @property
    def name(self) -> str:
        return "mytarget"

    def emit_module(self, graph, context) -> str:
        return ""
```

Plugin registration path:
- `icl compile ... --target mytarget --plugin my_pkg.my_plugin:register`

## 4.2 Writing Macro Expansions
Contract:
- Implement `MacroPlugin` with `name` and `expand(stmt)`.
- Return expanded AST statements.
- Register with `PluginManager.register_macro(...)`.

Current built-in macros:
- `#echo(expr)` -> `@print(expr)`
- `#dbg(expr)` -> `@print("dbg:")` + `@print(expr)`

## 4.3 Extending Grammar Safely
Required update sequence:
1. Add token(s) in `icl/tokens.py`.
2. Lex token(s) in `icl/lexer.py`.
3. Parse syntax in `icl/parser.py`.
4. Add AST nodes in `icl/ast.py` if needed.
5. Add semantic checks in `icl/semantic.py`.
6. Lower to graph in `icl/graph.py`.
7. Update each backend in `icl/expanders/`.
8. Update docs and tests.

## 4.4 Designing New Tokens
Checklist:
- Unique `TokenType` enum entry.
- Deterministic lexical rule.
- Non-overlapping parser consumption points.
- Diagnostic code path for invalid use.
- Backward compatibility test coverage.

## 5. Common Mistakes

## 5.1 Over-Compression Errors
Problem:
- Removing required delimiters for brevity.

Example invalid pattern:
```icl
if x { y := 1 }
```

Fix:
```icl
if x ? { y := 1; }
```

## 5.2 Misuse of Arrow Syntax
Problem:
- Using `=>` outside function definitions.

Fix:
- Restrict `=>` to `fn` expression-body form only.

## 5.3 Scope Leakage Assumptions
Problem:
- Defining variable inside `if` and using it outside.

Example:
```icl
if true ? { x := 1; }
@print(x);   // semantic error (undefined symbol)
```

Fix:
```icl
x := 0;
if true ? { x := 1; }
@print(x);
```

## 5.4 Backend Coupling Assumptions
Problem:
- Writing source that assumes one backend’s declaration behavior.

Fix:
- Declare shared variables before control flow blocks.
- Keep source target-agnostic; let backends handle syntax-specific emission.

# Simulation Notes (Pre-Implementation Validation)

## Program 1 — Recursion + Return Types
### ICL
```icl
fn fact(n:Num):Num {
  if n <= 1 ? { ret 1; } : { ret n * @fact(n - 1); }
}
x := @fact(5);
```

### AST Expectations
- `FunctionDefStmt(fact)` with `IfStmt` and `ReturnStmt` in both branches.
- Top-level `AssignmentStmt(x)` calling `fact`.

### IR Expectations
- `IRFunction(fact)` preserving parameter and return annotation.
- `IRIf` with `IRBinary(<=)` condition.
- `IRReturn` nodes in both branches.

### Lowering Checks
- Expression-bodied normalization not needed.
- Recursive call remains `LoweredCall(callee=fact)`.

### Target Shape Checks
- Python: nested `if` + `return` with call recursion.
- Rust: function emitted before `main`, returns `f64` scaffold style.
- Web: JS function + browser scaffold bundle.

### Validation Outcome
- No missing lowering rule.
- No type conflict in symbolic model.

## Program 2 — Nested Conditional + Loop
### ICL
```icl
total := 0;
loop i in 0..4 {
  if i % 2 == 0 ? { total := total + i; } : { total := total; }
}
@print(total);
```

### AST Expectations
- `LoopStmt` containing `IfStmt`.
- `BinaryExpr` chain for `%`, `==`, and `+`.

### IR Expectations
- `IRLoop` with ordered body statements.
- `IRIf` nested inside loop body.
- `IRExpressionStmt(IRCall(print))` at top-level.

### Lowering Checks
- Loop bounds lowered as start/end expression pair.
- `print` helper requirement discovered for web/js-class targets.

### Target Shape Checks
- Python: `for i in range(0, 4)`.
- Rust: `for i in (0 as i64)..(4 as i64)`.
- Web: JS loop plus runtime `print` helper into output pane.

### Validation Outcome
- No structural mismatch.
- Helper-runtime strategy required for browser target confirmed.

## Program 3 — Functions + Data Flow + Calls
### ICL
```icl
fn add(a:Num, b:Num):Num => a + b;
a := 3;
b := 7;
res := @add(a, b);
if res > 5 ? { @print(res); } : { @print(0); }
```

### AST Expectations
- Expression-bodied function + assignments + call + conditional.

### IR Expectations
- `IRFunction(expr_body=IRBinary(+))`.
- `IRAssignment(res, IRCall(add))`.
- `IRIf` with `IRBinary(>)`.

### Lowering Checks
- Function expr body normalized into explicit `LoweredReturn`.
- `@add(...)` canonicalized to normal call form.

### Target Shape Checks
- Python: `def add(...): return ...`.
- Rust: scaffolded function + main body.
- Web: JS function + HTML/CSS scaffold.

### Validation Outcome
- Lowering normalization confirmed.
- No missing rule discovered.

## Simulation Conclusions
1. IR boundary is sufficient for stable target semantics.
2. Lowering rules required: expr-body normalization, helper detection, feature-gate validation.
3. Web target needs scaffold + helper runtime policy, not just emitter output.
4. Experimental packs can share lowering and use best-effort emitters without changing core semantics.

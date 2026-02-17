# ICL Teaching & Onboarding Manual (v2)

## 1. What ICL Is
ICL is a universal translation platform:
- Write intent in one compact language.
- Compile once through deterministic AST/IR/lowering stages.
- Emit to many language packs.

## 2. Core Mental Model

```text
ICL Source
  -> AST
  -> IR
  -> Lowered (target-shaped)
  -> Language Pack Emit
  -> Scaffolded Output
```

Use this workflow:
1. `icl check` to validate semantics.
2. `icl explain` to inspect AST/IR/lowered/graph.
3. `icl compile` for one or many targets.

## 3. Quick Example
### ICL
```icl
fn add(a:Num, b:Num):Num => a + b;
x := @add(2, 3);
@print(x);
```

### Compile
```bash
icl compile --code 'fn add(a:Num,b:Num):Num=>a+b; x:=@add(2,3); @print(x);' --targets python,js,rust,web
```

## 4. Stable vs Experimental Targets
Stable packs provide semantic parity gates:
- `python`, `js`, `rust`, `web`

Experimental packs are best-effort scaffolds and must be treated as non-stable until promoted by contract tests.

## 5. AI Contributor Rules
- Follow execution rules in `README.md`.
- Do not bypass language contract.
- Do not mark packs stable without contract test pass.
- Keep semantic logic in IR/lowering, not target emitters.
- If a required language runtime/compiler is missing, install it when permitted; otherwise ask your mentor to install or approve it.

## 6. Creating New Packs
Use:
- `LANGUAGE_PACK_SPEC.md`
- `docs/language_pack_creation_guide.md`

Validate with:
```bash
icl pack validate --pack my_pack_module:register
icl contract test --target my_target --pack my_pack_module:register
```

# ICL — Universal Translation Platform (v2)

## Execution Rules (For Human and AI Contributors)
- Do NOT implement before planning documents are complete.
- Do NOT modify compiler core until IR design is finalized.
- Do NOT add language packs before migration strategy is defined.
- Do NOT mark any language pack stable without passing contract tests.
- All implementation must follow defined architecture strictly.
- If a required language runtime/compiler is missing, install it when permitted; otherwise ask your mentor to install or approve it.

## Identity
ICL is a universal translation platform with deterministic semantics:
- Intent DSL for compact authoring.
- Compiler pipeline with explicit IR and lowering.
- Language pack system for multi-target emission and scaffolding.

## Compiler Pipeline

```text
ICL Source
  -> Syntax Preprocess
  -> Parser
  -> AST
  -> IR
  -> Lowering
  -> Target Pack Emit
  -> Scaffolder
  -> Output
```

## Stable Targets
- `python`
- `js`
- `rust`
- `web` (browser JS + HTML/CSS scaffold)

## Experimental Targets
- `typescript`, `go`, `java`, `csharp`, `cpp`, `php`, `ruby`, `kotlin`, `swift`, `lua`, `dart`

## Key Features
- Deterministic lexer/parser/semantic pipeline.
- Target-agnostic IR with typed lowering stage.
- Language pack registry + custom pack loader (`module[:symbol]`).
- Multi-target compile in one frontend pass.
- Multi-target compile returns full bundle artifacts (not fragments) when writing JSON output.
- Pack manifest validation and contract test harness.
- Feature coverage matrix audit (`declared support` vs `observed behavior`) via `icl contract test`.
- Structured unsupported-feature failures (`LOW001`) and structured lowering fallback errors (`LOW002`, `LOW003`).
- Optional natural alias layer (`prnt`, `mkfn`, `lambda`, etc.) with traceable normalization.
- Intent graph + source map artifacts.
- HTTP API, stdio agent adapter, and MCP server.

## Install
```bash
cd /home/aru/ICL
python -m pip install -e .
```

## CLI Quick Start
```bash
# single target
icl compile examples/basic.icl --target python

# multi-target in one run
icl compile examples/basic.icl --targets python,js,rust,web -o out

# multi-target JSON bundle output (primary file + files map per target)
icl compile --code 'x := 1; @print(x);' --targets python,js,web

# explain with AST + IR + lowered + graph
icl explain examples/basic.icl --target rust

# contract tests (stable packs)
icl contract test

# include experimental packs in contract run
icl contract test --all

# list and validate packs
icl pack list
icl pack validate

# inspect alias mappings
icl alias list --mode extended
```

Contract behavior:
- Stable packs must pass all required contract cases and feature checks.
- Experimental packs may declare unsupported features; those must fail explicitly with `LOW001`.

## Language Pack Workflow
```bash
# load a custom pack module
icl compile --code 'x := 1;' --target mypack --pack my_module:register

# inspect built-in stable packs only
icl pack list --stability stable
```

## Example ICL
```icl
fn add(a:Num, b:Num):Num => a + b;
x:Num := 4;
y := @add(x, 6);
@print(y);
```

## AI Speed Benchmark
Measured on February 17, 2026 in this repo environment for 4-target generation (`python,js,rust,web`):
- Sequential single-target calls median: `0.006299s`
- Multi-target shared-frontend median: `0.002855s`
- Speedup: `2.21x`

Method: 50 iterations of equivalent source with identical targets.

## Service and MCP Integration
### HTTP API
```bash
icl serve --host 127.0.0.1 --port 8080
```

### Stdio Adapter
```bash
icl agent
```

### MCP Server
```bash
icl mcp --root /home/aru/ICL
```

### Standalone MCP Binary
```bash
# build
.venv/bin/pyinstaller --noconfirm icl-mcp.spec

# run
./dist/icl-mcp --root /home/aru/ICL
```

Core service methods:
- `compile`
- `check`
- `explain`
- `compress`
- `diff`
- `capabilities`

Static target runnability:
- `rust` stable emission is validated by runnable golden tests when `rustc` is available in environment.

## Documentation Index
- `ICL_2.0_UNIVERSAL_TRANSLATION_ARCHITECTURE_PLAN.md`
- `ICL_LANGUAGE_CONTRACT.md`
- `UNIVERSAL_ALIAS_MAP.md`
- `COMPILER_ARCHITECTURE.md`
- `LANGUAGE_PACK_SPEC.md`
- `SIMULATION_NOTES.md`
- `FEATURE_COVERAGE_MATRIX.md`
- `PHASE4_VALIDATION_REPORT.md`
- `PHASE5_HARDENING_REPORT.md`
- `PHASE6_STABILIZATION_REPORT.md`
- `MIGRATION_NOTES_v2.md`
- `RELEASE_NOTES_v2.0.0.md`
- `docs/cli_guide.md`

## Development
```bash
python -m unittest discover -s tests -v

# focused golden-program validation
python -m unittest tests.test_golden_programs -v
```

## License
See `license.md`.

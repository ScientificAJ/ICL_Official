# ICL 2.0 — Universal Translation Architecture Plan

## Execution Rules (Mandatory)
- Do NOT implement before planning documents are complete.
- Do NOT modify compiler core until IR design is finalized.
- Do NOT add language packs before migration strategy is defined.
- Do NOT mark any language pack stable without passing contract tests.
- All implementation must follow defined architecture strictly.

## Identity
ICL 2.0 is defined as a **universal translation platform** with three coordinated roles:
1. A logic DSL for compact intent authoring.
2. A universal compiler that preserves language-agnostic semantics.
3. A cross-language abstraction layer through IR + language packs.

Primary identity is the platform role. DSL and compiler roles exist to serve portable, deterministic translation.

## Full Compatibility Definition
"Full compatibility" means **semantic parity** for all contract-required constructs across stable targets.

### Guaranteed Across Stable Targets
- Deterministic parse, semantic, IR, lowering, and emission order.
- Equivalent control-flow and data-flow behavior for contract constructs.
- Equivalent error-phase boundaries (lex/parse/semantic/lowering/pack).
- Explicit diagnostics for unsupported behavior.
- Reproducible compile artifacts (`ir`, `lowered`, `graph`, `source_map`).

### Optional Per Language Pack
- Output syntax style and formatting.
- Runtime helper shape and scaffold layout.
- Target-specific type decoration strategy.
- Optional advanced features explicitly declared in pack coverage.

## Scope and Release Model
- v2.0 stable core: `python`, `js`, `rust`, `web`.
- v2.0 experimental wave: `typescript`, `go`, `java`, `csharp`, `cpp`, `php`, `ruby`, `kotlin`, `swift`, `lua`, `dart`.
- Stability promotion requires contract test pass-gates.

## Non-Goals
- No source-style parity guarantee between targets.
- No immediate stable status for all popular languages.
- No implicit target-specific semantic drift.
- No backend-specific logic in parser/semantic core.

## Architecture Principle
Pipeline authority is:

`ICL Source -> Parser -> AST -> IR -> Lowering -> Target Pack Emit -> Scaffolder -> Output`

This separates semantic authority (AST/IR) from syntax authority (pack emitter).

## Risks and Mitigations
1. Feature drift across packs.
- Mitigation: feature coverage manifest + contract tests + stable gate.

2. Lowering ambiguity.
- Mitigation: canonical lowering rules and trace artifacts per target.

3. Performance regressions from extra stages.
- Mitigation: shared frontend for multi-target compile.

4. Debuggability loss from abstraction.
- Mitigation: expose AST/IR/lowered/graph in explain and artifacts.

5. Integration breakage (CLI, MCP, service).
- Mitigation: preserve single-target interfaces and add backward-compatible extensions.

## Migration Objective
Transform ICL from a backend-coupled code generator into a compiler framework with reusable lowering and pack contracts, while preserving existing project integrations and test behavior.

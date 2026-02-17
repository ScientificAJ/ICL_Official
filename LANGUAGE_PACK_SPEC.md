# Language Pack Specification (ICL v2.0)

## 1. Purpose
Language packs define how lowered ICL semantics map to target syntax and output scaffolds.

## 2. Required Pack Components
Each pack MUST provide:
1. `PackManifest`
2. Emit strategy (`emit(lowered, context) -> str`)
3. Scaffolding strategy (`scaffold(code, context) -> OutputBundle`)

## 3. Pack Manifest Contract
Required fields:
- `pack_id`: unique identifier
- `version`: pack version
- `target`: canonical target key used by CLI/service
- `stability`: `experimental | beta | stable`
- `file_extension`
- `block_model`: `indent | braces | tags | other documented`
- `statement_termination`: `newline | semicolon | documented custom`
- `type_strategy`: mapping strategy from symbolic types to target syntax/runtime
- `runtime_helpers`: helper inventory
- `scaffolding`: filenames/layout contract
- `feature_coverage`: feature-to-bool matrix
- `aliases`: optional alternate target names

## 4. Syntax Mapping Rules
Packs map lowered constructs to target syntax:
- assignments
- expressions
- function definitions/calls
- lambda expressions
- conditionals
- loops
- returns

Mappings must preserve contract semantics or fail explicitly.

## 5. Block Model
Pack must declare and implement one:
- indentation blocks
- brace blocks
- tag/template blocks
- custom (documented)

## 6. Statement Termination
Pack must define explicit termination policy:
- newline-driven
- semicolon-driven
- custom (documented)

## 7. Type Strategy
Pack must document:
- symbolic-to-native type mapping
- dynamic fallback behavior
- unsupported type features and errors

## 8. Helper Runtime Strategy
Pack must document helper APIs and injection policy.
- Helpers may be emitted inline or scaffolded.
- Helper names must avoid silent collision with user symbols.

## 9. Scaffolding Rules
Pack scaffolding must declare:
- primary output file
- additional files
- runtime entrypoint behavior
- path layout conventions

## 10. Feature Coverage Declaration
`feature_coverage` is mandatory and authoritative.
- `true`: feature supported by pack.
- `false`: compile must fail with explicit unsupported diagnostic.

## 11. Stability Policy
- Experimental: best-effort, no stability guarantee.
- Beta: near-stable, contract gaps allowed with explicit limitations.
- Stable: requires 100% pass on required-stable contract tests.

## 12. Validation
`icl pack validate` checks manifest completeness and structure.
`icl contract test` enforces cross-target compatibility gates.

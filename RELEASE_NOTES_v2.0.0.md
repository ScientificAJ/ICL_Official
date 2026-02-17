# ICL v2.0.0 Release Notes

Release Name: `ICL v2.0 — Universal Target Engine`
Release Date: February 17, 2026

## Migration Notes
- Compiler pipeline is now explicit and phase-separated:
  `Source -> Syntax Preprocess -> Parser -> AST -> IR -> Lowering -> Pack Emit -> Scaffold`.
- Stable target set is now: `python`, `js`, `rust`, `web`.
- Experimental targets are declared via pack manifests and enforced by feature coverage.
- Multi-target compile produces bundle artifacts per target (primary path + files), not fragments.

## Breaking Changes
- `explain` payload includes normalized `ir` and `lowered` representations alongside `ast`, `graph`, and `source_map`.
- Target support is now governed by pack feature declarations; unsupported features fail explicitly (`LOW001`) instead of implicit degradation.

## New Features
- Universal natural alias layer (optional): `mkfn`, `prnt`, `lambda`, and extended aliases in controlled mode.
- First-class lambda expression support (`lam(...) => expr`) through parser, semantic, IR, lowering, and stable emitters.
- Contract matrix now includes lambda coverage and validates stable-pack parity.
- Phase 4 artifacts produced:
  - `output/phase4/contract_stable.json`
  - `output/phase4/contract_all.json`
  - `output/phase4/golden_tests.txt`
  - `output/phase4/snapshots/*`
- Phase 5 backward-compat report produced:
  - `output/phase5/backward_compat_report.json`

## Known Limitations
- Experimental targets remain best-effort scaffolds and are not stable guarantees.
- Alias normalization is opt-in by design (`--natural`) to preserve strict canonical parsing by default.
- Rust lambda emission currently maps to closure syntax with symbolic `Fn` handling and remains limited to current core contract shapes.

# ICL v2.0 Migration Notes

## Release
- Version: `2.0.0`
- Title: `ICL v2.0 — Universal Target Engine`

## What Changed
1. Compiler pipeline now includes explicit `IR` and `Lowering` stages.
2. Language targets now use `PackRegistry` and `LanguagePack` manifests.
3. New stable target: `web` (browser JS + HTML/CSS scaffold).
4. New experimental targets: `typescript`, `go`, `java`, `csharp`, `cpp`, `php`, `ruby`, `kotlin`, `swift`, `lua`, `dart`.
5. New CLI features:
- `compile --targets`
- `pack list`, `pack validate`
- `contract test`
6. Contract harness now audits feature matrix consistency (declared coverage vs observed behavior).
7. Multi-target compile responses/artifacts carry bundle file maps to avoid fragment-only outputs.

## Compatibility
- Existing `compile --target python|js|rust` behavior is preserved.
- Existing plugin system remains for syntax/macro extensions.
- Service and MCP methods remain stable; compile supports richer payloads.

## Potential Breaking Changes
- Service capabilities version updated to `2.0.0`.
- `explain` output now includes `ir` and `lowered` sections in addition to `ast`, `graph`, `source_map`.

## New Features
- Shared-frontend multi-target compile (measured `2.21x` median speedup for 4-target workflow in this environment).
- Pack manifest validation and contract test harness.
- Web scaffolding output bundle.
- Structured lowering fallback diagnostics (`LOW002`, `LOW003`) and unsupported feature diagnostics (`LOW001`).

## Known Limitations
- Experimental packs are best-effort syntax scaffolds.
- Stable-pack promotion requires contract gate completion per target.

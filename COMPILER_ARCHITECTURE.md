# Compiler Architecture (ICL v2.0)

## Pipeline
`ICL Source -> Parser -> AST -> IR -> Lowering -> Target Pack Emit -> Scaffolder -> Output`

## Stage Definitions
1. Parser
- Lexer + parser produce typed AST with source spans.

2. AST
- Source-faithful program structure.
- Preserves language-level constructs before normalization.

3. IR
- Target-agnostic semantic representation.
- Normalizes constructs so packs do not duplicate semantic logic.
- Carries inferred type metadata and stable schema version.

4. Lowering
- Converts IR to target-shaped lowered module.
- Applies pack feature compatibility checks.
- Produces required helper/runtime declarations.

5. Target Pack Emit
- Converts lowered module into target source text.
- Stable packs enforce semantic parity for contract constructs.
- Experimental packs are best-effort and clearly labeled.

6. Scaffolder
- Wraps emitted source into output bundle (single file or multi-file scaffold).
- Example: `web` target outputs `index.html`, `styles.css`, `app.js`.

7. Output
- Primary code output plus optional debug artifacts.

## Why IR Exists
- Removes backend-specific semantic duplication.
- Centralizes compatibility guarantees.
- Enables broad language coverage with lower incremental cost.
- Improves AI tooling speed for multi-target workflows by sharing frontend work.

## AST vs IR
- AST: syntax-oriented representation tied to source grammar.
- IR: semantics-oriented representation independent of target syntax.

## Lowering Definition
Lowering is a deterministic transform from canonical IR into target-shaped lowered nodes, including:
- function body normalization
- call-form normalization
- target helper requirement discovery
- feature support validation against pack manifest

## Pack Plug-In Model
- Packs are registered via `PackRegistry`.
- Each pack declares a manifest (`PackManifest`) and `emit` + `scaffold` behavior.
- Custom packs are loaded via `module[:symbol]` specs.

## Current Stable Targets
- `python`
- `js`
- `rust`
- `web`

## Current Experimental Targets
- `typescript`, `go`, `java`, `csharp`, `cpp`, `php`, `ruby`, `kotlin`, `swift`, `lua`, `dart`

## Debug and Trace Artifacts
- AST explanation payload
- IR payload
- Lowered payload
- Intent graph payload
- Source map payload

These artifacts are available through CLI/service explain and compile options.

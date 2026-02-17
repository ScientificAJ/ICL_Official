# Compiler Architecture (v2)

## Pipeline
1. Syntax preprocess plugins (`icl/plugin.py`, `icl/plugins/`)
2. Lexer (`icl/lexer.py`)
3. Parser (`icl/parser.py`)
4. Semantic analyzer (`icl/semantic.py`)
5. IR builder (`icl/ir.py`)
6. Lowering (`icl/lowering.py`)
7. Language pack emission (`icl/language_pack.py`, `icl/packs/`)
8. Scaffolding (`icl/scaffolder.py`)
9. Optional graph optimization (`icl/optimize.py`) for debug/analysis artifacts

## Stage Ownership
- Parser/semantic define language truth.
- IR holds normalized semantics.
- Lowering shapes target constraints without embedding syntax.
- Packs own target syntax + file layout.

## Extensibility
- Syntax and macro plugins remain managed by `PluginManager`.
- Language packs are managed by `PackRegistry` and can be loaded via `module[:symbol]`.

## Stable Targets
- `python`, `js`, `rust`, `web`

## Experimental Targets
- `typescript`, `go`, `java`, `csharp`, `cpp`, `php`, `ruby`, `kotlin`, `swift`, `lua`, `dart`

## Integration Adapters
- Service layer (`icl/service.py`)
- HTTP adapter (`icl/api_server.py`)
- Stdio adapter (`icl/agent_stdio.py`)
- MCP adapter (`icl/mcp_server.py`)

## Artifacts
- AST explanation payload
- IR payload
- Lowered payload
- Intent graph JSON
- Source map JSON

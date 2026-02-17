# ICL — Intent Compression Language

ICL is an AI-native symbolic intent language that compiles compressed intent syntax into executable target languages.

Architecture flow:

```
Human Intent
  -> ICL Syntax
  -> Semantic AST
  -> Intent Graph
  -> Expansion Engine
  -> Target Code (Python / JS)
```

## Features
- Deterministic lexer/parser/semantic pipeline.
- Compact symbolic syntax with readable canonical forms.
- Intent Graph IR with source provenance map.
- Pluggable backends, syntax hooks, and macro expansion.
- Built-in Python and JavaScript code generation.
- Rust scaffold backend for typed-lowering future work.
- Graph optimizer (constant folding + dead assignment removal).
- Intent graph diff tooling.
- Plugin loader for macros, syntax hooks, and custom backends.
- Zero-dependency HTTP API for tool and agent integrations.
- Stdio JSON adapter for agent runtimes that prefer line-based IPC.

## Install
```bash
cd /home/aru/ICL
python -m pip install -e .
```

## CLI Quick Start
```bash
icl compile examples/basic.icl --target python
icl compile examples/basic.icl --target js
icl compile examples/basic.icl --target rust
icl check examples/control_flow.icl
icl explain examples/basic.icl
icl compile examples/basic.icl --target python --emit-graph graph.json --emit-sourcemap map.json
icl compile examples/macros.icl --target python --plugin icl.plugins.std_macros
icl serve --host 127.0.0.1 --port 8080
icl agent
```

## Example ICL
```icl
fn add(a:Num, b:Num):Num => a + b;
x:Num := 4;
y := @add(x, 6);
@print(y);
```

## Project Layout
- `icl/`: compiler source
- `tests/`: unit + integration tests
- `examples/`: sample ICL programs
- `docs/`: specification and architecture docs

## Development
```bash
python -m unittest discover -s tests -v
```

## Plugin Specs
- Format: `module[:symbol]`
- Default symbol when omitted: `register`
- Example:
```bash
icl compile --code '#echo(1);' --target python --plugin icl.plugins.std_macros
```

## AI Integration Modes

### 1. Python API
```python
from icl import compile_source
artifacts = compile_source(\"x := 1 + 2;\", target=\"python\")
print(artifacts.code)
```

### 2. HTTP API (`icl-api` / `icl serve`)
Start server:
```bash
icl-api --host 127.0.0.1 --port 8080
```

Compile request:
```bash
curl -s http://127.0.0.1:8080/v1/compile \\
  -H 'Content-Type: application/json' \\
  -d '{\"source\":\"x := 1 + 2;\",\"target\":\"python\"}'
```

### 3. Stdio JSON Adapter (`icl-agent` / `icl agent`)
```bash
printf '%s\n' '{\"id\":\"1\",\"method\":\"compile\",\"params\":{\"source\":\"x := 1;\",\"target\":\"python\"}}' | icl-agent
```

Request format:
- One JSON object per line.
- Fields: `id`, `method`, `params`.

Methods:
- `compile`
- `check`
- `explain`
- `compress`
- `diff`
- `capabilities`

## Release Packaging
Build distributions:
```bash
python -m pip install -e .[release]
python -m build
```

## License
See `license.md`.

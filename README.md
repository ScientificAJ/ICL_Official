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

## License
MIT (add LICENSE file if required for distribution).

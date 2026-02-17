# CLI Usage Guide (ICL v2)

## Install
```bash
python -m pip install -e .
```

## Compile
### Single Target
```bash
icl compile input.icl --target python
icl compile --code 'x := 1 + 2;' --target js
```

### Multi-Target
```bash
icl compile input.icl --targets python,js,rust,web -o out
icl compile --code 'x := 1;' --targets python --targets js
```

Notes:
- With `-o <dir>`, each target is written as runnable bundle files under `<dir>/<target>/`.
- Without `-o`, multi-target output is JSON bundles (`primary_path` + `files`) for each target.

Useful flags:
- `--emit-graph graph.json` (single target)
- `--emit-sourcemap map.json`
- `--optimize`
- `--debug`
- `--natural` (enable universal natural alias normalization)
- `--alias-mode core|extended` (default: `core`)
- `--plugin module[:symbol]` (repeatable)
- `--pack module[:symbol]` (repeatable)

## Check
```bash
icl check input.icl
icl check --code 'fn add(a,b)=>a+b;'
icl check --code '#echo(1);' --plugin icl.plugins.std_macros
icl check --code 'mkfn add(a,b)=>a+b; prnt(add(1,2));' --natural
```

## Explain
Prints AST + IR + lowered + graph + source map.
```bash
icl explain input.icl
icl explain input.icl --target rust
icl explain --code 'ok := yes and not no;' --natural --alias-mode extended --alias-trace
```

## Alias Catalog
```bash
icl alias list
icl alias list --mode extended
icl alias list --mode extended --json
```

## Compress
```bash
icl compress input.icl
```

## Diff
```bash
icl diff before_graph.json after_graph.json
```

## Pack Commands
```bash
icl pack list
icl pack list --stability stable
icl pack validate
icl pack validate --target web
```

## Contract Tests
```bash
# stable packs only
icl contract test

# include experimental packs
icl contract test --all

# specific targets
icl contract test --target python --target web
```

Contract semantics:
- Stable packs must pass full required feature coverage.
- Declared unsupported features must fail explicitly with `LOW001`.

## HTTP API
```bash
icl serve --host 127.0.0.1 --port 8080
```

## Stdio Adapter
```bash
icl agent
```

## MCP Server
```bash
icl mcp --root /home/aru/ICL
```

## Exit Codes
- `0`: success
- `1`: compiler error
- `2`: CLI usage error
- `3`: internal error

# CLI Usage Guide

## Install
```bash
python -m pip install -e .
```

## Commands

### Compile
```bash
icl compile input.icl --target python
icl compile input.icl --target js -o out.js
icl compile input.icl --target rust -o out.rs
icl compile --code 'x := 1 + 2;' --target python
```

Useful flags:
- `--emit-graph graph.json`
- `--emit-sourcemap map.json`
- `--optimize`
- `--debug`
- `--plugin icl.plugins.std_macros` (repeatable)

Plugin spec format:
- `module` (loads `module:register`)
- `module:symbol` (loads specific callable/object)

### Check (syntax + semantic)
```bash
icl check input.icl
icl check --code 'fn add(a,b)=>a+b;'
icl check --code '#echo(1);' --plugin icl.plugins.std_macros
```

### Explain (AST + graph JSON)
```bash
icl explain input.icl
icl explain input.icl --plugin icl.plugins.std_macros
```

### Compress (canonical compact ICL)
```bash
icl compress input.icl
```

### Intent Graph Diff
```bash
icl diff before_graph.json after_graph.json
```

## Exit Codes
- `0`: success
- `1`: compiler error
- `2`: CLI usage error
- `3`: internal error

## Debug Mode
`--debug` prints token/node/edge counts and optimization stats to stderr.

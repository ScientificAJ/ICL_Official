# MCP Tool Docs (ICL v2)

## Server
```bash
icl mcp --root /home/aru/ICL
```

## Methods
- `initialize`
- `ping`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- `prompts/list`
- `prompts/get`

## Tools
- `icl_capabilities`
- `icl_compile`
- `icl_check`
- `icl_explain`
- `icl_compress`
- `icl_diff`

## Compile Tool Notes
`icl_compile` supports:
- single-target (`target`)
- multi-target (`targets`)
- optional payloads (`include_ir`, `include_lowered`, `include_graph`, `include_source_map`)
- optional bundle payload (`include_bundle`) for single-target full artifact files
- natural alias normalization (`natural_aliases`, `alias_mode`)
- alias trace payload (`include_alias_trace`)

Multi-target responses include runnable bundle artifacts per target (`primary_path` + `files`).

## Policy Controls
- `ICL_MCP_ROOT`: allowed file root for path arguments.
- `ICL_MCP_PLUGIN_ALLOWLIST`: plugin allowlist.

## Guidance
For stable automations, prefer stable pack targets (`python`, `js`, `rust`, `web`).
Contract/matrix checks are available via CLI (`icl contract test`) and should be part of stable pack release gates.
If a required language runtime/compiler is not installed, install it when permissions allow; if blocked, ask your mentor to install or approve it.

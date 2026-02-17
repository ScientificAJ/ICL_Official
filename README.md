# ICL_Official

Consumer-ready binary distribution of the ICL MCP server.
This repository intentionally ships executable + docs only (no compiler source tree).

## What You Get
- `bin/icl-mcp` (Linux x86_64 executable)
- `bin/icp-mcp` (compat alias executable)
- `run_mcp.sh` launcher
- `docs/` language and architecture references
- `examples/` sample ICL files and generated outputs
- `ICL_STANDARDS.md`
- `ICL_SEMANTICS_GUIDE.md`
- `ICL_TEACHING_MANUAL.md`
- `LICENSE.md`

## Quick Start
```bash
cd ICL_Official
./run_mcp.sh
```

Equivalent direct run:
```bash
./bin/icl-mcp --root "$(pwd)"
```

## MCP Surface
Methods:
- `initialize`
- `ping`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- `prompts/list`
- `prompts/get`

Tools:
- `icl_capabilities`
- `icl_compile`
- `icl_check`
- `icl_explain`
- `icl_compress`
- `icl_diff`

## Security/Policy
- Path args are restricted to `--root` (or `ICL_MCP_ROOT`).
- Plugins are disabled unless `ICL_MCP_PLUGIN_ALLOWLIST` is set.

## MCP Client Config Example
```json
{
  "mcpServers": {
    "icl": {
      "command": "/absolute/path/to/ICL_Official/bin/icl-mcp",
      "args": ["--root", "/absolute/path/to/ICL_Official"],
      "env": {
        "ICL_MCP_ROOT": "/absolute/path/to/ICL_Official"
      }
    }
  }
}
```

## Verification
```bash
sha256sum -c checksums.txt
```

## Note
Binary-only packaging lowers casual code exposure but is not a cryptographic anti-reverse-engineering guarantee.

# ICL_Official

Consumer-ready binary MCP distribution for ICL.

This repo ships:
- Executable MCP server
- Language docs/manuals
- Example `.icl` programs and generated outputs

It intentionally does not ship the full compiler source tree.

## Contents
- `bin/icl-mcp` (Linux x86_64 executable)
- `bin/icp-mcp` (compat alias executable)
- `run_mcp.sh`
- `docs/`
- `examples/`
- `ICL_STANDARDS.md`
- `ICL_SEMANTICS_GUIDE.md`
- `ICL_TEACHING_MANUAL.md`
- `LICENSE.md`

## Local Smoke Test
```bash
cd ICL_Official
./run_mcp.sh
```

Equivalent:
```bash
./bin/icl-mcp --root "$(pwd)"
```

## MCP Surface
Supported MCP methods:
- `initialize`
- `ping`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- `prompts/list`
- `prompts/get`

Exposed tools:
- `icl_capabilities`
- `icl_compile`
- `icl_check`
- `icl_explain`
- `icl_compress`
- `icl_diff`

## Policy Behavior
- Path arguments are restricted to `--root` / `ICL_MCP_ROOT`.
- Plugins are blocked unless allowlisted with `ICL_MCP_PLUGIN_ALLOWLIST`.

## App Setup
Set this once for examples below:
```bash
ICL_ROOT="/absolute/path/to/ICL_Official"
```

### Codex (CLI/IDE)
Codex MCP docs: `https://developers.openai.com/codex/mcp`

Add server with CLI:
```bash
codex mcp add icl -- "$ICL_ROOT/bin/icl-mcp" --root "$ICL_ROOT"
```

Optional plugin allowlist:
```bash
codex mcp add icl \
  --env ICL_MCP_PLUGIN_ALLOWLIST=icl.plugins.std_macros \
  -- "$ICL_ROOT/bin/icl-mcp" --root "$ICL_ROOT"
```

Manual config in `~/.codex/config.toml`:
```toml
[mcp_servers.icl]
command = "/absolute/path/to/ICL_Official/bin/icl-mcp"
args = ["--root", "/absolute/path/to/ICL_Official"]
startup_timeout_sec = 20

[mcp_servers.icl.env]
ICL_MCP_ROOT = "/absolute/path/to/ICL_Official"
```

Verify:
```bash
codex mcp --help
codex mcp list
```
In TUI, run `/mcp`.

### Gemini CLI
Gemini MCP docs: `https://geminicli.com/docs/tools/mcp-server/`

Add server (user scope):
```bash
gemini mcp add -s user -e ICL_MCP_ROOT="$ICL_ROOT" \
  icl "$ICL_ROOT/bin/icl-mcp" -- --root "$ICL_ROOT"
```

Optional plugin allowlist:
```bash
gemini mcp add -s user \
  -e ICL_MCP_ROOT="$ICL_ROOT" \
  -e ICL_MCP_PLUGIN_ALLOWLIST=icl.plugins.std_macros \
  icl "$ICL_ROOT/bin/icl-mcp" -- --root "$ICL_ROOT"
```

Manual config in `~/.gemini/settings.json` (or project `.gemini/settings.json`):
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

Verify:
```bash
gemini mcp list
```
In session, run `/mcp`.

### Claude Code
Claude Code MCP docs: `https://code.claude.com/docs/en/mcp`

Add server (user scope):
```bash
claude mcp add --transport stdio --scope user \
  --env ICL_MCP_ROOT="$ICL_ROOT" \
  icl -- "$ICL_ROOT/bin/icl-mcp" --root "$ICL_ROOT"
```

Project-scoped config in `.mcp.json`:
```json
{
  "mcpServers": {
    "icl": {
      "type": "stdio",
      "command": "/absolute/path/to/ICL_Official/bin/icl-mcp",
      "args": ["--root", "/absolute/path/to/ICL_Official"],
      "env": {
        "ICL_MCP_ROOT": "/absolute/path/to/ICL_Official"
      }
    }
  }
}
```

Verify:
```bash
claude mcp list
```
In session, run `/mcp`.

## Verification
```bash
sha256sum -c checksums.txt
```

## Notes
- This package is Linux x86_64 binary-first.
- Binary-only packaging lowers casual source exposure, but is not anti-reverse-engineering protection.

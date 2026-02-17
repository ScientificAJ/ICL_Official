# MCP Quickstart

## 1. Start server
```bash
cd /home/aru/ICP
./run_mcp.sh
```

## 2. Add to MCP client config
Example shape (client-specific keys may differ):

```json
{
  "mcpServers": {
    "icp": {
      "command": "/home/aru/ICP/bin/icp-mcp",
      "args": ["--root", "/home/aru/ICP"],
      "env": {
        "ICL_MCP_ROOT": "/home/aru/ICP"
      }
    }
  }
}
```

## 3. Validate
Call:
- `initialize`
- `tools/list`
- `tools/call` with `icl_compile`

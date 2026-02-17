# MCP Quickstart

## 1. Start server
```bash
cd /home/aru/ICL_Official
./run_mcp.sh
```

## 2. Add to MCP client config
Example shape (client-specific keys may differ):

```json
{
  "mcpServers": {
    "icl": {
      "command": "/home/aru/ICL_Official/bin/icl-mcp",
      "args": ["--root", "/home/aru/ICL_Official"],
      "env": {
        "ICL_MCP_ROOT": "/home/aru/ICL_Official"
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

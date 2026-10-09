# celebrum MCP server

Dependency-free [Model Context Protocol](https://modelcontextprotocol.io)
server. Speaks JSON-RPC 2.0 over stdio and implements the `tools` capability, so
any MCP client (Claude Desktop, opencode, Cursor, VS Code, ...) can drive this
application as tools.

## Run

```bash
python3 mcp-server/mcp_server.py
```

## Tools

Tools are derived from `mcp-server/server_config.json` and include `app_info`
plus (depending on the application) `run_cli`, one tool per discovered HTTP
route, and static-content tools.

## Client configuration

The repository root includes `.mcp.json`:

```json
{
  "mcpServers": {
    "celebrum": {
      "command": "python3",
      "args": [
        "mcp-server/mcp_server.py"
      ]
    }
  }
}
```

## Tests

```bash
python3 -m unittest discover -s tests -p "test_mcp_server.py" -v
```

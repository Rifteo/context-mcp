# auditguard-context-mcp

MCP server that serves [AuditGuard security contexts](https://github.com/AuditGuard-Community/contexts) to AI agents — load the right security knowledge before starting an engagement.

## Install

```bash
pip install auditguard-context-mcp
```

Or run without installing:

```bash
uvx auditguard-context-mcp
```

## MCP Tools

| Tool | Description |
|---|---|
| `list_contexts` | List all available contexts with one-line summaries |
| `get_context` | Load a context by name (L1 overview or L2 full methodology) |
| `search_contexts` | Search contexts by keyword |

## Usage with Claude Code

Add to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "auditguard-contexts": {
      "command": "uvx",
      "args": ["auditguard-context-mcp"]
    }
  }
}
```

Then in your agent:

```
list all available security contexts
load the web-app-pentest context
get the full methodology for cloud-audit
```

## Context levels

Each context has two levels:

- **L1** — Overview and when to use (default)
- **L2** — Full detailed methodology

```
get_context("web-app-pentest", level="L2")
```

## Part of AuditGuard

Part of the [AuditGuard](https://github.com/AuditGuard-Community) open security toolkit.

## License

MIT

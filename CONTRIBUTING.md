# Contributing to auditguard-context-mcp

Thanks for contributing to the AuditGuard open security toolkit.

## Setup

```bash
git clone https://github.com/AuditGuard-Community/context-mcp
cd context-mcp
pip install -e .
```

## Testing locally

Point the server at your local contexts folder:

```bash
$env:AUDITGUARD_CONTEXTS_PATH = "path/to/contexts"
auditguard-context-mcp
```

Or register it with Claude Code:

```bash
claude mcp add auditguard-contexts -e AUDITGUARD_CONTEXTS_PATH="path/to/contexts" -- auditguard-context-mcp
```

## Adding a new MCP tool

1. Add a new `@mcp.tool()` function in `src/auditguard_context_mcp/server.py`
2. Keep tools focused — one job per tool
3. Always handle 404 gracefully and return a helpful message

## Guidelines

- Python 3.10+
- Use `async` for all tools — the server is async throughout
- No breaking changes to existing tool signatures without a version bump
- Test both local mode (`AUDITGUARD_CONTEXTS_PATH`) and remote mode (GitHub API)

## Questions

Open an issue or start a discussion.

<div align="center">

# auditguard-context-mcp

MCP server that serves [AuditGuard security contexts](https://github.com/AuditGuard-Community/contexts) to AI agents — load the right security knowledge before starting an engagement.

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-coming%20soon-lightgrey)](https://pypi.org/project/auditguard-context-mcp)
[![Issues](https://img.shields.io/github/issues/AuditGuard-Community/context-mcp)](https://github.com/AuditGuard-Community/context-mcp/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/AuditGuard-Community/context-mcp/pulls)

</div>

## Install

> PyPI release coming soon. In the meantime, install from source:

```bash
git clone https://github.com/AuditGuard-Community/context-mcp
cd context-mcp
pip install -e .
```

## Register with your agent

### Auto-install (all detected agents)

```bash
auditguard-context install
```

### Single agent

```bash
auditguard-context install --agent claude-code
auditguard-context install --agent cursor
auditguard-context install --agent gemini-cli
```

### Project-level install

```bash
auditguard-context install --agent claude-code --project
```

### See which agents are detected

```bash
auditguard-context agents
```

### Supported agents

| Agent | Config location |
|---|---|
| `claude-code` | `~/.claude.json` (via `claude mcp add`) |
| `cursor` | `~/.cursor/mcp.json` |
| `windsurf` | `~/.codeium/windsurf/mcp_config.json` |
| `gemini-cli` | `~/.gemini/settings.json` |
| `cline` | `~/.cline/data/settings/cline_mcp_settings.json` |
| `kiro` | `~/.kiro/settings/mcp.json` |
| `codex` | `~/.codex/config.toml` |
| `opencode` | `~/.config/opencode/opencode.json` |
| `amp` | `~/.config/amp/settings.json` |
| `continue` | `~/.continue/config.json` |

### Manual install (Claude Code)

```bash
claude mcp add --scope user auditguard-contexts auditguard-context-mcp
```

## MCP Tools

| Tool | Description |
|---|---|
| `list_contexts` | List all available contexts with one-line summaries |
| `get_context` | Load a context by name — L1 overview or L2 full methodology |
| `search_contexts` | Search contexts by keyword |

## Usage

Once registered, ask your agent:

```
list all available security contexts
get the web-app-pentest context
load cloud-audit full methodology
```

## Context levels

Each context has two levels:

- **L1** — Overview and when to use (default)
- **L2** — Full detailed methodology

```
get_context("web-app-pentest", level="L2")
```

## Local development

Point the server at a local clone of the contexts repo:

```bash
AUDITGUARD_CONTEXTS_PATH=/path/to/contexts auditguard-context-mcp
```

Or set it in your agent's MCP config env:

```json
{
  "command": "auditguard-context-mcp",
  "args": [],
  "env": {
    "AUDITGUARD_CONTEXTS_PATH": "/path/to/contexts"
  }
}
```

Without this env var the server fetches contexts live from the GitHub API.

## Part of AuditGuard

Part of the [AuditGuard](https://github.com/AuditGuard-Community) open security toolkit.

## License

MIT

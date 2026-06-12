<div align="center">

# Rifteo Context MCP

MCP server that gives AI agents live bug bounty program scope and [Rifteo security contexts](https://github.com/rifteo/contexts) — load the right knowledge before starting an engagement.

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-coming%20soon-lightgrey)](https://pypi.org/project/rifteo-context-mcp)
[![Issues](https://img.shields.io/github/issues/rifteo/context-mcp)](https://github.com/rifteo/context-mcp/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/rifteo/context-mcp/pulls)

</div>

## Install

> PyPI release coming soon. In the meantime, install from source:

```bash
git clone https://github.com/rifteo/context-mcp
cd context-mcp
pip install -e .
```

## Register with your agent

### Auto-install (all detected agents)

```bash
rifteo-context install
```

### Single agent

```bash
rifteo-context install --agent claude-code
rifteo-context install --agent cursor
rifteo-context install --agent gemini-cli
```

### Project-level install

```bash
rifteo-context install --agent claude-code --project
```

### See which agents are detected

```bash
rifteo-context agents
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
claude mcp add --scope user rifteo-contexts rifteo-context-mcp
```

## MCP Tools

### Contexts

| Tool | Description |
|---|---|
| `list_contexts` | List all available contexts with one-line summaries |
| `get_context` | Load a context by name (L1 overview or L2 full methodology) |
| `search_contexts` | Search contexts by keyword |

Once registered, ask your agent:

```
list all available security contexts
get the web-app-pentest context
load cloud-audit full methodology
```

Each context has two levels:

- **L1** — Overview and when to use (default)
- **L2** — Full detailed methodology

### Bug Bounty Platforms

| Tool | Description |
|---|---|
| `get_program_scope` | Fetch live scope for any bug bounty program (in-scope, out-of-scope, bounty eligibility, policy) |
| `search_hacktivity` | Search publicly disclosed reports by vulnerability type, technology, or keyword |

Connect your accounts:

**HackerOne** — get your token at https://hackerone.com/settings/api_token/edit

```bash
rifteo-context auth hackerone
# HackerOne username: yourname
# HackerOne API token: ****
```

**Intigriti** — get your token at https://app.intigriti.com/settings/api

```bash
rifteo-context auth intigriti
# Intigriti API token: ****
```

YesWeHack works without credentials. Immunefi has no public API.

Then ask your agent:

```
get the scope for hackerone program "security"
get the scope for yeswehack program "datadome-bot-bounty"
search hacktivity for GraphQL vulnerabilities
```

Platform support:

| Platform | Scope | Auth required |
|---|---|---|
| `hackerone` | Full scope + policy | Yes — username + API token |
| `bugcrowd` | Partial (public HTML only) | No (full scope coming soon) |
| `intigriti` | Full scope | Yes — API token |
| `yeswehack` | Full scope | No |
| `immunefi` | Direct link | No |

`search_hacktivity` searches HackerOne public disclosed reports and requires no credentials.

Manage connected platforms:

```bash
rifteo-context auth --list
rifteo-context auth --remove hackerone
```

## Local development

Point the server at a local clone of the contexts repo:

```bash
RIFTEO_CONTEXTS_PATH=/path/to/contexts rifteo-context-mcp
```

Or set it in your agent's MCP config env:

```json
{
  "command": "rifteo-context-mcp",
  "args": [],
  "env": {
    "RIFTEO_CONTEXTS_PATH": "/path/to/contexts"
  }
}
```

Without this env var the server fetches contexts live from the GitHub API.

## Part of Rifteo

Part of the [Rifteo](https://github.com/rifteo) open security toolkit.

## License

MIT

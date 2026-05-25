import os
import json
import tomllib
import tomli_w
import argparse
import subprocess
import getpass
from pathlib import Path
from auditguard_context_mcp.credentials import PLATFORMS, get_platform, set_platform, remove_platform

HOME = Path.home()
XDG  = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))

MCP_ENTRY = {
    "command": "auditguard-context-mcp",
    "args": [],
}

# ── Agent registry ────────────────────────────────────────────────────────────

AGENTS = {
    "claude-code": {
        "config": HOME / ".claude.json",
        "format": "claude-code-cli",
    },
    "cursor": {
        "config": HOME / ".cursor" / "mcp.json",
        "project": Path(".cursor") / "mcp.json",
        "format": "mcpServers",
    },
    "windsurf": {
        "config": HOME / ".codeium" / "windsurf" / "mcp_config.json",
        "format": "mcpServers",
    },
    "gemini-cli": {
        "config": HOME / ".gemini" / "settings.json",
        "format": "mcpServers",
    },
    "cline": {
        "config": HOME / ".cline" / "data" / "settings" / "cline_mcp_settings.json",
        "format": "mcpServers",
    },
    "kiro": {
        "config": HOME / ".kiro" / "settings" / "mcp.json",
        "project": Path(".kiro") / "settings" / "mcp.json",
        "format": "mcpServers",
    },
    "codex": {
        "config": HOME / ".codex" / "config.toml",
        "project": Path(".codex") / "config.toml",
        "format": "toml",
    },
    "opencode": {
        "config": XDG / "opencode" / "opencode.json",
        "format": "mcp",
    },
    "amp": {
        "config": XDG / "amp" / "settings.json",
        "format": "mcpServers",
    },
    "continue": {
        "config": HOME / ".continue" / "config.json",
        "format": "mcpServers-array",
    },
}


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_agents() -> list[str]:
    detected = []
    for name, entry in AGENTS.items():
        config_path = entry["config"]
        if name == "claude-code":
            # Detect via ~/.claude.json or claude binary on PATH
            if config_path.exists() or subprocess.run(
                ["claude", "--version"], capture_output=True
            ).returncode == 0:
                detected.append(name)
        elif config_path.exists() or config_path.parent.exists():
            detected.append(name)
    return detected


# ── Writers ───────────────────────────────────────────────────────────────────

def _read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _install_mcpservers(path: Path, entry_name: str):
    data = _read_json(path)
    data.setdefault("mcpServers", {})[entry_name] = MCP_ENTRY
    _write_json(path, data)


def _install_mcp_key(path: Path, entry_name: str):
    data = _read_json(path)
    data.setdefault("mcp", {})[entry_name] = MCP_ENTRY
    _write_json(path, data)


def _install_mcpservers_array(path: Path, entry_name: str):
    data = _read_json(path)
    servers = data.setdefault("mcpServers", [])
    if not any(s.get("name") == entry_name for s in servers):
        servers.append({"name": entry_name, **MCP_ENTRY})
    _write_json(path, data)


def _install_toml(path: Path, entry_name: str):
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {}

    servers = data.setdefault("mcp_servers", [])
    if not any(s.get("name") == entry_name for s in servers):
        servers.append({"name": entry_name, "command": "auditguard-context-mcp", "args": []})

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def _install_claude_code(entry_name: str, scope: str = "user"):
    # Claude Code stores MCP config in ~/.claude.json; use the CLI to register correctly.
    # Valid scopes: user (global), project (current dir .claude/settings.json)
    cmd = ["claude", "mcp", "add", "--transport", "stdio", "--scope", scope, entry_name, "auditguard-context-mcp"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"claude mcp add exited {result.returncode}")


def install_agent(agent_name: str, entry_name: str = "auditguard-contexts", project: bool = False):
    entry = AGENTS.get(agent_name)
    if not entry:
        raise ValueError(f"Unknown agent '{agent_name}'")

    fmt = entry["format"]

    if fmt == "claude-code-cli":
        scope = "project" if project else "user"
        _install_claude_code(entry_name, scope)
        return f"~/.claude.json (scope: {scope})"

    if project and "project" in entry:
        path = Path.cwd() / entry["project"]
    else:
        path = entry["config"]

    if fmt == "mcpServers":
        _install_mcpservers(path, entry_name)
    elif fmt == "mcp":
        _install_mcp_key(path, entry_name)
    elif fmt == "mcpServers-array":
        _install_mcpservers_array(path, entry_name)
    elif fmt == "toml":
        _install_toml(path, entry_name)

    return path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="auditguard-context",
        description="Manage auditguard-context-mcp across AI agents",
    )
    sub = parser.add_subparsers(dest="command")

    # install
    p_install = sub.add_parser("install", help="Register MCP server in detected agents")
    p_install.add_argument("--agent", help="Target a specific agent (default: all detected)")
    p_install.add_argument("--project", action="store_true", help="Install at project level instead of global")

    # agents
    sub.add_parser("agents", help="List detected agents on this machine")

    # auth
    p_auth = sub.add_parser("auth", help="Connect a bug bounty platform account")
    p_auth.add_argument("platform", nargs="?", help=f"Platform to connect: {', '.join(PLATFORMS)}")
    p_auth.add_argument("--list", action="store_true", help="Show connected platforms")
    p_auth.add_argument("--remove", metavar="PLATFORM", help="Remove credentials for a platform")

    args = parser.parse_args()

    if args.command == "agents":
        detected = detect_agents()
        if not detected:
            print("No supported agents detected.")
        else:
            print("Detected agents:")
            for a in detected:
                print(f"  - {a}")
        return

    if args.command == "install":
        targets = [args.agent] if args.agent else detect_agents()
        if not targets:
            print("No supported agents detected. Use --agent to specify one manually.")
            return

        for agent in targets:
            try:
                path = install_agent(agent, project=args.project)
                print(f"  [OK] {agent} -> {path}")
            except Exception as e:
                print(f"  [FAIL] {agent} -> {e}")
        return

    if args.command == "auth":
        if args.list:
            from auditguard_context_mcp.credentials import load
            data = load()
            if not data:
                print("No platforms connected. Run: auditguard-context auth <platform>")
            else:
                print("Connected platforms:")
                for p in data:
                    print(f"  - {p}")
            return

        if args.remove:
            remove_platform(args.remove)
            print(f"  Removed credentials for {args.remove}")
            return

        platform = args.platform
        if not platform:
            print(f"Available platforms: {', '.join(PLATFORMS)}")
            print("Usage: auditguard-context auth <platform>")
            return

        if platform not in PLATFORMS:
            print(f"Unknown platform '{platform}'. Available: {', '.join(PLATFORMS)}")
            return

        config = PLATFORMS[platform]
        print(f"\n  Connecting {platform}")
        if "help" in config:
            print(f"  {config['help']}\n")

        values = {}
        for field, prompt in zip(config["fields"], config["prompts"]):
            if "token" in field or "password" in field:
                values[field] = getpass.getpass(f"  {prompt}")
            else:
                values[field] = input(f"  {prompt}").strip()

        set_platform(platform, values)
        print(f"\n  Credentials saved. Run auditguard-context auth --list to see connected platforms.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

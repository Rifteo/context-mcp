import os
import re
import base64
from pathlib import Path

import httpx
from fastmcp import FastMCP

REPO_OWNER   = "AuditGuard-Community"
REPO_NAME    = "contexts"
API_BASE     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"
HEADERS      = {"User-Agent": "auditguard-context-mcp"}
LOCAL_CONTEXTS = os.environ.get("AUDITGUARD_CONTEXTS_PATH")

mcp = FastMCP("auditguard-context-mcp")

SKIP = {".github", ".gitignore", ".gitattributes", "README.md", "LICENSE"}


# ── local helpers ────────────────────────────────────────────────────────────

def _local_list() -> list[str]:
    root = Path(LOCAL_CONTEXTS)
    return [d.name for d in root.iterdir() if d.is_dir() and d.name not in SKIP]


def _local_get(name: str) -> str:
    path = Path(LOCAL_CONTEXTS) / name / "CONTEXT.md"
    if not path.exists():
        raise FileNotFoundError(f"Context '{name}' not found at {path}")
    return path.read_text(encoding="utf-8")


# ── remote helpers ───────────────────────────────────────────────────────────

async def _fetch(url: str) -> dict | list:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def _remote_list() -> list[str]:
    items = await _fetch(API_BASE)
    return [i["name"] for i in items if i["type"] == "dir" and i["name"] not in SKIP]


async def _remote_get(name: str) -> str:
    data = await _fetch(f"{API_BASE}/{name}/CONTEXT.md")
    return base64.b64decode(data["content"]).decode("utf-8")


# ── unified accessors ────────────────────────────────────────────────────────

async def _list_names() -> list[str]:
    if LOCAL_CONTEXTS:
        return _local_list()
    return await _remote_list()


async def _get_content(name: str) -> str:
    if LOCAL_CONTEXTS:
        return _local_get(name)
    return await _remote_get(name)


# ── parsers ──────────────────────────────────────────────────────────────────

def _extract_l0(content: str) -> str:
    m = re.search(r"^l0:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extract_section(content: str, level: str) -> str:
    pattern = rf"## {level} —.*?\n([\s\S]*?)(?=\n## |\Z)"
    m = re.search(pattern, content)
    return m.group(1).strip() if m else content


# ── MCP tools ────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_contexts() -> str:
    """List all available AuditGuard security contexts with one-line summaries."""
    names = await _list_names()
    results = []
    for name in sorted(names):
        try:
            content = await _get_content(name)
            l0 = _extract_l0(content)
            results.append(f"- **{name}** — {l0}")
        except Exception:
            results.append(f"- **{name}**")

    return "## Available Contexts\n\n" + "\n".join(results) + \
           "\n\nUse `get_context` to load a context."


@mcp.tool()
async def get_context(name: str, level: str = "L1") -> str:
    """
    Load a security context by name.

    Args:
        name:  Context name (e.g. 'web-app-pentest')
        level: L1 for overview (default), L2 for full methodology
    """
    try:
        content = await _get_content(name)
    except (FileNotFoundError, httpx.HTTPStatusError) as e:
        if isinstance(e, FileNotFoundError) or getattr(e.response, "status_code", 0) == 404:
            return f"Context '{name}' not found. Use list_contexts to see available options."
        raise

    level = level.upper()
    if level == "L0":
        return _extract_l0(content)
    if level in ("L1", "L2"):
        return _extract_section(content, level)
    return content


@mcp.tool()
async def search_contexts(query: str) -> str:
    """
    Search contexts by keyword.

    Args:
        query: Keyword to search for (e.g. 'jwt', 'cloud', 'android')
    """
    names = await _list_names()
    results = []
    q = query.lower()
    for name in names:
        try:
            content = await _get_content(name)
            if q in content.lower() or q in name.lower():
                l0 = _extract_l0(content)
                results.append(f"- **{name}** — {l0}")
        except Exception:
            pass

    if not results:
        return f"No contexts found matching '{query}'."
    return f"## Contexts matching '{query}'\n\n" + "\n".join(results)


def main():
    mcp.run()


if __name__ == "__main__":
    main()

import os
import re
import sys
import base64
import logging
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

# ── logging ──────────────────────────────────────────────────────────────────

_log_level = os.environ.get("AUDITGUARD_LOG_LEVEL", "INFO").upper()
_log_file  = os.environ.get("AUDITGUARD_LOG_FILE")

_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
if _log_file:
    _handlers.append(logging.FileHandler(_log_file, encoding="utf-8"))

logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)
logger = logging.getLogger("auditguard-context-mcp")


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
    logger.info("tool=list_contexts")
    names = await _list_names()
    results = []
    for name in sorted(names):
        try:
            content = await _get_content(name)
            l0 = _extract_l0(content)
            results.append(f"- **{name}** — {l0}")
        except Exception:
            results.append(f"- **{name}**")

    logger.info(f"list_contexts returned {len(names)} context(s)")
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
    logger.info(f"tool=get_context name={name} level={level}")
    try:
        content = await _get_content(name)
    except (FileNotFoundError, httpx.HTTPStatusError) as e:
        if isinstance(e, FileNotFoundError) or getattr(e.response, "status_code", 0) == 404:
            logger.warning(f"get_context: context '{name}' not found")
            return f"Context '{name}' not found. Use list_contexts to see available options."
        logger.error(f"get_context: HTTP error fetching '{name}': {e}")
        raise

    level = level.upper()
    if level == "L0":
        return _extract_l0(content)
    if level in ("L1", "L2"):
        result = _extract_section(content, level)
        logger.info(f"get_context: returned {level} for '{name}' ({len(result)} chars)")
        return result
    return content


@mcp.tool()
async def search_contexts(query: str) -> str:
    """
    Search contexts by keyword.

    Args:
        query: Keyword to search for (e.g. 'jwt', 'cloud', 'android')
    """
    logger.info(f"tool=search_contexts query={query!r}")
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

    logger.info(f"search_contexts: {len(results)} match(es) for {query!r}")
    if not results:
        return f"No contexts found matching '{query}'."
    return f"## Contexts matching '{query}'\n\n" + "\n".join(results)


def main():
    mode = f"local ({LOCAL_CONTEXTS})" if LOCAL_CONTEXTS else "remote (GitHub API)"
    logger.info(f"auditguard-context-mcp starting — mode: {mode}")
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nauditguard-context-mcp stopped.", file=sys.stderr)

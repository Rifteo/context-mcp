import os
import re
import base64
import httpx
from html import unescape as html_unescape
from rifteo_context_mcp.credentials import get_platform

H1_API_BASE = "https://api.hackerone.com/v1"
INTIGRITI_API_BASE = "https://api.intigriti.com/core/researcher/v1"
YWH_API_BASE = "https://api.yeswehack.com"
IMMUNEFI_API_BASE = "https://immunefi.com/api"

_UA = "rifteo-context-mcp"


# ── HackerOne ─────────────────────────────────────────────────────────────────

def _h1_headers() -> dict | None:
    creds = get_platform("hackerone")
    username = (creds or {}).get("username") or os.environ.get("H1_API_USERNAME")
    token = (creds or {}).get("token") or os.environ.get("H1_API_TOKEN")
    if username and token:
        encoded = base64.b64encode(f"{username}:{token}".encode()).decode()
        return {"Authorization": f"Basic {encoded}", "Accept": "application/json"}
    return None


async def h1_get_program_scope(program: str) -> str:
    headers = _h1_headers()
    if not headers:
        return "HackerOne credentials not configured.\nRun: rifteo-context auth hackerone"

    async with httpx.AsyncClient() as client:
        prog_r = await client.get(f"{H1_API_BASE}/hackers/programs/{program}", headers=headers)
        scope_r = await client.get(
            f"{H1_API_BASE}/hackers/programs/{program}/structured_scopes",
            headers=headers,
            params={"page[size]": 100},
        )

    if prog_r.status_code == 401:
        return "HackerOne authentication failed.\nRun: rifteo-context auth hackerone"
    if prog_r.status_code == 404:
        return f"Program '{program}' not found on HackerOne."
    prog_r.raise_for_status()

    attrs = prog_r.json().get("attributes", {})
    name = attrs.get("name", program)
    policy = attrs.get("policy", "")
    offers_bounties = attrs.get("offers_bounties", False)

    in_scope, out_scope = [], []
    if scope_r.status_code == 200:
        for item in scope_r.json().get("data", []):
            a = item.get("attributes", {})
            identifier = a.get("asset_identifier", "")
            asset_type = a.get("asset_type", "")
            eligible_bounty = a.get("eligible_for_bounty", False)
            eligible_submission = a.get("eligible_for_submission", True)
            instruction = a.get("instruction", "")

            line = f"- [{asset_type}] {identifier}"
            if eligible_bounty:
                line += " *(bounty eligible)*"
            if instruction:
                line += f"\n  Note: {instruction}"

            if eligible_submission:
                in_scope.append(line)
            else:
                out_scope.append(line)

    lines = [f"# {name} — HackerOne"]
    if offers_bounties:
        lines.append("Bounties: yes")
    if in_scope:
        lines.append("\n## In Scope\n" + "\n".join(in_scope))
    if out_scope:
        lines.append("\n## Out of Scope\n" + "\n".join(out_scope))
    if policy:
        lines.append(f"\n## Policy\n{policy[:1500]}")

    return "\n".join(lines)


async def h1_search_hacktivity(query: str, limit: int = 10) -> str:
    gql = """
    query HacktivitySearch($query: String!, $limit: Int!) {
      search(index: CompleteHacktivityReportIndex, query_string: $query, size: $limit) {
        nodes {
          ... on HacktivityDocument {
            report {
              title
              url
              substate
              severity { rating }
              reporter { username }
              team { name handle }
              weakness { name }
            }
          }
        }
      }
    }
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://hackerone.com/graphql",
            json={"query": gql, "variables": {"query": query, "limit": limit}},
            headers={"Content-Type": "application/json", "User-Agent": _UA},
        )

    if r.status_code != 200:
        return f"Hacktivity search failed (HTTP {r.status_code})."

    nodes = r.json().get("data", {}).get("search", {}).get("nodes", [])
    if not nodes:
        return f"No hacktivity results found for '{query}'."

    lines = [f"## Hacktivity: {query}\n"]
    for node in nodes:
        report = node.get("report") or {}
        title = report.get("title", "Untitled")
        program = (report.get("team") or {}).get("name", "Unknown")
        severity = ((report.get("severity") or {}).get("rating") or "").upper()
        substate = (report.get("substate") or "").upper()
        weakness = (report.get("weakness") or {}).get("name", "")
        reporter = (report.get("reporter") or {}).get("username", "")
        url = report.get("url", "")

        line = f"**{title}**"
        if severity:
            line += f" [{severity}]"
        if substate:
            line += f" [{substate}]"
        if weakness:
            line += f" — {weakness}"
        line += f"\n  Program: {program}"
        if reporter:
            line += f" | by @{reporter}"
        if url:
            line += f"\n  {url}"
        lines.append(line)

    return "\n\n".join(lines)


# ── Bugcrowd ─────────────────────────────────────────────────────────────────

def _extract_urls_from_text(text: str) -> list[str]:
    urls = []
    for m in re.finditer(r"https?://[\w\-.*]+\.\w+(?:/[\w\-./]*)?", text):
        url = m.group(0).rstrip("/")
        if "bugcrowd" not in url and url not in urls:
            urls.append(url)
    return urls


async def bc_get_program_scope(program: str) -> str:
    url = f"https://bugcrowd.com/engagements/{program}"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": _UA, "Accept": "text/html"})

    if r.status_code == 404:
        return f"Program '{program}' not found on Bugcrowd."
    if r.status_code != 200:
        return f"Bugcrowd fetch failed (HTTP {r.status_code})."

    html = r.text

    # Extract program name from title
    title_m = re.search(r"<title>([^<]+)</title>", html)
    name = program
    if title_m:
        name = re.sub(r"\s*[-–]?\s*Bugcrowd.*$", "", title_m.group(1)).strip()
        name = re.sub(r"^Bug Bounty:\s*", "", name).strip() or program

    # Extract URLs from brief
    in_scope = _extract_urls_from_text(html_unescape(html))

    lines = [f"# {name} — Bugcrowd"]
    lines.append(f"Program URL: {url}")
    if in_scope:
        lines.append("\n## In Scope (extracted from brief)")
        for asset in in_scope[:30]:
            lines.append(f"- {asset}")
    else:
        lines.append("\nScope not publicly visible. Authentication required for full scope.")
        lines.append("Run: rifteo-context auth bugcrowd")

    return "\n".join(lines)


# ── Intigriti ─────────────────────────────────────────────────────────────────

def _intigriti_headers() -> dict | None:
    creds = get_platform("intigriti")
    token = (creds or {}).get("token") or os.environ.get("INTIGRITI_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    return None


async def intigriti_get_program_scope(program: str) -> str:
    headers = _intigriti_headers()
    if not headers:
        return "Intigriti credentials not configured.\nRun: rifteo-context auth intigriti"

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{INTIGRITI_API_BASE}/programs/{program}",
            headers=headers,
        )

    if r.status_code == 401:
        return "Intigriti authentication failed.\nRun: rifteo-context auth intigriti"
    if r.status_code == 404:
        return f"Program '{program}' not found on Intigriti."
    r.raise_for_status()

    data = r.json()
    name = data.get("name", program)
    domains = data.get("domains", [])
    in_scope, out_scope = [], []

    for d in domains:
        endpoint = d.get("endpoint", "")
        tier = d.get("tier", "")
        bounty = d.get("bounty", False)
        in_s = d.get("inScope", True)

        line = f"- {endpoint}"
        if tier:
            line += f" [tier {tier}]"
        if bounty:
            line += " *(bounty eligible)*"

        if in_s:
            in_scope.append(line)
        else:
            out_scope.append(line)

    lines = [f"# {name} — Intigriti"]
    if in_scope:
        lines.append("\n## In Scope\n" + "\n".join(in_scope))
    if out_scope:
        lines.append("\n## Out of Scope\n" + "\n".join(out_scope))

    return "\n".join(lines)


# ── YesWeHack ─────────────────────────────────────────────────────────────────

async def ywh_get_program_scope(program: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{YWH_API_BASE}/programs/{program}",
            headers={"Accept": "application/json", "User-Agent": _UA},
        )

    if r.status_code == 404:
        return f"Program '{program}' not found on YesWeHack."
    if r.status_code != 200:
        return f"YesWeHack fetch failed (HTTP {r.status_code})."

    data = r.json()
    name = data.get("title", program)
    scopes = data.get("scopes", [])
    bounty_min = data.get("bounty_reward_min")
    bounty_max = data.get("bounty_reward_max")

    in_scope = []
    for s in scopes:
        scope_type = s.get("scope_type_name") or s.get("scope_type", "")
        scope = s.get("scope", "")
        asset_value = s.get("asset_value", "")

        line = f"- [{scope_type}] {scope}"
        if asset_value:
            line += f" [value: {asset_value}]"
        in_scope.append(line)

    lines = [f"# {name} — YesWeHack"]
    if bounty_min and bounty_max:
        lines.append(f"Bounty range: {bounty_min} - {bounty_max} EUR")
    if in_scope:
        lines.append("\n## In Scope\n" + "\n".join(in_scope))

    return "\n".join(lines)


# ── Immunefi ─────────────────────────────────────────────────────────────────

async def immunefi_get_program_scope(program: str) -> str:
    url = f"https://immunefi.com/bug-bounty/{program}/"
    return (
        f"# {program} — Immunefi\n\n"
        f"Immunefi does not expose a public API for program scope.\n"
        f"View full scope and bounty details at: {url}"
    )


# ── Credential verification ───────────────────────────────────────────────────

async def verify_hackerone(creds: dict) -> tuple[bool, str]:
    username = creds.get("username", "")
    token = creds.get("token", "")
    if not username or not token:
        return False, "Missing username or token."
    encoded = base64.b64encode(f"{username}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {encoded}", "Accept": "application/json", "User-Agent": _UA}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{H1_API_BASE}/hackers/programs", headers=headers, params={"page[size]": 1})
    if r.status_code == 200:
        return True, f"Authenticated as @{username}"
    if r.status_code == 401:
        return False, "Invalid credentials. Check your username and API token."
    return False, f"Unexpected response (HTTP {r.status_code})."


async def verify_intigriti(creds: dict) -> tuple[bool, str]:
    token = creds.get("token", "")
    if not token:
        return False, "Missing token."
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{INTIGRITI_API_BASE}/me", headers=headers)
    if r.status_code == 200:
        data = r.json()
        name = data.get("userName") or data.get("email") or "unknown"
        return True, f"Authenticated as {name}"
    if r.status_code == 401:
        return False, "Invalid token."
    return False, f"Unexpected response (HTTP {r.status_code})."


PLATFORM_VERIFIERS = {
    "hackerone": verify_hackerone,
    "intigriti": verify_intigriti,
}


# ── Router ────────────────────────────────────────────────────────────────────

SUPPORTED_PLATFORMS = {
    "hackerone": h1_get_program_scope,
    "bugcrowd": bc_get_program_scope,
    "intigriti": intigriti_get_program_scope,
    "yeswehack": ywh_get_program_scope,
    "immunefi": immunefi_get_program_scope,
}


async def get_program_scope(platform: str, program: str) -> str:
    handler = SUPPORTED_PLATFORMS.get(platform.lower())
    if not handler:
        supported = ", ".join(SUPPORTED_PLATFORMS)
        return f"Platform '{platform}' not supported.\nSupported: {supported}"
    return await handler(program)

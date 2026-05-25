import os
import base64
import httpx
from auditguard_context_mcp.credentials import get_platform

H1_API_BASE = "https://api.hackerone.com/v1"


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
        return (
            "HackerOne credentials not configured.\n"
            "Run: auditguard-context auth hackerone"
        )

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{H1_API_BASE}/hackers/programs/{program}",
            headers=headers,
            params={"include": "structured_scopes"},
        )

    if r.status_code == 401:
        return (
            "HackerOne authentication failed.\n"
            "Run: auditguard-context auth hackerone"
        )
    if r.status_code == 404:
        return f"Program '{program}' not found on HackerOne."
    r.raise_for_status()

    data = r.json()
    attrs = data.get("attributes", {})
    name = attrs.get("name", program)
    policy = attrs.get("policy", "")
    offers_bounties = attrs.get("offers_bounties", False)

    scopes = data.get("relationships", {}).get("structured_scopes", {}).get("data", [])
    in_scope, out_scope = [], []
    for item in scopes:
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
            headers={"Content-Type": "application/json", "User-Agent": "auditguard-context-mcp"},
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

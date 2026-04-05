import base64
import re

import httpx

from app.config import settings
from app.confluence_format import page_title, storage_html
from app.models import DialEntry


class ConfluenceError(Exception):
    pass


def normalized_confluence_site_url(raw: str) -> str:
    """
    Confluence Cloud REST calls use the site root, e.g. https://your-site.atlassian.net
    (not .../wiki). Accepts pasted browser URLs and strips /wiki if present.
    """
    base = (raw or "").strip().rstrip("/")
    if not base:
        return base
    # Strip path after host (e.g. .../wiki/spaces/FOO)
    m = re.match(r"^(https?://[^/]+)", base, re.I)
    if m:
        base = m.group(1).rstrip("/")
    if base.lower().endswith("/wiki"):
        base = base[:-5].rstrip("/")
    return base


def _auth_header() -> str:
    raw = f"{settings.confluence_email}:{settings.confluence_api_token}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


def _api_base() -> str:
    site = normalized_confluence_site_url(settings.confluence_base_url)
    return f"{site}/wiki/rest/api"


async def publish_dial_entry(entry: DialEntry) -> dict:
    if not all(
        [
            settings.confluence_base_url,
            settings.confluence_email,
            settings.confluence_api_token,
            settings.confluence_space_key,
        ]
    ):
        raise ConfluenceError("Confluence is not fully configured (check .env).")

    url = f"{_api_base()}/content"

    body = {
        "type": "page",
        "title": page_title(entry),
        "space": {"key": settings.confluence_space_key},
        "body": {
            "storage": {
                "value": storage_html(entry),
                "representation": "storage",
            }
        },
    }
    if settings.confluence_parent_page_id:
        body["ancestors"] = [{"id": settings.confluence_parent_page_id.strip()}]

    headers = {
        "Authorization": _auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=body, headers=headers)

    if r.status_code >= 400:
        raise ConfluenceError(f"Confluence API error {r.status_code}: {r.text[:500]}")

    return r.json()


async def probe_confluence() -> dict:
    """
    Lightweight checks: credentials and space access. Does not create content.
    """
    missing: list[str] = []
    if not settings.confluence_base_url.strip():
        missing.append("CONFLUENCE_BASE_URL")
    if not settings.confluence_email.strip():
        missing.append("CONFLUENCE_EMAIL")
    if not settings.confluence_api_token.strip():
        missing.append("CONFLUENCE_API_TOKEN")
    if not settings.confluence_space_key.strip():
        missing.append("CONFLUENCE_SPACE_KEY")

    if missing:
        return {"ok": False, "missing": missing, "message": "Set these in .env (see .env.example)."}

    space_key = settings.confluence_space_key.strip()
    url = f"{_api_base()}/space/{space_key}"
    headers = {
        "Authorization": _auth_header(),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=headers)

        if r.status_code == 200:
            data = r.json()
            out: dict = {
                "ok": True,
                "space_key": data.get("key"),
                "space_name": data.get("name"),
                "site": normalized_confluence_site_url(settings.confluence_base_url),
            }
            if settings.confluence_parent_page_id:
                pid = settings.confluence_parent_page_id.strip()
                pr = await client.get(
                    f"{_api_base()}/content/{pid}?expand=ancestors",
                    headers=headers,
                )
                if pr.status_code == 200:
                    p = pr.json()
                    out["parent_page"] = {"id": p.get("id"), "title": p.get("title")}
                else:
                    out["parent_page_warning"] = (
                        f"Could not load parent page {pid}: HTTP {pr.status_code}"
                    )
            return out

    return {
        "ok": False,
        "http_status": r.status_code,
        "message": r.text[:800] if r.text else "No response body",
        "hint": "Check site URL, email, API token, and that your account can view this space.",
    }

import base64

import httpx

from app.config import settings
from app.confluence_format import page_title, storage_html
from app.models import DialEntry


class ConfluenceError(Exception):
    pass


def _auth_header() -> str:
    raw = f"{settings.confluence_email}:{settings.confluence_api_token}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


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

    base = settings.confluence_base_url.rstrip("/")
    url = f"{base}/wiki/rest/api/content"

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
        body["ancestors"] = [{"id": settings.confluence_parent_page_id}]

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

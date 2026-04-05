from datetime import date

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import settings
from app.confluence_client import ConfluenceError, publish_dial_entry
from app.models import DialEntry
from app.parse_unstructured import parse_telegram_or_email_text

app = FastAPI(title="Espresso dial journal", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _check_webhook_secret(secret: str | None) -> None:
    expected = settings.webhook_secret
    if not expected:
        return
    if not secret or secret != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@app.get("/", response_class=HTMLResponse)
async def form_page() -> str:
    today = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Espresso dial log</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 32rem; margin: 2rem auto; padding: 0 1rem; }}
    label {{ display: block; margin-top: 0.75rem; font-weight: 600; }}
    input, textarea {{ width: 100%; box-sizing: border-box; margin-top: 0.25rem; padding: 0.5rem; }}
    button {{ margin-top: 1rem; padding: 0.5rem 1rem; }}
  </style>
</head>
<body>
  <h1>Log a dial</h1>
  <form method="post" action="/entries/form">
    <label>Roaster <input name="roaster" required /></label>
    <label>Roast style <input name="roast_style" required /></label>
    <label>Date <input name="entry_date" type="date" value="{today}" required /></label>
    <label>Dose in (g) <input name="dose_in_g" type="number" step="0.1" required /></label>
    <label>Dose out (g) <input name="dose_out_g" type="number" step="0.1" required /></label>
    <label>Grind size <input name="grind_size" required /></label>
    <label>Grinder <input name="grinder" required /></label>
    <label>Extraction time (s) <input name="extraction_time_s" type="number" step="0.1" required /></label>
    <label>Tasting notes <textarea name="tasting_notes" rows="4"></textarea></label>
    <button type="submit">Post to Confluence</button>
  </form>
</body>
</html>"""


@app.post("/entries/form")
async def create_from_form(
    roaster: str = Form(),
    roast_style: str = Form(),
    entry_date: date = Form(),
    dose_in_g: float = Form(),
    dose_out_g: float = Form(),
    grind_size: str = Form(),
    grinder: str = Form(),
    extraction_time_s: float = Form(),
    tasting_notes: str = Form(""),
) -> JSONResponse:
    entry = DialEntry(
        roaster=roaster,
        roast_style=roast_style,
        entry_date=entry_date,
        dose_in_g=dose_in_g,
        dose_out_g=dose_out_g,
        grind_size=grind_size,
        grinder=grinder,
        extraction_time_s=extraction_time_s,
        tasting_notes=tasting_notes,
        source="web",
    )
    try:
        result = await publish_dial_entry(entry)
    except ConfluenceError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return JSONResponse({"ok": True, "confluence_id": result.get("id"), "title": result.get("title")})


@app.post("/api/v1/entries")
async def create_from_json(entry: DialEntry) -> JSONResponse:
    try:
        result = await publish_dial_entry(entry)
    except ConfluenceError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return JSONResponse({"ok": True, "confluence_id": result.get("id"), "title": result.get("title")})


@app.post("/webhooks/telegram")
async def webhook_telegram(
    request: Request,
    secret: str | None = Query(default=None),
) -> JSONResponse:
    _check_webhook_secret(secret)
    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return JSONResponse({"ok": True, "ignored": True})

    text = msg.get("text") or msg.get("caption")
    if not text:
        raise HTTPException(status_code=400, detail="No text in message")

    try:
        entry = parse_telegram_or_email_text(text, "telegram")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse entry: {exc}") from exc

    try:
        result = await publish_dial_entry(entry)
    except ConfluenceError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return JSONResponse({"ok": True, "confluence_id": result.get("id")})


@app.post("/webhooks/email")
async def webhook_email(
    request: Request,
    secret: str | None = Query(default=None),
) -> JSONResponse:
    """
    Accept SendGrid Inbound Parse (multipart) or JSON {{ "text": "..." }}.
    Body should use the same key:value lines as Telegram.
    """
    _check_webhook_secret(secret)
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc
        text = payload.get("text") or payload.get("body") or ""
        if not text and isinstance(payload.get("html"), str):
            text = payload["html"]
    else:
        form = await request.form()
        text = str(form.get("text") or form.get("plain") or "")
        if not text:
            text = str(form.get("html") or "")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty body")

    try:
        entry = parse_telegram_or_email_text(text, "email")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse entry: {exc}") from exc

    try:
        result = await publish_dial_entry(entry)
    except ConfluenceError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return JSONResponse({"ok": True, "confluence_id": result.get("id")})

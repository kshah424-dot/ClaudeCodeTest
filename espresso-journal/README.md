# Espresso dial journal

Log espresso dialing sessions and create a **Confluence** page for each entry. Submit data from a **web form**, **JSON API**, **Telegram**, or an **email webhook** (e.g. SendGrid Inbound Parse).

## Fields

| Field | Description |
|--------|-------------|
| Roaster | Roaster name |
| Roast style | e.g. light, blend, SO espresso |
| Date | Dial date |
| Dose in (g) | Ground coffee in the basket |
| Dose out (g) | Yield in the cup |
| Grind size | Setting or reference |
| Grinder | Grinder model |
| Extraction time (s) | Shot time |
| Tasting notes | Free text |

## Setup

1. **Python 3.10 or newer** (3.11 recommended). The service uses current FastAPI and Pydantic; older system Pythons are not supported.

   ```bash
   cd espresso-journal
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. Configure **Confluence Cloud** in `.env` (see [Confluence Cloud](#confluence-cloud) below).

3. Run the server:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. Open `http://localhost:8000` for the HTML form.

5. Check Confluence connectivity: `GET http://localhost:8000/health/confluence` or:

   ```bash
   cd espresso-journal
   PYTHONPATH=. python scripts/verify_confluence.py
   ```

### Confluence Cloud

Authentication uses **Basic auth**: your **Atlassian account email** and an **[API token](https://id.atlassian.com/manage-profile/security/api-tokens)** (not your normal password).

| Variable | What to put |
|----------|----------------|
| `CONFLUENCE_BASE_URL` | Site root: `https://your-site.atlassian.net` (no `/wiki` required; pasted wiki URLs are normalized) |
| `CONFLUENCE_EMAIL` | Same email you use for Atlassian / Confluence |
| `CONFLUENCE_API_TOKEN` | Token from Atlassian account → Security → **Create and manage API tokens** |
| `CONFLUENCE_SPACE_KEY` | Short key from the space URL (`/wiki/spaces/ABC/...` → `ABC`) |
| `CONFLUENCE_PARENT_PAGE_ID` | Optional. Numeric page ID so new dial logs are **child pages** under your journal page |

Your account needs permission to **create pages** in that space (typically “Add” on pages or space admin). If the probe succeeds but creating pages returns 403, ask a space admin to grant **create** permission.

### JSON API

`POST /api/v1/entries` with JSON body, for example:

```json
{
  "roaster": "Heart",
  "roast_style": "light espresso",
  "entry_date": "2026-04-05",
  "dose_in_g": 18.0,
  "dose_out_g": 36.0,
  "grind_size": "2.5",
  "grinder": "Niche Zero",
  "extraction_time_s": 28.0,
  "tasting_notes": "Bright, short finish."
}
```

### Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token.
2. Expose your server over HTTPS (e.g. Cloudflare Tunnel, ngrok, or a VPS).
3. Set the webhook (replace values):

   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-host/webhooks/telegram?secret=YOUR_WEBHOOK_SECRET"
   ```

4. Put `WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET` in `.env` (same value as `secret` in the URL).

Send a message using **key:value lines** (or a single JSON object). Example:

```
roaster: Heart
roast_style: light espresso
date: 2026-04-05
dose_in: 18
dose_out: 36
grind_size: 2.5
grinder: Niche Zero
extraction_time: 28
notes: Bright, short finish.
```

### Email

Use a provider that **POSTs the parsed email** to your URL (e.g. [SendGrid Inbound Parse](https://docs.sendgrid.com/for-developers/parsing-email/inbound-email)). Point it at:

`https://your-host/webhooks/email?secret=YOUR_WEBHOOK_SECRET`

Use the same key:value body in the plain-text part of the email as in the Telegram example.

## Separate GitHub repository

This folder can live inside a larger repo or be pushed on its own:

```bash
cd espresso-journal
git init
git add .
git commit -m "Initial espresso journal service"
gh repo create espresso-dial-journal --private --source=. --remote=origin --push
```

(Requires [GitHub CLI](https://cli.github.com/) and authentication.)

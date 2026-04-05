"""Parse key:value or JSON from Telegram, email body, etc."""

from __future__ import annotations

import json
import re
from datetime import date, datetime

from dateutil import parser as date_parser

from app.models import DialEntry, SourceChannel

KEY_ALIASES: dict[str, str] = {
    "roaster": "roaster",
    "roast": "roast_style",
    "roast_style": "roast_style",
    "style": "roast_style",
    "date": "entry_date",
    "dose_in": "dose_in_g",
    "dose_in_g": "dose_in_g",
    "in": "dose_in_g",
    "dose_out": "dose_out_g",
    "dose_out_g": "dose_out_g",
    "out": "dose_out_g",
    "yield": "dose_out_g",
    "grind": "grind_size",
    "grind_size": "grind_size",
    "setting": "grind_size",
    "grinder": "grinder",
    "time": "extraction_time_s",
    "extraction_time": "extraction_time_s",
    "extraction_time_s": "extraction_time_s",
    "shot_time": "extraction_time_s",
    "notes": "tasting_notes",
    "tasting_notes": "tasting_notes",
    "tasting": "tasting_notes",
}


def _parse_date(value: str) -> date:
    value = value.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    dt = date_parser.parse(value, dayfirst=False, yearfirst=True)
    return dt.date()


def parse_key_value_body(text: str, source: SourceChannel) -> DialEntry:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    data: dict[str, object] = {}
    notes_lines: list[str] = []
    in_notes = False

    for line in lines:
        lower = line.lower()
        if lower.startswith("notes:") or lower.startswith("tasting_notes:"):
            in_notes = True
            _, _, rest = line.partition(":")
            rest = rest.strip()
            if rest:
                notes_lines.append(rest)
            continue
        if in_notes:
            notes_lines.append(line)
            continue

        m = re.match(r"^([^:]+):\s*(.*)$", line)
        if not m:
            continue
        key_raw = m.group(1).strip().lower().replace(" ", "_")
        val = m.group(2).strip()
        key = KEY_ALIASES.get(key_raw, key_raw)
        if key == "entry_date":
            data["entry_date"] = _parse_date(val)
        elif key == "dose_in_g":
            data["dose_in_g"] = float(val.replace("g", "").strip())
        elif key == "dose_out_g":
            data["dose_out_g"] = float(val.replace("g", "").strip())
        elif key == "extraction_time_s":
            data["extraction_time_s"] = float(re.sub(r"s$", "", val, flags=re.I).strip())
        elif key in ("roaster", "roast_style", "grind_size", "grinder"):
            data[key] = val
        elif key == "tasting_notes":
            notes_lines.append(val)

    if notes_lines:
        data["tasting_notes"] = "\n".join(notes_lines)

    data["source"] = source
    if "entry_date" not in data:
        data["entry_date"] = date.today()

    return DialEntry.model_validate(data)


def parse_json_body(raw: str, source: SourceChannel) -> DialEntry:
    obj = json.loads(raw)
    if isinstance(obj, dict):
        obj = dict(obj)
        obj.setdefault("source", source)
        if "date" in obj and "entry_date" not in obj:
            obj["entry_date"] = obj.pop("date")
        return DialEntry.model_validate(obj)
    raise ValueError("JSON must be an object")


def parse_telegram_or_email_text(text: str, source: SourceChannel) -> DialEntry:
    text = text.strip()
    if text.startswith("{"):
        return parse_json_body(text, source)
    return parse_key_value_body(text, source)

from xml.sax.saxutils import escape

from app.models import DialEntry


def page_title(entry: DialEntry) -> str:
    d = entry.entry_date.isoformat()
    short_roaster = entry.roaster.strip()[:40]
    return f"Dial — {short_roaster} — {d}"


def storage_html(entry: DialEntry) -> str:
    """Confluence storage format (XHTML-like)."""
    rows = [
        ("Roaster", entry.roaster),
        ("Roast style", entry.roast_style),
        ("Date", entry.entry_date.isoformat()),
        ("Dose in (g)", f"{entry.dose_in_g:g}"),
        ("Dose out (g)", f"{entry.dose_out_g:g}"),
        ("Grind size", entry.grind_size),
        ("Grinder", entry.grinder),
        ("Extraction time (s)", f"{entry.extraction_time_s:g}"),
        ("Source", entry.source),
    ]
    trs = []
    for label, value in rows:
        trs.append(
            f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>"
        )
    notes = entry.tasting_notes.strip() or "—"
    notes_block = f"<h2>Tasting notes</h2><p>{escape(notes).replace(chr(10), '<br/>')}</p>"
    table = (
        "<table class='wrapped'>"
        "<tbody>"
        + "".join(trs)
        + "</tbody></table>"
    )
    return table + notes_block


def plain_text_summary(entry: DialEntry) -> str:
    lines = [
        f"Roaster: {entry.roaster}",
        f"Roast style: {entry.roast_style}",
        f"Date: {entry.entry_date.isoformat()}",
        f"Dose in: {entry.dose_in_g:g} g",
        f"Dose out: {entry.dose_out_g:g} g",
        f"Grind size: {entry.grind_size}",
        f"Grinder: {entry.grinder}",
        f"Extraction time: {entry.extraction_time_s:g} s",
        f"Source: {entry.source}",
        "",
        "Tasting notes:",
        entry.tasting_notes.strip() or "—",
    ]
    return "\n".join(lines)

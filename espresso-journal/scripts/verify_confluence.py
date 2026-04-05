#!/usr/bin/env python3
"""
Verify Confluence Cloud credentials without creating a page.

Run from the espresso-journal directory (so .env is found):

  cd espresso-journal
  PYTHONPATH=. python scripts/verify_confluence.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def _main() -> int:
    from app.confluence_client import probe_confluence

    result = await probe_confluence()
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

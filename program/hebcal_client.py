"""Hebcal JSON API client for the KKZZ bulletin.

Fetches the Jewish calendar (parashiyot, holidays, Rosh Hodesh, Hebrew
dates) from Hebcal's public calendar service, per bulletin/sources.md.
Zemanim are NOT taken from here (computed locally in zemanim.py); Hebcal
serves dates and names, and may be used to cross-check times.

Attribution (required, goes in the bulletin colophon): calendar data from
Hebcal.com.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date

API = "https://www.hebcal.com/hebcal"

# diaspora, sedra on, major+minor holidays, Rosh Hodesh, fast days,
# special Shabbatot, Hebrew date for every day off (requested per-item).
BASE_PARAMS = {
    "v": "1",
    "cfg": "json",
    "maj": "on",
    "min": "on",
    "nx": "on",  # Rosh Hodesh
    "mf": "on",  # minor fasts
    "ss": "on",  # special Shabbatot
    "s": "on",   # weekly sedra
    "i": "off",  # diaspora
    "lg": "s",   # Sephardic transliterations
}


def fetch_events(start: date, end: date) -> list[dict]:
    """All Hebcal events from start to end inclusive, as raw item dicts."""
    params = dict(BASE_PARAMS)
    params["start"] = start.isoformat()
    params["end"] = end.isoformat()
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "kzzhv-bulletin/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data.get("items", [])


def parashah_by_shabbat(items: list[dict]) -> dict[date, str]:
    """Map each Saturday date to its Torah reading name (e.g. 'Nitzavim')."""
    out: dict[date, str] = {}
    for it in items:
        if it.get("category") == "parashat":
            d = date.fromisoformat(it["date"][:10])
            name = it["title"]
            if name.startswith("Parashat "):
                name = name[len("Parashat "):]
            out[d] = name
    return out


def holidays(items: list[dict]) -> list[dict]:
    """Holiday/fast/roshchodesh items with parsed dates."""
    out = []
    for it in items:
        if it.get("category") in ("holiday", "roshchodesh", "fast"):
            out.append(
                {
                    "date": date.fromisoformat(it["date"][:10]),
                    "title": it["title"],
                    "category": it["category"],
                    "subcat": it.get("subcat"),
                    "yomtov": bool(it.get("yomtov")),
                    "hebrew": it.get("hebrew"),
                }
            )
    return out


if __name__ == "__main__":
    items = fetch_events(date(2026, 9, 1), date(2026, 10, 15))
    for d, p in sorted(parashah_by_shabbat(items).items()):
        print(d, p)
    for h in holidays(items)[:12]:
        print(h["date"], h["title"], "(yomtov)" if h["yomtov"] else "")

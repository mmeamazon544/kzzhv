"""The calendar scope as bulletins (bulletin/luach.md, "Calendar scope";
Marc's order of 15 November 2026 that every holiday get a bulletin).

Every Shabbat gets a bulletin. So does every festival and fast the brief
names: Rosh Hashana, Kippur, Sukkot, Shemini Atseret, Simhat Torah,
Hanukkah, Purim, Pesah, Shabuot, Tish'a Be'Ab, the minor fasts (Gedalia,
Tebet, Esther, Tammuz), Tu BiShbat and Lag LaOmer. An occasion within two
days of a Shabbat, or of another occasion that is, belongs to that
Shabbat's bulletin (the brief's clustering rule, applied transitively, so
Pesah VII on a Wednesday joins Pesah VIII on the Thursday and the Shabbat
after). An occasion further from any Shabbat gets a bulletin of its own,
whose id is its first day. Rosh Hodesh, Purim Katan, Pesah Sheni, Shushan
Purim, the intermediate days and the modern days get no bulletin and no
place here; the Shabbat bulletin's week-ahead lines announce them.

Hanukkah counts by its first day only (a season, not a chain of days;
otherwise it would fuse two Shabbatot into one bulletin). The bulletin
that holds it lists all eight candle lightings.

Nothing here touches the network except fetch_events (Hebcal).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from hebcal_client import fetch_events, holidays

FASTS = {"Tzom Gedaliah", "Asara B'Tevet", "Ta'anit Esther", "Tzom Tammuz", "Tish'a B'Av"}
FESTIVALS = {"Purim"}                   # not yom tob, a bulletin of its own all the same
MINOR = {"Tu BiShvat", "Lag BaOmer"}
HANUKKAH_FIRST_DAY = "Chanukah: 2 Candles"   # the first candle burns the evening before
RANK = {"yomtov": 0, "festival": 1, "hanukkah": 1, "fast": 2, "minor": 3}
REACH = 2                               # days: the brief's "within two days"


def norm(title: str) -> str:
    """Hebcal spells with typographic apostrophes; names.md with plain ones."""
    return title.replace("’", "'").replace("‘", "'")


def strip_year(title: str) -> str:
    return re.sub(r" \d{4,5}$", "", title)


def strip_day(base: str) -> str:
    """'Pesach VII' -> 'Pesach'; 'Rosh Hashana II' -> 'Rosh Hashana'."""
    return re.sub(r" (I|II|VII|VIII)$", "", base)


def occasions(events: list[dict]) -> list[dict]:
    """Every day in the events that earns a bulletin or a place in one:
    {date, base (Hebcal name, year stripped), kind, title, hebrew}."""
    out: dict[tuple, dict] = {}
    for h in holidays(events):
        if h["category"] == "roshchodesh":
            continue
        base = norm(strip_year(h["title"]))
        if h["yomtov"]:
            kind = "yomtov"
        elif base in FASTS:
            kind = "fast"
        elif base in FESTIVALS:
            kind = "festival"
        elif base == HANUKKAH_FIRST_DAY:
            kind, base = "hanukkah", "Chanukah"
        elif base in MINOR:
            kind = "minor"
        else:
            continue
        out.setdefault((h["date"], base), {
            "date": h["date"], "base": base, "kind": kind,
            "title": norm(h["title"]), "hebrew": h.get("hebrew"),
        })
    return sorted(out.values(), key=lambda o: (o["date"], RANK[o["kind"]]))


def saturdays(start: date, end: date) -> list[date]:
    d = start + timedelta(days=(5 - start.weekday()) % 7)
    out = []
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


def _bulletin(anchor: date, shabbat: date | None, occ: list[dict]) -> dict:
    dates = sorted({o["date"] for o in occ} | ({shabbat} if shabbat else set()))
    return {
        "id": anchor, "shabbat": shabbat, "occasions": occ,
        "dates": dates, "eve": dates[0] - timedelta(days=1),
    }


def bulletins(start: date, end: date, events: list[dict] | None = None) -> list[dict]:
    """Every bulletin anchored in [start, end], in date order. Each is
    {id, shabbat (date or None), occasions, dates (all days it covers,
    Shabbat included), eve (the day before the first of them)}."""
    lo, hi = start - timedelta(days=10), end + timedelta(days=10)
    if events is None:
        events = fetch_events(lo, hi)
    occ = occasions(events)
    nodes = sorted({o["date"] for o in occ} | set(saturdays(lo, hi)))
    chains: list[list[date]] = []
    for d in nodes:
        if chains and (d - chains[-1][-1]).days <= REACH:
            chains[-1].append(d)
        else:
            chains.append([d])
    out = []
    for chain in chains:
        sats = [d for d in chain if d.weekday() == 5]
        mine = [o for o in occ if o["date"] in chain]
        if not sats:
            out.append(_bulletin(mine[0]["date"], None, mine))
            continue
        for s in sats:
            # Two Shabbatot can share a chain only if occasions bridge the
            # week between them; each occasion then goes to the nearer one.
            own = [o for o in mine
                   if min(sats, key=lambda x: (abs((o["date"] - x).days), x)) == s]
            out.append(_bulletin(s, s, own))
    return sorted((b for b in out if start <= b["id"] <= end), key=lambda b: b["id"])


def bulletin_for(anchor: date, events: list[dict] | None = None) -> dict | None:
    """The bulletin whose id is this day, or None when the day is neither
    a Saturday nor the first day of a standalone occasion."""
    for b in bulletins(anchor, anchor, events):
        if b["id"] == anchor:
            return b
    return None


if __name__ == "__main__":
    import sys
    y = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year
    for b in bulletins(date(y, 1, 1), date(y, 12, 31)):
        if not b["occasions"] and len(sys.argv) < 3:
            continue
        kind = "Shabbat" if b["shabbat"] else "ALONE  "
        occ = ", ".join(f"{o['base']} ({o['date']:%a %d %b})" for o in b["occasions"])
        print(f"{b['id']}  {kind}  eve {b['eve']:%a %d %b}  {occ}")

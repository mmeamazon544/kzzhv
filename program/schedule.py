"""When a bulletin is proofed and when it goes out (Marc's rule of
15 November 2026).

The bulletin for a Shabbat is proofed the day before its eve and goes out
on the eve itself: a plain Shabbat is proofed on Thursday and mailed on
Friday. A festival cluster whose first eve falls earlier in the week moves
both days earlier by the same rule — proof the day before the first eve,
mail on the first eve — so a Pesah that begins on a Thursday is proofed on
Tuesday and mailed on Wednesday. The same two days hold for the reminder
(evening of the proof day) and the send moment (6:00 am New York on the
mailing day; a GitHub cron queued late still lands the same morning, and an
approval that arrives after that moment publishes and sends at once).

Festivals more than two days from a Shabbat are not yet clustered (see
bulletin.detect_cluster) and so take no part here.

Usage:
  python3 program/schedule.py --proof-today     prints the bulletin id to
                                                proof now, or nothing
  python3 program/schedule.py 2027-04-24        describes one bulletin
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SEND_HOUR = 6


def today_ny() -> date:
    return datetime.now(NY).date()


def next_bulletin(today: date | None = None) -> date:
    """The Saturday of the bulletin that is next in line: the coming
    Saturday, or the one after when today is itself a Saturday (that
    bulletin has already gone out)."""
    t = today or today_ny()
    days = (5 - t.weekday()) % 7
    if days == 0:
        days = 7
    return t + timedelta(days=days)


def first_eve(sat: date) -> tuple[date, str]:
    """The earliest eve the bulletin covers — Friday, or the eve of a
    clustered festival when that comes first — and the cluster's name
    ('' for a plain Shabbat)."""
    import bulletin

    eve = sat - timedelta(days=1)
    events = bulletin.fetch_events(sat - timedelta(days=3), sat + timedelta(days=8))
    cluster = bulletin.detect_cluster(sat, events)
    if cluster and cluster["eve"] < eve:
        return cluster["eve"], cluster["name"]
    return eve, (cluster["name"] if cluster else "")


def plan(sat: date) -> dict:
    eve, name = first_eve(sat)
    return {
        "id": sat.isoformat(),
        "cluster": name,
        "proof_day": (eve - timedelta(days=1)).isoformat(),
        "send_day": eve.isoformat(),
        "send_moment": datetime.combine(eve, time(SEND_HOUR, 0), NY).isoformat(),
    }


def send_moment(sat: date) -> datetime:
    eve, _ = first_eve(sat)
    return datetime.combine(eve, time(SEND_HOUR, 0), NY)


def proof_day(sat: date) -> date:
    eve, _ = first_eve(sat)
    return eve - timedelta(days=1)


def proof_today(today: date | None = None) -> str:
    """The id to proof today, or ''. The scheduled proof runs every day
    and asks this question; only the proof day answers yes."""
    t = today or today_ny()
    sat = next_bulletin(t)
    return sat.isoformat() if proof_day(sat) == t else ""


if __name__ == "__main__":
    if "--proof-today" in sys.argv:
        print(proof_today())
    else:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        sat = date.fromisoformat(args[0]) if args else next_bulletin()
        print(json.dumps(plan(sat), indent=1))

"""When a bulletin is proofed and when it goes out (Marc's rule of
15 November 2026), for every bulletin the calendar scope produces
(program/occasions.py): the Shabbat bulletins and the standalone festival
and fast bulletins.

A bulletin is proofed the day before its first eve and goes out on that
eve: a plain Shabbat is proofed on Thursday and mailed on Friday. A
Shabbat bulletin that also carries a festival whose eve falls earlier in
the week moves both days earlier by the same rule — Pesah beginning on a
Thursday is proofed on Tuesday and mailed on Wednesday. A festival or fast
too far from any Shabbat to ride in its bulletin gets one of its own, keyed
by its first day, proofed the day before its eve and mailed on the eve:
Lag LaOmer on Tuesday 25 May 2027 is proofed Sunday the 23rd and mailed
Monday the 24th. The same two days hold for the reminder (evening of the
proof day) and the send moment (6:00 am New York on the mailing day; a
GitHub cron queued late still lands the same morning, and an approval that
arrives after that moment publishes and sends at once).

Usage:
  python3 program/schedule.py --proof-today     the bulletin id to proof
                                                now, or nothing
  python3 program/schedule.py --list            the next eight bulletins
  python3 program/schedule.py --write           bulletin/state/schedule.json
                                                (the Desk's "Coming up")
  python3 program/schedule.py 2027-05-25        describes one bulletin
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import occasions

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = ROOT / "bulletin" / "state" / "schedule.json"
NY = ZoneInfo("America/New_York")
SEND_HOUR = 6
HORIZON = 120          # days ahead the schedule looks
LISTED = 8             # bulletins the Desk is shown


def today_ny() -> date:
    return datetime.now(NY).date()


def _plan_from(b: dict) -> dict:
    """The schedule facts of one occasions.bulletins() entry. Names come
    from bulletin.py's names map; no network beyond the events already
    fetched."""
    import bulletin

    cluster = bulletin.cluster_from(b) if b["occasions"] else None
    eve = b["eve"]
    anchor = b["id"]
    if b["shabbat"] is None:
        title = cluster["label"]
    elif cluster:
        title = f"Shabbat {anchor.day} {bulletin.MONTHS[anchor.month]} and {cluster['label']}"
    else:
        title = f"Shabbat {anchor.day} {bulletin.MONTHS[anchor.month]}"
    return {
        "id": anchor.isoformat(),
        "shabbat": b["shabbat"] is not None,
        "cluster": cluster["label"] if cluster else "",
        "title": title,
        "proof_day": (eve - timedelta(days=1)).isoformat(),
        "send_day": eve.isoformat(),
        "send_moment": datetime.combine(eve, time(SEND_HOUR, 0), NY).isoformat(),
    }


def plan(anchor: date) -> dict:
    b = occasions.bulletin_for(anchor)
    if b is None:
        raise ValueError(f"{anchor} is neither a Saturday nor the first day of "
                         "an occasion with a bulletin of its own")
    return _plan_from(b)


def upcoming(today: date | None = None, n: int = LISTED) -> list[dict]:
    """The next bulletins whose mailing day has not passed, in order."""
    t = today or today_ny()
    out = [_plan_from(b) for b in occasions.bulletins(t - timedelta(days=7), t + timedelta(days=HORIZON))]
    return [p for p in out if p["send_day"] >= t.isoformat()][:n]


def next_bulletin(today: date | None = None) -> date:
    """The bulletin next in line: the first whose mailing day is today or
    later (on a Saturday that is the following week's)."""
    return date.fromisoformat(upcoming(today, 1)[0]["id"])


def proof_today(today: date | None = None) -> str:
    """The id to proof today, or ''. The scheduled proof runs every day
    and asks this question; only a proof day answers yes."""
    t = today or today_ny()
    for p in upcoming(t, 3):
        if p["proof_day"] == t.isoformat():
            return p["id"]
    return ""


def sending_on(day: date | None = None) -> dict | None:
    """The bulletin whose mailing day is this day, or None. The family
    letters go out on the same mornings (family.py --auto)."""
    d = day or today_ny()
    for p in upcoming(d, 3):
        if p["send_day"] == d.isoformat():
            return p
    return None


def send_moment(anchor: date) -> datetime:
    return datetime.fromisoformat(plan(anchor)["send_moment"])


def proof_day(anchor: date) -> date:
    return date.fromisoformat(plan(anchor)["proof_day"])


def write_schedule(today: date | None = None) -> Path:
    """bulletin/state/schedule.json: what the Desk shows under Coming up.
    Written by every proof run, so it is never more than a week old."""
    t = today or today_ny()
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(
        {"written": t.isoformat(), "bulletins": upcoming(t)}, indent=1) + "\n")
    return SCHEDULE_FILE


if __name__ == "__main__":
    if "--proof-today" in sys.argv:
        print(proof_today())
    elif "--list" in sys.argv:
        for p in upcoming():
            print(f"{p['id']}  {p['title']:<44}  proof {p['proof_day']}  out {p['send_day']}")
    elif "--write" in sys.argv:
        print(write_schedule())
    else:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        anchor = date.fromisoformat(args[0]) if args else next_bulletin()
        print(json.dumps(plan(anchor), indent=1))

"""Verify (or refit) the end-of-Shabbat rule against Shearith Israel's
published times.

The dataset (program/data/shearith-times.csv) holds Congregation Shearith
Israel's own published candle-lighting and Habdala figures, collected from
shearithisrael.org, their weekly handout PDFs, and Wayback Machine snapshots
of their pages, October 2020 - September 2026. Only figures they themselves
published; nothing computed or inferred.

The fitted rule (recorded in bulletin/luach.md, implemented in zemanim.py):

    end of Shabbat = sunset + 33.75 seasonal minutes, rounded UP,

where one seasonal minute is 1/60 of 1/12 of that day's sunrise-to-sunset
span. A fixed solar depression, the brief's first guess, does not fit their
year: it fails in winter by 6-9 minutes. The seasonal rule reproduces their
published Habdala to the minute in about two thirds of 143 independent
weeks and to within one minute in about 92%, with the residue traceable to
their own generator's coarser sunsets (their published sunsets differ from
high-precision astronomy by a minute in roughly a third of the sampled
weeks). The rounding is chosen upward so the bulletin practically never
ends Shabbat earlier than their convention.

Usage:
  python3 program/calibrate_habdala.py program/data/shearith-times.csv
  python3 program/calibrate_habdala.py --grid ...   (rerun the model search)
"""

from __future__ import annotations

import csv
import math
import sys
from collections import Counter
from datetime import date, datetime, timedelta

from zemanim import HABDALA_SEASONAL_MINUTES, habdala, round_up, round_nearest, sunrise, sunset

# Their times are for New York; Central Park West fits their published
# sunsets best of the coordinate candidates tried.
SI_LAT, SI_LON = 40.7690, -73.9813

# Published 7:59 pm on a smooth 20:02 -> 20:10 neighborhood; a typo or
# extraction slip, excluded from scoring.
KNOWN_OUTLIERS = {date(2025, 4, 12)}


def parse_clock(s: str, d: date) -> datetime | None:
    s = s.strip().lower().replace(".", "")
    if not s:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            return datetime.combine(d, datetime.strptime(s, fmt).time())
        except ValueError:
            continue
    return None


ROUNDINGS = {
    "nearest": round_nearest,
    "ceil": round_up,
    "floor": lambda dt: dt.replace(second=0, microsecond=0),
}


def load(path: str):
    """One habdala point per Shabbat, deduplicated, outliers dropped."""
    pts = []
    seen = set()
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                sd = date.fromisoformat(r["shabbat_date"].strip())
            except ValueError:
                continue
            hab = parse_clock(r.get("habdala", ""), sd)
            if not hab or sd in seen or sd in KNOWN_OUTLIERS:
                continue
            seen.add(sd)
            pts.append((sd, hab))
    return pts


def evaluate(pts) -> None:
    c = Counter()
    for sd, hab in pts:
        calc = habdala(sd, SI_LAT, SI_LON).replace(tzinfo=None)
        c[round((calc - hab).total_seconds() / 60.0)] += 1
    n = len(pts)
    exact = c.get(0, 0)
    within1 = exact + c.get(1, 0) + c.get(-1, 0)
    earlier = sum(v for k, v in c.items() if k < 0)
    print(f"rule: sunset + {HABDALA_SEASONAL_MINUTES} seasonal minutes, rounded up")
    print(f"n={n}  exact {exact} ({exact*100//n}%)  within 1 min {within1} ({within1*100//n}%)  earlier-than-published {earlier}")
    print("residuals (calc - published, minutes):", dict(sorted(c.items())))


def grid(pts) -> None:
    best = []
    for k20 in range(640, 720):
        k = k20 / 20.0
        for rname, rfun in ROUNDINGS.items():
            ex = 0
            for sd, hab in pts:
                ss = sunset(sd, SI_LAT, SI_LON)
                dl = (ss - sunrise(sd, SI_LAT, SI_LON)).total_seconds() / 60.0
                calc = rfun(ss + timedelta(minutes=k * dl / 720.0)).replace(tzinfo=None)
                if calc == hab:
                    ex += 1
            best.append((ex, k, rname))
    best.sort(key=lambda x: -x[0])
    n = len(pts)
    for ex, k, rname in best[:10]:
        print(f"{ex*100/n:5.1f}%  seasonal minutes {k:.2f}  rounded {rname}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--grid"]
    pts = load(args[0])
    evaluate(pts)
    if "--grid" in sys.argv:
        print()
        grid(pts)

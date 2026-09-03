"""Fit the end-of-Shabbat rule to Shearith Israel's published times.

Reads a CSV of their published figures (shabbat_date,candle_lighting,
habdala,source_url,notes), fits a solar-depression rule for New York that
reproduces the published Habdala times to the minute, and reports the best
(coordinates, depression, rounding) combination. Also checks their candle
times against sunset-18 to infer the sunset rounding convention.

Usage: python3 program/calibrate_habdala.py path/to/shearith-times.csv
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timedelta

from zemanim import depression, sunset, round_nearest

CANDIDATE_COORDS = {
    "CPW (40.7690, -73.9813)": (40.7690, -73.9813),
    "City Hall (40.7128, -74.0060)": (40.7128, -74.0060),
    "Midtown (40.7500, -73.9900)": (40.7500, -73.9900),
}

ROUNDINGS = {
    "nearest": lambda dt: (dt + timedelta(seconds=30)).replace(second=0, microsecond=0),
    "ceil": lambda dt: (dt + timedelta(seconds=59, microseconds=999999)).replace(second=0, microsecond=0),
    "floor": lambda dt: dt.replace(second=0, microsecond=0),
}


def parse_clock(s: str, d: date) -> datetime | None:
    s = s.strip().lower().replace(".", "")
    if not s:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(s, fmt).time()
            return datetime.combine(d, t)
        except ValueError:
            continue
    return None


def load(path: str):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                sd = date.fromisoformat(r["shabbat_date"].strip())
            except ValueError:
                continue
            rows.append(
                {
                    "shabbat": sd,
                    "candles": parse_clock(r.get("candle_lighting", ""), sd - timedelta(days=1)),
                    "habdala": parse_clock(r.get("habdala", ""), sd),
                    "source": r.get("source_url", ""),
                }
            )
    return rows


def naive_local(dt):
    return dt.replace(tzinfo=None)


def fit(rows):
    print(f"{len(rows)} rows loaded; "
          f"{sum(1 for r in rows if r['habdala'])} with habdala, "
          f"{sum(1 for r in rows if r['candles'])} with candles\n")

    print("=== Habdala: depression fit ===")
    results = []
    for cname, (lat, lon) in CANDIDATE_COORDS.items():
        for tenth in range(60, 91):  # 6.0 .. 9.0 degrees
            deg = tenth / 10.0
            for rname, rfun in ROUNDINGS.items():
                exact = 0
                off = []
                n = 0
                for r in rows:
                    if not r["habdala"]:
                        continue
                    n += 1
                    calc = naive_local(rfun(depression(r["shabbat"], deg, lat, lon)))
                    dmin = (r["habdala"] - calc).total_seconds() / 60.0
                    if dmin == 0:
                        exact += 1
                    else:
                        off.append((r["shabbat"], dmin))
                if n:
                    results.append((exact / n, deg, rname, cname, n, off))
    results.sort(key=lambda x: -x[0])
    for frac, deg, rname, cname, n, off in results[:8]:
        print(f"  {frac*100:5.1f}% exact  depression {deg:.1f}  round {rname:7s}  {cname}  (n={n})")
        if off and frac > 0.8:
            worst = sorted(off, key=lambda o: -abs(o[1]))[:4]
            print("           misses:", ", ".join(f"{d} {m:+.0f}m" for d, m in worst))

    best = results[0]
    print("\n=== Candles: sunset-18 check (using best coords) ===")
    cname = best[3]
    lat, lon = CANDIDATE_COORDS[cname]
    for rname, rfun in ROUNDINGS.items():
        exact = 0
        n = 0
        misses = []
        for r in rows:
            if not r["candles"]:
                continue
            n += 1
            fri = r["shabbat"] - timedelta(days=1)
            ss = sunset(fri, lat, lon)
            calc = naive_local(rfun(ss) - timedelta(minutes=18))
            dmin = (r["candles"] - calc).total_seconds() / 60.0
            if dmin == 0:
                exact += 1
            else:
                misses.append((fri, dmin))
        if n:
            tag = ""
            if misses and exact / n > 0.8:
                worst = sorted(misses, key=lambda o: -abs(o[1]))[:4]
                tag = "  misses: " + ", ".join(f"{d} {m:+.0f}m" for d, m in worst)
            print(f"  sunset rounded {rname:7s} minus 18: {exact/n*100:5.1f}% exact (n={n}){tag}")
    return best


if __name__ == "__main__":
    rows = load(sys.argv[1])
    fit(rows)

"""Print a plain-text year of Shabbat times for Poughkeepsie, for Marc's
review (build order step 2).

The habdala rule (depression and rounding) comes from the Shearith Israel
calibration; until bulletin/luach.md records the fitted rule, the values
below carry the provisional fit and are clearly labeled.

Usage: python3 program/shabbat_year.py [start YYYY-MM-DD] [weeks]
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from hebcal_client import fetch_events, parashah_by_shabbat
from zemanim import depression, format_time, round_nearest, sunset

# ---- the rule under calibration ----------------------------------------
HABDALA_DEPRESSION = 7.5   # degrees below horizon; PROVISIONAL until fitted
HABDALA_ROUND = "nearest"  # nearest | ceil | floor; PROVISIONAL until fitted
# ------------------------------------------------------------------------

from datetime import datetime, timedelta as _td


def _round(dt: datetime, how: str) -> datetime:
    if how == "ceil":
        return (dt + _td(seconds=59, microseconds=999999)).replace(second=0, microsecond=0)
    if how == "floor":
        return dt.replace(second=0, microsecond=0)
    return round_nearest(dt)


def main() -> None:
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 9, 5)
    weeks = int(sys.argv[2]) if len(sys.argv) > 2 else 53
    # First Saturday on/after start.
    sat = start + timedelta(days=(5 - start.weekday()) % 7)

    items = fetch_events(sat - timedelta(days=7), sat + timedelta(weeks=weeks))
    parashiyot = parashah_by_shabbat(items)

    print("Shabbat times for Poughkeepsie, NY (41.70° N, 73.92° W)")
    print(f"Candle lighting 18 minutes before sunset; end of Shabbat at solar")
    print(f"depression {HABDALA_DEPRESSION}° (rounded {HABDALA_ROUND}) — provisional until calibrated.")
    print()
    print(f"{'Shabbat':<12} {'Parashah':<28} {'Candles':>8} {'Sunset':>8} {'Ends':>8}")
    for w in range(weeks):
        s = sat + timedelta(weeks=w)
        fri = s - timedelta(days=1)
        ss = sunset(fri)
        candles = round_nearest(ss) - timedelta(minutes=18)
        ends = _round(depression(s, HABDALA_DEPRESSION), HABDALA_ROUND)
        name = parashiyot.get(s, "—")
        print(
            f"{s.isoformat():<12} {name:<28} {format_time(candles):>8} "
            f"{format_time(round_nearest(ss)):>8} {format_time(ends):>8}"
        )


if __name__ == "__main__":
    main()

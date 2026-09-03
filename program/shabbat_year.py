"""Print a plain-text year of Shabbat times for Poughkeepsie, for Marc's
review (build order step 2).

Rules per bulletin/luach.md: candles 18 minutes before the printed sunset;
end of Shabbat at sunset plus 33.75 seasonal minutes, rounded up (the
Shearith Israel calibration).

Usage: python3 program/shabbat_year.py [start YYYY-MM-DD] [weeks]
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from hebcal_client import fetch_events, holidays, parashah_by_shabbat
from zemanim import candle_lighting, format_time, habdala


def main() -> None:
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 9, 5)
    weeks = int(sys.argv[2]) if len(sys.argv) > 2 else 53
    sat = start + timedelta(days=(5 - start.weekday()) % 7)

    items = fetch_events(sat - timedelta(days=7), sat + timedelta(weeks=weeks))
    parashiyot = parashah_by_shabbat(items)
    hols = holidays(items)

    def saturday_name(s: date) -> str:
        if s in parashiyot:
            return parashiyot[s]
        names = [h["title"] for h in hols if h["date"] == s]
        return "; ".join(names) if names else "—"

    for w in range(weeks):
        s = sat + timedelta(weeks=w)
        candles, printed_sunset = candle_lighting(s - timedelta(days=1))
        ends = habdala(s)
        print(
            f"{s.strftime('%d %b %Y')}  {saturday_name(s)} — "
            f"candles {format_time(candles)} (sunset {format_time(printed_sunset)}), "
            f"ends {format_time(ends)}"
        )


if __name__ == "__main__":
    main()

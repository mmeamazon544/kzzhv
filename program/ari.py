"""Ari's Friday-morning email (Marc's commission, 3 September 2026).

Every Friday at 6:00 am New York time, exclusively to Ari (the "ari" tag
segment), sponsored by Kehillah Kedoshah Zikhron Zvi: the coming Shabbat
and festival times computed for Tufts University, Medford, MA; the
parashah and haftarah with their summaries; the week ahead; and the
Reflections — the last three reused from the week's approved bulletin
when it covers the same Shabbat, so father and son read the same Torah.

Usage: python3 program/ari.py [--proof] [YYYY-MM-DD]
  --proof sends to Marc's Proof segment instead of Ari (for review).
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

import bulletin
from mailchimp_send import send

ROOT = Path(__file__).resolve().parent.parent

TUFTS_LAT, TUFTS_LON = 42.4075, -71.1190
TUFTS_HEADING = "Times for Tufts University, Medford, MA (42.41° N, 71.12° W)"


def next_saturday() -> date:
    t = datetime.now(ZoneInfo("America/New_York")).date()
    return t + timedelta(days=(5 - t.weekday()) % 7)


def main() -> None:
    proof = "--proof" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sat = date.fromisoformat(args[0]) if args else next_saturday()

    ctx = bulletin.build_context(sat)

    # Recompute every clock time for the Medford sky.
    ctx["times"] = bulletin.build_times(sat, ctx["fri"], ctx["cluster"],
                                        TUFTS_LAT, TUFTS_LON)
    events = bulletin.fetch_events(sat - timedelta(days=3), sat + timedelta(days=8))
    ctx["observances"] = bulletin.observance_lines(sat, events, TUFTS_LAT, TUFTS_LON)
    ctx["times_heading"] = TUFTS_HEADING
    ctx["eyebrow"] = "Sponsored by Kehillah Kedoshah Zikhron Zvi"

    # Not for this email: congregational logistics.
    ctx["service_times"] = []
    ctx["kiddush"] = []
    ctx["announcements"] = []
    ctx["guest_text"] = None
    ctx["skip_empty_reflections"] = True

    # Reuse the approved bulletin's teachings and summaries when they
    # cover this same Shabbat.
    cur_file = ROOT / "bulletin" / "state" / "current.json"
    if cur_file.exists():
        cur = json.loads(cur_file.read_text())
        tfile = ROOT / "bulletin" / "state" / cur["id"] / "teachings.json"
        if cur["id"] == sat.isoformat() and tfile.exists():
            t = json.loads(tfile.read_text())
            ctx["halakha"] = t["halakha_html"]
            ctx["aggada"] = t["aggada_html"]
            ctx["torah_summary"] = t.get("parashah_summary")
            ctx["haftarah_summary"] = t.get("haftarah_summary")

    html_p, txt_p = bulletin.render_email(ctx)
    subject = f"{ctx['title']} · times for Medford, MA"
    cid = send(subject, html_p.read_text(), txt_p.read_text(),
               proof=proof, segment_key="ari_segment_id")
    print(f"Ari email sent: campaign {cid} "
          + ("(to Marc as a proof)" if proof else "(to Ari)"))


if __name__ == "__main__":
    main()

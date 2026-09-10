"""Localized bulletin sends (Marc's commission, 7 September 2026).

Sends the current PUBLISHED bulletin — full content, greetings and banner
included — to family members far from Poughkeepsie, with two changes:
the KKZZ service times are dropped, and the halakhic times (and their
heading) are recomputed for the recipient's own sky. Everything else is
exactly the approved bulletin, teachings included (read from the
published state, never redrafted).

Each send goes to that member's own Mailchimp tag segment. Coordinates
and segments come from family.py's FAMILY table.

Usage: python3 program/localized_send.py (--proof | --live)
           --members ari,misha,gabi [YYYY-MM-DD]
       --render-only writes out/ files without sending (no API key).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import bulletin
from family import FAMILY, cc_marc, copy_subject, next_saturday

ROOT = Path(__file__).resolve().parent.parent

# The halakhic-times heading per member, in the bulletin's split style
# (larger before the em-dash, normal after).
HALAKHIC_HEADINGS = {
    "ari": "Halakhic (Ritual) Times — Tufts University, Medford, MA 42.41 N 71.12 W",
    "misha": "Halakhic (Ritual) Times — Philadelphia, PA 39.95 N 75.17 W",
    "gabi": "Halakhic (Ritual) Times — Philadelphia, PA 39.95 N 75.17 W",
    "mom": "Halakhic (Ritual) Times — New York City, NY 40.77 N 73.98 W",
}

PLACE_SHORT = {
    "ari": "Times for Tufts University",
    "misha": "Times for Philadelphia",
    "gabi": "Times for Philadelphia",
    "mom": "Times for New York City",
}


def build(member: str, sat: date) -> tuple[dict, str]:
    m = FAMILY[member]
    ctx = bulletin.build_context(sat)
    ctx["times"] = bulletin.build_times(sat, ctx["fri"], ctx["cluster"],
                                        m["lat"], m["lon"])
    ctx["times_heading"] = HALAKHIC_HEADINGS[member]
    ctx["service_times"] = []

    cur = json.loads((ROOT / "bulletin" / "state" / "current.json").read_text())
    if cur["id"] != sat.isoformat():
        sys.exit(f"current bulletin is {cur['id']}, not {sat}; refusing")
    if cur["status"] not in ("published", "sent"):
        sys.exit(f"bulletin {cur['id']} is {cur['status']}, not published; "
                 "localized sends carry only approved, published content")
    t = json.loads((ROOT / "bulletin" / "state" / cur["id"] / "teachings.json").read_text())
    bulletin.apply_teachings(ctx, t)

    subject = f"{cur['subject']} · {PLACE_SHORT[member]}"
    return ctx, subject


def main() -> None:
    live = "--live" in sys.argv
    render_only = "--render-only" in sys.argv
    if not (live or render_only or "--proof" in sys.argv):
        sys.exit("say --proof, --live, or --render-only")
    members = ["ari", "misha", "gabi"]
    if "--members" in sys.argv:
        members = [m.strip() for m in
                   sys.argv[sys.argv.index("--members") + 1].split(",") if m.strip()]
    for m in members:
        if m not in FAMILY:
            sys.exit(f"unknown member {m}")
    args = [a for a in sys.argv[1:] if not a.startswith("--")
            and a not in ",".join(members).split(",")
            and a != ",".join(members)]
    sat = date.fromisoformat(args[0]) if args else next_saturday()

    for member in members:
        ctx, subject = build(member, sat)
        html_p, txt_p = bulletin.render_email(ctx)
        if render_only:
            out_h = ROOT / "out" / f"localized-{member}.html"
            out_t = ROOT / "out" / f"localized-{member}.txt"
            out_h.write_text(html_p.read_text())
            out_t.write_text(txt_p.read_text())
            print(f"{member}: rendered {out_h.name} (subject: {subject})")
            continue
        from mailchimp_send import send
        html, text = html_p.read_text(), txt_p.read_text()
        if live:
            cid = send(subject, html, text, proof=False,
                       segment_key=FAMILY[member]["segment_key"])
            print(f"{member}: campaign {cid} (sent live)")
            if cc_marc():
                ccid = send(copy_subject(member, subject), html, text, proof=True)
                print(f"{member}: copy {ccid} to Marc")
        else:
            cid = send(copy_subject(member, subject), html, text, proof=True)
            print(f"{member}: campaign {cid} (to Marc as a copy of {member}'s letter)")


if __name__ == "__main__":
    main()

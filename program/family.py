"""The family Friday-morning emails (Marc's commissions, 3-4 September
2026): Ari at Tufts, Misha and Hannah and Gabi and Pascale in
Philadelphia, Mom in New York. Modeled on one another: Shabbat and
festival times for the recipient's own sky, the summaries, the week
ahead, and the week's Reflections, under a centered masthead with Ahad
Haʿam's words. Each goes exclusively to its own Mailchimp tag segment.

Scheduled runs send only the members named in FAMILY_ARMED
(comma-separated, from the repository variable).

Usage: python3 program/family.py (--proof | --live) --member ari|misha|gabi|mom|armed [YYYY-MM-DD]
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import bulletin
from mailchimp_send import send

ROOT = Path(__file__).resolve().parent.parent

QUOTE_HTML = """    <div dir="rtl" style="font-family:Georgia,'Times New Roman',serif; font-size:15px; line-height:1.8; color:#f1dccc; padding-top:18px; text-align:center;">אֶפְשָׁר לֵאמֹר בְּלִי שׁוּם הַפְרָזָה, כִּי יוֹתֵר מִשֶּׁיִּשְׂרָאֵל שָׁמְרוּ אֶת הַשַּׁבָּת, שָׁמְרָה הַשַּׁבָּת אוֹתָם.</div>
    <div style="font-family:Georgia,'Times New Roman',serif; font-style:italic; font-size:13px; line-height:1.6; color:#d6b1a6; padding-top:8px; text-align:center;">“You could say without any exaggeration that more than the Jews have kept Shabbat, Shabbat has kept them (Jewish).”</div>
    <div style="font-family:Georgia,'Times New Roman',serif; font-size:11px; line-height:1.6; color:#9a7273; padding-top:5px; text-align:center;">Ahad Haʿam, “Shabbat ve-Tsiyonut” (שבת וציוניות, “Sabbath and Zionism”), published in <em>Ha-Shiloaḥ</em>, vol. 3, no. 6 (Sivan 5658 / June 1898)</div>
"""

FAMILY = {
    "ari": {
        "segment_key": "ari_segment_id",
        "lat": 42.4075, "lon": -71.1190,
        "heading": "Times for Tufts University, Medford, MA (42.41° N, 71.12° W)",
        "subject": "Ári ❤️! Shabbat Times For Tufts University: {label}",
        "sponsor": ("SPONSORED BY YOUR HOME CONGREGATION",
                    "KEHILLAH KEDOSHAH ZIKHRON ZVI"),
        "love": "❤️ WITH LOVE FROM אבא and ANYU- GOOD SHABBOS! ❤️",
    },
    "misha": {
        "segment_key": "misha_segment_id",
        "lat": 39.9526, "lon": -75.1652,
        "heading": "Times for Philadelphia, PA (39.95° N, 75.17° W)",
        "subject": "Misha and Hannah ❤️! Shabbat Times For Philly: {label}",
        "sponsor": ("SPONSORED BY",
                    "CONGREGATION KEHILLAH KEDOSHAH ZIKHRON ZVI"),
        "love": "❤️ WITH LOVE FROM אבא and ÁGI- GOOD SHABBOS! ❤️",
    },
    "gabi": {
        "segment_key": "gabi_segment_id",
        "lat": 39.9526, "lon": -75.1652,
        "heading": "Times for Philadelphia, PA (39.95° N, 75.17° W)",
        "subject": "Gabi and Pascale ❤️! Shabbat Times For Philly: {label}",
        "sponsor": ("SPONSORED BY",
                    "CONGREGATION KEHILLAH KEDOSHAH ZIKHRON ZVI"),
        "love": "❤️ WITH LOVE FROM אבא and ÁGI- GOOD SHABBOS! ❤️",
    },
    "mom": {
        "segment_key": "mom_segment_id",
        "lat": 40.7690, "lon": -73.9813,
        "heading": "Times for New York City, NY (40.77° N, 73.98° W)",
        "subject": "Mom ❤️! Shabbat Times For NYC: {label}",
        "sponsor": ("SPONSORED BY",
                    "CONGREGATION KEHILLAH KEDOSHAH ZIKHRON ZVI"),
        "love": "❤️ WITH LOVE FROM MARC and ÁGI- GOOD SHABBOS! ❤️",
    },
}


def next_saturday() -> date:
    t = datetime.now(ZoneInfo("America/New_York")).date()
    return t + timedelta(days=(5 - t.weekday()) % 7)


def decide_auto() -> date | None:
    """The anchor Saturday for a scheduled run, or None when today is not a
    send day. Send days: every Friday, and the eve of any festival's first
    day. Never on Shabbat or on a yom tob itself."""
    from hebcal_client import holidays as hol_items

    ny = datetime.now(ZoneInfo("America/New_York")).date()
    if ny.weekday() == 5:
        print("today is Shabbat; no send")
        return None
    if ny.weekday() == 4:
        return ny + timedelta(days=1)
    tom = ny + timedelta(days=1)
    events = bulletin.fetch_events(ny - timedelta(days=1), tom + timedelta(days=1))
    yt = {h["date"] for h in hol_items(events) if h["yomtov"]}
    if ny in yt:
        print("today is yom tob; no send")
        return None
    if tom not in yt:
        print("not Friday and not a festival eve; no send")
        return None
    prev_sat = ny - timedelta(days=(ny.weekday() - 5) % 7)
    next_sat = ny + timedelta(days=(5 - ny.weekday()) % 7)
    for sat in (next_sat, prev_sat):
        c = bulletin.detect_cluster(
            sat, bulletin.fetch_events(sat - timedelta(days=3), sat + timedelta(days=8)))
        if c and tom in c["days"]:
            return sat
    print("festival eve, but no covering cluster yet; skipping "
          "(cluster logic covers festivals within two days of a Shabbat)")
    return None


def build_and_send(member: str, sat: date, proof: bool) -> None:
    m = FAMILY[member]
    cfg = json.loads((ROOT / "program" / "data" / "mailchimp.json").read_text())
    if m["segment_key"] not in cfg:
        print(f"{member}: segment not configured yet ({m['segment_key']} "
              "missing from mailchimp.json); skipping")
        return

    ctx = bulletin.build_context(sat)
    ctx["times"] = bulletin.build_times(sat, ctx["fri"], ctx["cluster"],
                                        m["lat"], m["lon"])
    events = bulletin.fetch_events(sat - timedelta(days=3), sat + timedelta(days=8))
    ctx["observances"] = bulletin.observance_lines(sat, events, m["lat"], m["lon"])
    ctx["times_heading"] = m["heading"]
    ctx["eyebrow_line_html"] = (
        '    <div class="display" style="font-family:Georgia,\'Times New Roman\',serif; '
        "font-size:13px; letter-spacing:3px; color:#c79f50; text-transform:uppercase; "
        'text-align:center; line-height:1.7;">'
        f"{m['sponsor'][0]}<br>{m['sponsor'][1]}</div>")
    ctx["eyebrow_extra_html"] = (
        '    <div style="font-family:Georgia,\'Times New Roman\',serif; font-size:16px; '
        'letter-spacing:2px; color:#e376a3; padding-top:12px; text-align:center;">'
        f"{m['love']}</div>\n" + QUOTE_HTML)
    ctx["service_times"] = []
    ctx["kiddush"] = []
    ctx["announcements"] = []
    ctx["guest_text"] = None
    ctx["skip_empty_reflections"] = True
    ctx["skip_membership"] = True
    ctx["center_masthead"] = True

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
    label = f"Parashat {ctx['parashah']}" if ctx["parashah"] else ctx["title"]
    subject = m["subject"].format(label=label)
    cid = send(subject, html_p.read_text(), txt_p.read_text(),
               proof=proof, segment_key=m["segment_key"])
    print(f"{member}: campaign {cid} "
          + ("(to Marc as a proof)" if proof else "(sent)"))


if __name__ == "__main__":
    proof = "--proof" in sys.argv
    if not proof and "--live" not in sys.argv:
        sys.exit("say --proof or --live")
    if "--auto" in sys.argv:
        anchor = decide_auto()
        if anchor is None:
            sys.exit(0)
        member = "armed"
        sat = anchor
    else:
        member = sys.argv[sys.argv.index("--member") + 1]
        args = [a for a in sys.argv[1:]
                if not a.startswith("--") and a not in FAMILY and a != "armed"]
        sat = date.fromisoformat(args[0]) if args else next_saturday()

    if member == "armed":
        armed = [k.strip() for k in os.environ.get("FAMILY_ARMED", "").split(",")
                 if k.strip() in FAMILY]
        if not armed:
            print("no family members armed; nothing to send")
        for k in armed:
            build_and_send(k, sat, proof)
    else:
        if member not in FAMILY:
            sys.exit(f"unknown member {member}")
        build_and_send(member, sat, proof)

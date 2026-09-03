"""Bulletin generator — build order step 3: everything except the teachings.

Gathers the week's data (calendar and readings from Hebcal, times from the
congregation's own luach in zemanim.py, location and announcements from
bulletin/), renders the web page from bulletin/templates/web.html, and
writes site/bulletin/index.html.

Usage: python3 program/bulletin.py [YYYY-MM-DD]   (a Saturday; default: next)
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from hebcal_client import fetch_events, holidays
from zemanim import candle_lighting, format_time, habdala

ROOT = Path(__file__).resolve().parent.parent
SECRETARY = "kehillatzikhronzvi@gmail.com"

ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh"]

# ---------------------------------------------------------------- names.md --

def load_names() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in (ROOT / "bulletin" / "names.md").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("<!--"):
            k, _, v = line.partition("=")
            if k.strip() and v.strip():
                mapping[k.strip()] = v.strip()
    return mapping


NAMES = load_names()


def display_name(hebcal_name: str) -> str:
    """Map a Hebcal name to the congregation's spelling; combined
    parashiyot are mapped part by part."""
    if hebcal_name in NAMES:
        return NAMES[hebcal_name]
    if "-" in hebcal_name:
        parts = [NAMES.get(p.strip(), p.strip()) for p in hebcal_name.split("-")]
        return "–".join(parts)
    return hebcal_name


def display_title(hebcal_name: str) -> str:
    """As display_name, but with the en dash wrapped for the display face,
    which lacks the glyph (site convention: span.mid)."""
    name = display_name(hebcal_name)
    return name.replace("–", '<span class="mid">–</span>')


# ------------------------------------------------------------------ hebcal --

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "kzzhv-bulletin/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def hebrew_date(d: date) -> tuple[int, str, int]:
    j = fetch_json(
        "https://www.hebcal.com/converter?cfg=json&g2h=1&"
        + urllib.parse.urlencode({"gy": d.year, "gm": d.month, "gd": d.day})
    )
    return j["hd"], NAMES.get(j["hm"], j["hm"]), j["hy"]


def leyning(d: date) -> dict | None:
    j = fetch_json(
        f"https://www.hebcal.com/leyning?cfg=json&start={d.isoformat()}&end={d.isoformat()}"
    )
    items = j.get("items", [])
    return items[0] if items else None


# ------------------------------------------------------------------- dates --

MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def span_gregorian(fri: date, sat: date) -> str:
    if fri.month == sat.month:
        return f"{fri.day}–{sat.day} {MONTHS[sat.month]} {sat.year}"
    if fri.year == sat.year:
        return f"{fri.day} {MONTHS[fri.month]}–{sat.day} {MONTHS[sat.month]} {sat.year}"
    return f"{fri.day} {MONTHS[fri.month]} {fri.year}–{sat.day} {MONTHS[sat.month]} {sat.year}"


def span_hebrew(fri: date, sat: date) -> str:
    fd, fm, fy = hebrew_date(fri)
    sd, sm, sy = hebrew_date(sat)
    if (fm, fy) == (sm, sy):
        return f"{fd}–{sd} {sm} {sy}"
    if fy == sy:
        return f"{fd} {fm}–{sd} {sm} {sy}"
    return f"{fd} {fm} {fy}–{sd} {sm} {sy}"


def long_day(d: date) -> str:
    return f"{d.strftime('%A')}, {d.day} {MONTHS[d.month]}"


# ---------------------------------------------------------------- readings --

def format_ref(book: str, b: str, e: str) -> str:
    """Deuteronomy 29:9-29:28 -> Deuteronomy 29:9–28; keeps the chapter when
    it changes."""
    bch, bv = b.split(":")
    ech, ev = e.split(":")
    if bch == ech:
        return f"{book} {bch}:{bv}–{ev}"
    return f"{book} {bch}:{bv}–{ech}:{ev}"


def compress_ref(prev_book: str | None, book: str, b: str, e: str) -> str:
    r = format_ref(book, b, e)
    if prev_book == book:
        return r[len(book) + 1:]
    return r


def readings_html(item: dict) -> str:
    out = []
    name = display_name(item["name"]["en"])
    summary = (item.get("summary") or "").replace("-", "–")
    verses = sum(a.get("v", 0) for k, a in (item.get("fullkriyah") or {}).items() if k != "M")
    vtxt = f" ({verses} verses)" if verses else ""
    out.append(f"<p><strong>{name}</strong>, {summary}{vtxt}.</p>")

    fk = item.get("fullkriyah") or {}
    if fk:
        parts = []
        prev = None
        for i in range(1, 8):
            a = fk.get(str(i))
            if not a:
                continue
            label = f"{ORDINALS[i-1]} aliya" if i == 1 else ORDINALS[i - 1]
            parts.append(f"{label}, {compress_ref(prev, a['k'], a['b'], a['e'])}")
            prev = a["k"]
        if "M" in fk:
            a = fk["M"]
            parts.append(f"maftir, {compress_ref(prev, a['k'], a['b'], a['e'])}")
        text = "; ".join(parts) + "."
        out.append("<p>" + text[0].upper() + text[1:] + "</p>")

    seph = item.get("sephardic")
    haft = item.get("haftara")
    if seph:
        out.append(
            f"<p><strong>Haftarah:</strong> {seph.replace('-', '–')}, the Sephardic reading "
            f"(Ashkenazim read {haft.replace('-', '–')}).</p>"
        )
    elif haft:
        out.append(f"<p><strong>Haftarah:</strong> {haft.replace('-', '–')}. Ashkenazim and Sephardim read the same passage.</p>")
    return "\n".join(out)


# -------------------------------------------------------------- observances --

YOMTOV_EVES = {"Erev Rosh Hashana", "Erev Yom Kippur", "Erev Sukkot",
               "Erev Shavuot", "Erev Pesach", "Erev Simchat Torah"}


def observances_html(sat: date, events: list[dict]) -> str:
    """Observances from motzaei Shabbat through the coming Friday, plus Rosh
    Hodesh announcement for the week after (announced the preceding
    Shabbat)."""
    out = []
    window = [e for e in holidays(events) if sat <= e["date"] <= sat + timedelta(days=7)]
    for e in sorted(window, key=lambda x: x["date"]):
        title = e["title"]
        base = re.sub(r" \d{4,5}$", "", title)  # strip year from "Rosh Hashana 5787"
        if e["date"] == sat and e["category"] != "roshchodesh" and base not in NAMES and not title.startswith("Leil"):
            continue  # the Shabbat itself is the page's subject
        shown = NAMES.get(base, None)
        if base.startswith("Rosh Chodesh"):
            month = base.removeprefix("Rosh Chodesh ").strip()
            shown = "Rosh Hodesh " + NAMES.get(month, month)
        if shown is None:
            shown = display_name(base)
        line = f"{long_day(e['date'])} — {shown}."
        if base in YOMTOV_EVES or (e["yomtov"] and e["date"] > sat):
            if base in YOMTOV_EVES:
                candles, printed = candle_lighting(e["date"])
                line += f" Candle lighting {format_time(candles)} (18 minutes before sunset; sunset {format_time(printed)})."
        out.append(f"<p>{line}</p>")
    if not out:
        return ""
    return "<h2>In the Week Ahead</h2>\n" + "\n".join(out)


# ---------------------------------------------------------------- sections --

def announcements_html() -> str:
    raw = (ROOT / "bulletin" / "announcements.md").read_text()
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S).strip()
    if not raw:
        return ""
    paras = [f"<p>{p.strip()}</p>" for p in raw.split("\n\n") if p.strip()]
    return "<h2>Announcements</h2>\n" + "\n".join(paras)


def location_line() -> str:
    raw = (ROOT / "bulletin" / "location.md").read_text()
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S).strip()
    return raw or "Poughkeepsie"


GUESTS = {
    "Shearith Israel, New York":
        "Congregation Shearith Israel, the Spanish and Portuguese Synagogue, New York",
    "Sha'ar HaShamayim, London (Lauderdale Road)":
        "Congregation Sha'ar HaShamayim, London, at Lauderdale Road",
    "Sha'ar HaShamayim, London (Bevis Marks)":
        "Congregation Sha'ar HaShamayim, London, at Bevis Marks",
    "Mikveh Israel, Philadelphia":
        "Congregation Mikveh Israel, Philadelphia",
}


def guest_notice(loc: str) -> str:
    if loc == "Poughkeepsie":
        return ""
    if loc == "Poughkeepsie, no services this week":
        text = "There are no services this week."
    else:
        text = f"This Shabbat the congregation is guests of {GUESTS.get(loc, loc)}."
    return f'''
    <section class="schedule" aria-label="Where we are this week">
        <div class="upcoming-dates">
            <p class="upcoming-list" style="font-family: var(--font-serif); text-transform: none; letter-spacing: 0; font-style: italic;">{text}</p>
        </div>
    </section>
'''


def home_block(loc: str) -> str:
    if loc != "Poughkeepsie":
        return ""
    return f"""<h2>Kiddush</h2>
<p>Kiddush follows the service. Meals are dairy and vegetarian.</p>
<p>We meet in a private home; our address is shared by message. If prayer is not your thing, you are welcome to join only for the Kiddush and the company.</p>
<p>To RSVP and to register food issues and avoidances, kindly contact the Congregation's secretary at <a href="mailto:{SECRETARY}">{SECRETARY}</a></p>"""


def times_rows(fri: date, sat: date) -> str:
    candles, printed = candle_lighting(fri)
    ends = habdala(sat)
    return f"""            <div class="row">
                <dt>Candle lighting
                    <small>Erev Shabbat, {long_day(fri)} &middot; 18 minutes before sunset; sunset {format_time(printed)}</small>
                </dt>
                <dd>{format_time(candles)}</dd>
            </div>
            <div class="row row--final">
                <dt>Habdala
                    <small>{long_day(sat)} &middot; end of Shabbat</small>
                </dt>
                <dd>{format_time(ends)}</dd>
            </div>"""


PLACEHOLDER = ('<p><em style="color: var(--ink-mute);">The {kind} teaching for the week '
               "will appear here; the teachings pipeline is build-order step 4.</em></p>")


def teachings_html() -> str:
    return ("<h2>Halakha</h2>\n" + PLACEHOLDER.format(kind="halakhic")
            + "\n<h2>Aggada</h2>\n" + PLACEHOLDER.format(kind="aggadic"))


COLOPHON = (
    'Torah readings and calendar data by <a href="https://www.hebcal.com">Hebcal.com</a> '
    "(CC BY 4.0). Times are computed for Poughkeepsie by the congregation's luach; "
    "the end of Shabbat follows the convention of Congregation Shearith Israel, New York."
)


# -------------------------------------------------------------------- main --

def next_saturday(today: date) -> date:
    return today + timedelta(days=(5 - today.weekday()) % 7)


def special_shabbat(sat: date, events: list[dict]) -> str | None:
    for e in events:
        if e.get("category") == "holiday" and e.get("date", "")[:10] == sat.isoformat():
            t = e["title"]
            if t.startswith("Shabbat "):
                return NAMES.get(t, t)
    return None


def generate(sat: date) -> Path:
    fri = sat - timedelta(days=1)
    item = leyning(sat)
    events = fetch_events(sat - timedelta(days=1), sat + timedelta(days=8))
    loc = location_line()

    parashah = item["name"]["en"] if item else None
    title = f"Shabbat {display_title(parashah)}" if parashah else "Shabbat"
    lede_bits = [span_gregorian(fri, sat), span_hebrew(fri, sat)]
    special = special_shabbat(sat, events)
    if special:
        lede_bits.insert(0, special)
    lede = ' <span class="mid">·</span> '.join(lede_bits)

    body = []
    if item:
        body.append('<h2>Torah Reading <span class="amp">&amp;</span> Haftarah</h2>')
        body.append(readings_html(item))
    obs = observances_html(sat, events)
    if obs:
        body.append(obs)
    hb = home_block(loc)
    if hb:
        body.append(hb)
    ann = announcements_html()
    if ann:
        body.append(ann)
    body.append(teachings_html())

    tpl = (ROOT / "bulletin" / "templates" / "web.html").read_text()
    page_title = f"Shabbat {display_name(parashah)}" if parashah else "Weekly Bulletin"
    html = (
        tpl.replace("{{PAGE_TITLE}}", page_title)
        .replace("{{EYEBROW}}", "Weekly Bulletin")
        .replace("{{TITLE}}", title)
        .replace("{{LEDE}}", lede)
        .replace("{{GUEST_NOTICE}}", guest_notice(loc))
        .replace("{{TIMES_ROWS}}", times_rows(fri, sat))
        .replace("{{BODY_SECTIONS}}", "\n\n".join(body))
        .replace("{{COLOPHON}}", COLOPHON)
    )
    out = ROOT / "site" / "bulletin" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


if __name__ == "__main__":
    sat = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else next_saturday(date.today())
    if sat.weekday() != 5:
        sys.exit("date must be a Saturday")
    print(generate(sat))

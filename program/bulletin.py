"""Bulletin generator — build order step 3: everything except the teachings.

Gathers the week's data (calendar and readings from Hebcal, times from the
congregation's own luach in zemanim.py, location and announcements from
bulletin/), and renders three artifacts from one context:

  site/bulletin/index.html   the web page (bulletin/templates/web.html)
  out/email.html             the congregational email (templates/email.html)
  out/email.txt              its plain-text alternative

out/ is not committed; the publish workflow regenerates and places these.

Usage: python3 program/bulletin.py [YYYY-MM-DD] [--base URL]
       (a Saturday; default next Saturday. --base overrides the image/font
        host in the email, e.g. a local mirror when proofing.)
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
from zemanim import KKZZ_LAT, KKZZ_LON, candle_lighting, dawn, format_time, habdala

ROOT = Path(__file__).resolve().parent.parent
SECRETARY = "kehillatzikhronzvi@gmail.com"
SITE = "https://kzzhv.org"

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
    if hebcal_name in NAMES:
        return NAMES[hebcal_name]
    if "-" in hebcal_name:
        parts = [NAMES.get(p.strip(), p.strip()) for p in hebcal_name.split("-")]
        return "–".join(parts)
    return hebcal_name


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


def span_hebrew_parts(fh: tuple, sh: tuple) -> str:
    fd, fm, fy = fh
    sd, sm, sy = sh
    if (fm, fy) == (sm, sy):
        return f"{fd}–{sd} {sm} {sy}"
    if fy == sy:
        return f"{fd} {fm}–{sd} {sm} {sy}"
    return f"{fd} {fm} {fy}–{sd} {sm} {sy}"


def long_day(d: date) -> str:
    return f"{d.strftime('%A')}, {d.day} {MONTHS[d.month]}"


# ----------------------------------------------------------------- context --

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

YOMTOV_EVES = {"Erev Rosh Hashana", "Erev Yom Kippur", "Erev Sukkot",
               "Erev Shavuot", "Erev Pesach", "Erev Simchat Torah"}


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()


def service_times(cluster: dict | None = None) -> list[dict]:
    """Structured service schedule: items of kind heading / row / note.
    A festival cluster with its own file (bulletin/service-times/<slug>.md)
    overrides the standing Shabbat schedule in bulletin/service-times.md."""
    path = ROOT / "bulletin" / "service-times.md"
    if cluster:
        slug_name = re.sub(r"[^a-z0-9]+", "-", cluster["name"].lower()).strip("-")
        cand = ROOT / "bulletin" / "service-times" / f"{slug_name}.md"
        if cand.exists():
            path = cand
    out: list[dict] = []
    raw = strip_comments(path.read_text())
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            out.append({"kind": "heading", "text": line[2:].strip()})
        elif line.startswith("* "):
            out.append({"kind": "note", "text": line[2:].strip()})
        elif "=" in line:
            label, _, rest = line.partition("=")
            time_part, _, note = rest.partition("|")
            if label.strip() and time_part.strip():
                out.append({"kind": "row", "label": label.strip(),
                            "time": time_part.strip(), "note": note.strip()})
    return out


def observance_lines(sat: date, events: list[dict],
                     lat: float = KKZZ_LAT, lon: float = KKZZ_LON) -> list[str]:
    out = []
    for e in sorted(
        (e for e in holidays(events) if sat <= e["date"] <= sat + timedelta(days=7)),
        key=lambda x: x["date"],
    ):
        base = re.sub(r" \d{4,5}$", "", e["title"])
        if e["date"] == sat and e["category"] != "roshchodesh" and base not in NAMES and not e["title"].startswith("Leil"):
            continue
        shown = NAMES.get(base)
        if base.startswith("Rosh Chodesh"):
            month = base.removeprefix("Rosh Chodesh ").strip()
            shown = "Rosh Hodesh " + NAMES.get(month, month)
        if shown is None:
            shown = display_name(base)
        if base == "Leil Selichot":
            shown = ("Leil Selihot for Ashkenazim; Sephardim have been saying "
                     "Selihot since 2 Elul")
        line = f"{long_day(e['date'])} — {shown}."
        if base in YOMTOV_EVES:
            candles, printed = candle_lighting(e["date"], lat, lon)
            line += (f" Candle lighting {format_time(candles)} (18 minutes to sunset); "
                     f"sunset {format_time(printed)}.")
        out.append(line)
    return out


def special_shabbat(sat: date, events: list[dict]) -> str | None:
    for e in events:
        if e.get("category") == "holiday" and e.get("date", "")[:10] == sat.isoformat():
            t = e["title"]
            if t.startswith("Shabbat "):
                return NAMES.get(t, t)
    return None


def strip_year(title: str) -> str:
    return re.sub(r" \d{4,5}$", "", title)


def reading_from_item(item: dict) -> dict:
    seph = item.get("sephardic")
    haft = item.get("haftara")
    if seph:
        haft_line = (f"Haftarah: {seph.replace('-', '–')}, the Sephardic reading "
                     f"(Ashkenazim read {haft.replace('-', '–')}).")
    elif haft:
        haft_line = (f"Haftarah: {haft.replace('-', '–')}. "
                     "Ashkenazim and Sephardim read the same passage.")
    else:
        haft_line = None
    rng = (item.get("summary") or "").replace("-", "–")
    if "M" in (item.get("fullkriyah") or {}) and "; " in rng:
        head, _, maf = rng.rpartition("; ")
        rng = f"{head}; maftir {maf}"
    return {
        "name": display_name(item["name"]["en"]),
        "range": rng,
        "range_raw": (item.get("summary") or "").split(";")[0].strip(),
        "haftarah": haft_line,
        "haftarah_raw": seph or haft or "",
    }


def detect_cluster(sat: date, events: list[dict]) -> dict | None:
    """A festival cluster touching this Shabbat: consecutive yom tob days
    within two days of it, plus a fast within two days after them (the
    brief's clustering rule). None for a plain Shabbat."""
    hols = holidays(events)
    yt = sorted({h["date"] for h in hols if h["yomtov"] and abs((h["date"] - sat).days) <= 2})
    if not yt:
        return None
    chain = [yt[0]]
    for d in yt[1:]:
        if (d - chain[-1]).days <= 2:
            chain.append(d)
    fast = next(
        (h for h in hols
         if not h["yomtov"]
         and (h.get("subcat") == "fast" or strip_year(h["title"]).startswith(("Tzom", "Ta'anit", "Asara")))
         and 0 < (h["date"] - chain[-1]).days <= 2),
        None)
    first_title = next(h["title"] for h in hols if h["date"] == chain[0] and h["yomtov"])
    base = re.sub(r" I+$", "", strip_year(first_title))
    return {"name": NAMES.get(base, base), "eve": chain[0] - timedelta(days=1),
            "days": chain, "fast": fast}


def cluster_times(cluster: dict, lat: float = KKZZ_LAT, lon: float = KKZZ_LON) -> list:
    rows = []
    eve, days, name = cluster["eve"], cluster["days"], cluster["name"]
    ev_label = f"Erev {name}" + (" and Shabbat" if eve.weekday() == 4 else "")
    candles, printed = candle_lighting(eve, lat, lon)
    rows.append(("Candle lighting", f"{ev_label}, {long_day(eve)} · 18 minutes to sunset",
                 format_time(candles), False))
    rows.append(("Sunset", long_day(eve), format_time(printed), False))
    for prev, d in zip(days, days[1:]):
        rows.append(("Candle lighting, second day",
                     f"{long_day(prev)}, after the first day ends · from a flame lit before the festival",
                     format_time(habdala(prev, lat, lon)), False))
    fast = cluster["fast"]
    rows.append((f"{name} ends", f"{long_day(days[-1])} · Habdala",
                 format_time(habdala(days[-1], lat, lon)), fast is None))
    if fast:
        fname = NAMES.get(strip_year(fast["title"]), strip_year(fast["title"]))
        rows.append((f"{fname} begins", f"{long_day(fast['date'])} · dawn",
                     format_time(dawn(fast["date"], lat, lon)), False))
        rows.append((f"{fname} ends", f"{long_day(fast['date'])} · nightfall",
                     format_time(habdala(fast["date"], lat, lon)), True))
    return rows


def leyning_range(start: date, end: date) -> list[dict]:
    j = fetch_json(
        f"https://www.hebcal.com/leyning?cfg=json&start={start.isoformat()}&end={end.isoformat()}"
    )
    return j.get("items", [])


def cluster_readings(cluster: dict) -> list[dict]:
    out = []
    for it in leyning_range(cluster["days"][0], cluster["days"][-1]):
        d = date.fromisoformat(it["date"])
        if d in cluster["days"] and it.get("fullkriyah") and it.get("type") in ("holiday", "shabbat"):
            out.append(reading_from_item(it))
    return out


TIMES_HEADING_TEXT = "Shabbat times for Poughkeepsie, NY (41.70° N, 73.92° W)"
TIMES_HEADING_FESTIVAL_TEXT = "Times for Poughkeepsie, NY (41.70° N, 73.92° W)"


def build_times(sat: date, fri: date, cluster: dict | None,
                lat: float = KKZZ_LAT, lon: float = KKZZ_LON) -> list:
    """The times rows for any sky: plain Shabbat, pure festival, or the
    hybrid Shabbat-plus-festival cluster."""
    candles, printed = candle_lighting(fri, lat, lon)
    ends = habdala(sat, lat, lon)
    shabbat_times = [
        ("Candle lighting", f"Erev Shabbat, {long_day(fri)} · 18 minutes to sunset",
         format_time(candles), False),
        ("Sunset", f"Erev Shabbat, {long_day(fri)}", format_time(printed), False),
        ("Habdala", f"{long_day(sat)} · end of Shabbat", format_time(ends), True),
    ]
    if cluster and sat in cluster["days"]:
        return cluster_times(cluster, lat, lon)
    if cluster:
        shabbat_times[-1] = shabbat_times[-1][:3] + (False,)
        return shabbat_times + cluster_times(cluster, lat, lon)
    return shabbat_times


def build_context(sat: date) -> dict:
    fri = sat - timedelta(days=1)
    item = leyning(sat)
    events = fetch_events(sat - timedelta(days=3), sat + timedelta(days=8))
    loc = strip_comments((ROOT / "bulletin" / "location.md").read_text()) or "Poughkeepsie"

    parashah = display_name(item["name"]["en"]) if item else None
    sat_hebrew = hebrew_date(sat)
    lede_bits = [span_gregorian(fri, sat),
                 span_hebrew_parts(hebrew_date(fri), sat_hebrew)]
    special = special_shabbat(sat, events)
    if special:
        lede_bits.insert(0, special)

    guest_text = None
    if loc == "Poughkeepsie, no services this week":
        guest_text = "There are no services this week."
    elif loc != "Poughkeepsie":
        guest_text = f"This Shabbat the congregation is guests of {GUESTS.get(loc, loc)}."

    cluster = detect_cluster(sat, events)

    readings: list[dict] = []
    if cluster:
        readings = cluster_readings(cluster)
    elif item:
        readings = [reading_from_item(item)]

    announcements = [p.strip() for p in
                     strip_comments((ROOT / "bulletin" / "announcements.md").read_text()).split("\n\n")
                     if p.strip()]

    kiddush = []
    if loc == "Poughkeepsie":
        kiddush = [
            "Kiddush follows the service. Meals are dairy and vegetarian.",
            "We meet in a private home; our address is shared by message. If prayer "
            "is not your thing, you are welcome to join only for the Kiddush and the company.",
            "To RSVP and to register food issues and avoidances, kindly contact the "
            f"Congregation's secretary at {SECRETARY} by Thursday night at 10:00 pm",
        ]

    times = build_times(sat, fri, cluster)

    if cluster and sat in cluster["days"]:
        # The Shabbat is itself a festival day (Rosh Hashana on Shabbat).
        span_end = cluster["fast"]["date"] if cluster["fast"] else cluster["days"][-1]
        hy = hebrew_date(cluster["days"][0])[2]
        title = f"{cluster['name']} {hy}"
        lede = (span_gregorian(cluster["eve"], span_end) + " · "
                + span_hebrew_parts(hebrew_date(cluster["eve"]), hebrew_date(span_end)))
        times_heading = TIMES_HEADING_FESTIVAL_TEXT
        reflections_heading = f"Reflections on {cluster['name']}"
        parashah = None
    elif cluster:
        # A festival within two days of an ordinary Shabbat: one bulletin
        # covers both (the brief's clustering rule). Shabbat first, then
        # the festival's own times and readings.
        span_end = cluster["fast"]["date"] if cluster["fast"] else cluster["days"][-1]
        hy = hebrew_date(cluster["days"][0])[2]
        title = (f"Shabbat {parashah} and {cluster['name']} {hy}"
                 if parashah else f"Shabbat and {cluster['name']} {hy}")
        lede = (span_gregorian(fri, span_end) + " · "
                + span_hebrew_parts(hebrew_date(fri), hebrew_date(span_end)))
        times_heading = TIMES_HEADING_FESTIVAL_TEXT
        reflections_heading = f"Reflections on the Parasha and {cluster['name']}"
        readings = ([reading_from_item(item)] if item else []) + readings
    else:
        title = f"Shabbat {parashah}" if parashah else "Shabbat"
        lede = " · ".join(lede_bits)
        times_heading = TIMES_HEADING_TEXT
        reflections_heading = "Reflections on the Parasha"

    return {
        "sat": sat, "fri": fri,
        "sat_hebrew": sat_hebrew,
        "cluster": cluster,
        "parashah": parashah,
        "title": title,
        "lede": lede,
        "guest_text": guest_text,
        "times": times,
        "times_heading": times_heading,
        "reflections_heading": reflections_heading,
        "readings": readings,
        "torah_summary": None,      # filled by the teachings pipeline
        "haftarah_summary": None,
        "observances": observance_lines(sat, events),
        "service_times": service_times(cluster) if loc == "Poughkeepsie" else [],
        "kiddush": kiddush,
        "announcements": announcements,
        "halakha": None,   # filled by the teachings pipeline (step 4)
        "aggada": None,
    }


# --------------------------------------------------------------- rendering --

COLOPHON_WEB = (
    'Torah readings and calendar data by <a href="https://www.hebcal.com">Hebcal.com</a> '
    "(CC BY 4.0). Times are computed for Poughkeepsie by the congregation's luach; "
    "the end of Shabbat follows the convention of Congregation Shearith Israel, New York."
)

PLACEHOLDER = ('The {kind} teaching for the week will appear here; '
               "the teachings pipeline is build-order step 4.")


def linkify(text: str) -> str:
    return text.replace(SECRETARY, f'<a href="mailto:{SECRETARY}">{SECRETARY}</a>')


def mid(text: str) -> str:
    """Wrap glyphs the display face lacks (– · °) for site markup."""
    return (text.replace("–", '<span class="mid">–</span>')
                .replace("—", '<span class="mid">—</span>')
                .replace("·", '<span class="mid">·</span>')
                .replace("°", '<span class="mid">°</span>'))


def times_rows_html(ctx: dict) -> str:
    times = []
    for label, small, value, final in ctx["times"]:
        cls = ' class="row row--final"' if final else ' class="row"'
        times.append(f"""            <div{cls}>
                <dt>{label}
                    <small>{small.replace("·", "&middot;")}</small>
                </dt>
                <dd>{value}</dd>
            </div>""")
    return "\n".join(times)


def build_body(ctx: dict) -> list[str]:
    body = []
    if ctx["readings"]:
        single = len(ctx["readings"]) == 1
        body.append('<h2>Torah Reading <span class="amp">&amp;</span> Haftarah</h2>')
        for r in ctx["readings"]:
            body.append(f"<p><strong>{r['name']}</strong>, {r['range']}.</p>")
            if single and ctx.get("torah_summary"):
                body.append(f"<p>{ctx['torah_summary']}</p>")
            if r["haftarah"]:
                body.append("<p>" + r["haftarah"].replace("Haftarah:", "<strong>Haftarah:</strong>", 1) + "</p>")
            if single and ctx.get("haftarah_summary"):
                body.append(f"<p>{ctx['haftarah_summary']}</p>")
        if not single:
            if ctx.get("torah_summary"):
                body.append(f"<p>{ctx['torah_summary']}</p>")
            if ctx.get("haftarah_summary"):
                body.append(f"<p>{ctx['haftarah_summary']}</p>")
    if ctx["observances"]:
        body.append("<h2>In the Week Ahead</h2>")
        body += [f"<p>{o}</p>" for o in ctx["observances"]]
    if ctx["kiddush"]:
        body.append("<h2>Kiddush</h2>")
        body += [f"<p>{linkify(k)}</p>" for k in ctx["kiddush"]]
    if ctx["announcements"]:
        body.append("<h2>Announcements</h2>")
        body += [f"<p>{a}</p>" for a in ctx["announcements"]]
    body.append(f"<h2>{ctx.get('reflections_heading', 'Reflections on the Parasha')}</h2>")
    for head, key, kind in (("Halakha", "halakha", "halakhic"), ("Aggada", "aggada", "aggadic")):
        body.append(f"<h3>{head}</h3>")
        if ctx[key]:
            body.append(ctx[key])
        else:
            body.append(f'<p><em style="color: var(--ink-mute);">{PLACEHOLDER.format(kind=kind)}</em></p>')
    return body


def service_times_web(ctx: dict) -> str:
    """The service-times block in site markup, used on the bulletin page
    and in the services-page splice."""
    items = ctx.get("service_times") or []
    if not items:
        return ""
    groups = []
    cur = {"heading": None, "rows": [], "notes": []}
    for it in items:
        if it["kind"] == "heading":
            if cur["rows"] or cur["notes"] or cur["heading"]:
                groups.append(cur)
            cur = {"heading": it["text"], "rows": [], "notes": []}
        elif it["kind"] == "row":
            cur["rows"].append(it)
        else:
            cur["notes"].append(it["text"])
    groups.append(cur)

    parts = ['    <section class="schedule" aria-label="Service times">',
             '        <p class="schedule-note">Service Times for Kehillah Kedoshah Zikhron Zvi</p>']
    for g in groups:
        if g["heading"]:
            parts.append('        <p class="schedule-note" style="margin: 1.4rem 0 0.8rem; color: var(--gold-pale); letter-spacing: 0.2em;">'
                         + mid(g["heading"].replace("&", '<span class="amp">&amp;</span>')) + "</p>")
        if g["rows"]:
            parts.append("        <dl>")
            for i, r in enumerate(g["rows"]):
                cls = ' class="row row--final"' if i == len(g["rows"]) - 1 else ' class="row"'
                label = r["label"].replace("&", '<span class="amp">&amp;</span>')
                small = f"\n                    <small>{r['note']}</small>" if r["note"] else ""
                parts.append(f"""            <div{cls}>
                <dt>{label}{small}
                </dt>
                <dd>{r['time']}</dd>
            </div>""")
            parts.append("        </dl>")
        for n in g["notes"]:
            parts.append('        <p style="margin: 0.8rem 0 0; color: var(--ink-soft); '
                         f'font-style: italic; font-size: 0.95rem;">{n}</p>')
    parts.append("    </section>")
    return "\n".join(parts)


def render_web(ctx: dict) -> Path:
    body = build_body(ctx)

    guest = ""
    if ctx["guest_text"]:
        guest = f'''
    <section class="schedule" aria-label="Where we are this week">
        <div class="upcoming-dates">
            <p class="upcoming-list" style="font-family: var(--font-serif); text-transform: none; letter-spacing: 0; font-style: italic;">{ctx["guest_text"]}</p>
        </div>
    </section>
'''

    tpl = (ROOT / "bulletin" / "templates" / "web.html").read_text()
    html = (
        tpl.replace("{{PAGE_TITLE}}", ctx["title"])
        .replace("{{EYEBROW}}", ctx.get("eyebrow", "Weekly Bulletin"))
        .replace("{{TITLE}}", mid(ctx["title"]))
        .replace("{{LEDE}}", mid(ctx["lede"]))
        .replace("{{GUEST_NOTICE}}", guest)
        .replace("{{TIMES_HEADING}}", mid(ctx["times_heading"]))
        .replace("{{SERVICE_TIMES}}", service_times_web(ctx))
        .replace("{{TIMES_ROWS}}", times_rows_html(ctx))
        .replace("{{BODY_SECTIONS}}", "\n\n".join(body))
        .replace("{{COLOPHON}}", COLOPHON_WEB)
    )
    out = ROOT / "site" / "bulletin" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def render_services_fragments(ctx: dict) -> dict:
    """The two weekly fragments spliced into site/services.html at publish
    time, between the weekly-parashah and weekly-bulletin markers. Marc's
    hand-written page around them is never touched."""
    sat = ctx["sat"]
    hd, hm, hy = ctx["sat_hebrew"]
    name = mid(ctx["parashah"]) if ctx["parashah"] else mid(ctx["title"])
    label = f"Shabbat Parashat {name}" if ctx["parashah"] else mid(ctx["title"])
    box = f'''<div class="upcoming-dates">
                <p class="upcoming-month">This Shabbat &nbsp;<span class="mid">·</span>&nbsp; Saturday, {sat.day} {MONTHS[sat.month]} {sat.year} &nbsp;<span class="mid">·</span>&nbsp; {hd} {hm} {hy}</p>
                <p class="upcoming-list">{label}</p>
            </div>'''

    guest = ""
    if ctx["guest_text"]:
        guest = f'''    <section class="schedule" aria-label="Where we are this week">
        <div class="upcoming-dates">
            <p class="upcoming-list" style="font-family: var(--font-serif); text-transform: none; letter-spacing: 0; font-style: italic;">{ctx["guest_text"]}</p>
        </div>
    </section>
'''
    weekly = f'''{guest}    <section class="schedule" aria-label="Times for this Shabbat">
        <p class="schedule-note">{mid(ctx["times_heading"])}</p>
        <dl>
{times_rows_html(ctx)}
        </dl>
    </section>

{service_times_web(ctx) if ctx.get("cluster") else ""}
    <section class="prose" aria-label="Readings, observances, and teachings">
{chr(10).join(build_body(ctx))}
    </section>'''
    return {"parashah_box": box, "weekly": weekly}


# email palette
E_INK, E_SOFT, E_MUTE = "#f1dccc", "#d6b1a6", "#9a7273"
E_GOLD, E_GOLD_PALE, E_FUCHSIA, E_LINE = "#c79f50", "#e6c780", "#e376a3", "#5a2a48"
SERIF = "Georgia,'Times New Roman',serif"


def e_disp(text: str) -> str:
    """Glyphs the display face lacks (– & · °) set in the serif instead,
    the email counterpart of the site's .amp/.mid spans."""
    span = '<span style="font-family:Georgia,serif; font-style:italic;">{}</span>'
    for glyph in ("–", "&amp;", "·", "°"):
        text = text.replace(glyph, span.format(glyph))
    return text


def e_h2(text: str) -> str:
    text = e_disp(text)
    return (f'  <tr><td style="padding:20px 26px 2px;">'
            f'<div class="display" style="font-family:{SERIF}; font-size:14px; letter-spacing:2px; '
            f'color:{E_GOLD_PALE}; text-transform:uppercase; border-bottom:1px solid {E_LINE}; '
            f'padding-bottom:7px;">{text}</div></td></tr>\n')


def e_h3(text: str) -> str:
    text = e_disp(text)
    return (f'  <tr><td style="padding:14px 26px 0;">'
            f'<div class="display" style="font-family:{SERIF}; font-size:12px; letter-spacing:2px; '
            f'color:{E_FUCHSIA}; text-transform:uppercase;">{text}</div></td></tr>\n')


def e_p(html_text: str, color: str = E_INK, italic: bool = False, size: int = 14) -> str:
    style = f"font-family:{SERIF}; font-size:{size}px; line-height:1.65; color:{color};"
    if italic:
        style += " font-style:italic;"
    return f'  <tr><td style="padding:10px 26px 0;"><div style="{style}">{html_text}</div></td></tr>\n'


def render_email(ctx: dict, base: str = SITE) -> tuple[Path, Path]:
    times = []
    for label, small, value, final in ctx["times"]:
        color = E_GOLD_PALE if final else E_INK
        vcolor = E_GOLD_PALE if final else E_FUCHSIA
        times.append(f"""      <tr>
        <td style="padding:13px 0 3px; border-bottom:1px solid {E_LINE};">
          <div class="display" style="font-family:{SERIF}; font-size:14px; letter-spacing:1px; color:{color}; text-transform:uppercase;">{label}</div>
          <div style="font-family:{SERIF}; font-style:italic; font-size:11px; color:{E_MUTE}; padding:3px 0 9px;">{small}</div>
        </td>
        <td align="right" valign="top" style="padding:13px 0 3px; border-bottom:1px solid {E_LINE};">
          <div class="display" style="font-family:{SERIF}; font-size:16px; letter-spacing:1px; color:{vcolor};">{value}</div>
        </td>
      </tr>""")

    sections = []
    if ctx["readings"]:
        single = len(ctx["readings"]) == 1
        sections.append(e_h2("Torah Reading &amp; Haftarah"))
        for r in ctx["readings"]:
            sections.append(e_p(f"<strong style='color:{E_GOLD_PALE}; font-weight:500;'>{r['name']}</strong>, {r['range']}."))
            if single and ctx.get("torah_summary"):
                sections.append(e_p(ctx["torah_summary"]))
            if r["haftarah"]:
                sections.append(e_p(r["haftarah"].replace(
                    "Haftarah:", f"<strong style='color:{E_GOLD_PALE}; font-weight:500;'>Haftarah:</strong>", 1)))
            if single and ctx.get("haftarah_summary"):
                sections.append(e_p(ctx["haftarah_summary"]))
        if not single:
            if ctx.get("torah_summary"):
                sections.append(e_p(ctx["torah_summary"]))
            if ctx.get("haftarah_summary"):
                sections.append(e_p(ctx["haftarah_summary"]))
    if ctx["observances"]:
        sections.append(e_h2("In the Week Ahead"))
        for o in ctx["observances"]:
            sections.append(e_p(o))
    if ctx["kiddush"]:
        sections.append(e_h2("Kiddush"))
        for k in ctx["kiddush"]:
            sections.append(e_p(linkify(k)))
    if ctx["announcements"]:
        sections.append(e_h2("Announcements"))
        for a in ctx["announcements"]:
            sections.append(e_p(a))
    if not (ctx.get("skip_empty_reflections") and not ctx["halakha"] and not ctx["aggada"]):
        sections.append(e_h2(ctx.get("reflections_heading", "Reflections on the Parasha")))
        for head, key, kind in (("Halakha", "halakha", "halakhic"), ("Aggada", "aggada", "aggadic")):
            sections.append(e_h3(head))
            if ctx[key]:
                sections.append(e_p(ctx[key]))
            else:
                sections.append(e_p(PLACEHOLDER.format(kind=kind), color=E_MUTE, italic=True))

    svc = ""
    if ctx.get("service_times"):
        rows = []
        for it in ctx["service_times"]:
            if it["kind"] == "heading":
                rows.append(f"""      <tr><td colspan="2" style="padding:18px 0 3px;">
          <div class="display" style="font-family:{SERIF}; font-size:11px; letter-spacing:2px; color:{E_GOLD_PALE}; text-transform:uppercase;">{e_disp(it['text'].replace('&', '&amp;'))}</div>
        </td></tr>""")
                continue
            if it["kind"] == "note":
                rows.append(f"""      <tr><td colspan="2" style="padding:7px 0 2px;">
          <div style="font-family:{SERIF}; font-style:italic; font-size:12px; color:{E_SOFT};">{it['text']}</div>
        </td></tr>""")
                continue
            note_html = (f'<div style="font-family:{SERIF}; font-style:italic; font-size:11px; '
                         f'color:{E_MUTE}; padding:2px 0 8px;">{it["note"]}</div>') if it["note"] else ""
            rows.append(f"""      <tr>
        <td style="padding:11px 0 2px; border-bottom:1px solid {E_LINE};">
          <div class="display" style="font-family:{SERIF}; font-size:13px; letter-spacing:1px; color:{E_INK}; text-transform:uppercase;">{e_disp(it['label'].replace('&', '&amp;'))}</div>
          {note_html}
        </td>
        <td align="right" valign="top" style="padding:11px 0 2px; border-bottom:1px solid {E_LINE};">
          <div class="display" style="font-family:{SERIF}; font-size:14px; letter-spacing:1px; color:{E_FUCHSIA};">{it['time']}</div>
        </td>
      </tr>""")
        svc = (f'  <tr><td style="padding:24px 26px 0;">\n'
               f'    <div class="display" style="font-family:{SERIF}; font-size:12px; '
               f'letter-spacing:2px; color:{E_GOLD}; text-transform:uppercase; '
               f'padding-bottom:4px;">Service Times for Kehillah Kedoshah Zikhron Zvi</div>\n'
               f'    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">\n'
               + "\n".join(rows) + "\n    </table>\n  </td></tr>\n")

    guest = ""
    if ctx["guest_text"]:
        guest = (f'  <tr><td style="padding:18px 26px 0;">'
                 f'<div style="font-family:{SERIF}; font-style:italic; font-size:15px; line-height:1.6; '
                 f'color:{E_INK}; border:1px solid {E_LINE}; border-left:3px solid {E_GOLD}; '
                 f'background-color:#240a1c; padding:14px 16px;">{ctx["guest_text"]}</div></td></tr>\n')

    colophon = (
        'Torah readings and calendar data by <a href="https://www.hebcal.com" '
        f'style="color:{E_GOLD_PALE};">Hebcal.com</a> (CC BY 4.0). Times are computed for '
        "Poughkeepsie by the congregation's luach; the end of Shabbat follows the convention "
        "of Congregation Shearith Israel, New York.<br><br>"
        f'You receive this bulletin as a friend of the congregation. '
        f'<a href="*|UNSUB|*" style="color:{E_GOLD_PALE};">Unsubscribe</a> &nbsp;·&nbsp; *|LIST:ADDRESSLINE|*'
    )

    footer_meta = (f'<a href="{SITE}/contact.html" style="color:{E_GOLD_PALE};">Contact</a> &nbsp;·&nbsp; '
                   f'<a href="{SITE}/services.html" style="color:{E_GOLD_PALE};">Services</a> &nbsp;·&nbsp; '
                   f'<a href="{SITE}/kiddush.html" style="color:{E_GOLD_PALE};">Kiddush</a>'
                   f"<br>© Kehillah Kedoshah Zikhron Zvi")

    tpl = (ROOT / "bulletin" / "templates" / "email.html").read_text()
    html = (
        tpl.replace("{{BASE}}", base)
        .replace("{{PAGE_TITLE}}", ctx["title"])
        .replace("{{EYEBROW}}", ctx.get("eyebrow", "Weekly Bulletin"))
        .replace("{{TITLE}}", e_disp(ctx["title"]))
        .replace("{{LEDE}}", ctx["lede"])
        .replace("{{GUEST_NOTICE}}", guest)
        .replace("{{TIMES_HEADING}}", e_disp(ctx["times_heading"]))
        .replace("{{TIMES_ROWS}}", "\n".join(times))
        .replace("{{SERVICE_TIMES}}", svc)
        .replace("{{SECTIONS}}", "".join(sections))
        .replace("{{COLOPHON}}", colophon)
        .replace("{{FOOTER_META}}", footer_meta)
    )

    outdir = ROOT / "out"
    outdir.mkdir(exist_ok=True)
    html_path = outdir / "email.html"
    html_path.write_text(html)

    text_path = outdir / "email.txt"
    text_path.write_text(render_text(ctx))
    return html_path, text_path


def render_text(ctx: dict) -> str:
    lines = ["KEHILLAH KEDOSHAH ZIKHRON ZVI — WEEKLY BULLETIN", "", ctx["title"], ctx["lede"], ""]
    if ctx["guest_text"]:
        lines += [ctx["guest_text"], ""]
    lines.append(ctx["times_heading"].replace("°", ""))
    for label, small, value, _final in ctx["times"]:
        lines.append(f"{label}: {value}  ({small})")
    lines.append("")
    if ctx.get("service_times"):
        lines.append("SERVICE TIMES FOR KEHILLAH KEDOSHAH ZIKHRON ZVI")
        for it in ctx["service_times"]:
            if it["kind"] == "heading":
                lines.append(it["text"].upper())
            elif it["kind"] == "note":
                lines.append(it["text"])
            else:
                lines.append(f"{it['label']}: {it['time']}")
        lines.append("")
    if ctx["readings"]:
        lines.append("TORAH READING & HAFTARAH")
        for r in ctx["readings"]:
            lines.append(f"{r['name']}, {r['range']}.")
            if r["haftarah"]:
                lines.append(r["haftarah"])
        if ctx.get("torah_summary"):
            lines.append(ctx["torah_summary"])
        if ctx.get("haftarah_summary"):
            lines.append(ctx["haftarah_summary"])
        lines.append("")
    if ctx["observances"]:
        lines += ["IN THE WEEK AHEAD"] + ctx["observances"] + [""]
    if ctx["kiddush"]:
        lines += ["KIDDUSH"] + ctx["kiddush"] + [""]
    if ctx["announcements"]:
        lines += ["ANNOUNCEMENTS"] + ctx["announcements"] + [""]
    lines.append("REFLECTIONS ON THE PARASHA")
    for head, key, kind in (("Halakha", "halakha", "halakhic"), ("Aggada", "aggada", "aggadic")):
        lines.append(head)
        lines.append(re.sub(r"<[^>]+>", "", ctx[key]) if ctx[key] else f"({PLACEHOLDER.format(kind=kind)})")
        lines.append("")
    lines += [
        "Torah readings and calendar data by Hebcal.com (CC BY 4.0). Times are",
        "computed for Poughkeepsie by the congregation's luach; the end of Shabbat",
        "follows the convention of Congregation Shearith Israel, New York.",
        "",
        "Unsubscribe: *|UNSUB|*",
    ]
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------- main --

def next_saturday(today: date) -> date:
    return today + timedelta(days=(5 - today.weekday()) % 7)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = SITE
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    sat = date.fromisoformat(args[0]) if args else next_saturday(date.today())
    if sat.weekday() != 5:
        sys.exit("date must be a Saturday")
    ctx = build_context(sat)
    print(render_web(ctx))
    for p in render_email(ctx, base):
        print(p)

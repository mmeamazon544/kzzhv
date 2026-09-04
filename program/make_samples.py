"""Step-4 sample run: generate the two teachings for a given Shabbat and
render the complete bulletin (web + email + text) with them in place.

Runs in GitHub Actions (where ANTHROPIC_API_KEY lives); writes everything
to out/ for the artifact. Publishes nothing, sends nothing.

Usage: python3 program/make_samples.py 2026-09-05
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import bulletin
import teachings

ROOT = Path(__file__).resolve().parent.parent


def week_description(ctx: dict) -> str:
    lines = [ctx["title"], ctx["lede"]]
    for r in ctx["readings"]:
        lines.append(f"Reading: {r['name']}, {r['range']}")
        if r["haftarah"]:
            lines.append(r["haftarah"])
    if ctx.get("cluster"):
        c = ctx["cluster"]
        days = ", ".join(d.strftime("%A %d %B") for d in c["days"])
        lines.append(f"This is a festival bulletin: {c['name']}, days: {days}; "
                     f"eve {c['eve'].strftime('%A %d %B')}."
                     + (f" It also covers the fast on {c['fast']['date'].strftime('%A %d %B')}."
                        if c["fast"] else ""))
    if ctx["observances"]:
        lines.append("In the week ahead: " + " ".join(ctx["observances"]))
    return "\n".join(lines)


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def reading_refs(ctx: dict) -> tuple | None:
    if not ctx.get("readings"):
        return None
    r = ctx["readings"][0]
    return (r.get("range_raw") or "", r.get("haftarah_raw") or "")


def apply_teachings(ctx: dict, t: dict) -> None:
    ctx["halakha"] = t["halakha_html"]
    ctx["aggada"] = t["aggada_html"]
    ctx["torah_summary"] = t.get("parashah_summary")
    ctx["haftarah_summary"] = t.get("haftarah_summary")


def main() -> None:
    sat = date.fromisoformat(sys.argv[1])
    ctx = bulletin.build_context(sat)
    t = teachings.generate(week_description(ctx), reading_refs=reading_refs(ctx))

    apply_teachings(ctx, t)

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "teachings.json").write_text(json.dumps(t, indent=1))

    web = bulletin.render_web(ctx)
    shutil.copy(web, out / "bulletin-web.html")
    bulletin.render_email(ctx)

    offsets = ROOT / "program" / "data" / "kst-offsets.json"
    if offsets.exists():
        shutil.copy(offsets, out / "kst-offsets.json")

    preview = [
        f"# Sample teachings — {ctx['title']}",
        "",
        f"Halakhic topic: {t['plan']['halakhic_topic']}",
        f"Aggadic topic: {t['plan']['aggadic_topic']}",
        "",
        "## Parashah summary", "", t.get("parashah_summary", ""), "",
        "## Haftarah summary", "", t.get("haftarah_summary", ""), "",
        "## Halakha",
        "",
        strip_tags(t["halakha_html"]),
        "",
        "Citations: " + "; ".join(c["display"] for c in t["halakha_citations"]),
        "",
        "## Aggada",
        "",
        strip_tags(t["aggada_html"]),
        "",
        "Citations: " + "; ".join(c["display"] for c in t["aggada_citations"]),
        "",
    ]
    (out / "preview.md").write_text("\n".join(preview))
    print("\n".join(preview))


if __name__ == "__main__":
    main()

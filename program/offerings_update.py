"""Update the Offerings page's goal figures from the ledger.

Reads bulletin/offerings-ledger.md, sums each goal project, and rewrites
the three marked regions in site/offerings.html (the ornamental fill, the
figures line, and the accessible values). Run by the offerings workflow
whenever the ledger changes.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GOALS = {
    "restoration": (6000, "toward the restoration"),
    "torah": (23000, "toward the Torah scroll"),
    "siddur": (1000, "toward the siddurim"),
    "mahzor": (1600, "toward the mahzorim"),
}


def totals() -> dict[str, float]:
    sums = {k: 0.0 for k in GOALS}
    raw = (ROOT / "bulletin" / "offerings-ledger.md").read_text()
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        project = parts[1].lower()
        try:
            amount = float(parts[2].replace("$", "").replace(",", ""))
        except ValueError:
            continue
        if project in sums:
            sums[project] += amount
    return sums


def money(x: float) -> str:
    return "${:,.0f}".format(x)


def money_html(x: float) -> str:
    """The display face lacks $; set it in the serif (site .amp convention)."""
    return '<span class="amp">$</span>' + "{:,.0f}".format(x)


def block(slug: str, raised: float) -> str:
    goal, tagline = GOALS[slug]
    pct = max(0.0, min(100.0, raised / goal * 100.0))
    empty = " data-empty" if raised <= 0 else ""
    label = f"{slug.capitalize()}: {money(raised)} raised of {money(goal)}"
    return f'''            <div class="offering-goal" role="progressbar" aria-valuemin="0" aria-valuemax="{goal}" aria-valuenow="{int(raised)}" aria-label="{label}">
                <div class="offering-rule">
                    <div class="offering-fill"{empty} style="width: {pct:.1f}%;"><span class="offering-mark" aria-hidden="true">&#9670;</span></div>
                </div>
                <p class="offering-figures">{money_html(raised)} of {money_html(goal)} &nbsp;<em>{tagline}</em></p>
            </div>'''


def main() -> None:
    page = ROOT / "site" / "offerings.html"
    text = page.read_text()
    sums = totals()
    for slug in GOALS:
        b = f"<!-- goal:{slug}:begin -->"
        e = f"<!-- goal:{slug}:end -->"
        i = text.index(b) + len(b)
        j = text.index(e)
        text = text[:i] + "\n" + block(slug, sums[slug]) + "\n            " + text[j:]
        print(f"{slug}: {money(sums[slug])} of {money(GOALS[slug][0])}")
    page.write_text(text)
    print("offerings page updated")


if __name__ == "__main__":
    main()

"""Turn a sent bulletin into a copy that can be pasted into an ordinary
email and keep its appearance.

Pasting from a browser into Gmail, Apple Mail or Mimestream keeps inline
style attributes and discards everything else: the <style> block, its
classes, its @font-face rules. So this rewrites the bulletin to depend on
nothing but inline style.

Two things change and one thing is deliberately left alone.

  * The seven anchors that only the stylesheet was colouring are given
    the colour inline; otherwise they paste as default blue.
  * The Mailchimp footer sentence goes, since its merge tags mean nothing
    outside a campaign and would paste as literal *|UNSUB|* text.
  * The <style> block is removed outright rather than inlined. Its
    @font-face cannot survive a paste, and its .display rule would then
    resolve "Chelsea Studio" against whatever is INSTALLED on the reader's
    machine. The copy of Chelsea Studio on Marc's Mac (and on any machine
    carrying that old file) has blank glyphs for the digits, so every
    service time, date and Hebrew year would silently vanish while the
    words around them stayed put. The display elements already carry
    Georgia inline, which is what a mail client shows anyway, and Georgia
    renders the numbers. Legible beats ornamental.

Usage: python3 program/pasteable.py <bulletin-id> <output.html>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = "#e376a3"


def drop_style_block(html: str) -> tuple[str, int]:
    out, n = re.subn(r"[ \t]*<style\b.*?</style>\s*", "", html, flags=re.S)
    return out, n


def inline_link_colour(html: str) -> tuple[str, int]:
    n = 0

    def fix(m: re.Match) -> str:
        nonlocal n
        tag = m.group(0)
        if "color:" in tag:
            return tag
        n += 1
        if 'style="' in tag:
            return tag.replace('style="', f'style="color:{LINK};', 1)
        return tag[:-1] + f' style="color:{LINK};">'

    return re.sub(r"<a\s[^>]*>", fix, html), n


def strip_campaign_footer(html: str) -> tuple[str, bool]:
    pattern = (r"You receive this bulletin as a friend of the congregation\."
               r".*?\*\|LIST:ADDRESSLINE\|\*")
    out = re.sub(pattern, "", html, flags=re.S)
    return out, out != html


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: pasteable.py <bulletin-id> <output.html>")
    bid, out_path = sys.argv[1], Path(sys.argv[2])

    src = ROOT / "bulletin" / "state" / bid / "email.html"
    if not src.exists():
        sys.exit(f"no stored email for {bid}")
    html = src.read_text()

    html, styles = drop_style_block(html)
    html, links = inline_link_colour(html)
    html, footer = strip_campaign_footer(html)

    # Guards. Each of these would ship a copy that looks wrong.
    leftover = re.findall(r"\*\|[A-Z_:]+\|\*", html)
    if leftover:
        sys.exit(f"merge tags still present: {sorted(set(leftover))}")
    if "<style" in html or "@font-face" in html:
        sys.exit("a stylesheet survived; it would not survive a paste")
    if re.search(r"font-family:\s*['\"]?Chelsea", html, re.I):
        sys.exit("Chelsea Studio named inline: the installed cut has blank "
                 "digits and every time would disappear")
    if 'class="display"' in html and "font-family:Georgia" not in html:
        sys.exit("display elements lost their inline font")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    print(f"stylesheet blocks removed: {styles}")
    print(f"anchors coloured inline: {links}")
    print(f"campaign footer removed: {'yes' if footer else 'NO — check it'}")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()

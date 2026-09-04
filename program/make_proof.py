"""Build and send a proof (build order step 7).

For a given Shabbat: builds the bulletin (teachings included), renders
web + email + text, captures the web page as PNG and PDF, stores all of
it under bulletin/state/<id>/ (committed by the workflow — the publish
step later ships exactly these bytes), updates bulletin/state/current.json,
and mails the proof — the finished email with an approval banner on top —
to the Proof segment (Marc alone).

Change requests pass extra instructions through --instructions; the
teachings drafting sees them.

Two phases, because the proof email links to the PNG/PDF at their
raw.githubusercontent URLs, which exist only after the workflow commits:
  python3 program/make_proof.py 2026-09-05 [--instructions "..."]   build
  python3 program/make_proof.py --send-only                          mail
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import bulletin
import teachings
import proof_links
from make_samples import apply_teachings, reading_refs, week_description
from mailchimp_send import send as mailchimp_send

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/mmeamazon544/kzzhv/main"


def banner(bulletin_id: str, rev: str, title: str) -> str:
    approve, changes = proof_links.links(bulletin_id, rev)
    png = f"{RAW}/bulletin/state/{bulletin_id}/proof.png"
    pdf = f"{RAW}/bulletin/state/{bulletin_id}/proof.pdf"
    btn = ("display:inline-block; font-family:Georgia,serif; letter-spacing:2px; "
           "text-transform:uppercase; font-size:13px; padding:12px 22px; "
           "text-decoration:none; margin:6px 10px 6px 0;")
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#240a1c; border-bottom:3px solid #c79f50;">
<tr><td align="center" style="padding:18px 20px;">
  <div style="font-family:Georgia,serif; font-size:12px; letter-spacing:3px; color:#c79f50; text-transform:uppercase;">Proof — not yet published</div>
  <div style="font-family:Georgia,serif; font-size:14px; color:#f1dccc; padding:8px 0 4px;">{title}</div>
  <div>
    <a href="{approve}" style="{btn} background-color:#611c40; color:#f1dccc; border:1px solid #c79f50;">Approve</a>
    <a href="{changes}" style="{btn} background-color:#170611; color:#d6b1a6; border:1px solid #5a2a48;">Request changes</a>
  </div>
  <div style="font-family:Georgia,serif; font-size:11px; color:#9a7273; padding-top:6px;">
    The web page: <a href="{png}" style="color:#e6c780;">PNG</a> &nbsp;·&nbsp; <a href="{pdf}" style="color:#e6c780;">PDF</a>
  </div>
</td></tr></table>
"""


def capture(web_html: Path, outdir: Path) -> None:
    """Full-page PNG via Playwright chromium, PDF from the PNG (screen
    look, not print styles)."""
    from playwright.sync_api import sync_playwright
    from PIL import Image

    # Serve nothing: load the site assets from the live site by rewriting
    # absolute paths to kzzhv.org (fonts, css, images are all deployed).
    html = web_html.read_text().replace('href="/assets', 'href="https://kzzhv.org/assets') \
                               .replace('src="/assets', 'src="https://kzzhv.org/assets')
    tmp = outdir / "proof-render.html"
    tmp.write_text(html)

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 1400})
        page.goto(tmp.resolve().as_uri())
        page.wait_for_timeout(2500)
        page.screenshot(path=str(outdir / "proof.png"), full_page=True)
        b.close()
    tmp.unlink()

    im = Image.open(outdir / "proof.png").convert("RGB")
    im.save(outdir / "proof.pdf", resolution=96.0)


def send_only() -> None:
    current = json.loads((ROOT / "bulletin" / "state" / "current.json").read_text())
    bulletin_id, rev = current["id"], current["rev"]
    state = ROOT / "bulletin" / "state" / bulletin_id
    email_html = (state / "email.html").read_text()
    proof_html = re.sub(
        r"(<body[^>]*>)", r"\1\n" + banner(bulletin_id, rev, current["subject"]),
        email_html, count=1)
    approve, changes = proof_links.links(bulletin_id, rev)
    proof_text = (f"PROOF — approve: {approve}\nrequest changes: {changes}\n\n"
                  + (state / "email.txt").read_text())
    cid = mailchimp_send(f"PROOF: {current['subject']}", proof_html, proof_text, proof=True)
    print(f"proof email for {bulletin_id} rev {rev}: campaign {cid} to Marc only")


def main() -> None:
    if "--send-only" in sys.argv:
        send_only()
        return

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    instructions = ""
    if "--instructions" in sys.argv:
        instructions = sys.argv[sys.argv.index("--instructions") + 1]

    sat = date.fromisoformat(args[0])
    bulletin_id = sat.isoformat()
    rev = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%dT%H%M%S")

    ctx = bulletin.build_context(sat)
    week = week_description(ctx)
    if instructions:
        week += ("\n\nInstructions from Marc for this revision (follow them):\n"
                 + instructions)
    t = teachings.generate(week, reading_refs=reading_refs(ctx))
    apply_teachings(ctx, t)

    web = bulletin.render_web(ctx)
    email_html_path, email_txt_path = bulletin.render_email(ctx)

    state = ROOT / "bulletin" / "state" / bulletin_id
    state.mkdir(parents=True, exist_ok=True)
    shutil.copy(web, state / "web.html")
    shutil.copy(email_html_path, state / "email.html")
    shutil.copy(email_txt_path, state / "email.txt")
    (state / "teachings.json").write_text(json.dumps(t, indent=1))
    frags = bulletin.render_services_fragments(ctx)
    (state / "services-parashah.html").write_text(frags["parashah_box"])
    (state / "services-weekly.html").write_text(frags["weekly"])
    (state / "services-schedule.html").write_text(frags["schedule"])
    capture(state / "web.html", state)

    greg = ctx["lede"].split(" · ")[0] if " · " in ctx["lede"] else ctx["lede"]
    current = {
        "id": bulletin_id, "rev": rev, "status": "proofed",
        "title": ctx["title"], "subject": f"{ctx['title']} · {greg}",
        "proofed_at": rev,
    }
    (ROOT / "bulletin" / "state" / "current.json").write_text(
        json.dumps(current, indent=1) + "\n")
    print(f"proofed {bulletin_id} rev {rev}; commit, then --send-only")


if __name__ == "__main__":
    main()

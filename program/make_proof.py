"""Build and send a proof (build order step 7).

For a given Shabbat: builds the bulletin (teachings included), renders
web + email + text, captures the web page as PNG and PDF, stores all of
it under bulletin/state/<id>/ (committed by the workflow — the publish
step later ships exactly these bytes), updates bulletin/state/current.json,
and mails the proof — the finished email with an approval banner on top —
to the Proof segment (Marc alone).

Change requests pass extra instructions through --instructions. Two
things happen with them: the content files Marc owns (banner,
announcements, location, service times, greetings) are edited to match,
and the teachings drafting sees them. What neither path can do — layout,
templates, program behavior — is reported back in the fresh proof's
banner so Marc knows to bring it to Claude directly.

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

# ------------------------------------------------------- change requests --
# Files the Request-changes box may edit: the content Marc owns. Never
# templates, never program code — those changes go to Claude directly and
# the proof banner says so.
CONTENT_FILES = ["bulletin/banner.md", "bulletin/announcements.md",
                 "bulletin/location.md", "bulletin/service-times.md"]
CONTENT_DIRS = ["bulletin/service-times", "bulletin/greetings"]

CHANGES_SCHEMA = {
    "type": "object",
    "properties": {
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"},
                               "content": {"type": "string"}},
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
        "not_done": {"type": "string"},
    },
    "required": ["edits", "not_done"],
    "additionalProperties": False,
}


def editable_files() -> list[str]:
    paths = [p for p in CONTENT_FILES if (ROOT / p).exists()]
    for d in CONTENT_DIRS:
        base = ROOT / d
        if base.is_dir():
            paths += sorted(str(p.relative_to(ROOT)) for p in base.glob("*.md"))
    return paths


def path_allowed(rel: str) -> bool:
    if ".." in rel or rel.startswith("/"):
        return False
    if rel in CONTENT_FILES:
        return True
    return any(rel.startswith(d + "/") and rel.endswith(".md")
               for d in CONTENT_DIRS)


def apply_instructions(instructions: str) -> str:
    """Edit the content files to match Marc's change request. Returns a
    plain-English note of whatever the request asked for that these files
    cannot carry (layout, templates, program behavior), '' when nothing."""
    import teachings as t

    files = editable_files()
    listing = "\n\n".join(
        f"=== {p} ===\n{(ROOT / p).read_text()}" for p in files)
    prompt = f"""You maintain the content files of the weekly bulletin of Kehillah
Kedoshah Zikhron Zvi. Marc, who runs the congregation, pressed "Request
changes" on a proof and wrote:

{instructions}

Below are the content files you may edit, with their current contents.
Each file's opening comment states its own format; keep formats exactly.
Return, as edits, the complete new text of only the files that must
change (path exactly as given). You may also create a new file under
bulletin/service-times/ or bulletin/greetings/ if the request calls for
one, following the format of its siblings.

Rules:
- Never invent facts. If the request needs a time, name, text, or
  greeting Marc did not supply and the files do not contain, do not
  guess — put that part in not_done, asking him plainly for it.
- Requests about the divrei torah / teachings / reflections are handled
  by a separate drafting step that also sees his instructions; do not
  list those in not_done and do not try to act on them here.
- Anything about layout, design, typography, templates, the program's
  behavior, or publishing cannot be done from here: describe it briefly
  and plainly in not_done (it will be shown to Marc so he can bring it
  to Claude). If everything is handled, not_done is an empty string.

{listing}"""
    try:
        r = t._create(
            max_tokens=8000,
            output_config={"format": {"type": "json_schema", "schema": CHANGES_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        out = t._json_out(r)
    except Exception as e:
        # The proof must still arrive: the teachings drafting sees the
        # instructions regardless; only the file edits are lost.
        print(f"change-request applier failed: {e}")
        return ("the automatic change step failed this round, so nothing in the "
                "times, announcements, banner, or greetings was edited. "
                "Tell Claude what should change.")
    for e in out.get("edits", []):
        rel = e["path"].strip()
        if not path_allowed(rel):
            print(f"change-request edit to {rel} refused (outside the content files)")
            continue
        (ROOT / rel).write_text(e["content"])
        print(f"change request edited {rel}")
    note = out.get("not_done", "").strip()
    if note:
        print(f"change request, not done from here: {note}")
    return note


def banner(bulletin_id: str, rev: str, title: str, note: str = "") -> str:
    approve, changes = proof_links.links(bulletin_id, rev)
    png = f"{RAW}/bulletin/state/{bulletin_id}/proof.png"
    pdf = f"{RAW}/bulletin/state/{bulletin_id}/proof.pdf"
    btn = ("display:inline-block; font-family:Georgia,serif; letter-spacing:2px; "
           "text-transform:uppercase; font-size:13px; padding:12px 22px; "
           "text-decoration:none; margin:6px 10px 6px 0;")
    note_html = ""
    if note:
        note_html = (f'\n  <div style="font-family:Georgia,serif; font-size:12px; '
                     f'color:#e6c780; padding-top:10px; max-width:520px;">'
                     f'Not changed from this proof cycle — bring it to Claude: {note}</div>')
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
  </div>{note_html}
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
    note = current.get("note", "")
    proof_html = re.sub(
        r"(<body[^>]*>)",
        r"\1\n" + banner(bulletin_id, rev, current["subject"], note),
        email_html, count=1)
    approve, changes = proof_links.links(bulletin_id, rev)
    note_text = f"Not changed from this proof cycle — bring it to Claude: {note}\n" if note else ""
    proof_text = (f"PROOF — approve: {approve}\nrequest changes: {changes}\n{note_text}\n"
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

    note = apply_instructions(instructions) if instructions else ""

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
    if note:
        current["note"] = note
    (ROOT / "bulletin" / "state" / "current.json").write_text(
        json.dumps(current, indent=1) + "\n")
    print(f"proofed {bulletin_id} rev {rev}; commit, then --send-only")


if __name__ == "__main__":
    main()

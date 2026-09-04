"""Approval state machine and publication (build order step 7).

bulletin/state/current.json carries {id, rev, status, subject, ...};
status runs proofed -> approved -> published -> sent. The publish step
ships exactly the bytes stored at proof time under bulletin/state/<id>/.

Modes:
  --record-approval ID REV   validate against current.json, mark approved;
                             prints "immediate=yes" when the send moment
                             has already passed (late approval).
  --publish [--if-due]       copy the approved page into site/bulletin/
                             (current + dated archive), write the teachings
                             archive; --if-due no-ops before the send moment.
  --send                     send the approved email; to the Proof segment
                             unless BULLETIN_DRY_RUN=false.
  --remind                   if still unapproved near the send moment,
                             mail Marc the approval links again.

The send moment for a Shabbat bulletin is 6:00 pm America/New_York on the
Wednesday before it (bulletin/luach.md).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import proof_links

ROOT = Path(__file__).resolve().parent.parent
NY = ZoneInfo("America/New_York")
CURRENT = ROOT / "bulletin" / "state" / "current.json"


def load() -> dict:
    return json.loads(CURRENT.read_text())


def save(cur: dict) -> None:
    CURRENT.write_text(json.dumps(cur, indent=1) + "\n")


def send_moment(bulletin_id: str) -> datetime:
    sat = date.fromisoformat(bulletin_id)
    wed = sat - timedelta(days=3)
    return datetime(wed.year, wed.month, wed.day, 18, 0, tzinfo=NY)


def now() -> datetime:
    return datetime.now(NY)


def slug(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "bulletin"


def record_approval(bulletin_id: str, rev: str) -> None:
    cur = load()
    if cur["id"] != bulletin_id or cur["rev"] != rev:
        sys.exit(f"approval for {bulletin_id} rev {rev} does not match current "
                 f"({cur['id']} rev {cur['rev']}); ignoring")
    if cur["status"] not in ("proofed", "approved"):
        sys.exit(f"current status is {cur['status']}; ignoring")
    cur["status"] = "approved"
    cur["approved_at"] = now().isoformat()
    save(cur)
    late = now() >= send_moment(bulletin_id)
    print(f"approved {bulletin_id} rev {rev}")
    print(f"immediate={'yes' if late else 'no'}")


def splice(text: str, marker: str, content: str) -> str:
    b, e = f"<!-- {marker}:begin -->", f"<!-- {marker}:end -->"
    i = text.index(b) + len(b)
    j = text.index(e)
    return text[:i] + "\n" + content + "\n" + text[j:]


def splice_services(state: Path) -> bool:
    """Put the week's full bulletin content into site/services.html between
    its weekly markers (Marc's directive of 3 September 2026: the services
    page carries everything the email carries, divrei torah included)."""
    box = state / "services-parashah.html"
    weekly = state / "services-weekly.html"
    if not (box.exists() and weekly.exists()):
        print("no services fragments in this proof; services.html untouched")
        return False
    path = ROOT / "site" / "services.html"
    text = path.read_text()
    text = splice(text, "weekly-parashah", box.read_text())
    text = splice(text, "weekly-bulletin", weekly.read_text())
    schedule = state / "services-schedule.html"
    if schedule.exists() and "weekly-schedule:begin" in text:
        text = splice(text, "weekly-schedule", schedule.read_text())
    path.write_text(text)
    return True


def publish(if_due: bool) -> None:
    cur = load()
    if cur["status"] == "published":
        print("already published")
        return
    if cur["status"] != "approved":
        if if_due:
            print(f"status is {cur['status']}; nothing to publish")
            return
        sys.exit(f"cannot publish: status is {cur['status']}")
    if if_due and now() < send_moment(cur["id"]):
        print("send moment not reached; waiting")
        return

    state = ROOT / "bulletin" / "state" / cur["id"]
    web = (state / "web.html").read_text()

    outdir = ROOT / "site" / "bulletin"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "index.html").write_text(web)
    arch = outdir / f"{cur['id']}-{slug(cur['title'])}"
    arch.mkdir(parents=True, exist_ok=True)
    (arch / "index.html").write_text(web)

    # Teachings library: topics feed the never-repeat check.
    t = json.loads((state / "teachings.json").read_text())
    lines = [
        f"topic: {t['plan']['halakhic_topic']}",
        f"topic: {t['plan']['aggadic_topic']}",
        "",
        "## Halakha", "", t["halakha_html"], "",
        "## Aggada", "", t["aggada_html"], "",
    ]
    archdir = ROOT / "bulletin" / "archive" / "teachings"
    archdir.mkdir(parents=True, exist_ok=True)
    (archdir / f"{cur['id']}.md").write_text("\n".join(lines))

    splice_services(state)

    cur["status"] = "published"
    cur["published_at"] = now().isoformat()
    save(cur)
    print(f"published {cur['id']} to site/bulletin/, services.html, and archive")


def send() -> None:
    import os
    from mailchimp_send import send as mc_send

    cur = load()
    if cur["status"] == "sent":
        print("already sent")
        return
    if cur["status"] != "published":
        sys.exit(f"cannot send: status is {cur['status']}")
    state = ROOT / "bulletin" / "state" / cur["id"]
    proof_only = os.environ.get("BULLETIN_DRY_RUN", "true").lower() != "false"
    cid = mc_send(cur["subject"], (state / "email.html").read_text(),
                  (state / "email.txt").read_text(), proof=proof_only)
    cur["status"] = "sent"
    cur["sent_at"] = now().isoformat()
    cur["dry_run"] = proof_only
    save(cur)
    print(f"sent campaign {cid} to "
          + ("the Proof segment (dry run)" if proof_only else "the whole list"))


def remind() -> None:
    from mailchimp_send import send as mc_send

    cur = load()
    if cur["status"] != "proofed":
        print(f"status is {cur['status']}; no reminder needed")
        return
    approve, changes = proof_links.links(cur["id"], cur["rev"])
    html = f"""<div style="font-family:Georgia,serif; background:#170611; color:#f1dccc; padding:30px;">
<p>The bulletin for <strong>{cur['subject']}</strong> is proofed and awaiting your word; it goes nowhere without it.</p>
<p><a href="{approve}" style="color:#e6c780;">Approve</a> &nbsp;·&nbsp; <a href="{changes}" style="color:#e376a3;">Request changes</a></p>
</div>"""
    text = f"The bulletin awaits your approval.\nApprove: {approve}\nRequest changes: {changes}\n"
    cid = mc_send(f"Awaiting approval: {cur['subject']}", html, text, proof=True)
    print(f"reminder campaign {cid} sent to Marc")


if __name__ == "__main__":
    if "--record-approval" in sys.argv:
        i = sys.argv.index("--record-approval")
        record_approval(sys.argv[i + 1], sys.argv[i + 2])
    elif "--publish" in sys.argv:
        publish("--if-due" in sys.argv)
    elif "--send" in sys.argv:
        send()
    elif "--remind" in sys.argv:
        remind()
    else:
        sys.exit("mode required: --record-approval | --publish [--if-due] | --send | --remind")

"""Send a bulletin email through Mailchimp (build order steps 6-7).

Creates a regular campaign, sets our fully designed HTML and plain text,
and sends it — to the Proof segment (Marc alone) with --proof, or to the
whole audience with --list. Configuration comes from
program/data/mailchimp.json; the key from MAILCHIMP_API_KEY.

The From address is shabbat@kzzhv.org (Mailchimp uses one address as both
From and Reply-To; shabbat@ forwards to the secretary's Gmail, so replies
reach the secretary as the brief intends).

Usage:
  python3 program/mailchimp_send.py --proof --subject "..." \
      --html out/email.html --text out/email.txt
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROM_NAME = "Kehillah Kedoshah Zikhron Zvi"
FROM_EMAIL = "shabbat@kzzhv.org"

CFG = json.loads((ROOT / "program" / "data" / "mailchimp.json").read_text())
BASE = f"https://{CFG['server_prefix']}.api.mailchimp.com/3.0"


def _auth() -> str:
    key = os.environ.get("MAILCHIMP_API_KEY", "")
    if not key:
        sys.exit("MAILCHIMP_API_KEY missing")
    return "Basic " + base64.b64encode(f"key:{key}".encode()).decode()


def api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE + path,
        method=method,
        headers={"Authorization": _auth(), "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {}


def _campaign(subject: str, html: str, text: str, recipients: dict,
              title: str, fatal: bool = True) -> str:
    """Create, fill and send one campaign. With fatal=False a failure is
    reported and skipped instead of ending the run — used for Marc's copy,
    which must never cost a family member their letter."""
    def fail(msg: str) -> str:
        if fatal:
            sys.exit(msg)
        print(f"warning: {msg}")
        return ""

    st, camp = api("POST", "/campaigns", {
        "type": "regular",
        "recipients": recipients,
        "settings": {
            "subject_line": subject,
            "title": title,
            "from_name": FROM_NAME,
            "reply_to": FROM_EMAIL,
            "auto_footer": False,
            "inline_css": False,
        },
    })
    if st != 200:
        return fail(f"campaign create failed (HTTP {st}): "
                    f"{camp.get('detail','')} {camp.get('errors','')}")
    cid = camp["id"]

    st, r = api("PUT", f"/campaigns/{cid}/content", {
        "html": html, "plain_text": text,
    })
    if st != 200:
        return fail(f"content upload failed (HTTP {st}): {r.get('detail','')}")

    st, r = api("POST", f"/campaigns/{cid}/actions/send")
    if st != 204:
        return fail(f"send failed (HTTP {st}): "
                    f"{r.get('detail','')} {r.get('errors','')}")
    return cid


def send(subject: str, html: str, text: str, proof: bool,
         segment_key: str | None = None, copy_to_marc: bool = True) -> str:
    """proof=True -> the Proof segment (Marc alone). Otherwise the segment
    named by segment_key ('weekly_segment_id', 'ari_segment_id'); the
    congregational default is the weekly tag segment, and only if no
    weekly segment is configured does a send go to the entire audience.

    Marc's standing instruction (9 September 2026) is to be copied on
    everything that goes out. He carries the Weekly tag, so a
    congregational send already reaches him; only a letter aimed at
    someone else's segment gets a second campaign to the Proof segment.
    The copy carries the same subject he wants to see, and is marked as a
    copy only in the Mailchimp title."""
    recipients: dict = {"list_id": CFG["audience_id"]}
    key = None
    if proof:
        recipients["segment_opts"] = {"saved_segment_id": CFG["proof_segment_id"]}
    else:
        key = segment_key or "weekly_segment_id"
        if key in CFG:
            recipients["segment_opts"] = {"saved_segment_id": CFG[key]}
        elif segment_key:
            sys.exit(f"segment {segment_key} not configured in mailchimp.json")

    cid = _campaign(subject, html, text, recipients,
                    ("PROOF " if proof else "") + subject)

    if (copy_to_marc and not proof and key != "weekly_segment_id"
            and "proof_segment_id" in CFG):
        copy = _campaign(
            subject, html, text,
            {"list_id": CFG["audience_id"],
             "segment_opts": {"saved_segment_id": CFG["proof_segment_id"]}},
            "COPY TO MARC — " + subject, fatal=False)
        print(f"    copy to Marc: {copy}" if copy
              else "    copy to Marc: FAILED (the letter itself went)")
    return cid


if __name__ == "__main__":
    args = sys.argv[1:]

    def val(flag: str) -> str:
        return args[args.index(flag) + 1]

    proof = "--proof" in args
    if not proof and "--list" not in args:
        sys.exit("say --proof (Marc only) or --list (the whole audience)")
    subject = val("--subject")
    html = Path(val("--html")).read_text()
    text = Path(val("--text")).read_text()
    cid = send(subject, html, text, proof)
    print(f"sent campaign {cid} to " + ("the Proof segment (Marc only)" if proof else "THE WHOLE LIST"))

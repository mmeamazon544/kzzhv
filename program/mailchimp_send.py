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


def send(subject: str, html: str, text: str, proof: bool) -> str:
    recipients: dict = {"list_id": CFG["audience_id"]}
    if proof:
        recipients["segment_opts"] = {"saved_segment_id": CFG["proof_segment_id"]}

    st, camp = api("POST", "/campaigns", {
        "type": "regular",
        "recipients": recipients,
        "settings": {
            "subject_line": subject,
            "title": ("PROOF " if proof else "") + subject,
            "from_name": FROM_NAME,
            "reply_to": FROM_EMAIL,
            "auto_footer": False,
            "inline_css": False,
        },
    })
    if st != 200:
        sys.exit(f"campaign create failed (HTTP {st}): {camp.get('detail','')} {camp.get('errors','')}")
    cid = camp["id"]

    st, r = api("PUT", f"/campaigns/{cid}/content", {
        "html": html, "plain_text": text,
    })
    if st != 200:
        sys.exit(f"content upload failed (HTTP {st}): {r.get('detail','')}")

    st, r = api("POST", f"/campaigns/{cid}/actions/send")
    if st != 204:
        sys.exit(f"send failed (HTTP {st}): {r.get('detail','')} {r.get('errors','')}")
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

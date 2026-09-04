"""Mailchimp wiring (build order step 6). Runs in GitHub Actions with
MAILCHIMP_API_KEY; never on Marc's Mac.

Idempotent. Each run:
  1. verifies the API key (ping);
  2. finds the audience (uses the only one; refuses politely if several);
  3. makes sure Marc's address is a member and that a static "Proof"
     segment containing only Marc exists — proof emails go to it;
  4. drives sending-domain verification for kzzhv.org: first run asks
     Mailchimp to mail a verification code to contact@kzzhv.org (which
     forwards to the secretary's Gmail); a later run with --code XXXX
     completes it;
  5. writes program/data/mailchimp.json (server prefix, audience id,
     segment id, domain status — configuration, not secrets) for the
     bulletin workflows.

Usage: python3 program/mailchimp_setup.py [--code XXXXX]
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARC = "mmeamazon544@gmail.com"
DOMAIN = "kzzhv.org"
VERIFY_EMAIL = "contact@kzzhv.org"

KEY = os.environ.get("MAILCHIMP_API_KEY", "")
if not KEY or "-" not in KEY:
    sys.exit("MAILCHIMP_API_KEY missing or malformed")
PREFIX = KEY.rsplit("-", 1)[1]
BASE = f"https://{PREFIX}.api.mailchimp.com/3.0"
AUTH = "Basic " + base64.b64encode(f"key:{KEY}".encode()).decode()


def api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE + path,
        method=method,
        headers={"Authorization": AUTH, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {}


def main() -> None:
    code = ""
    if "--code" in sys.argv:
        code = sys.argv[sys.argv.index("--code") + 1].strip()

    st, ping = api("GET", "/ping")
    if st != 200:
        sys.exit(f"API key rejected (HTTP {st}): {ping.get('detail','')}")
    print("Mailchimp ping OK, server", PREFIX)

    st, lists = api("GET", "/lists?count=100")
    auds = lists.get("lists", [])
    if not auds:
        sys.exit("No audience exists in this Mailchimp account.")
    if len(auds) > 1:
        names = ", ".join(a["name"] for a in auds)
        sys.exit(f"Several audiences exist ({names}); Marc must say which.")
    aud = auds[0]
    print(f"Audience: {aud['name']} (id {aud['id']}, "
          f"{aud['stats']['member_count']} members)")

    # Marc as member (upsert; harmless if already there).
    h = hashlib.md5(MARC.lower().encode()).hexdigest()
    st, _ = api("PUT", f"/lists/{aud['id']}/members/{h}", {
        "email_address": MARC, "status_if_new": "subscribed",
        "merge_fields": {"FNAME": "Marc"},
    })
    print("Marc in audience:", "OK" if st == 200 else f"HTTP {st}")

    # Proof segment containing only Marc.
    st, segs = api("GET", f"/lists/{aud['id']}/segments?type=static&count=100")
    seg = next((s for s in segs.get("segments", []) if s["name"] == "Proof"), None)
    if seg is None:
        st, seg = api("POST", f"/lists/{aud['id']}/segments", {
            "name": "Proof", "static_segment": [MARC],
        })
        if st != 200:
            sys.exit(f"could not create Proof segment (HTTP {st}): {seg}")
        print("Proof segment created")
    else:
        print("Proof segment exists")

    # Tag segments created by Marc's imports: "weekly" (the congregational
    # list) and "ari" (Ari's Friday email). Tags surface as static segments.
    st, segs2 = api("GET", f"/lists/{aud['id']}/segments?type=static&count=200")
    tag_ids = {}
    for s in segs2.get("segments", []):
        if s["name"].lower() in ("weekly", "ari"):
            tag_ids[s["name"].lower()] = s["id"]
            print(f"tag segment '{s['name']}': {s['member_count']} members")
    for want in ("weekly", "ari"):
        if want not in tag_ids:
            print(f"tag segment '{want}' not found yet (import with that tag, then re-run)")

    # Sending-domain verification.
    st, doms = api("GET", "/verified-domains")
    dom = next((d for d in doms.get("domains", [])
                if d.get("domain") == DOMAIN), None)
    if dom and dom.get("verified"):
        domain_status = "verified"
        print(f"{DOMAIN} is verified for sending",
              "and authenticated" if dom.get("authenticated") else
              "(authentication pending: DKIM records)")
        if dom.get("authenticated"):
            domain_status = "authenticated"
    elif dom and code:
        st, r = api("POST", f"/verified-domains/{DOMAIN}/actions/verify",
                    {"code": code})
        if st == 200 and r.get("verified"):
            domain_status = "verified"
            print(f"{DOMAIN} verified with the code.")
        else:
            domain_status = "verification-failed"
            print(f"verification failed (HTTP {st}): {r.get('detail','')}")
    elif dom:
        domain_status = "code-sent"
        print(f"{DOMAIN} already awaiting its code (sent to {VERIFY_EMAIL}; "
              "it forwards to the secretary's Gmail). Re-run with the code.")
    else:
        st, r = api("POST", "/verified-domains",
                    {"verification_email": VERIFY_EMAIL})
        if st in (200, 214):
            domain_status = "code-sent"
            print(f"Verification code sent to {VERIFY_EMAIL} "
                  "(forwards to the secretary's Gmail). Re-run with --code.")
        else:
            domain_status = "error"
            print(f"could not start domain verification (HTTP {st}): "
                  f"{r.get('detail','')}")

    cfg = {
        "server_prefix": PREFIX,
        "audience_id": aud["id"],
        "audience_name": aud["name"],
        "proof_segment_id": seg["id"],
        "domain": DOMAIN,
        "domain_status": domain_status,
    }
    if "weekly" in tag_ids:
        cfg["weekly_segment_id"] = tag_ids["weekly"]
    if "ari" in tag_ids:
        cfg["ari_segment_id"] = tag_ids["ari"]
    out = ROOT / "program" / "data" / "mailchimp.json"
    out.write_text(json.dumps(cfg, indent=1) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()

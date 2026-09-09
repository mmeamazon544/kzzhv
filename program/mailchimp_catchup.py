"""Send the current bulletin to people who joined the list after it went
out — without a second copy landing on everyone who already has it.

Builds (or refreshes) a static Mailchimp segment named "Catchup" from the
addresses in the CATCHUP_EMAILS repository secret, then sends exactly the
bytes already stored under bulletin/state/<id>/ — the same email the list
received, not a rebuild. No address passes through code, workflow inputs,
or logs; only hash prefixes and counts are printed.

  CATCHUP_EMAILS   comma-separated addresses, already subscribed

Refuses while BULLETIN_DRY_RUN is anything but "false", exactly as the
congregational send does. Marc is copied automatically by mailchimp_send.

Usage: python3 program/mailchimp_catchup.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import mailchimp_send
from mailchimp_send import CFG, api, send

ROOT = Path(__file__).resolve().parent.parent
SEGMENT_NAME = "Catchup"


def addresses() -> list[str]:
    """The CATCHUP_EMAILS secret, validated. Never printed."""
    addrs = [a.strip().lower() for a in
             os.environ.get("CATCHUP_EMAILS", "").split(",") if a.strip()]
    if not addrs:
        sys.exit("CATCHUP_EMAILS missing")
    for a in addrs:
        if "@" not in a:
            sys.exit("CATCHUP_EMAILS contains a malformed address")
    return addrs


def ensure_segment(addrs: list[str]) -> str:
    """Build or refresh the static Catchup segment and return its id, after
    proving every address is already a subscribed member and that the
    segment holds exactly them. Refuses rather than sending too widely."""
    lid = CFG["audience_id"]

    # A static segment cannot pull in a stranger, and we must never
    # quietly add one.
    for a in addrs:
        h = hashlib.md5(a.encode()).hexdigest()
        st, r = api("GET", f"/lists/{lid}/members/{h}")
        if st != 200:
            sys.exit(f"{h[:8]}… is not on the audience; add them first")
        if r.get("status") != "subscribed":
            sys.exit(f"{h[:8]}… is {r.get('status')}, not subscribed")
        print(f"  {h[:8]}… subscribed")

    # PATCH with static_segment ADDS to a static segment rather than
    # replacing it, so a reused segment silently keeps the previous run's
    # recipients. Delete it and build it again, which is the only way to
    # guarantee the membership is exactly what was asked for. Deleting a
    # segment does not touch anybody's subscription.
    st, segs = api("GET", f"/lists/{lid}/segments?type=static&count=200")
    for s in segs.get("segments", []):
        if s["name"] == SEGMENT_NAME:
            st, _ = api("DELETE", f"/lists/{lid}/segments/{s['id']}")
            if st not in (200, 204):
                sys.exit(f"could not clear the old {SEGMENT_NAME} segment "
                         f"(HTTP {st})")
            print(f"{SEGMENT_NAME} segment from a previous run deleted")

    st, seg = api("POST", f"/lists/{lid}/segments",
                  {"name": SEGMENT_NAME, "static_segment": addrs})
    if st != 200:
        sys.exit(f"could not create the {SEGMENT_NAME} segment (HTTP {st})")
    print(f"{SEGMENT_NAME} segment created")

    st, r = api("GET", f"/lists/{lid}/segments/{seg['id']}")
    count = r.get("member_count", -1)
    print(f"{SEGMENT_NAME} holds {count} member(s); {len(addrs)} intended")
    if count != len(addrs):
        sys.exit("segment membership does not match the intended addresses; "
                 "refusing to send")
    mailchimp_send.CFG["catchup_segment_id"] = seg["id"]
    return seg["id"]


if __name__ == "__main__":
    if os.environ.get("BULLETIN_DRY_RUN", "true").lower() != "false":
        sys.exit("BULLETIN_DRY_RUN is not false; refusing to send")

    addrs = addresses()
    cur = json.loads((ROOT / "bulletin" / "state" / "current.json").read_text())
    state = ROOT / "bulletin" / "state" / cur["id"]
    html = (state / "email.html").read_text()
    text = (state / "email.txt").read_text()
    print(f"bulletin {cur['id']} — {cur['subject']}")
    print(f"status {cur['status']}, originally sent as campaign "
          f"{cur.get('campaign', '(none recorded)')}")

    ensure_segment(addrs)
    cid = send(cur["subject"], html, text, proof=False,
               segment_key="catchup_segment_id")
    print(f"sent campaign {cid} to the {SEGMENT_NAME} segment "
          f"({len(addrs)} recipient(s))")

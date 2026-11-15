"""Point the Proof segment — the one address that receives every proof,
every "awaiting approval" reminder and Marc's copy of each family letter —
at a different mailbox. No address passes through code, workflow inputs,
or logs (public repository): the new address arrives as the PROOF_ADDRESS
environment variable, set from a repository secret just before the run
and deleted right after, exactly as mailchimp_add.py does.

Marc's order of 15 November 2026: KKZZ business goes to the congregation's
own mailbox, not his personal one, so the proofs move there.

What it does (with --apply; without it, only reports):
  1. upserts the new address into the audience (subscribed) if absent;
  2. adds it to the Proof static segment;
  3. removes every OTHER member from that segment (their audience
     membership and other tags are untouched — a former proof reader who
     is also a congregant still receives the congregational bulletin).

Usage: python3 program/mailchimp_repoint_proof.py [--apply]
"""

from __future__ import annotations

import hashlib
import os
import sys

from mailchimp_send import CFG, api


def who(m: dict) -> str:
    mf = m.get("merge_fields") or {}
    last = (mf.get("LNAME") or "").strip()
    first = (mf.get("FNAME") or "").strip() or "(no first name)"
    return f"{first} {last[:1] + '…(' + str(len(last)) + ')' if last else '(no surname)'}" \
           f" [hash {m['id'][:8]}…]"


def segment_members(lid: str, seg: int) -> list[dict]:
    st, r = api("GET", f"/lists/{lid}/segments/{seg}/members?count=100"
                       f"&fields=members.id,members.merge_fields,members.status")
    if st != 200:
        sys.exit(f"could not list the Proof segment (HTTP {st})")
    return r.get("members", [])


def main() -> None:
    apply = "--apply" in sys.argv
    email = os.environ.get("PROOF_ADDRESS", "").strip()
    if not email or "@" not in email:
        sys.exit("PROOF_ADDRESS missing or malformed")
    lid, seg = CFG["audience_id"], CFG["proof_segment_id"]
    h = hashlib.md5(email.lower().encode()).hexdigest()
    print(f"new proof address: hash {h[:8]}… (address never printed)")

    before = segment_members(lid, seg)
    print(f"Proof segment before: {len(before)} member(s)")
    for m in before:
        print(f"  {who(m)} status={m.get('status')}"
              + ("  <- already the new address" if m["id"] == h else "  <- would be removed"))

    st, rec = api("GET", f"/lists/{lid}/members/{h}?fields=id,status,merge_fields")
    if st == 200:
        print(f"new address is in the audience: status={rec.get('status')}")
        if rec.get("status") not in ("subscribed",):
            sys.exit("the new address is in the audience but not subscribed "
                     f"({rec.get('status')}); Mailchimp will not let the API "
                     "resubscribe it — resubscribe it in Mailchimp first")
    elif st == 404:
        print("new address is not yet in the audience; would be added as subscribed")
    else:
        sys.exit(f"could not read the new address's record (HTTP {st})")

    if not apply:
        print("dry run; nothing changed")
        return

    if st == 404:
        st2, _ = api("PUT", f"/lists/{lid}/members/{h}", {
            "email_address": email, "status_if_new": "subscribed",
            "merge_fields": {"FNAME": "KKZZ", "LNAME": "Proofs"}})
        if st2 != 200:
            sys.exit(f"adding the new address to the audience failed (HTTP {st2})")
        print(f"added to the audience (hash {h[:8]}…), subscribed")

    st3, body = api("POST", f"/lists/{lid}/segments/{seg}/members", {"email_address": email})
    if st3 not in (200, 204):
        sys.exit(f"adding to the Proof segment failed (HTTP {st3}) {body.get('detail', '')}")
    print("added to the Proof segment")

    for m in before:
        if m["id"] == h:
            continue
        st4, body = api("DELETE", f"/lists/{lid}/segments/{seg}/members/{m['id']}")
        print(f"  removed {who(m)} from the Proof segment: HTTP {st4}"
              + ("" if st4 in (200, 204) else f" {body.get('detail', '')}"))

    after = segment_members(lid, seg)
    print(f"Proof segment after: {len(after)} member(s)")
    for m in after:
        print(f"  {who(m)}" + ("  <- the new address" if m["id"] == h else "  <- STILL THERE"))
    if [m["id"] for m in after] != [h]:
        sys.exit("the Proof segment is not exactly the new address; look above")
    print("done: every proof, reminder and family copy now goes to the new mailbox")


if __name__ == "__main__":
    main()

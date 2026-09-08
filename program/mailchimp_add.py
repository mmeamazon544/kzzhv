"""Add (upsert) one member to the audience and tag them — without any
address passing through code, workflow inputs, or logs. The address and
name arrive as environment variables, set from repository secrets by the
mailchimp-add workflow just before a run and deleted right after:

  NEW_MEMBER_EMAIL   the address (required)
  NEW_MEMBER_FNAME   first name (optional)
  NEW_MEMBER_LNAME   last name (optional)
  NEW_MEMBER_TAGS    comma-separated tags, e.g. "weekly,student" (optional)

Companion to mailchimp_untag.py. Prints only hashes, counts, and tag
names — never the address itself.

Usage: python3 program/mailchimp_add.py
"""

from __future__ import annotations

import hashlib
import os
import sys

from mailchimp_send import CFG, api

if __name__ == "__main__":
    email = os.environ.get("NEW_MEMBER_EMAIL", "").strip()
    if not email or "@" not in email:
        sys.exit("NEW_MEMBER_EMAIL missing or malformed")
    fname = os.environ.get("NEW_MEMBER_FNAME", "").strip()
    lname = os.environ.get("NEW_MEMBER_LNAME", "").strip()
    tags = [t.strip() for t in os.environ.get("NEW_MEMBER_TAGS", "").split(",")
            if t.strip()]

    lid = CFG["audience_id"]
    h = hashlib.md5(email.lower().encode()).hexdigest()

    merge = {}
    if fname:
        merge["FNAME"] = fname
    if lname:
        merge["LNAME"] = lname
    body = {"email_address": email, "status_if_new": "subscribed"}
    if merge:
        body["merge_fields"] = merge
    st, _ = api("PUT", f"/lists/{lid}/members/{h}", body)
    if st != 200:
        sys.exit(f"member upsert failed (HTTP {st})")
    print(f"member upserted (hash {h[:8]}…), status subscribed")

    if tags:
        st, _ = api("POST", f"/lists/{lid}/members/{h}/tags", {
            "tags": [{"name": t, "status": "active"} for t in tags],
        })
        if st in (200, 204):
            print("tags applied:", ", ".join(tags))
        else:
            sys.exit(f"tagging failed (HTTP {st})")
    print("done")

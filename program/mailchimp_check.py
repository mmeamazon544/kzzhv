"""Read-only: is this person on the audience, and under which tags? No
address ever passes through code, workflow inputs, or logs — it arrives
in the CHECK_MEMBER_EMAIL repository secret, set just before a run and
deleted right after, and only the hash prefix is printed back.

  CHECK_MEMBER_EMAIL   the address to look up (required)

Companion to mailchimp_add.py and mailchimp_untag.py. Changes nothing.

Usage: python3 program/mailchimp_check.py
"""

from __future__ import annotations

import hashlib
import os
import sys

from mailchimp_send import CFG, api

if __name__ == "__main__":
    email = os.environ.get("CHECK_MEMBER_EMAIL", "").strip()
    if not email or "@" not in email:
        sys.exit("CHECK_MEMBER_EMAIL missing or malformed")

    lid = CFG["audience_id"]
    h = hashlib.md5(email.lower().encode()).hexdigest()
    st, r = api("GET", f"/lists/{lid}/members/{h}")

    if st == 404:
        print(f"NOT ON THE AUDIENCE (hash {h[:8]}…)")
        sys.exit(0)
    if st != 200:
        sys.exit(f"lookup failed (HTTP {st})")

    tags = [t["name"] for t in r.get("tags", [])]
    print(f"ON THE AUDIENCE (hash {h[:8]}…)")
    print("status:", r.get("status", "?"))
    print("tags:", ", ".join(tags) if tags else "(none)")
    print("on the weekly list:",
          "yes" if any(t.lower() == "weekly" for t in tags) else "NO")

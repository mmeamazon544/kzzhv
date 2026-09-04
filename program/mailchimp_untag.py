"""Remove a tag from every member of a tag segment — without any address
passing through code or logs. Example: taking Mom off the congregational
"Weekly" tag while leaving her "mom" tag alone.

Usage: python3 program/mailchimp_untag.py --segment mom --tag Weekly
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mailchimp_send import CFG, api

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    seg_key = sys.argv[sys.argv.index("--segment") + 1] + "_segment_id"
    tag = sys.argv[sys.argv.index("--tag") + 1]
    if seg_key not in CFG:
        sys.exit(f"{seg_key} not in mailchimp.json")
    lid = CFG["audience_id"]
    st, r = api("GET", f"/lists/{lid}/segments/{CFG[seg_key]}/members?count=100")
    if st != 200:
        sys.exit(f"could not list segment members (HTTP {st})")
    n = 0
    for m in r.get("members", []):
        h = m["id"]
        st2, _ = api("POST", f"/lists/{lid}/members/{h}/tags", {
            "tags": [{"name": tag, "status": "inactive"},
                     {"name": tag.lower(), "status": "inactive"},
                     {"name": tag.capitalize(), "status": "inactive"}],
        })
        n += 1
        print(f"member {n}: tag '{tag}' removed" if st2 in (200, 204)
              else f"member {n}: HTTP {st2}")
    print(f"done: {n} member(s) processed")

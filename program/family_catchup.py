"""Send one family member's letter to somebody who is not on that
member's tag segment — a partner added later, a household that joined
mid-season — without a second copy landing on whoever already has it.

Builds the same static "Catchup" segment mailchimp_catchup.py uses, from
the CATCHUP_EMAILS secret, then builds FAMILY_MEMBER's letter exactly as
the Friday run would (their city's times, their sponsor and love lines,
the approved bulletin's teachings) and sends it there instead of to their
tag segment. No address passes through code, inputs, or logs.

  CATCHUP_EMAILS   comma-separated addresses, already subscribed
  FAMILY_MEMBER    ari | misha | gabi | mom
  CATCHUP_SHABBAT  optional YYYY-MM-DD; empty = the coming Saturday

Marc is copied automatically by mailchimp_send.

Usage: python3 program/family_catchup.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import family
from mailchimp_catchup import addresses, ensure_segment

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    member = os.environ.get("FAMILY_MEMBER", "").strip().lower()
    if member not in family.FAMILY:
        sys.exit(f"FAMILY_MEMBER must be one of {', '.join(family.FAMILY)}")

    when = os.environ.get("CATCHUP_SHABBAT", "").strip()
    sat = date.fromisoformat(when) if when else family.next_saturday()

    addrs = addresses()
    print(f"{member}'s letter for Shabbat {sat}, to {len(addrs)} address(es)")

    sid = ensure_segment(addrs)

    # build_and_send re-reads mailchimp.json from disk and refuses a
    # segment key it cannot find there, so the new segment has to be
    # visible in the file as well as in memory. This is the runner's
    # ephemeral checkout; nothing is committed.
    cfg_path = ROOT / "program" / "data" / "mailchimp.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["catchup_segment_id"] = sid
    cfg_path.write_text(json.dumps(cfg, indent=1) + "\n")

    # Send this one letter to the Catchup segment instead of the member's
    # own tag segment, so the person who already had it is not mailed twice.
    family.FAMILY[member]["segment_key"] = "catchup_segment_id"
    family.build_and_send(member, sat, proof=False)

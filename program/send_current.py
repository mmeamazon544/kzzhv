"""Send the current bulletin's stored email again — to the weekly list
(--list) or to the Proof segment (--proof). Sends exactly the bytes in
bulletin/state/<id>/; drafts nothing.

The --list mode refuses to run while BULLETIN_DRY_RUN is anything but
"false", so nothing reaches the congregation before Marc ends the dry run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mailchimp_send import send

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    proof = "--proof" in sys.argv
    if not proof and "--list" not in sys.argv:
        sys.exit("say --proof or --list")
    if not proof and os.environ.get("BULLETIN_DRY_RUN", "true").lower() != "false":
        sys.exit("BULLETIN_DRY_RUN is not 'false'; refusing to mail the list")
    cur = json.loads((ROOT / "bulletin" / "state" / "current.json").read_text())
    state = ROOT / "bulletin" / "state" / cur["id"]
    cid = send(cur["subject"], (state / "email.html").read_text(),
               (state / "email.txt").read_text(), proof=proof)
    print(f"sent campaign {cid} ({cur['subject']}) to "
          + ("Marc only" if proof else "the weekly list"))

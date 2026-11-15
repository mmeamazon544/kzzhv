"""Make a family member's letter their ONLY mailing: take every member of
that family segment off the congregational Weekly segment — the tag in
every casing, and the static membership itself — leaving their own tag
alone. No address passes through code or logs (public repository).

Marc's order of 15 November 2026: Joy Schwartz (the Mom letter's one
recipient) comes off the communal list and receives her own letter every
Shabbat and holiday.

Usage: python3 program/mailchimp_private.py --segment mom [--apply]
Without --apply it only reports who would change.
"""

from __future__ import annotations

import sys

from mailchimp_send import CFG, api

TAG_CASINGS = ("weekly", "Weekly", "WEEKLY")


def who(m: dict) -> str:
    mf = m.get("merge_fields") or {}
    last = (mf.get("LNAME") or "").strip()
    return f"{(mf.get('FNAME') or '').strip() or '(no first name)'} " \
           f"{last[:1] + '…(' + str(len(last)) + ')' if last else '(no surname)'}"


def main() -> None:
    seg_key = sys.argv[sys.argv.index("--segment") + 1] + "_segment_id"
    apply = "--apply" in sys.argv
    if seg_key not in CFG or "weekly_segment_id" not in CFG:
        sys.exit(f"{seg_key} or weekly_segment_id missing from mailchimp.json")
    lid, wk = CFG["audience_id"], CFG["weekly_segment_id"]

    st, r = api("GET", f"/lists/{lid}/segments/{CFG[seg_key]}/members?count=100"
                       f"&fields=members.id,members.merge_fields")
    if st != 200:
        sys.exit(f"could not list the family segment (HTTP {st})")
    fam = r.get("members", [])
    st, r = api("GET", f"/lists/{lid}/segments/{wk}/members?count=300&fields=members.id")
    if st != 200:
        sys.exit(f"could not list the weekly segment (HTTP {st})")
    weekly_ids = {m["id"] for m in r.get("members", [])}
    print(f"weekly segment before: {len(weekly_ids)} members")

    for m in fam:
        h = m["id"]
        on = h in weekly_ids
        print(f"{who(m)}: {'ON' if on else 'not on'} the weekly segment"
              + ("" if apply else " (dry run; nothing changed)"))
        if not apply:
            continue
        st2, _ = api("POST", f"/lists/{lid}/members/{h}/tags", {
            "tags": [{"name": t, "status": "inactive"} for t in TAG_CASINGS]})
        print(f"  weekly tag removed: HTTP {st2}")
        if on:
            st3, body = api("DELETE", f"/lists/{lid}/segments/{wk}/members/{h}")
            print(f"  removed from the weekly segment: HTTP {st3}"
                  + ("" if st3 in (200, 204) else f" {body.get('detail', '')}"))

    if apply:
        st, r = api("GET", f"/lists/{lid}/segments/{wk}/members?count=300&fields=members.id")
        after = {m["id"] for m in r.get("members", [])} if st == 200 else set()
        print(f"weekly segment after: {len(after)} members")
        still = [who(m) for m in fam if m["id"] in after]
        print("still on the weekly segment: " + (", ".join(still) if still else "none of them"))


if __name__ == "__main__":
    main()

"""Read-only list report (Marc's question of 9 September 2026: does he
himself receive what the congregation and the family receive?).

Prints the audience total, each configured segment's size, and whether
Marc is inside it. NO ADDRESS IS EVER PRINTED: this repo is public and so
are its workflow logs, and the congregation's addresses stay private
(the brief's rule). Marc is identified as the sole member of the Proof
segment, so his address is read but never shown.

Sends nothing; changes nothing.

Usage: python3 program/list_check.py
"""

from __future__ import annotations

from mailchimp_send import CFG, api

SEGMENT_KEYS = ("weekly_segment_id", "ari_segment_id", "misha_segment_id",
                "gabi_segment_id", "mom_segment_id")


def get(path: str) -> dict:
    status, body = api("GET", path)
    if status >= 400:
        raise RuntimeError(f"{status}: {body.get('detail', body)}")
    return body


def members_of(aid: str, sid: str) -> set[str]:
    body = get(f"/lists/{aid}/segments/{sid}/members?count=500")
    return {m["email_address"].lower() for m in body.get("members", [])}


def main() -> None:
    aid = CFG["audience_id"]
    info = get(f"/lists/{aid}")
    print(f"audience {info['name']}: {info['stats']['member_count']} subscribed, "
          f"{info['stats']['unsubscribe_count']} unsubscribed")

    marc = members_of(aid, CFG["proof_segment_id"])
    print(f"proof segment: {len(marc)} member(s) — this is Marc")

    for key in SEGMENT_KEYS:
        sid = CFG.get(key)
        if not sid:
            print(f"{key}: not configured")
            continue
        try:
            seg = get(f"/lists/{aid}/segments/{sid}")
            addrs = members_of(aid, sid)
        except RuntimeError as e:
            print(f"{key}: {e}")
            continue
        inside = "yes" if marc & addrs else "no"
        print(f"{key} ({seg['name']}): {seg['member_count']} member(s); "
              f"includes Marc: {inside}")


if __name__ == "__main__":
    main()

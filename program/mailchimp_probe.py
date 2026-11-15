"""Read-only probe of the Mailchimp responses the Desk relies on.

The Desk (netlify/functions/private.mjs) reads campaigns, each campaign's
sent-to report, and the members of the "student" tag. This runs the same
requests where the key already lives (GitHub Actions) and prints the SHAPE
of what comes back — field names, counts, segment ids, first names — so a
mistaken field name shows up here rather than as an empty table on the
Desk. NO ADDRESS IS EVER PRINTED (public repo, public logs): a surname
appears only as its initial and length. Sends and changes nothing.

Usage: python3 program/mailchimp_probe.py
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from mailchimp_send import CFG, api


def get(path: str) -> dict:
    status, body = api("GET", path)
    if status >= 400:
        raise RuntimeError(f"{status}: {body.get('detail', body)}")
    return body


def who(m: dict) -> str:
    """A member as 'First S…(8) tags=[...]' — never the address."""
    mf = m.get("merge_fields") or {}
    first = (mf.get("FNAME") or "").strip()
    last = (mf.get("LNAME") or "").strip()
    last_hint = f"{last[:1]}…({len(last)})" if last else "(no surname)"
    tags = sorted(t.get("name", "") for t in (m.get("tags") or []))
    return f"{first or '(no first name)'} {last_hint} tags={tags} status={m.get('status')}"


def members(seg_id: int) -> list[dict]:
    r = get(f"/lists/{CFG['audience_id']}/segments/{seg_id}/members?count=300"
            f"&fields=members.email_address,members.merge_fields,members.tags,members.status")
    return r.get("members", [])


def main() -> None:
    aid = CFG["audience_id"]
    since = (datetime.now(timezone.utc) - timedelta(days=63)).isoformat()
    fields = ",".join([
        "campaigns.id", "campaigns.send_time", "campaigns.emails_sent",
        "campaigns.settings.subject_line", "campaigns.settings.title",
        "campaigns.recipients.segment_opts.saved_segment_id",
    ])
    camps = get(f"/campaigns?list_id={aid}&status=sent&since_send_time={urllib.parse.quote(since)}"
                f"&count=300&sort_field=send_time&sort_dir=DESC&fields={fields}")
    items = camps.get("campaigns", [])
    print(f"campaigns sent in the last 63 days: {len(items)}")
    names = {CFG.get("proof_segment_id"): "proof", CFG.get("weekly_segment_id"): "weekly"}
    for m in ("ari", "misha", "gabi", "mom"):
        names[CFG.get(f"{m}_segment_id")] = m
    latest: dict[str, dict] = {}
    for c in items:
        seg = (c.get("recipients") or {}).get("segment_opts", {}).get("saved_segment_id")
        kind = names.get(seg, f"other({seg})")
        latest.setdefault(kind, c)
    for kind, c in latest.items():
        print(f"  latest {kind:<12} {c['send_time'][:16]}  sent={c.get('emails_sent')}  "
              f"title={c['settings'].get('title','')[:40]!r}")

    for kind in ("weekly", "ari", "misha", "gabi", "mom"):
        c = latest.get(kind)
        if not c:
            print(f"{kind}: no campaign in range")
            continue
        r = get(f"/reports/{c['id']}/sent-to?count=300"
                f"&fields=sent_to.email_address,sent_to.merge_fields,sent_to.status")
        rows = r.get("sent_to", [])
        first = sorted({(x.get("merge_fields") or {}).get("FNAME", "") for x in rows})
        print(f"{kind}: sent-to rows={len(rows)}; keys={sorted(rows[0].keys()) if rows else '-'}; "
              f"first names={first[:12]}")

    # The segments themselves: how each is defined, and who the family
    # segments hold (first name, surname initial, tags).
    for kind in ("weekly", "ari", "misha", "gabi", "mom"):
        sid = CFG.get(f"{kind}_segment_id")
        if not sid:
            continue
        s = get(f"/lists/{aid}/segments/{sid}")
        print(f"segment {kind}: id={sid} type={s.get('type')} members={s.get('member_count')} "
              f"options={s.get('options')}")
    family_first = set()
    for kind in ("ari", "misha", "gabi", "mom"):
        sid = CFG.get(f"{kind}_segment_id")
        if not sid:
            continue
        for m in members(sid):
            family_first.add(((m.get("merge_fields") or {}).get("FNAME") or "").strip().lower())
            print(f"  {kind} member: {who(m)}")
    wk = CFG.get("weekly_segment_id")
    if wk:
        rows = members(wk)
        print(f"weekly segment members: {len(rows)}")
        for m in rows:
            f = ((m.get("merge_fields") or {}).get("FNAME") or "").strip().lower()
            if f and f in family_first:
                print(f"  weekly member sharing a family first name: {who(m)}")

    ts = get(f"/lists/{aid}/tag-search?name=student")
    tags = ts.get("tags", [])
    print(f"tag-search 'student': {[(t.get('id'), t.get('name')) for t in tags]}")
    tag = next((t for t in tags if str(t.get("name", "")).lower() == "student"), None)
    if tag:
        rows = members(tag["id"])
        print(f"students: {len(rows)}; first names="
              f"{sorted((x.get('merge_fields') or {}).get('FNAME','') for x in rows)}")


if __name__ == "__main__":
    main()

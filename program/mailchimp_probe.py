"""Read-only probe of the Mailchimp responses the Desk relies on.

The Desk (netlify/functions/private.mjs) reads campaigns, each campaign's
sent-to report, and the members of the "student" tag. This runs the same
requests where the key already lives (GitHub Actions) and prints the SHAPE
of what comes back — field names, counts, segment ids, first names — so a
mistaken field name shows up here rather than as an empty table on the
Desk. NO ADDRESS IS EVER PRINTED (public repo, public logs). Sends and
changes nothing.

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
        print(f"  {c['send_time'][:16]}  {kind:<12} sent={c.get('emails_sent')}  "
              f"title={c['settings'].get('title','')[:40]!r}")
        latest.setdefault(kind, c)

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

    ts = get(f"/lists/{aid}/tag-search?name=student")
    tags = ts.get("tags", [])
    print(f"tag-search 'student': {[(t.get('id'), t.get('name')) for t in tags]}")
    tag = next((t for t in tags if str(t.get("name", "")).lower() == "student"), None)
    if tag:
        mem = get(f"/lists/{aid}/segments/{tag['id']}/members?count=300"
                  f"&fields=members.email_address,members.merge_fields")
        rows = mem.get("members", [])
        print(f"students: {len(rows)}; first names="
              f"{sorted((x.get('merge_fields') or {}).get('FNAME','') for x in rows)}")


if __name__ == "__main__":
    main()

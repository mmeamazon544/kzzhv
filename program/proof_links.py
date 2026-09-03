"""Signed approval links (build order step 7).

Must mirror netlify/functions/common.mjs exactly: the token is the first
32 hex chars of HMAC-SHA256("link.<id>.<rev>") keyed with
PRIVATE_PAGE_PASSWORD, which lives as a GitHub secret here and a Netlify
environment variable there.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import urllib.parse

SITE = "https://kzzhv.org"


def _secret() -> bytes:
    s = os.environ.get("PRIVATE_PAGE_PASSWORD", "")
    if not s:
        raise RuntimeError("PRIVATE_PAGE_PASSWORD missing")
    return s.encode()


def token(bulletin_id: str, rev: str) -> str:
    msg = f"link.{bulletin_id}.{rev}".encode()
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()[:32]


def links(bulletin_id: str, rev: str) -> tuple[str, str]:
    q = urllib.parse.urlencode({"id": bulletin_id, "rev": rev, "sig": token(bulletin_id, rev)})
    return f"{SITE}/approve?{q}", f"{SITE}/changes?{q}"

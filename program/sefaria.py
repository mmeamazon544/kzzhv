"""Sefaria client for the teachings pipeline (build order step 4).

Its one job that matters: verification. Per bulletin/sources.md, before a
teaching goes into a proof every citation in it is checked against
Sefaria's catalogue; a reference that does not resolve to an actual
passage is discarded and the teaching redrafted. Only sources that exist
may be cited.

Also enforces the exclusion list: nothing from the Chabad literature is
read or cited, and Sefaria's "Keter Shem Tov" (the Baal Shem Tov
anthology) is excluded by name so it can never be confused with Shem Tob
Gaguine's Keter Shem Tob, which is not on Sefaria at all.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.sefaria.org/api"

# Works that may never be cited or read (bulletin/sources.md). Matched
# case-insensitively against the start of the canonical book title.
EXCLUDED_TITLES = (
    "Tanya",
    "Likkutei Amarim",
    "Shulchan Arukh HaRav",
    "Shulchan Aruch HaRav",
    "Hayom Yom",
    "Keter Shem Tov",          # the Baal Shem Tov anthology (Kehot), NOT Gaguine
    "Torah Or",                # Shneur Zalman of Liadi
    "Likkutei Torah",          # ambiguous: Chabad classic; excluded to be safe
    "Derech Mitzvosecha",
    "Sefer HaMaamarim",
    "Igrot Kodesh",
    "Likkutei Sichot",
)


def _get(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": "kzzhv-bulletin/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def is_excluded(title_or_ref: str) -> bool:
    t = title_or_ref.strip().lower()
    return any(t.startswith(x.lower()) for x in EXCLUDED_TITLES)


def verify_ref(ref: str) -> dict:
    """Check one citation against Sefaria.

    Returns {"ok": bool, "ref": canonical ref, "url": Sefaria link,
    "reason": why not, "excluded": bool}. ok is True only when Sefaria
    resolves the reference to an actual passage with text in it and the
    work is not on the exclusion list.
    """
    ref = ref.strip()
    if is_excluded(ref):
        return {"ok": False, "excluded": True, "ref": ref,
                "reason": "work is on the exclusion list"}
    enc = urllib.parse.quote(ref.replace(" ", "_"), safe="_,.:()'-")
    j = _get(f"{API}/v3/texts/{enc}?return_format=text_only")
    if not j or "versions" not in j:
        # Second chance: ask the name resolver whether Sefaria recognizes
        # this as a reference under a canonical form.
        n = _get(f"{API}/name/{urllib.parse.quote(ref)}")
        if n and n.get("is_ref") and n.get("ref"):
            canon = n["ref"]
            if is_excluded(canon):
                return {"ok": False, "excluded": True, "ref": canon,
                        "reason": "work is on the exclusion list"}
            enc = urllib.parse.quote(canon.replace(" ", "_"), safe="_,.:()'-")
            j = _get(f"{API}/v3/texts/{enc}?return_format=text_only")
        if not j or "versions" not in j:
            return {"ok": False, "excluded": False, "ref": ref,
                    "reason": "does not resolve on Sefaria"}
    canonical = j.get("ref") or ref
    if is_excluded(j.get("indexTitle") or canonical):
        return {"ok": False, "excluded": True, "ref": canonical,
                "reason": "work is on the exclusion list"}
    versions = j.get("versions") or []
    has_text = False
    for v in versions:
        t = v.get("text")
        if (isinstance(t, str) and t.strip()) or (isinstance(t, list) and any(
                s.strip() if isinstance(s, str) else s for s in t)):
            has_text = True
            break
    if not has_text:
        return {"ok": False, "excluded": False, "ref": canonical,
                "reason": "resolves but contains no text (likely out of range)"}
    url = "https://www.sefaria.org/" + urllib.parse.quote(
        canonical.replace(" ", "."), safe=".:,-()'"
    )
    return {"ok": True, "excluded": False, "ref": canonical, "url": url,
            "reason": ""}


def fetch_text(ref: str, max_chars: int = 4000) -> str | None:
    """English (or fallback) text of a passage, for the drafting model to
    read. None when the reference does not verify."""
    v = verify_ref(ref)
    if not v["ok"]:
        return None
    enc = urllib.parse.quote(v["ref"].replace(" ", "_"), safe="_,.:()'-")
    j = _get(f"{API}/v3/texts/{enc}?return_format=text_only&version=english")
    if not j:
        j = _get(f"{API}/v3/texts/{enc}?return_format=text_only")
    if not j:
        return None
    for ver in j.get("versions") or []:
        t = ver.get("text")
        if isinstance(t, list):
            t = " ".join(s for s in t if isinstance(s, str))
        if isinstance(t, str) and t.strip():
            return t.strip()[:max_chars]
    return None


if __name__ == "__main__":
    tests = [
        "Deuteronomy 30:19",
        "Mishneh Torah, Sabbath 29:1",
        "Mishneh Torah, Repentance 2:4",
        "Zohar 1:15a",
        "Sefat Emet, Deuteronomy, Nitzavim 1:1",
        "Tanya, Part I 1",                      # must be refused: excluded
        "Keter Shem Tov 1",                     # must be refused: excluded
        "Mishneh Torah, Sabbath 99:1",          # must fail: out of range
        "Book of Imaginary Sources 3:2",        # must fail: nonexistent
    ]
    for t in tests:
        v = verify_ref(t)
        mark = "OK " if v["ok"] else ("EXCL" if v["excluded"] else "NO ")
        print(f"{mark} {t}  ->  {v.get('ref')}  {v.get('reason','')}")

"""Keter Shem Tob (Shem Tob Gaguine, 7 vols, 1934-1981) retrieval.

ketershemtob.com carries no text, only an English topical index per volume
(cached in program/data/kst-index/). The volumes themselves are scanned on
HebrewBooks.org. This module parses the index, finds entries bearing on a
topic, and fetches the scanned pages as single-page PDFs so the drafting
model can read the Hebrew and cite by volume, page, and se'if.

Print-page to scan-page offsets differ per volume (front matter, and vols
I-II share one scan); discovered offsets are cached in
program/data/kst-offsets.json. Discovery itself needs a vision call, so it
is injected by the caller (see teachings.py).

Volumes IV and V are not yet located on HebrewBooks ("find IV and V" in
the brief); entries from them can be cited only once they are found.
"""

from __future__ import annotations

import html as htmllib
import json
import re
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

# HebrewBooks scan ids per the brief; vols I-II share one scan.
HB_IDS = {1: 14392, 2: 14392, 3: 14390, 6: 14391, 7: 14389}

# Starting guesses for print->scan page offset, refined by probing.
# Vols I-II are paginated continuously and share one scan, so they live in
# the same offset space.
OFFSET_GUESS = {1: 30, 2: 30, 3: 20, 6: 20, 7: 20}

OFFSETS_FILE = DATA / "kst-offsets.json"

_PAGES_RE = re.compile(
    r"Pages?\s+(\d+)\s*(?:-\s*(\d+))?\s*,?\s*in\s+(\d+)", re.I
)


def _ols(seg: str) -> list[list[str]]:
    """All <ol> blocks in an HTML segment, as lists of item texts."""
    out = []
    for m in re.finditer(r"<ol>(.*?)</ol>", seg, re.S):
        items = [
            htmllib.unescape(re.sub(r"<[^>]+>", " ", li)).replace("\xa0", " ").strip()
            for li in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)
        ]
        out.append(items)
    return out


def parse_index(vol: int) -> list[dict]:
    """Entries of one volume's topical index:
    {"vol", "section", "topic", "page_from", "page_to", "seifim"}."""
    raw = (DATA / "kst-index" / f"volume{vol}.html").read_text(
        encoding="utf-8", errors="replace"
    )
    entries = []
    # Split on section headings; pair consecutive <ol>s (topics, pages).
    parts = re.split(r'<h2 class="wsite-content-title"[^>]*>(.*?)</h2>', raw)
    for i in range(1, len(parts), 2):
        section = htmllib.unescape(re.sub(r"<[^>]+>", "", parts[i])).strip()
        ols = _ols(parts[i + 1])
        j = 0
        while j + 1 < len(ols):
            topics, pages = ols[j], ols[j + 1]
            if not pages or not _PAGES_RE.search(pages[0] or ""):
                j += 1
                continue
            for topic, page in zip(topics, pages):
                m = _PAGES_RE.search(page)
                if not m or not topic:
                    continue
                a = int(m.group(1))
                b = int(m.group(2) or m.group(1))
                entries.append({
                    "vol": vol, "section": section, "topic": topic,
                    "page_from": a, "page_to": b, "seifim": int(m.group(3)),
                })
            j += 2
    return entries


def all_entries() -> list[dict]:
    out = []
    for vol in range(1, 8):
        if (DATA / "kst-index" / f"volume{vol}.html").exists():
            out += parse_index(vol)
    return out


def search(terms: list[str], only_scanned: bool = True) -> list[dict]:
    """Entries whose topic or section matches any term (case-insensitive
    substring), best matches first; only_scanned keeps volumes we can read."""
    scored = []
    for e in all_entries():
        if only_scanned and e["vol"] not in HB_IDS:
            continue
        hay = (e["topic"] + " " + e["section"]).lower()
        score = sum(1 for t in terms if t.lower().strip() and t.lower() in hay)
        if score:
            scored.append((score, len(e["topic"]), e))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [e for _s, _l, e in scored]


def fetch_page_pdf(vol: int, scan_page: int) -> bytes | None:
    hb = HB_IDS.get(vol)
    if not hb:
        return None
    url = f"https://beta.hebrewbooks.org/pagefeed/hebrewbooks_org_{hb}_{scan_page}.pdf"
    req = urllib.request.Request(url, headers={"User-Agent": "kzzhv-bulletin/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        return data if data[:4] == b"%PDF" else None
    except Exception:
        return None


def load_offsets() -> dict[str, int]:
    if OFFSETS_FILE.exists():
        return json.loads(OFFSETS_FILE.read_text())
    return {}


def save_offset(vol: int, offset: int) -> None:
    offs = load_offsets()
    offs[str(vol)] = offset
    OFFSETS_FILE.write_text(json.dumps(offs, indent=1) + "\n")


def find_offset(vol: int, probe_print_page: int, read_page_number) -> int | None:
    """Determine scan = print + offset for a volume. read_page_number is a
    callable (pdf_bytes) -> int | None returning the printed page number
    seen on the scan (vision, injected by the caller). Cached."""
    offs = load_offsets()
    if str(vol) in offs:
        return offs[str(vol)]
    offset = OFFSET_GUESS.get(vol, 20)
    for _ in range(5):
        pdf = fetch_page_pdf(vol, probe_print_page + offset)
        if pdf is None:
            offset -= 10
            continue
        printed = read_page_number(pdf)
        if printed is None:
            offset += 2
            continue
        if printed == probe_print_page:
            save_offset(vol, offset)
            return offset
        offset += probe_print_page - printed
    return None


if __name__ == "__main__":
    es = all_entries()
    print(len(es), "index entries across volumes",
          sorted({e['vol'] for e in es}))
    for e in search(["habdala"])[:3]:
        print(e)
    for e in search(["selihot", "rosh hashana"])[:5]:
        print(e)

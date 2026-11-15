"""Rabbi Joseph Dweck's parasha podcast (Marc's direction, 15 November 2026):
under the Torah portion summary, point the reader at the week's episode.

The show is "The Parasha with Rabbi Dweck". Marc gave its Spotify page;
the episodes come from the show's own RSS feed, so nothing here is
guessed — an episode is cited only when its title names this week's
parasha. When no episode names it, the line still goes out but points at
the show itself rather than inventing a citation.

The feed is read live at build time (seconds, and the proof already
spends minutes on Hebcal and Sefaria); program/data/dweck-index.json is
the fallback when the network is unavailable. Nothing here writes during
a bulletin build — the cache is refreshed by its own workflow, so a
proof run never leaves the tree dirty.

Usage: python3 program/dweck.py --refresh     rewrite the cached index
       python3 program/dweck.py <parasha>     show what would be cited
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "program" / "data" / "dweck-index.json"
FEED = "https://anchor.fm/s/c6240efc/podcast/rss"
SHOW = "https://open.spotify.com/show/4K5FOrrlOXRepm29ENnj1S"
RABBI = "Rabbi Joseph Dweck"


def skeleton(name: str) -> str:
    """A transliteration-blind key. The congregation and Rabbi Dweck both
    write Sephardic, but not identically (Nitzavim / Nitsabim, Hukkat /
    Hukat), so collapse the ways one Hebrew name is spelled in Latin
    letters: digraphs to one sound, bet/vet together, tsadi one way,
    doubled letters single."""
    s = name.lower()
    s = re.sub(r"[^a-z]", "", s)
    for a, b in (("tz", "s"), ("ts", "s"), ("ch", "h"), ("kh", "h"),
                 ("sh", "\x01"), ("z", "s"), ("v", "b"), ("w", "b"),
                 ("q", "k"), ("c", "k")):
        s = s.replace(a, b)
    s = s.replace("\x01", "sh")
    s = re.sub(r"(.)\1+", r"\1", s)
    # A final heh is silent: the congregation writes Terumah where the
    # show writes Teruma.
    return re.sub(r"h$", "", s) or s


YEAR = re.compile(r"\b(5\d{3}|20\d\d)\b")


def split_title(title: str) -> tuple[str, str, bool, bool]:
    """(headline, parasha-part, is-haftarah, separated) for the show's
    title shapes: "Headline | Parasha 2026", "Parasha 2026 - Headline",
    and the unpunctuated ones, where the whole title has to serve."""
    t = " ".join(title.split())
    split = True
    if "|" in t:
        head, _, tail = t.rpartition("|")
    elif " - " in t:
        tail, _, head = t.partition(" - ")
    else:
        head, tail = t, t
        split = False
    tail = YEAR.sub("", tail).strip(" -–—|")
    head = YEAR.sub("", head).strip(" -–—|")
    haftarah = bool(re.match(r"haftar", tail.strip(), re.I))
    tail = re.sub(r"^haftara?t?\s+", "", tail.strip(), flags=re.I)
    return head or t, tail, haftarah, split


def spans(text: str) -> set[str]:
    """Every one- and two-word run in a title fragment, as skeletons: the
    show joins double portions with a hyphen ("Nitsabim-Vayelekh"), a
    space ("Matot Mas'ei"), or nothing at all, and hangs special Shabbatot
    off the same field ("Tsav-Shabbat HaGadol")."""
    words = [w for w in re.split(r"[^A-Za-z']+", text) if w]
    out = {skeleton(w) for w in words}
    out |= {skeleton(words[i] + words[i + 1]) for i in range(len(words) - 1)}
    out.discard("")
    return out


def consonants(key: str) -> str:
    """A vowel-blind key, the last resort: the show writes Vayelekh where
    the congregation writes Vayeilech, Pekude where it writes Pekudei."""
    return re.sub(r"[aeiou]", "", key)


NUTSHELL = re.compile(r"in a nutshell", re.I)


def parse(xml_bytes: bytes) -> list[dict]:
    ch = ET.fromstring(xml_bytes).find("channel")
    out = []
    for it in ch.findall("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        head, parasha, haft, split = split_title(title)
        try:
            when = parsedate_to_datetime(it.findtext("pubDate") or "")
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except Exception:
            when = datetime.min.replace(tzinfo=timezone.utc)
        out.append({"title": title, "headline": head, "parasha": parasha,
                    "haftarah": haft, "link": link, "published": when.isoformat(),
                    "spans": sorted(spans(parasha)),
                    # A title the show did not punctuate gives no clean
                    # parasha field, so only an exact name may match it.
                    "loose": not split,
                    "nutshell": bool(NUTSHELL.search(title))})
    return out


def fetch(timeout: int = 20) -> list[dict] | None:
    try:
        req = urllib.request.Request(FEED, headers={"User-Agent": "kzzhv-bulletin/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse(r.read())
    except Exception as e:
        print(f"dweck: live feed unavailable ({e}); using the cached index",
              file=sys.stderr)
        return None


_CACHED: list[dict] | None = None


def episodes() -> list[dict]:
    global _CACHED
    if _CACHED is not None:
        return _CACHED
    _CACHED = _load()
    return _CACHED


def _load() -> list[dict]:
    live = fetch()
    if live:
        return live
    if CACHE.exists():
        return json.loads(CACHE.read_text())["episodes"]
    return []


def episode_for(parashah: str, eps: list[dict] | None = None) -> dict | None:
    """The episode on this parasha, or None when the show has none —
    never a near-miss. Haftarah episodes are not offered as discussion of
    the portion, and a full episode is preferred to a Nutshell summary."""
    if not parashah:
        return None
    eps = [e for e in (episodes() if eps is None else eps) if not e["haftarah"]]
    wanted = skeleton(parashah)
    halves = [skeleton(p) for p in re.split(r"[-–—]", parashah) if p.strip()]
    words = parashah.split()
    first = skeleton(words[0]) if len(words) > 1 else ""
    tiers = (
        lambda e: wanted in e["spans"],
        lambda e: len(halves) > 1 and any(h in e["spans"] for h in halves),
        lambda e: (not e["loose"]) and consonants(wanted) in
                  {consonants(s) for s in e["spans"]},
        # Last resort: a two-word portion named by its distinctive first
        # word alone (Shelah, for Shelah Lekha). Short first words are
        # never distinctive enough to risk it — "Ki" would drag in both
        # Ki Tabo and Ki Tetse.
        lambda e: len(first) >= 5 and first in e["spans"],
    )
    for hit in tiers:
        found = [e for e in eps if hit(e)]
        if found:
            return max(found, key=lambda e: (not e["nutshell"], e["published"]))
    return None


LEAD = "For further discussion of the Parasha, listen to "


def citation(parashah: str) -> dict | None:
    """The pieces of Marc's line (his direction, 15 November 2026): lead
    text, the words to link, and where they point. None when there is no
    parasha at all — a festival bulletin carries no portion of the week.

    When the show has an episode on this parasha it is named and linked;
    when it has none, the line still stands and points at the show, which
    is the truth rather than a citation that does not exist."""
    if not parashah:
        return None
    e = episode_for(parashah)
    if e:
        return {"lead": LEAD + RABBI + ": ", "label": e["headline"],
                "url": e["link"], "episode": e["title"]}
    return {"lead": LEAD, "label": RABBI, "url": SHOW, "episode": None}


def refresh() -> None:
    eps = fetch(timeout=60)
    if not eps:
        sys.exit("could not fetch the feed; cache left as it was")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(
        {"show": SHOW, "feed": FEED, "refreshed": datetime.now(timezone.utc).isoformat(),
         "episodes": eps}, indent=1, ensure_ascii=False) + "\n")
    print(f"cached {len(eps)} episodes to {CACHE.relative_to(ROOT)}")


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    else:
        name = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
        e = episode_for(name)
        print(f"{name}: {e['title'] if e else 'no episode — would link the show'}")
        if e:
            print("  headline:", e["headline"])
            print("  link:", e["link"])

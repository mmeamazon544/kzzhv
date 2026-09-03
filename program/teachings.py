"""The teachings pipeline (build order step 4).

Drafts the week's two teachings with the Claude API from bulletin/voice.md
and bulletin/sources.md, with the guarantee against invented sources:

  1. PLAN    — the model chooses a halakhic and an aggadic topic arising
               from the week, Sefaria references to read, and Keter Shem
               Tob index entries to consult.
  2. GATHER  — every planned Sefaria reference is verified against
               Sefaria's catalogue and its text fetched; KST scan pages
               are fetched from HebrewBooks (offsets probed by vision).
  3. DRAFT   — the model writes both teachings READING ONLY the gathered
               material, citing only what was provided.
  4. VERIFY  — every citation in the draft is checked again (Sefaria
               resolution + exclusion list; KST citations only when its
               pages were actually supplied). Failures send the draft back
               with feedback, up to two redrafts; still-failing citations
               are dropped and the teaching revised without them.

Requires ANTHROPIC_API_KEY (in GitHub Actions: the repository secret).
Nothing here publishes or sends anything.
"""

from __future__ import annotations

import base64
import json
import re
import sys
from datetime import date
from pathlib import Path

import anthropic

import ketershemtob as kst
from sefaria import fetch_text, is_excluded, verify_ref

ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-opus-5"
# Server-side refusal fallback, recommended default for claude-opus-5.
FALLBACK_BETA = ["server-side-fallback-2026-07-01"]

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _create(**kw):
    """Streaming messages call (long drafts exceed the non-streaming
    timeout) with the server-side refusal fallback; falls back to a plain
    call only if the fallback parameter itself is rejected."""
    try:
        with client().beta.messages.stream(
            model=MODEL, betas=FALLBACK_BETA, fallbacks="default", **kw
        ) as s:
            return s.get_final_message()
    except anthropic.BadRequestError as e:
        if "fallback" in str(e).lower() or "beta" in str(e).lower():
            with client().messages.stream(model=MODEL, **kw) as s:
                return s.get_final_message()
        raise


def _json_out(response) -> dict:
    if response.stop_reason == "refusal":
        raise RuntimeError(
            f"model refused: {getattr(response.stop_details, 'explanation', '')}"
        )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# ------------------------------------------------------------------- plan --

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "halakhic_topic": {"type": "string"},
        "kst_queries": {"type": "array", "items": {"type": "string"}},
        "sefaria_refs_halakha": {"type": "array", "items": {"type": "string"}},
        "aggadic_topic": {"type": "string"},
        "sefaria_refs_aggada": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["halakhic_topic", "kst_queries", "sefaria_refs_halakha",
                 "aggadic_topic", "sefaria_refs_aggada"],
    "additionalProperties": False,
}


def past_topics() -> list[str]:
    out = []
    for p in sorted((ROOT / "bulletin" / "archive" / "teachings").glob("*.md")):
        for line in p.read_text().splitlines():
            if line.lower().startswith("topic:"):
                out.append(line.split(":", 1)[1].strip())
    return out


def plan(week: str) -> dict:
    sources_policy = (ROOT / "bulletin" / "sources.md").read_text()
    kst_topics = "\n".join(
        f"vol. {e['vol']}, pp. {e['page_from']}–{e['page_to']} ({e['seifim']} se'ifim): "
        f"{e['section']} — {e['topic']}"
        for e in kst.all_entries() if e["vol"] in kst.HB_IDS
    )
    avoid = "\n".join(past_topics()) or "(none yet)"
    resp = _create(
        max_tokens=16000,
        system=(
            "You plan the two weekly teachings (one halakhic, one aggadic) for the "
            "bulletin of Kehillah Kedoshah Zikhron Zvi, a traditional egalitarian "
            "congregation in the Western Sephardic rite. Choose topics that arise "
            "directly from this week's reading or season. The halakhic topic should "
            "concern lived practice or custom; prefer topics where the Keter Shem Tob "
            "index below has a bearing entry, and where the Mishneh Torah is a natural "
            "first recourse. Sefaria references must be precise, existing passages in "
            "Sefaria's canonical citation style (e.g. 'Mishneh Torah, Repentance 2:4', "
            "'Zohar, Bereshit 1:1', 'Deuteronomy 30:19'). Never request anything from "
            "the excluded literature.\n\n--- source policy ---\n" + sources_policy
        ),
        messages=[{
            "role": "user",
            "content": (
                f"This week:\n{week}\n\nTopics already treated in past bulletins "
                f"(do not repeat):\n{avoid}\n\nKeter Shem Tob topical index "
                f"(volumes with readable scans):\n{kst_topics}\n\n"
                "Plan the two teachings. For kst_queries give short search phrases "
                "matching index topics above that bear on your halakhic topic (empty "
                "list if none genuinely applies)."
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
    )
    out = _json_out(resp)
    out["kst_queries"] = out["kst_queries"][:3]
    out["sefaria_refs_halakha"] = out["sefaria_refs_halakha"][:6]
    out["sefaria_refs_aggada"] = out["sefaria_refs_aggada"][:6]
    return out


# ----------------------------------------------------------------- gather --

PAGE_NUM_SCHEMA = {
    "type": "object",
    "properties": {"printed_page": {"type": ["integer", "null"]}},
    "required": ["printed_page"],
    "additionalProperties": False,
}


def read_page_number(pdf_bytes: bytes) -> int | None:
    resp = _create(
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode(),
                }},
                {"type": "text", "text":
                    "This is one scanned page of a printed Hebrew book. What page "
                    "number is printed on it (Arabic numerals or Hebrew numerals — "
                    "convert Hebrew numerals to an integer)? null if none visible."},
            ],
        }],
        output_config={"format": {"type": "json_schema", "schema": PAGE_NUM_SCHEMA}},
    )
    return _json_out(resp).get("printed_page")


def gather_kst(queries: list[str], max_entries: int = 2, max_pages: int = 5):
    """(descriptions, document_blocks, cited_ranges) for the best entries."""
    docs, descs, ranges = [], [], []
    if not queries:
        return descs, docs, ranges
    entries = kst.search(queries)[:max_entries]
    for e in entries:
        off = kst.find_offset(e["vol"], e["page_from"], read_page_number)
        if off is None:
            continue
        pages = list(range(e["page_from"], min(e["page_to"], e["page_from"] + max_pages - 1) + 1))
        got = []
        for p in pages:
            pdf = kst.fetch_page_pdf(e["vol"], p + off)
            if pdf:
                got.append(p)
                docs.append({"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf).decode()}})
        if got:
            descs.append(
                f"Keter Shem Tob, vol. {e['vol']}, pp. {got[0]}–{got[-1]} "
                f"(topic: {e['section']} — {e['topic']}; the scanned pages follow, in order)"
            )
            ranges.append({"vol": e["vol"], "from": got[0], "to": got[-1]})
    return descs, docs, ranges


def gather_sefaria(refs: list[str]) -> list[dict]:
    out = []
    for r in refs:
        v = verify_ref(r)
        if not v["ok"]:
            continue
        text = fetch_text(v["ref"], max_chars=2500)
        out.append({"ref": v["ref"], "url": v["url"], "text": text or "(no digital text)"})
    return out


# ------------------------------------------------------------------ draft --

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "halakha": {
            "type": "object",
            "properties": {
                "html": {"type": "string"},
                "citations": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "display": {"type": "string"},
                        "sefaria_ref": {"type": ["string", "null"]},
                        "kst": {"type": "boolean"},
                    },
                    "required": ["display", "sefaria_ref", "kst"],
                    "additionalProperties": False,
                }},
            },
            "required": ["html", "citations"],
            "additionalProperties": False,
        },
        "aggada": {
            "type": "object",
            "properties": {
                "html": {"type": "string"},
                "citations": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "display": {"type": "string"},
                        "sefaria_ref": {"type": ["string", "null"]},
                        "kst": {"type": "boolean"},
                    },
                    "required": ["display", "sefaria_ref", "kst"],
                    "additionalProperties": False,
                }},
            },
            "required": ["html", "citations"],
            "additionalProperties": False,
        },
    },
    "required": ["halakha", "aggada"],
    "additionalProperties": False,
}


def draft_system() -> str:
    voice = (ROOT / "bulletin" / "voice.md").read_text()
    return (
        voice
        + "\n\n--- operational rules for this draft ---\n"
        "Write BOTH teachings now, from the source material supplied in the "
        "user message and nothing else. Rules:\n"
        "- 150 to 250 words each. HTML: <p> paragraphs; <em> for italics; no "
        "other tags, no headings (the page supplies them).\n"
        "- Cite ONLY sources whose text or scanned pages are supplied. Name "
        "each citation in the prose exactly as it appears in the 'display' "
        "field you give for it. For Sefaria sources, sefaria_ref must repeat "
        "the exact reference as supplied. For Keter Shem Tob (supplied as "
        "scanned Hebrew pages), cite as: Keter Shem Tob, vol. N, p. P, se'if S "
        "— only pages actually supplied, and only if you actually read the "
        "se'if there; kst=true, sefaria_ref=null.\n"
        "- If a supplied source does not support the point, do not cite it.\n"
        "- Biblical verses inside the week's reading may be quoted from the "
        "supplied reading text and cited by chapter and verse.\n"
        "- Transliteration follows the congregation's Sephardic style "
        "(Shabbat, Habdala, Selihot, Kippur, Shabuot, Tish'a Be'Ab).\n"
    )


def build_draft_content(week: str, plan_out: dict, sef_h, sef_a, kst_descs, kst_docs) -> list:
    def block(srcs, label):
        if not srcs:
            return f"({label}: none available)\n"
        return "\n".join(
            f"[{s['ref']}]\n{s['text']}\n" for s in srcs
        )

    content: list = []
    content += kst_docs
    text = (
        f"This week:\n{week}\n\n"
        f"Planned halakhic topic: {plan_out['halakhic_topic']}\n"
        f"Planned aggadic topic: {plan_out['aggadic_topic']}\n\n"
        f"Verified sources for the halakhic teaching:\n{block(sef_h, 'halakhic')}\n"
        f"Verified sources for the aggadic teaching:\n{block(sef_a, 'aggadic')}\n"
    )
    if kst_descs:
        text += "\nKeter Shem Tob material supplied as scanned pages (in the order attached):\n" + "\n".join(kst_descs) + "\n"
    text += "\nWrite the two teachings."
    content.append({"type": "text", "text": text})
    return content


def draft(content: list) -> dict:
    resp = _create(
        max_tokens=32000,
        system=draft_system(),
        messages=[{"role": "user", "content": content}],
        output_config={"format": {"type": "json_schema", "schema": DRAFT_SCHEMA}},
    )
    return _json_out(resp)


# ----------------------------------------------------------------- verify --

def check(teaching: dict, supplied_refs: set[str], kst_ranges: list[dict]) -> list[str]:
    problems = []
    for c in teaching["citations"]:
        disp = c["display"]
        if c["kst"]:
            m = re.search(r"vol\.\s*(\d+),\s*pp?\.\s*(\d+)", disp)
            if not m:
                problems.append(f"KST citation not in canonical form: {disp}")
                continue
            vol, page = int(m.group(1)), int(m.group(2))
            if not any(r["vol"] == vol and r["from"] <= page <= r["to"] for r in kst_ranges):
                problems.append(f"KST citation outside supplied pages: {disp}")
            continue
        ref = c["sefaria_ref"]
        if not ref:
            problems.append(f"citation with no reference: {disp}")
            continue
        if is_excluded(ref):
            problems.append(f"excluded work cited: {disp}")
            continue
        v = verify_ref(ref)
        if not v["ok"]:
            problems.append(f"does not verify on Sefaria: {disp} ({ref}): {v['reason']}")
        elif v["ref"] not in supplied_refs and not _is_bible(v["ref"]):
            problems.append(f"cites a source that was not supplied: {disp} ({v['ref']})")
        if disp not in teaching["html"]:
            problems.append(f"citation display text not found in the teaching: {disp}")
    return problems


_BIBLE_BOOKS = ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
                "Isaiah", "Jeremiah", "Ezekiel", "Hosea", "Joel", "Amos",
                "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
                "Haggai", "Zechariah", "Malachi", "Psalms", "Proverbs", "Job",
                "Song of Songs", "Ruth", "Lamentations", "Ecclesiastes",
                "Esther", "Daniel", "Ezra", "Nehemiah", "I Chronicles",
                "II Chronicles", "I Samuel", "II Samuel", "I Kings", "II Kings",
                "Judges", "Joshua")


def _is_bible(ref: str) -> bool:
    return ref.startswith(_BIBLE_BOOKS)


def linkify(teaching: dict) -> str:
    html = teaching["html"]
    for c in teaching["citations"]:
        if c["kst"] or not c["sefaria_ref"]:
            continue
        v = verify_ref(c["sefaria_ref"])
        if v["ok"] and c["display"] in html:
            html = html.replace(
                c["display"], f'<a href="{v["url"]}">{c["display"]}</a>', 1
            )
    return html


# ------------------------------------------------------------------- main --

def generate(week_description: str) -> dict:
    p = plan(week_description)
    print("plan:", json.dumps({k: p[k] for k in ("halakhic_topic", "aggadic_topic")}), file=sys.stderr)
    sef_h = gather_sefaria(p["sefaria_refs_halakha"])
    sef_a = gather_sefaria(p["sefaria_refs_aggada"])
    kst_descs, kst_docs, kst_ranges = gather_kst(p["kst_queries"])
    print(f"gathered: {len(sef_h)}+{len(sef_a)} sefaria, {len(kst_docs)} KST pages", file=sys.stderr)

    supplied = {s["ref"] for s in sef_h} | {s["ref"] for s in sef_a}
    content = build_draft_content(week_description, p, sef_h, sef_a, kst_descs, kst_docs)
    d = draft(content)
    for attempt in range(2):
        problems = check(d["halakha"], supplied, kst_ranges) + check(d["aggada"], supplied, kst_ranges)
        if not problems:
            break
        print("redraft needed:", problems, file=sys.stderr)
        feedback = (
            "Your draft has citation problems; every citation must verify. "
            "Problems:\n- " + "\n- ".join(problems)
            + "\nRevise both teachings, dropping or correcting the offending "
            "citations. A teaching must stand on verified sources only."
        )
        resp = _create(
            max_tokens=32000,
            system=draft_system(),
            messages=[
                {"role": "user", "content": content},
                {"role": "assistant", "content": json.dumps(d)},
                {"role": "user", "content": feedback},
            ],
            output_config={"format": {"type": "json_schema", "schema": DRAFT_SCHEMA}},
        )
        d = _json_out(resp)
    else:
        problems = check(d["halakha"], supplied, kst_ranges) + check(d["aggada"], supplied, kst_ranges)
        if problems:
            raise RuntimeError("citations still failing after redrafts: " + "; ".join(problems))

    return {
        "plan": p,
        "halakha_html": linkify(d["halakha"]),
        "aggada_html": linkify(d["aggada"]),
        "halakha_citations": d["halakha"]["citations"],
        "aggada_citations": d["aggada"]["citations"],
    }


if __name__ == "__main__":
    week = sys.stdin.read().strip() or "Shabbat Nitzavim-Vayeilech, 4-5 September 2026"
    out = generate(week)
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "teachings.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:2000])

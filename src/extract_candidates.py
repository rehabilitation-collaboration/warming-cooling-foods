"""Structure-based candidate enumeration for the Axis A ledger (Route D, RD-1).

Axis A's problem is that only the *kept* attributions were ever recorded
(``claims.csv``, 649 rows); nothing records what was looked at and dropped, so a
reader cannot tell a coder's oversight from a correct exclusion under
``coding_protocol.md``. The fix mirrors Axis B: enumerate every candidate the
frame sources present, then judge each one with a reason code.

This module does the enumeration half. It is deliberately **dictionary-free**:
using the vocabulary already in ``claims.csv`` to search the sources would be
self-referential — a food no source was ever credited with could not be found
that way. Instead it reads the *structure* the sources use to present food
lists, so a food absent from the current ledger can still surface.

Extraction paths (each candidate records which one produced it):

``list``
    A line carrying delimiter-separated items (``きゅうり／トマト／ナス``).
``labeled``
    A line of the form ``category：item、item`` — the right-hand side is split.
``scoped``
    A short bare line sitting under a thermal heading, which is how several
    sources lay out one-item-per-line blocks (kawashimaya's 冷たい食べ物 block,
    yomeishu's per-food sections).
``prose``
    A sentence that carries thermal vocabulary and attributes a direction in
    running text (``味噌など色が濃いものも「陽性」に分類されます``). Measured
    against the coded rows, this is where every one of the 58 v1 misses lived.

**A candidate is a span, not a resolved food name.** Japanese prose gives no
reliable token boundary for foods written in kana (``じゃがいも`` ends in the
particle ``も``), so the extractor emits overlapping granularities — the
delimiter-level segment and the particle-level token — and leaves naming to the
judgment step, exactly as ``coding_protocol.md`` §3 already requires of a coder.
A messy span is still judgeable; a food that never became a span is not.

Recall of these paths is not assumed: ``verify_candidate_recall.py`` measures it
against the 649 already-coded rows, every one of which is known to occur
verbatim in its source (``verify_claims.py``). Noise is left in on purpose —
per the Route D goal declaration, a junk candidate is dropped in the ledger with
a ``fragment`` reason, which is auditable, whereas a stopword list drops it
silently.
"""

from __future__ import annotations

import re

import pandas as pd

from .definitions import SOURCES_CSV, SOURCES_RAW_DIR

# --- Vocabularies and shapes ---------------------------------------------

# Thermal vocabulary marking a line as being about warming/cooling. Wider than
# coding_protocol.md §3's direction table on purpose: this only decides "is this
# region of the page about the construct", not what direction anything gets.
THERM = re.compile(
    "温め|温める|温まる|温まり|温か|体を温|温性|熱性|陽性|極陽|陽の|温食材|温活|ぽかぽか"
    "|冷やす|冷やし|冷える|冷え|冷たい|体を冷|涼性|寒性|陰性|極陰|陰の|冷食材|クールダウン"
    "|陰陽|中庸|平性"
)

# Item separators seen across the frame (ideographic comma, nakaguro, slashes).
DELIM = re.compile(r"[、，,・･／/｜|]")

# ``category：items`` label separator.
LABEL_SEP = re.compile(r"[：:]")

# Sentence-final punctuation: a line carrying it is prose, not a list item.
SENTENCE_END = re.compile(r"[。！？!?]")

# A candidate must contain at least one CJK character (drops URLs, dates, tags).
CJK = re.compile(r"[぀-ヿ一-鿿]")

# Parenthetical asides are stripped before splitting: ``サラダ（過剰摂取）``.
# Both forms are emitted — some sources' own label carries the qualifier.
PARENS = re.compile(r"[（(\[【][^）)\]】]*[）)\]】]")

# Particles and connectives that join foods inside a sentence. Splitting on
# these fragments kana food names (``じゃがいも`` → ``じゃがい``), which is why
# the delimiter-level span is emitted alongside the particle-level token.
PARTICLES = re.compile(r"や|と|は|も|が|を|に|で|の|など|および|ならびに|そして|また")

MAX_HEADING_LEN = 28   # longer lines carrying thermal words are prose, not headings
MAX_ITEM_LEN = 16      # longest plausible food label in these sources
MAX_PROSE_SPAN = 40    # a clause may carry the food plus its qualifying phrase
MAX_SCOPE_LINES = 60   # how far a thermal heading's block may reach
THERM_WINDOW = 1       # lines either side that still count as thermal context

COLUMNS = ["source_id", "line_no", "path", "heading", "candidate", "line"]


def _is_heading(line: str) -> bool:
    """A short thermal line that is not itself a list opens an item block.

    One delimiter is tolerated because headings pair categories (体を温める肉・魚);
    two or more mean the line is the list.
    """
    return (
        len(line) <= MAX_HEADING_LEN
        and bool(THERM.search(line))
        and not SENTENCE_END.search(line)
        and len(DELIM.findall(line)) <= 1
    )


def _clean(token: str) -> str:
    return PARENS.sub("", token).strip(" 　\t・…‥-–—〜~")


def _is_item(token: str, max_len: int = MAX_ITEM_LEN) -> bool:
    return bool(token) and len(token) <= max_len and bool(CJK.search(token))


def _variants(raw: str) -> list[str]:
    """The token as the source writes it, and with parenthetical asides removed."""
    stripped = raw.strip(" 　\t・…‥-–—〜~")
    cleaned = _clean(raw)
    return [t for t in dict.fromkeys([cleaned, stripped]) if t]


def _paren_inner(text: str) -> list[str]:
    """Enumerations often sit inside parentheses: 刺激の強くない飲み物（三年番茶など）."""
    inner = re.findall(r"[（(\[【]([^）)\]】]*)[）)\]】]", text)
    out: list[str] = []
    for chunk in inner:
        for part in DELIM.split(chunk):
            out.extend(t for t in PARTICLES.split(part) if _is_item(t.strip()))
            if _is_item(part.strip()):
                out.append(part.strip())
    return out


def _split_items(payload: str) -> list[str]:
    out = []
    for part in DELIM.split(payload):
        out.extend(t for t in _variants(part) if _is_item(t))
        out.extend(_paren_inner(part))
    return list(dict.fromkeys(out))


def _split_prose(line: str) -> list[str]:
    """Spans from a running-text sentence, at two granularities (see module doc)."""
    out: list[str] = []
    for sentence in SENTENCE_END.split(line):
        for segment in DELIM.split(sentence):
            segment = segment.strip()
            if _is_item(segment, MAX_PROSE_SPAN):
                out.append(segment)
            for token in PARTICLES.split(segment):
                out.extend(t for t in _variants(token) if _is_item(t))
            out.extend(_paren_inner(segment))
    return list(dict.fromkeys(out))


def extract_source(source_id: str, text: str) -> pd.DataFrame:
    """Enumerate candidate food tokens from one source's extracted body text."""
    rows: list[dict] = []
    heading = ""
    heading_line = -(MAX_SCOPE_LINES + 1)

    # Inline emphasis splits a sentence across lines — hiesyo_com renders
    # "バナナやパイナップルは<strong>陰性食品</strong>" as two lines, leaving the
    # food line with no thermal word of its own. Thermal context is therefore
    # read over a window, not per line.
    lines = [raw.strip() for raw in text.split("\n")]
    thermal = [bool(THERM.search(ln)) for ln in lines]

    def in_thermal_context(idx: int) -> bool:
        lo = max(0, idx - THERM_WINDOW)
        return any(thermal[lo : idx + THERM_WINDOW + 1])

    for line_no, line in enumerate(lines, start=1):
        if not line or line.startswith("#"):
            continue

        # A heading opens a block, but it can also name foods itself
        # ("ビールや炭酸系カクテルは体を冷やしやすい"), so it is not consumed.
        if _is_heading(line):
            heading, heading_line = line, line_no

        def emit(path: str, items: list[str]) -> None:
            for item in items:
                rows.append(
                    {
                        "source_id": source_id,
                        "line_no": line_no,
                        "path": path,
                        "heading": heading,
                        "candidate": item,
                        "line": line,
                    }
                )

        # Running text can carry an attribution on a line that is also a list
        # ("人参やごぼうなどの根菜類、味噌など色が濃いものも「陽性」"), so the
        # prose path runs in addition to the structural ones, not instead.
        if in_thermal_context(line_no - 1):
            emit("prose", _split_prose(line))

        if LABEL_SEP.search(line):
            payload = LABEL_SEP.split(line, maxsplit=1)[1]
            emit("labeled", _split_items(payload))
            continue

        if len(DELIM.findall(line)) >= 1:
            emit("list", _split_items(line))
            continue

        in_scope = line_no - heading_line <= MAX_SCOPE_LINES
        if in_scope and not SENTENCE_END.search(line):
            items = [t for t in _variants(line) if _is_item(t)]
            items.extend(_paren_inner(line))
            emit("scoped", list(dict.fromkeys(items)))

    return pd.DataFrame(rows, columns=COLUMNS)


def extract_all() -> pd.DataFrame:
    """Enumerate candidates for every source in the frame."""
    sources = pd.read_csv(SOURCES_CSV)
    frames = []
    for source_id in sources["source_id"]:
        path = SOURCES_RAW_DIR / f"{source_id}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} missing — Route D's input is git-ignored; restore it from "
                "the backup rather than re-fetching (the page may have changed)."
            )
        frames.append(extract_source(source_id, path.read_text(encoding="utf-8")))
    return pd.concat(frames, ignore_index=True)


def dedupe(occurrences: pd.DataFrame) -> pd.DataFrame:
    """Collapse occurrences to one row per (source_id, candidate) for the ledger."""
    grouped = occurrences.groupby(["source_id", "candidate"], as_index=False).agg(
        n_occurrences=("line_no", "size"),
        first_line_no=("line_no", "min"),
        paths=("path", lambda s: "|".join(sorted(set(s)))),
        heading=("heading", "first"),
        line=("line", "first"),
    )
    return grouped.sort_values(["source_id", "first_line_no"]).reset_index(drop=True)


def main() -> None:
    occurrences = extract_all()
    unique = dedupe(occurrences)
    print(f"occurrences: {len(occurrences)}  unique (source, candidate): {len(unique)}")
    print("\nby extraction path:")
    print(occurrences["path"].value_counts().to_string())
    print("\nunique candidates per source:")
    print(unique.groupby("source_id").size().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()

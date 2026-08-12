"""RD-4 steps (b) and (c): two invariants the ledger can only be checked against
after it is finished, and both are `claims.csv`-independent by design.

**(b) D61 — a head noun inheriting two opposite directions.** §9.4 rule 2 says
that where the source presents both 夏野菜 and 果物, "the shorter one … is the
row". kawashimaya never presents a bare 果物: it presents 寒冷地の果物 (warm) and
南国の果物 (cool), and the bare token is the residue of stripping the modifier
off both, so its `lines` carry two directions at once. Applied literally the rule
drops the two categories the source actually built and mints one contradictory
row. D61 held the rule as it stands, on the grounds that the failure is
detectable mechanically once the codings are in — this is that detector.

It runs on the enumeration's own `lines`, never on `claims.csv`, because the
goal declaration counts a completeness claim resting on the known set as a
failure of the route.

**(c) D68 — extractor-produced spans that are not verbatim.** §9.4 rule 3 scopes
`not-verbatim` to a coder's paraphrase, "because the candidate string comes from
the extractor". That premise is false: stripping a parenthetical can leave a span
that is not contiguous in the source (`酒粕＋鮭（温性）＋にんじん` -> `酒粕＋鮭＋にんじん`).
D68 measured the class at 44 candidates, 0.23%, and established that none can
reach an include because every one of them is long enough or malformed enough to
fall out under rule 2. This locks that measurement so a future extractor change
cannot quietly widen the class.

Run: ``python3 -m src.rd4_checks``
"""

from __future__ import annotations

import pandas as pd

from .definitions import DATA_DIR, SOURCES_RAW_DIR
from .extract_candidates import CANDIDATES_CSV

LEDGER = DATA_DIR / "claims_ledger.csv"

# D68's measured bound. The class is an artefact of the paren expansion (D58);
# it is allowed to exist, not allowed to grow unnoticed.
D68_MAX = 44
D68_MAX_SHORT = 8  # a span this short could plausibly be a bare food name


def _lines_of(cell: str) -> list[int]:
    return [int(x) for x in str(cell).split(";") if str(x).strip().isdigit()]


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    led = pd.read_csv(LEDGER, dtype=str).fillna("")
    cand = pd.read_csv(CANDIDATES_CSV, dtype=str).fillna("")
    return led[led["final_label"] == "include"], cand


def head_noun_conflicts(inc: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Included head nouns that are the residue of two oppositely-labelled forms.

    Not "two included spans on one line disagree" — a list line naming both
    にんにく and 大根 disagrees for the ordinary reason that the source put a warm
    food and a cool food on one line, and flagging those buries the real case in
    sixty of them.

    D61's signature is narrower and structural: a short span that is a proper
    substring of longer spans sharing its emission lines, where those longer
    spans carry opposite directions. That is 果物 sitting inside 寒冷地の果物 (warm)
    and 南国の果物 (cool) — the modifier is doing the work, and the bare token
    inherits a direction the source never gave it.
    """
    lines = {(r.source_id, r.candidate): set(_lines_of(r.lines))
             for r in cand.itertuples()}
    by_source: dict[str, list] = {}
    for r in inc.itertuples():
        by_source.setdefault(r.source_id, []).append(r)

    rows = []
    for src, items in by_source.items():
        for short in items:
            longer = [
                o for o in items
                if o.candidate != short.candidate
                and short.candidate in o.candidate
                and lines.get((src, short.candidate), set())
                & lines.get((src, o.candidate), set())
            ]
            directions = {o.direction for o in longer}
            if len(directions) < 2:
                continue
            rows.append({
                "source_id": src,
                "head_noun": short.candidate,
                "its_direction": short.direction,
                "enclosing": " | ".join(
                    f"{o.candidate}={o.direction}" for o in sorted(
                        longer, key=lambda x: x.candidate)),
            })
    return pd.DataFrame(rows)


def non_verbatim(cand: pd.DataFrame) -> pd.DataFrame:
    """Candidates that are not contiguous substrings of their source text (D68)."""
    rows = []
    for src, group in cand.groupby("source_id"):
        path = SOURCES_RAW_DIR / f"{src}.txt"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for r in group.itertuples():
            if "wrapped" in r.paths:
                continue  # the wrapped path joins two lines on purpose
            if r.candidate not in text:
                rows.append({"source_id": src, "candidate": r.candidate,
                             "paths": r.paths, "length": len(r.candidate)})
    return pd.DataFrame(rows)


def main() -> None:
    inc, cand = load()

    print("=== (b) D61: 逆方向の見出しを跨ぐ include ===")
    conflicts = head_noun_conflicts(inc, cand)
    print(f"逆方向の修飾形に挟まれた include: {len(conflicts)}")
    for r in conflicts.itertuples():
        print(f"  {r.source_id}: `{r.head_noun}`={r.its_direction}  <-  {r.enclosing}")

    print("\n=== (c) D68: source_text の連続部分文字列でない候補 ===")
    nv = non_verbatim(cand)
    short = nv[nv["length"] <= D68_MAX_SHORT] if len(nv) else nv
    print(f"該当 {len(nv)} / {len(cand)} ({len(nv) / len(cand):.2%})"
          f"  — D68 の実測上限 {D68_MAX}")
    print(f"うち {D68_MAX_SHORT} 字以下（裸の食品名になりうる長さ）: {len(short)}")
    for r in short.itertuples():
        print(f"    {r.source_id:22s} {r.candidate}")
    included = set(zip(inc["source_id"], inc["candidate"]))
    leaked = [r for r in nv.itertuples() if (r.source_id, r.candidate) in included]
    print(f"★ うち include に化けたもの: {len(leaked)}"
          f"{'' if not leaked else ' — ' + str([r.candidate for r in leaked])}")


if __name__ == "__main__":
    main()

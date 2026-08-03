"""Deterministic grounding check for claims.csv (hallucination guard).

Coding is done by an LLM (per the protocol), so the risk is not
non-determinism but hallucination: a food or direction label that is not
actually in the source. This module verifies, by exact substring match against
the fetched source text, that every coded food label really appears in its
cited source. It is pure Python — no model, fully reproducible — so it can be
run in CI to stop unverifiable rows from accumulating.

A row PASSES its food-grounding check when its ``food_ja`` label occurs
verbatim in ``data/sources_raw/{source_id}.txt``. Rows that fail are printed
for human re-check against the original text; the LLM's output is never trusted
without this pass.
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import CLAIMS_CSV, SOURCES_RAW_DIR

# Direction cue words expected to appear in a source that assigns this
# direction. Used for a soft check that the source uses the vocabulary at all
# (not per-row, which would need span alignment) — reported as info, not fail.
DIRECTION_CUES = {
    "warm": ("温め", "温める", "温性", "熱性", "陽性", "陽", "体を温"),
    "cool": ("冷やす", "冷え", "涼性", "寒性", "陰性", "陰", "体を冷"),
    "neutral": ("平性", "平", "中庸", "中性"),
}


def _load_source_texts(source_ids) -> dict[str, str]:
    texts = {}
    for sid in source_ids:
        path = SOURCES_RAW_DIR / f"{sid}.txt"
        texts[sid] = path.read_text(encoding="utf-8") if path.exists() else None
    return texts


def verify(path=CLAIMS_CSV) -> pd.DataFrame:
    """Return the subset of claims whose food label is NOT found in its source.

    An empty result means every coded food is grounded in its cited source.
    """
    df = pd.read_csv(path).fillna("")
    texts = _load_source_texts(df["source_id"].unique())

    failures = []
    for idx, row in df.iterrows():
        sid = str(row["source_id"])
        food_ja = str(row["food_ja"]).strip()
        text = texts.get(sid)
        if text is None:
            failures.append((idx, sid, food_ja, row["food_en"], "source txt missing"))
            continue
        if food_ja and food_ja not in text:
            failures.append(
                (idx, sid, food_ja, row["food_en"], "food_ja not in source text")
            )
    return pd.DataFrame(
        failures, columns=["row", "source_id", "food_ja", "food_en", "reason"]
    )


def direction_cue_coverage(path=CLAIMS_CSV) -> pd.DataFrame:
    """Per source: does the source text contain the cue words for each coded
    direction it uses? A source coded ``cool`` whose text has no cooling cue is
    suspicious (info-level, not a hard fail — headers/tables vary)."""
    df = pd.read_csv(path).fillna("")
    texts = _load_source_texts(df["source_id"].unique())
    rows = []
    for sid, grp in df.groupby("source_id"):
        text = texts.get(sid) or ""
        for direction in grp["direction"].unique():
            cues = DIRECTION_CUES.get(direction, ())
            has_cue = any(c in text for c in cues)
            rows.append(
                {"source_id": sid, "direction": direction, "source_has_cue": has_cue}
            )
    return pd.DataFrame(rows)


def main() -> None:
    fails = verify()
    if fails.empty:
        df = pd.read_csv(CLAIMS_CSV)
        print(f"OK: all {len(df)} coded food labels grounded in their sources.")
    else:
        print(f"UNGROUNDED ROWS ({len(fails)}) — re-check against source txt:")
        print(fails.to_string(index=False))

    cues = direction_cue_coverage()
    missing = cues[~cues["source_has_cue"]]
    if not missing.empty:
        print("\nDirection-cue gaps (info — verify header/table wording):")
        print(missing.to_string(index=False))

    sys.exit(1 if not fails.empty else 0)


if __name__ == "__main__":
    main()

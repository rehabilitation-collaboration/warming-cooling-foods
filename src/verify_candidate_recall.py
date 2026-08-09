"""Measure the recall of the Axis A candidate extraction (Route D, RD-1).

The Route D goal declaration makes this check a condition of success: a ledger
built on a candidate list of unknown recall would reproduce the very problem it
exists to fix — the母集団 itself would be silently incomplete.

The reference set is ``claims.csv``. Every one of its 649 rows carries a
``food_ja`` label that ``verify_claims.py`` confirms occurs **verbatim** in that
row's source text, so each row is a known-correct answer the extractor should
surface. Recall is therefore measurable without any new data.

Two levels are reported, because they mean different things for the ledger:

``exact``
    Some candidate token equals ``food_ja`` — the ledger will carry that food as
    its own row.
``covered``
    Some candidate token *contains* ``food_ja`` (``ゴボウなどの根菜類`` covers
    ``ゴボウ``). The coder still sees the food and judges it, so the attribution
    is auditable; the ledger row is just coarser.

``covered`` is the headline number: it is the fraction of known attributions a
coder working from the candidate list would be shown. Anything below it is a
structural blind spot, and the misses are printed so the extraction paths can be
extended until they are not.
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import CLAIMS_CSV, SOURCES_CSV
from .extract_candidates import dedupe, extract_all

RECALL_TARGET = 0.90  # PLAN branch condition: below this, extend the paths


def _candidate_sets(unique: pd.DataFrame) -> dict[str, list[str]]:
    return {
        sid: grp["candidate"].tolist() for sid, grp in unique.groupby("source_id")
    }


def score(claims: pd.DataFrame, unique: pd.DataFrame) -> pd.DataFrame:
    """Per claims row: was its food label surfaced as a candidate?"""
    by_source = _candidate_sets(unique)
    rows = []
    for _, row in claims.iterrows():
        sid = str(row["source_id"])
        food_ja = str(row["food_ja"]).strip()
        candidates = by_source.get(sid, [])
        exact = food_ja in candidates
        covering = [c for c in candidates if food_ja and food_ja in c]
        rows.append(
            {
                "source_id": sid,
                "food_ja": food_ja,
                "food_en": row["food_en"],
                "exact": exact,
                "covered": bool(covering),
                "covering_example": covering[0] if covering else "",
            }
        )
    return pd.DataFrame(rows)


def summarise(scored: pd.DataFrame, tier1: set[str]) -> pd.DataFrame:
    frames = {"all 15 sources": scored, "Tier 1 only": scored[scored.source_id.isin(tier1)]}
    return pd.DataFrame(
        [
            {
                "frame": name,
                "rows": len(df),
                "exact": df["exact"].sum(),
                "exact_recall": round(df["exact"].mean(), 4) if len(df) else float("nan"),
                "covered": df["covered"].sum(),
                "covered_recall": round(df["covered"].mean(), 4) if len(df) else float("nan"),
            }
            for name, df in frames.items()
        ]
    )


def main() -> None:
    claims = pd.read_csv(CLAIMS_CSV).fillna("")
    sources = pd.read_csv(SOURCES_CSV)
    tier1 = set(sources[sources["tier"] == 1]["source_id"])

    occurrences = extract_all()
    unique = dedupe(occurrences)
    scored = score(claims, unique)

    print(f"candidates: {len(unique)} unique (source, candidate) "
          f"from {len(occurrences)} occurrences")
    print("\n=== recall against the 649 already-coded rows ===")
    print(summarise(scored, tier1).to_string(index=False))

    per_source = (
        scored.groupby("source_id")
        .agg(rows=("covered", "size"), covered=("covered", "sum"))
        .assign(recall=lambda d: (d["covered"] / d["rows"]).round(3))
        .sort_values("recall")
    )
    print("\n=== per source (worst first) ===")
    print(per_source.to_string())

    misses = scored[~scored["covered"]]
    print(f"\n=== misses ({len(misses)}) — foods a coder would never be shown ===")
    if not misses.empty:
        print(misses[["source_id", "food_ja", "food_en"]].to_string(index=False))

    covered_recall = scored["covered"].mean()
    print(f"\nheadline covered-recall = {covered_recall:.4f} (target {RECALL_TARGET})")
    sys.exit(0 if covered_recall >= RECALL_TARGET else 1)


if __name__ == "__main__":
    main()

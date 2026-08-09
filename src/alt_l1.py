"""Alternative definitions of L1, the literature-volume adjustment.

The third review's fifth point: what carries the primary model is not lay-source
coverage but log(L1 + 1), and L1 is a bare title/abstract count of the food name.
What that count contains differs by food — chicken's 94,310 records are largely
poultry science, salt's 201,716 largely saline and sodium physiology — so "L1
is doing the work" invites the reply that the L1 *definition* is doing the work.

Two narrower readings are collected here, each a PubMed filter on the same food
term group:

    humans      AND humans[mh] — drops the animal and agronomic literature
    nutrition   AND "diet, food, and nutrition"[mh] — restricts to the MeSH
                nutrition tree, i.e. the food studied as a food

Both filters were checked against the live index before being written down:
PubMed's query translation returns them as `"humans"[MeSH Terms]` and
`"diet, food, and nutrition"[MeSH Terms]` with no error or unmatched-phrase
warning, so neither is silently matching nothing.

This writes its own CSV and never touches `pubmed_counts.csv`, because
`collect_counts` rewrites that file wholesale and drops the `L2_screened`
column with it.

Run: python3 -m src.alt_l1  (from the project root)
"""

from __future__ import annotations

from time import sleep

import pandas as pd

from .definitions import DATA_DIR, PUBMED_COUNTS_CSV
from .evidence_mapping import (
    PUBMED_DELAY,
    _cached_count,
    _parse_pubmed,
    _save_raw,
    pubmed_count,
)
from .food_query_terms import pubmed_query

ALT_L1_CSV = DATA_DIR / "alt_l1_counts.csv"

# Layer name -> the clause ANDed onto the L1 food-term group. The layer name is
# also the query_log filename stem, so these must stay distinct from L1/L2/L3.
ALT_L1_FILTERS = {
    "L1_humans": "humans[mh]",
    "L1_nutrition": '"diet, food, and nutrition"[mh]',
}


def alt_l1_query(food_en: str, variant: str) -> str:
    """The L1 query for ``food_en`` narrowed by ``variant``'s filter."""
    if variant not in ALT_L1_FILTERS:
        raise ValueError(
            f"unknown L1 variant {variant!r}; expected one of {sorted(ALT_L1_FILTERS)}"
        )
    return f"{pubmed_query(food_en, 'L1')} AND {ALT_L1_FILTERS[variant]}"


def collect_alt_l1(foods: list[str], *, reuse_cache: bool = True) -> pd.DataFrame:
    """Fetch every alternative L1 count for ``foods``, one row per food.

    PubMed failures are not swallowed: this is a covariate the primary model is
    refit on, and a silently missing count would drop the food from the refit
    rather than announce itself.
    """
    rows = []
    for food in foods:
        row = {"food_key": food}
        for variant in ALT_L1_FILTERS:
            query = alt_l1_query(food, variant)
            n = (
                _cached_count("pubmed", food, variant, _parse_pubmed, query=query)
                if reuse_cache
                else None
            )
            if n is None:
                n, raw = pubmed_count(query)
                _save_raw("pubmed", food, variant, raw, query=query)
                sleep(PUBMED_DELAY)
            row[variant] = n
            row[f"{variant}_query"] = query
        rows.append(row)
    return pd.DataFrame(rows)


def load_alt_l1() -> pd.DataFrame | None:
    """Read the collected counts, or None if they have not been fetched yet."""
    if not ALT_L1_CSV.exists():
        return None
    return pd.read_csv(ALT_L1_CSV)


def main() -> None:
    counts = pd.read_csv(PUBMED_COUNTS_CSV)
    foods = sorted(counts.loc[counts["layer"] == "L1", "food_key"].unique())
    print(f"fetching {len(ALT_L1_FILTERS)} alternative L1 counts for {len(foods)} foods")
    out = collect_alt_l1(foods)
    ALT_L1_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(ALT_L1_CSV, index=False)

    base = counts[counts["layer"] == "L1"].set_index("food_key")["n_pubmed"]
    merged = out.set_index("food_key")
    print(f"wrote {ALT_L1_CSV} ({len(out)} foods)")
    for variant in ALT_L1_FILTERS:
        ratio = (merged[variant] / base.reindex(merged.index)).dropna()
        print(f"  {variant:14s} total={int(merged[variant].sum()):,}  "
              f"median share of L1={ratio.median():.3f}")


if __name__ == "__main__":
    main()

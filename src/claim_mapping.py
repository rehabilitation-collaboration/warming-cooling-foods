"""Axis A aggregation: lay-belief breadth (consensus coverage) per food.

Reads the hand-coded claims table (one row per food-source-direction, per the
coding protocol) and computes, for each food, how many distinct sources call it
warming vs cooling, the majority direction, and a consensus ratio. Tier 1
(corporate/association) is the primary frame; Tier 2 (individual) is used only
for sensitivity analysis.

No network or scraping here — coding is done by hand into claims.csv. This
module only aggregates and is fully unit-tested.
"""

from __future__ import annotations

import pandas as pd

from .definitions import (
    CLAIMS_CSV,
    COFFEE_REPRESENTATIVE_MIN_SOURCES,
    COOL,
    NEUTRAL,
    SOURCES_CSV,
    TIER_ORG,
    WARM,
)

# Synonyms normalized to a single canonical food key before aggregation.
# Extend as coding surfaces new spellings; unit-tested for stability.
FOOD_SYNONYMS = {
    "しょうが": "ginger",
    "生姜": "ginger",
    "ジンジャー": "ginger",
    "コーヒー": "coffee",
    "珈琲": "coffee",
    "きゅうり": "cucumber",
    "胡瓜": "cucumber",
}

CONTESTED = "contested"


def normalize_food(name: str) -> str:
    """Map a raw food label to its canonical key (identity if unknown)."""
    return FOOD_SYNONYMS.get(name.strip(), name.strip())


def _canonical_key(row: pd.Series) -> str:
    """Canonical food key: prefer the English name, else normalize the JA name.

    ``food_en`` is the canonical identifier in the coded data; ``normalize_food``
    only needs to fold JA synonyms when an English name is absent.
    """
    food_en = row.get("food_en")
    if isinstance(food_en, str) and food_en.strip():
        return food_en.strip()
    return normalize_food(str(row.get("food_ja", "")))


def _add_food_key(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with a canonical ``food_key`` column derived from names.

    Idempotent: if ``food_key`` already exists it is left as-is, so the
    aggregation functions work whether given raw or already-loaded claims.
    """
    if "food_key" in df.columns:
        return df
    out = df.copy()
    out["food_key"] = out.apply(_canonical_key, axis=1)
    return out


def load_claims(path=CLAIMS_CSV) -> pd.DataFrame:
    """Load the hand-coded claims table and normalize food names.

    Expected columns: food_en, food_ja, source_id, direction, quote.
    """
    return _add_food_key(pd.read_csv(path))


def load_sources(path=SOURCES_CSV) -> pd.DataFrame:
    return pd.read_csv(path)


def _tier_source_ids(sources: pd.DataFrame, tier: int) -> set[str]:
    return set(sources.loc[sources["tier"] <= tier, "source_id"])


def aggregate_axis_a(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    max_tier: int = TIER_ORG,
) -> pd.DataFrame:
    """Per-food Axis A metrics over sources up to and including ``max_tier``.

    Returns columns: food_key, n_warm, n_cool, n_neutral, n_sources,
    direction, consensus. One row per food, sorted by breadth then consensus.
    """
    claims = _add_food_key(claims)
    allowed = _tier_source_ids(sources, max_tier)
    sub = claims[claims["source_id"].isin(allowed)]

    rows = []
    for food, grp in sub.groupby("food_key"):
        # Distinct sources per direction (a source counted once per direction).
        n_warm = grp.loc[grp["direction"] == WARM, "source_id"].nunique()
        n_cool = grp.loc[grp["direction"] == COOL, "source_id"].nunique()
        n_neutral = grp.loc[grp["direction"] == NEUTRAL, "source_id"].nunique()
        n_sources = grp["source_id"].nunique()

        directional = n_warm + n_cool
        if directional == 0:
            direction = NEUTRAL
            consensus = float("nan")
        elif n_warm > n_cool:
            direction = WARM
            consensus = n_warm / directional
        elif n_cool > n_warm:
            direction = COOL
            consensus = n_cool / directional
        else:
            direction = CONTESTED
            consensus = n_warm / directional  # == 0.5

        rows.append(
            {
                "food_key": food,
                "n_warm": n_warm,
                "n_cool": n_cool,
                "n_neutral": n_neutral,
                "n_sources": n_sources,
                "direction": direction,
                "consensus": consensus,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(
        ["n_sources", "consensus"], ascending=[False, False]
    ).reset_index(drop=True)


def coffee_is_representative(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    min_sources: int = COFFEE_REPRESENTATIVE_MIN_SOURCES,
) -> bool:
    """PLAN branch: is "coffee = cools" backed by ≥N Tier-1 sources?

    Decides whether coffee can stay the flagship "belief runs opposite to
    evidence" example, or must be replaced.
    """
    claims = _add_food_key(claims)
    tier1 = _tier_source_ids(sources, TIER_ORG)
    coffee = claims[
        (claims["food_key"] == "coffee")
        & (claims["source_id"].isin(tier1))
        & (claims["direction"] == COOL)
    ]
    return coffee["source_id"].nunique() >= min_sources

"""Behaviour tests for Axis A aggregation (consensus coverage).

Tests the aggregation contract, not implementation details: how many sources
call a food warm vs cool, the majority direction, the consensus ratio, tier
separation, the coffee branch, and food-name normalization.
"""

import math

import pandas as pd
import pytest

from src.claim_mapping import (
    CONTESTED,
    aggregate_axis_a,
    coffee_is_representative,
    normalize_food,
)
from src.definitions import COOL, NEUTRAL, TIER_INDIVIDUAL, TIER_ORG, WARM


@pytest.fixture
def sources():
    # 3 Tier-1 sources, 2 Tier-2 sources.
    return pd.DataFrame(
        {
            "source_id": ["s1", "s2", "s3", "b1", "b2"],
            "tier": [1, 1, 1, 2, 2],
        }
    )


@pytest.fixture
def claims():
    # ginger: warm in s1,s2,s3 (unanimous, Tier1) + b1 (Tier2)
    # coffee: cool in s1,s2,s3 (3 Tier-1) — passes coffee branch
    # cucumber: cool in s1, warm in s2 — contested at Tier1
    # miso: warm in b1,b2 only (Tier2) — absent from Tier1
    return pd.DataFrame(
        [
            {"food_en": "ginger", "food_ja": "生姜", "source_id": "s1", "direction": WARM, "quote": "温性"},
            {"food_en": "ginger", "food_ja": "しょうが", "source_id": "s2", "direction": WARM, "quote": "体を温める"},
            {"food_en": "ginger", "food_ja": "生姜", "source_id": "s3", "direction": WARM, "quote": "陽性"},
            {"food_en": "ginger", "food_ja": "生姜", "source_id": "b1", "direction": WARM, "quote": "温"},
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "s1", "direction": COOL, "quote": "陰性"},
            {"food_en": "coffee", "food_ja": "珈琲", "source_id": "s2", "direction": COOL, "quote": "体を冷やす"},
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "s3", "direction": COOL, "quote": "涼"},
            {"food_en": "cucumber", "food_ja": "きゅうり", "source_id": "s1", "direction": COOL, "quote": "寒"},
            {"food_en": "cucumber", "food_ja": "胡瓜", "source_id": "s2", "direction": WARM, "quote": "温"},
            {"food_en": "miso", "food_ja": "味噌", "source_id": "b1", "direction": WARM, "quote": "温"},
            {"food_en": "miso", "food_ja": "味噌", "source_id": "b2", "direction": WARM, "quote": "陽性"},
        ]
    )


def test_normalize_food_folds_synonyms():
    assert normalize_food("しょうが") == "ginger"
    assert normalize_food("生姜") == "ginger"
    assert normalize_food("珈琲") == "coffee"
    # Unknown names pass through, trimmed.
    assert normalize_food("  なつめ ") == "なつめ"


def test_tier1_aggregation_counts_distinct_sources(claims, sources):
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    ginger = agg[agg["food_key"] == "ginger"].iloc[0]
    # Tier1 only: s1,s2,s3 — the Tier2 b1 row must not be counted.
    assert ginger["n_warm"] == 3
    assert ginger["n_cool"] == 0
    assert ginger["n_sources"] == 3
    assert ginger["direction"] == WARM
    assert ginger["consensus"] == pytest.approx(1.0)


def test_coffee_majority_cool(claims, sources):
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    coffee = agg[agg["food_key"] == "coffee"].iloc[0]
    assert coffee["n_cool"] == 3
    assert coffee["direction"] == COOL
    assert coffee["consensus"] == pytest.approx(1.0)


def test_contested_food_is_flagged_with_half_consensus(claims, sources):
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    cuke = agg[agg["food_key"] == "cucumber"].iloc[0]
    assert cuke["n_warm"] == 1
    assert cuke["n_cool"] == 1
    assert cuke["direction"] == CONTESTED
    assert cuke["consensus"] == pytest.approx(0.5)


def test_tier1_excludes_tier2_only_foods(claims, sources):
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    # miso appears only in Tier2 blogs → absent from the Tier1 frame.
    assert "miso" not in set(agg["food_key"])


def test_sensitivity_tier_includes_individual_sources(claims, sources):
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_INDIVIDUAL)
    assert "miso" in set(agg["food_key"])
    ginger = agg[agg["food_key"] == "ginger"].iloc[0]
    # Now b1 counts too: 4 warming sources.
    assert ginger["n_warm"] == 4
    assert ginger["n_sources"] == 4


def test_food_absent_from_all_sources_not_in_output(claims, sources):
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    assert "durian" not in set(agg["food_key"])


def test_neutral_only_food_has_nan_consensus(sources):
    claims = pd.DataFrame(
        [
            {"food_en": "rice", "food_ja": "米", "source_id": "s1", "direction": NEUTRAL, "quote": "平"},
        ]
    )
    agg = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    rice = agg[agg["food_key"] == "rice"].iloc[0]
    assert rice["direction"] == NEUTRAL
    assert math.isnan(rice["consensus"])
    assert rice["n_sources"] == 1


def test_coffee_representative_passes_with_three_tier1_cool(claims, sources):
    assert coffee_is_representative(claims, sources) is True


def test_coffee_representative_fails_below_threshold(sources):
    claims = pd.DataFrame(
        [
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "s1", "direction": COOL, "quote": "陰性"},
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "s2", "direction": COOL, "quote": "涼"},
            # only 2 Tier-1 cool → below the min of 3
        ]
    )
    assert coffee_is_representative(claims, sources) is False


def test_coffee_representative_ignores_tier2(sources):
    # 2 Tier-1 cool + 2 Tier-2 cool: Tier2 must not push it over the threshold.
    claims = pd.DataFrame(
        [
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "s1", "direction": COOL, "quote": "陰"},
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "s2", "direction": COOL, "quote": "涼"},
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "b1", "direction": COOL, "quote": "陰"},
            {"food_en": "coffee", "food_ja": "コーヒー", "source_id": "b2", "direction": COOL, "quote": "陰"},
        ]
    )
    assert coffee_is_representative(claims, sources) is False


def test_empty_claims_returns_empty_frame(sources):
    agg = aggregate_axis_a(pd.DataFrame(columns=["food_en", "food_ja", "source_id", "direction", "quote"]), sources, max_tier=TIER_ORG)
    assert agg.empty

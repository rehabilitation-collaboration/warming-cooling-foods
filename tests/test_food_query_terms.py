"""Behaviour tests for Axis B query-term construction.

Tests the query-building contract, not implementation details: the plain name is
always searched, curated synonyms are OR-ed in, MeSH augmentation is opt-in,
composite labels are refused, and the L1/L2/L3 layers nest correctly. No network
here — this mirrors the module, which only builds strings.
"""

import pytest

from src.food_query_terms import (
    EFFECT_TERMS,
    EXCLUDE,
    food_terms,
    is_queryable,
    pubmed_query,
)


def test_effect_vocab_covers_every_accepted_outcome_class():
    """The query has to be at least as wide as the screen it feeds.

    Widened from four terms to twenty-two on 2026-08-08. The four-term set was
    narrower than `screening_protocol.md` §2 condition 3, so a study could be
    absent for never having been offered the criterion it met — demonstrated by
    Fagundes 2021, a ginger crossover trial measuring TEF, indirect calorimetry
    and axillary temperature, which none of the four terms retrieve. This test
    pins one term per accepted outcome class so the vocabulary cannot silently
    narrow back below the inclusion rule.
    """
    assert len(EFFECT_TERMS) == 22
    assert len(set(EFFECT_TERMS)) == 22, "duplicate effect term"
    for required in (
        "body temperature", "core temperature", "skin temperature",
        "tympanic temperature", "axillary temperature",   # §2.3 temperature sites
        "thermogenesis", "thermic effect",                 # §2.3 thermogenesis/TEF
        "energy expenditure",                              # §2.3 EE in thermogenic context
        "peripheral circulation", "blood flow", "microcirculation",
        "thermoregulation", "cold tolerance",
        "thermal sensation", "cold sensitivity",           # §2.3 subjective
    ):
        assert required in EFFECT_TERMS, f"{required!r} dropped from the effect vocabulary"


def test_effect_vocab_retains_the_terms_that_recover_the_known_miss():
    # Fagundes 2021 is retrieved only via these two. Losing either reopens the
    # false negative the 2026-08-08 widening exists to close.
    assert "axillary temperature" in EFFECT_TERMS
    assert "energy expenditure" in EFFECT_TERMS


def test_plain_food_uses_bare_name_only():
    assert food_terms("banana") == ["banana"]


def test_japanese_food_adds_curated_synonyms():
    terms = food_terms("natto")
    assert "natto" in terms
    assert "fermented soybean" in terms


def test_mesh_is_opt_in_only():
    assert "Zingiber officinale" not in food_terms("ginger")
    assert "Zingiber officinale" in food_terms("ginger", with_mesh=True)


def test_food_terms_deduplicates_preserving_order():
    # No synonym duplicates the name for these; order stays name-first.
    terms = food_terms("daikon")
    assert terms[0] == "daikon"
    assert len(terms) == len(set(terms))


def test_composite_label_is_not_queryable():
    assert is_queryable("red meat and fish") is False
    assert is_queryable("banana") is True


def test_excluded_food_raises_with_reason():
    with pytest.raises(ValueError):
        food_terms("red meat and fish")
    with pytest.raises(ValueError):
        pubmed_query("nuts")


def test_l1_is_food_only():
    q = pubmed_query("banana", "L1")
    assert q == "banana[tiab]"
    assert "AND" not in q


def test_l2_adds_effect_group():
    q = pubmed_query("banana", "L2")
    assert q.startswith("banana[tiab] AND (")
    assert "thermogenesis[tiab]" in q
    assert '"body temperature"[tiab]' in q
    # multiword phrases quoted, single words not
    assert "thermoregulation[tiab]" in q


def test_l3_narrows_l2_with_rct_filter():
    q = pubmed_query("banana", "L3")
    assert q.startswith(pubmed_query("banana", "L2"))
    assert '"randomized controlled trial"[pt]' in q


def test_multiword_food_synonym_is_quoted():
    q = pubmed_query("natto", "L2")
    assert '"fermented soybean"[tiab]' in q
    # the food OR-group is parenthesized when there are multiple terms
    assert q.startswith("(natto[tiab] OR")


def test_unknown_layer_raises():
    with pytest.raises(ValueError):
        pubmed_query("banana", "L9")


def test_all_excluded_labels_are_category_composites():
    # Sanity: every excluded key carries a non-empty reason string.
    assert all(reason.strip() for reason in EXCLUDE.values())

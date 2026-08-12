"""Tests for the Axis A framing split (review round 3, item 3)."""

import pandas as pd
import pytest

from src.claim_framing import (
    FRAMINGS,
    classify_claims,
    framed_model_frame,
    framing_counts,
    framing_population_gap,
    load_framing_claims,
    select_framing,
)
from src.claim_mapping import load_claims, load_sources
from src.definitions import CLAIMS_FROZEN_CSV, TIER_ORG


def _sources():
    return pd.DataFrame(
        [
            {"source_id": "s_phys", "tier": 1},
            {"source_id": "s_tcm", "tier": 1},
            {"source_id": "s_both", "tier": 1},
            {"source_id": "s_label", "tier": 1},
            {"source_id": "s_tier2", "tier": 2},
        ]
    )


def _claims():
    return pd.DataFrame(
        [
            # A stated bodily effect only.
            {"food_en": "ginger", "food_ja": "しょうが", "source_id": "s_phys",
             "direction": "warm", "quote": "しょうがは体を温める食べ物です", "condition": ""},
            # Five-natures only.
            {"food_en": "ginger", "food_ja": "しょうが", "source_id": "s_tcm",
             "direction": "warm", "quote": "しょうがは陽性の食材です", "condition": ""},
            # Both vocabularies in one quote — the case that forces a per-quote split.
            {"food_en": "ginger", "food_ja": "しょうが", "source_id": "s_both",
             "direction": "warm", "quote": "体を温める食材(陽性)＞薬味: しょうが", "condition": ""},
            # A bare category label.
            {"food_en": "ginger", "food_ja": "しょうが", "source_id": "s_label",
             "direction": "warm", "quote": "＜温食材＞調味料: しょうが", "condition": ""},
            # Direction read off the surrounding text; no thermal wording here.
            {"food_en": "mozuku seaweed", "food_ja": "もずく", "source_id": "s_phys",
             "direction": "cool", "quote": "もずくは味噌汁に加えられます", "condition": ""},
        ]
    )


def _counts():
    return pd.DataFrame(
        [
            {"food_key": "ginger", "food_ja": "しょうが", "scope": "core",
             "l2_raw": 40, "l2_screened": 12.0, "n_openalex": 0, "l1": 5000},
            {"food_key": "mozuku seaweed", "food_ja": "もずく", "scope": "single",
             "l2_raw": 0, "l2_screened": 0.0, "n_openalex": 0, "l1": 100},
        ]
    )


class TestClassifyClaims:
    def test_flags_cover_every_row_exactly_once_outside_physio_tcm_overlap(self):
        tagged = classify_claims(_claims())
        # label/context are defined as "none of the richer classes matched", so
        # the four flags must partition the rows once the physio/tcm overlap is
        # collapsed. A row falling through all four would be silently dropped
        # from every framing.
        covered = (
            tagged["is_physio"] | tagged["is_tcm"] | tagged["is_label"] | tagged["is_context"]
        )
        assert covered.all()

    def test_a_quote_carrying_both_vocabularies_is_in_both(self):
        tagged = classify_claims(_claims())
        both = tagged[tagged["source_id"] == "s_both"].iloc[0]
        assert both["is_physio"] and both["is_tcm"]
        # ...and therefore in neither residual class.
        assert not both["is_label"] and not both["is_context"]

    def test_category_label_is_not_counted_as_a_stated_effect(self):
        tagged = classify_claims(_claims())
        label = tagged[tagged["source_id"] == "s_label"].iloc[0]
        assert label["is_label"]
        assert not label["is_physio"] and not label["is_tcm"]

    def test_quote_without_thermal_wording_falls_to_context(self):
        tagged = classify_claims(_claims())
        ctx = tagged[tagged["food_en"] == "mozuku seaweed"].iloc[0]
        assert ctx["is_context"]
        assert not (ctx["is_physio"] or ctx["is_tcm"] or ctx["is_label"])

    def test_missing_quote_column_fails_loudly(self):
        with pytest.raises(ValueError, match="quote"):
            classify_claims(_claims().drop(columns=["quote"]))


class TestSelectFraming:
    def test_physio_excludes_the_tcm_only_source_but_keeps_the_overlap(self):
        kept = set(select_framing(_claims(), "physio")["source_id"])
        assert kept == {"s_phys", "s_both"}

    def test_tcm_excludes_the_plain_language_sources(self):
        kept = set(select_framing(_claims(), "tcm")["source_id"])
        assert kept == {"s_tcm", "s_both"}

    def test_nontcm_adds_the_label_source_to_physio(self):
        kept = set(select_framing(_claims(), "nontcm")["source_id"])
        assert kept == {"s_phys", "s_both", "s_label"}

    def test_unknown_framing_fails_loudly(self):
        with pytest.raises(ValueError, match="unknown framing"):
            select_framing(_claims(), "yin")

    def test_framings_are_all_selectable(self):
        for framing in FRAMINGS:
            assert not select_framing(_claims(), framing).empty


class TestFramingCounts:
    def test_both_column_is_the_overlap_not_the_sum(self):
        table = framing_counts(_claims()).set_index("source_id")
        row = table.loc["s_both"]
        assert row["physio"] == 1 and row["tcm"] == 1 and row["both"] == 1


class TestFramedModelFrame:
    def test_breadth_is_recounted_within_the_framing(self):
        # ginger is named by all four Tier-1 sources, but only two of them frame
        # it as a five-natures classification.
        tcm = framed_model_frame(_claims(), _sources(), _counts(), "tcm")
        assert int(tcm.loc[tcm["food_key"] == "ginger", "n_sources"].iloc[0]) == 2

        physio = framed_model_frame(_claims(), _sources(), _counts(), "physio")
        assert int(physio.loc[physio["food_key"] == "ginger", "n_sources"].iloc[0]) == 2

        nontcm = framed_model_frame(_claims(), _sources(), _counts(), "nontcm")
        assert int(nontcm.loc[nontcm["food_key"] == "ginger", "n_sources"].iloc[0]) == 3

    def test_food_with_no_claim_in_this_framing_is_reported_not_absorbed(self):
        # mozuku is only ever a context row, so it leaves every framing. That is
        # the split working, not a desync, so it must be recorded rather than
        # raised on — but it must not vanish unrecorded either.
        frame = framed_model_frame(_claims(), _sources(), _counts(), "physio")
        assert "mozuku seaweed" not in set(frame["food_key"])
        assert frame.attrs["outside_framing"] == ["mozuku seaweed"]

    def test_tier2_sources_stay_out_of_the_primary_frame(self):
        claims = pd.concat(
            [
                _claims(),
                pd.DataFrame(
                    [{"food_en": "ginger", "food_ja": "しょうが", "source_id": "s_tier2",
                      "direction": "warm", "quote": "しょうがは体を温めます", "condition": ""}]
                ),
            ],
            ignore_index=True,
        )
        frame = framed_model_frame(claims, _sources(), _counts(), "physio")
        assert int(frame.loc[frame["food_key"] == "ginger", "n_sources"].iloc[0]) == 2


class TestFramingInput:
    def test_the_split_reads_the_frozen_coding(self):
        assert load_framing_claims().equals(pd.read_csv(CLAIMS_FROZEN_CSV))

    def test_the_classifier_can_actually_read_its_input(self):
        # The guard that the RD-4 change needed and did not have. The ledger
        # projection's `quote` is the candidate span a coder judged, not the
        # sentence the source wrote, so classifying it puts more than half of the
        # Tier-1 rows in CONTEXT and empties LABEL. Repointing this loader at
        # data/claims.csv fails both assertions.
        claims = load_framing_claims()
        sources = load_sources()
        tier1 = claims[
            claims["source_id"].isin(set(sources.loc[sources["tier"] <= TIER_ORG, "source_id"]))
        ]
        tagged = classify_claims(tier1)
        assert tagged["is_context"].mean() < 0.05
        assert tagged["is_label"].sum() > 0


class TestFramingPopulationGap:
    def _pairs(self, rows):
        return pd.DataFrame(
            [{"source_id": s, "food_en": f, "quote": "", "direction": "warm"} for s, f in rows]
        )

    def test_pairs_are_split_three_ways(self):
        gap = framing_population_gap(
            self._pairs([("s_phys", "ginger"), ("s_tcm", "carrot")]),
            self._pairs([("s_phys", "ginger"), ("s_both", "onion")]),
            _sources(),
        )
        assert gap == {"shared": 1, "framing_only": 1, "ledger_only": 1}

    def test_tier2_pairs_are_outside_the_primary_frame(self):
        gap = framing_population_gap(
            self._pairs([("s_tier2", "ginger")]),
            self._pairs([("s_tier2", "ginger")]),
            _sources(),
        )
        assert gap == {"shared": 0, "framing_only": 0, "ledger_only": 0}

    def test_every_classified_pair_is_accounted_for_on_the_real_data(self):
        # shared + framing_only must exhaust the frozen coding: a pair may not
        # fall out of the tally just because the ledger does not carry it.
        framing_claims, claims, sources = load_framing_claims(), load_claims(), load_sources()
        gap = framing_population_gap(framing_claims, claims, sources)
        tiers = set(sources.loc[sources["tier"] <= TIER_ORG, "source_id"])
        sub = framing_claims[framing_claims["source_id"].isin(tiers)]
        assert gap["shared"] + gap["framing_only"] == len(set(zip(sub["source_id"], sub["food_en"])))
        assert gap["shared"] > 0

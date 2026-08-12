"""Folding preparations into the food they are a preparation of.

The ledger's coders named preparations as foods (`boiled egg`, `raw ginger`,
`coarse sea salt`). `food_en` is what Axis B joins on, so left alone each one
reads as a food needing its own PubMed query, and — because the analysis frame
is built from `pubmed_counts.csv` — silently leaves the frame instead.
"""

import pandas as pd
import pytest

from src.build_claims import PREP_PARENT, collapse, fold_preparations


def _inc(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {"quote": "…", "sublabels": "", **r} for r in rows
    ])


class TestFoldPreparations:
    def test_a_preparation_takes_the_parent_food_en(self):
        out = fold_preparations(_inc([
            {"food_en": "boiled egg", "food_ja": "ゆでたまご",
             "source_id": "onkatsu_note", "direction": "warm"},
        ]))
        assert out["food_en"].tolist() == ["egg"]

    def test_the_japanese_label_is_left_alone(self):
        # The frozen file keeps 塩サケ as food_ja under food_en=salmon; the
        # preparation stays visible, it just stops being its own food.
        out = fold_preparations(_inc([
            {"food_en": "raw ginger", "food_ja": "生しょうが",
             "source_id": "karada_onkatsu", "direction": "warm"},
        ]))
        assert out["food_ja"].tolist() == ["生しょうが"]
        assert out["food_en"].tolist() == ["ginger"]

    def test_a_food_outside_the_map_is_untouched(self):
        out = fold_preparations(_inc([
            {"food_en": "yogurt", "food_ja": "ヨーグルト",
             "source_id": "karada_onkatsu", "direction": "neutral"},
        ]))
        assert out["food_en"].tolist() == ["yogurt"]

    @pytest.mark.parametrize("food_en", ["dried persimmon", "dried daikon",
                                         "freeze-dried tofu"])
    def test_preparations_that_contradict_their_parent_are_not_folded(self, food_en):
        # These are preparations too, and they keep their own key because the
        # same source gives them the opposite direction from the parent —
        # attaka_navi has 干し柿 warm against 柿 cool, prezo 切り干し大根 warm
        # against 大根 cool, gveggie 高野豆腐 warm against 豆腐 cool. Folding
        # them would make claims.csv assert both directions for one (food,
        # source). That test is what separates them from the nine below, so it
        # has to stay visible in the code.
        assert food_en not in PREP_PARENT

    def test_folding_is_not_chained(self):
        # No parent is itself a key, so one pass is enough and the map cannot
        # depend on iteration order.
        assert not set(PREP_PARENT) & set(PREP_PARENT.values())

    def test_a_folded_row_merges_into_the_parent_when_the_source_agrees(self):
        # oitr says both 卵 and ゆで卵 are warm, so after folding §2's unit
        # (food, source) holds once — and the shorter label is the row, which is
        # §9.4 rule 2's tie-break.
        out = collapse(fold_preparations(_inc([
            {"food_en": "egg", "food_ja": "卵", "source_id": "oitr",
             "direction": "warm"},
            {"food_en": "boiled egg", "food_ja": "ゆで卵", "source_id": "oitr",
             "direction": "warm"},
        ])))
        assert len(out) == 1
        assert out["food_ja"].tolist() == ["卵"]

    def test_a_folded_row_survives_where_the_source_has_no_parent_row(self):
        # onkatsu_note names only ゆでたまご. Folding must not drop the source
        # from egg's breadth — that is the count the whole Axis A rests on.
        out = collapse(fold_preparations(_inc([
            {"food_en": "egg", "food_ja": "卵", "source_id": "oitr",
             "direction": "warm"},
            {"food_en": "boiled egg", "food_ja": "ゆでたまご",
             "source_id": "onkatsu_note", "direction": "warm"},
        ])))
        assert sorted(out["source_id"]) == ["oitr", "onkatsu_note"]
        assert set(out["food_en"]) == {"egg"}

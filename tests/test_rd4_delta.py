"""Behaviour tests for RD-4's delta classification.

The number this module produces decides RD-5's size — how many foods need a
PubMed query built and screened — so the two ways it can be wrong both cost
real work: counting one referent under several English names inflates it, and
folding two different foods together hides one.
"""

import pandas as pd

from src import rd4_delta as rd


def _rows(**kw) -> pd.DataFrame:
    base = {"source_id": "s1", "food_ja": "x", "food_en": "x",
            "direction": "warm", "sublabels": "", "final_label": "include"}
    base.update(kw)
    return pd.DataFrame([base])


class TestNormEn:
    def test_folds_plural_and_phrasing_of_one_referent(self):
        """The coders named foods independently, so one food got several names."""
        keys = {rd._norm_en(s) for s in
                ("cold-region fruit", "cold-region fruits", "fruit cold region")}
        assert len(keys) == 1

    def test_drops_a_parenthetical_gloss(self):
        assert rd._norm_en("koya tofu (freeze-dried tofu)") == rd._norm_en("koya tofu")

    def test_keeps_different_foods_apart(self):
        assert rd._norm_en("green tea") != rd._norm_en("black tea")
        assert rd._norm_en("white sugar") != rd._norm_en("sugar")


class TestKata:
    def test_joins_the_two_scripts_of_one_name(self):
        assert rd.kata("じゃがいも") == rd.kata("ジャガイモ")

    def test_does_not_join_different_names(self):
        assert rd.kata("だいこん") != rd.kata("にんじん")


class TestDelta:
    def test_a_food_already_in_claims_is_not_new(self):
        claims = pd.DataFrame([{"source_id": "s1", "food_ja": "生姜",
                                "food_en": "ginger", "direction": "warm"}])
        out = rd.delta(_rows(food_ja="生姜", food_en="ginger"), claims)
        assert out.empty

    def test_a_kana_spelling_variant_is_not_new(self):
        """じゃがいも in the ledger against ジャガイモ in claims is one food."""
        claims = pd.DataFrame([{"source_id": "s1", "food_ja": "ジャガイモ",
                                "food_en": "potato", "direction": "cool"}])
        out = rd.delta(_rows(food_ja="じゃがいも", food_en="potato"), claims)
        assert out.empty

    def test_category_and_dish_are_held_out_of_the_frame(self):
        """D30: no single-food query represents them, so they never reach RD-5."""
        claims = pd.DataFrame(columns=["source_id", "food_ja", "food_en", "direction"])
        for sub in ("category", "dish"):
            out = rd.delta(_rows(food_ja="根菜類", food_en="root vegetables",
                                 sublabels=sub), claims)
            assert out["class"].iloc[0] == f"non-queryable ({sub})"

    def test_a_new_english_name_for_a_known_food_is_an_alias_not_a_new_food(self):
        claims = pd.DataFrame([{"source_id": "s0", "food_ja": "にんじん",
                                "food_en": "carrot", "direction": "warm"}])
        out = rd.delta(_rows(food_ja="人参", food_en="carrots"), claims)
        assert out["class"].iloc[0] == "既存食品の別名 (RB-4)"

    def test_a_genuinely_new_food_routes_to_rd5(self):
        claims = pd.DataFrame([{"source_id": "s0", "food_ja": "にんじん",
                                "food_en": "carrot", "direction": "warm"}])
        out = rd.delta(_rows(food_ja="フェンネル", food_en="fennel"), claims)
        assert out["class"].iloc[0].startswith("新規の queryable")

    def test_a_d30_excluded_label_is_not_sent_to_rd5(self):
        """The EXCLUDE list is checked even when no sub-label was written."""
        claims = pd.DataFrame(columns=["source_id", "food_ja", "food_en", "direction"])
        out = rd.delta(_rows(food_ja="海藻", food_en="seaweed"), claims)
        assert out["class"].iloc[0] == "non-queryable (D30 EXCLUDE)"

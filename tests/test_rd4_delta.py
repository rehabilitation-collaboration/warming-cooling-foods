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


class TestBuildClaims:
    """The projection ledger -> claims.csv (D46)."""

    def test_spans_naming_one_food_in_one_source_become_one_claim(self):
        """§2's unit is (food, source); the ledger's is (source, candidate)."""
        from src.build_claims import collapse

        inc = pd.DataFrame([
            {"source_id": "s1", "food_ja": "すりおろし生姜", "food_en": "ginger",
             "direction": "warm", "quote": "q1", "sublabels": ""},
            {"source_id": "s1", "food_ja": "生姜", "food_en": "ginger",
             "direction": "warm", "quote": "q2", "sublabels": ""},
        ])
        out = collapse(inc)
        assert len(out) == 1
        # rule 2's own tie-break: the shorter label is the row
        assert out.iloc[0]["food_ja"] == "生姜"

    def test_a_condition_split_survives_the_collapse(self):
        """§3 requires both sides where the source splits one food by condition."""
        from src.build_claims import collapse

        inc = pd.DataFrame([
            {"source_id": "s1", "food_ja": "豆腐（冷たい）", "food_en": "tofu",
             "direction": "cool", "quote": "q1", "sublabels": ""},
            {"source_id": "s1", "food_ja": "豆腐（温かい）", "food_en": "tofu",
             "direction": "warm", "quote": "q2", "sublabels": ""},
        ])
        assert len(collapse(inc)) == 2

    def test_a_coders_new_english_name_is_canonicalised_to_the_frozen_key(self, tmp_path):
        """food_en is the key Axis B joins on, so drift would orphan the food."""
        from src.build_claims import canonicalise_food_en

        frozen = tmp_path / "frozen.csv"
        pd.DataFrame([{"food_en": "burdock", "food_ja": "ごぼう", "source_id": "s1",
                       "direction": "warm", "quote": "", "condition": ""}]).to_csv(
            frozen, index=False)
        inc = pd.DataFrame([{"source_id": "s1", "food_ja": "ごぼう",
                             "food_en": "burdock root", "direction": "warm", "quote": ""}])
        assert canonicalise_food_en(inc, frozen).iloc[0]["food_en"] == "burdock"

    def test_a_label_the_frozen_file_never_carried_keeps_the_coders_name(self, tmp_path):
        """Canonicalising must not invent a mapping for a genuinely new food."""
        from src.build_claims import canonicalise_food_en

        frozen = tmp_path / "frozen.csv"
        pd.DataFrame([{"food_en": "burdock", "food_ja": "ごぼう", "source_id": "s1",
                       "direction": "warm", "quote": "", "condition": ""}]).to_csv(
            frozen, index=False)
        inc = pd.DataFrame([{"source_id": "s1", "food_ja": "フェンネル",
                             "food_en": "fennel", "direction": "warm", "quote": ""}])
        assert canonicalise_food_en(inc, frozen).iloc[0]["food_en"] == "fennel"

    def test_an_include_missing_its_coded_fields_is_an_error_not_a_blank_row(self, tmp_path):
        """§9.3 requires them on every include; a blank row would reach claims.csv."""
        import pytest

        from src.build_claims import load_includes

        led = tmp_path / "ledger.csv"
        pd.DataFrame([{"source_id": "s1", "candidate": "x", "final_label": "include",
                       "food_ja": "生姜", "food_en": "", "direction": "warm"}]).to_csv(
            led, index=False)
        with pytest.raises(ValueError, match="§9.3"):
            load_includes(led)

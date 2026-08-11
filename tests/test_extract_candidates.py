"""Tests for the Axis A candidate enumeration (Route D, RD-1).

Each case in ``TestStructuralBlindSpots`` is a real line from a frame source that
the first extractor missed. They are kept as regression tests because the misses
were only found by measuring recall against the 649 coded rows — reasoning about
the parser did not surface any of them.
"""

import pandas as pd
import pytest

from src import extract_candidates as ex
from src.verify_candidate_recall import score


def candidates(text: str, source_id: str = "src") -> list[str]:
    return ex.extract_source(source_id, text)["candidate"].tolist()


class TestExtractionPaths:
    def test_delimited_line_yields_each_item(self):
        got = candidates("きゅうり／トマト／ナス／レタス")
        assert {"きゅうり", "トマト", "ナス", "レタス"} <= set(got)

    def test_labeled_line_splits_the_right_hand_side_only(self):
        got = candidates("野菜：ニンジン、ゴボウ、カボチャ")
        assert {"ニンジン", "ゴボウ", "カボチャ"} <= set(got)

    def test_bare_lines_under_a_thermal_heading_are_items(self):
        # kawashimaya lays its cooling block out one item per line.
        got = candidates("冷たい食べ物\nアイスクリーム\nかき氷")
        assert {"アイスクリーム", "かき氷"} <= set(got)

    def test_a_line_outside_any_thermal_context_yields_nothing(self):
        assert candidates("会員登録\nログイン") == []


class TestStructuralBlindSpots:
    def test_prose_attribution_is_extracted(self):
        # yomeishu: the food sits in running text, not in a list.
        got = candidates("人参やごぼうなどの根菜類、味噌など色が濃いものも「陽性」に分類されます。")
        assert any("味噌" in c for c in got)

    def test_thermal_word_on_an_adjacent_line_still_opens_prose(self):
        # hiesyo_com renders <strong>陰性食品</strong> onto its own line, so the
        # food's line carries no thermal vocabulary of its own.
        got = candidates("南の国で穫れるバナナやパイナップルは\n陰性食品\nです。")
        assert any("バナナ" in c for c in got)
        assert any("パイナップル" in c for c in got)

    def test_heading_naming_a_food_is_not_swallowed_by_the_heading_rule(self):
        # onkatsu_note: short, thermal, no delimiter — shaped exactly like a
        # heading, but it names the food.
        got = candidates("ビールや炭酸系カクテルは体を冷やしやすい")
        assert any("ビール" in c for c in got)

    def test_heading_may_carry_one_delimiter(self):
        # prezo's 体を温める肉・魚 heading opens a one-item-per-line block.
        got = candidates("体を温める肉・魚\n牛肉\n鶏肉")
        assert {"牛肉", "鶏肉"} <= set(got)

    def test_two_delimiters_make_it_a_list_not_a_heading(self):
        got = candidates("体を温める食材：生姜、ねぎ、にんにく")
        assert {"生姜", "ねぎ", "にんにく"} <= set(got)

    def test_parenthetical_enumeration_is_reached(self):
        # macrobiotic_rashinban: 三年番茶 only ever appears inside parentheses.
        got = candidates("刺激の強くない飲み物（三年番茶など） / ナッツ類 / 温帯性の果物")
        assert any("三年番茶" in c for c in got)

    def test_the_source_s_own_parenthetical_label_is_kept_alongside_the_stripped_one(self):
        # claims.csv codes 赤身魚（まぐろなど） verbatim; dropping the qualifier
        # would leave that row unmatchable and まぐろ unseen.
        got = candidates("体を温める魚\n赤身魚（まぐろなど）")
        assert "赤身魚（まぐろなど）" in got
        assert "赤身魚" in got

    def test_the_label_side_of_a_labelled_list_is_itself_a_candidate(self):
        # kawashimaya: 肉類 / 魚類 / 大豆製品 carry the attribution and are
        # codeable categories under coding_protocol.md 9.5, but only the
        # right-hand side was being split. Found by the independent read.
        got = candidates("たんぱく質が多い食材\n肉類：鶏肉、牛肉、豚肉、羊肉")
        assert "肉類" in got
        assert {"鶏肉", "牛肉"} <= set(got)

    def test_prose_inside_a_thermal_block_is_read_even_with_no_thermal_word(self):
        # kawashimaya: the heading supplies the direction and a plain sentence
        # several lines below supplies the food. Also found by the independent read.
        text = "たんぱく質が多い食材は…温活に効果的です。\n卵\n脂身の少ない赤身肉や、赤身の魚を選ぶとよいでしょう。"
        got = candidates(text)
        assert any("赤身肉" in c for c in got)

    def test_an_interpunct_inside_a_compound_term_does_not_destroy_it(self):
        # karada_onkatsu: ・ joins 加熱 and 乾燥 into one modifier here rather
        # than separating two items, so the split forms lose the term the
        # source actually names. Found by the independent read.
        got = candidates("体を温める効果が高い形\n🔥 加熱・乾燥しょうが（ショウガオール）")
        assert any("加熱・乾燥しょうが" in c for c in got)

    def test_a_food_broken_across_a_line_break_is_rejoined(self):
        # macrobiotic_rashinban: get_text("\n") breaks at every inline tag, so
        # 夏野菜 is split as "…代表的な夏野" / "菜に". Nothing line-based can see
        # it — including an independent reader held to the verbatim rule, which
        # is why this class had to be closed on structure rather than evidence.
        got = candidates("陰性になります\n他、代表的な夏野\n菜に\nナスやトマト")
        assert any("夏野菜" in c for c in got)

    def test_kana_food_ending_in_a_particle_survives_as_a_span(self):
        # じゃがいも ends in も, so particle splitting alone destroys it; the
        # clause-level span is what keeps it visible.
        got = candidates("地面の下にできるのにカリウムが多いじゃがいもは陰性です。")
        assert any("じゃがいも" in c for c in got)


class TestCandidateShape:
    def test_candidates_must_contain_a_cjk_character(self):
        assert candidates("2024/02/16\nhttps://example.com/a／b") == []

    def test_comment_lines_are_skipped(self):
        assert candidates("# src\n# TITLE: 体を温める食べ物一覧") == []

    def test_spans_are_capped_so_a_whole_paragraph_never_becomes_one_candidate(self):
        text = "体を温める" + "あ" * 200 + "。"
        assert all(len(c) <= ex.MAX_PROSE_SPAN for c in candidates(text))

    def test_a_span_never_carries_whitespace_at_either_end(self):
        # macrobiotic_rashinban pads every item of its lists with U+2002 EN
        # SPACE, which the decorative TRIM set does not contain, so the strip
        # used to stop at the first character. The result was 34 spans wearing
        # their padding, 33 of which the enumeration also held bare: the same
        # span in two rows, which ledger.py keys to one and drops to a warning
        # on stderr - a candidate silently absent from a ledger whose reason for
        # existing is that nothing goes missing silently.
        #
        # Written with escapes because the character is invisible in a diff, and
        # asserted against TRIM first because an ASCII or ideographic space is
        # already in TRIM: the same test spelled with one would have passed
        # against the unfixed strip.
        assert "\u2002チーズ\u2002".strip(ex.TRIM) != "チーズ"

        got = candidates("陰性食品\n\u2002チーズ\u2002、\u2002卵\u2002、\u2002精製塩\u2002")

        assert got == [c.strip() for c in got]
        assert "チーズ" in got

    def test_a_parenthesised_list_survives_the_delimiters_inside_it(self):
        # The bracket pair is what tells _paren_inner there is an enumeration
        # here, and the enumeration's own delimiters used to cut the pair in
        # half first: 夏野菜（トマト、きゅうり） became 夏野菜（トマト and
        # きゅうり）, neither of which matches a pattern needing both brackets.
        # The foods then reached a coder only inside a span carrying half a
        # bracket, which §9.4 rule 2 excludes as a fragment — correctly, since
        # the source does not present 夏野菜（トマト as an item. Thirteen rows of
        # claims.csv had no other span to be coded from.
        got = candidates("体を冷やす\n夏野菜（トマト、きゅうり）")
        assert "トマト" in got and "きゅうり" in got

    def test_the_same_holds_for_a_parenthesis_inside_running_text(self):
        got = candidates("平性 — 温めも冷やしもしない（米、大豆、卵など）。")
        assert "米" in got and "大豆" in got

    def test_a_span_wearing_both_padding_and_a_separator_loses_both(self):
        # One pass in either order leaves the other's characters behind.
        got = candidates("体を温める\n\u2002・生姜・\u2002")
        assert "生姜" in got
        assert got == [c.strip() for c in got]


class TestDedupe:
    def test_occurrences_collapse_to_one_row_per_source_and_candidate(self):
        occ = ex.extract_source("src", "冷たい食べ物\nかき氷\nかき氷は体を冷やす。")
        unique = ex.dedupe(occ)
        rows = unique[unique["candidate"] == "かき氷"]
        assert len(rows) == 1
        assert rows.iloc[0]["n_occurrences"] >= 2

    def test_the_paths_that_found_a_candidate_are_recorded(self):
        occ = ex.extract_source("src", "体を温める食材\n生姜\n生姜や ねぎは体を温める")
        unique = ex.dedupe(occ)
        paths = unique.loc[unique["candidate"] == "生姜", "paths"].iloc[0]
        assert "scoped" in paths and "prose" in paths


class TestRecallScoring:
    def _claims(self, *pairs):
        return pd.DataFrame(
            [{"source_id": s, "food_ja": f, "food_en": f} for s, f in pairs]
        )

    def _unique(self, *pairs):
        return pd.DataFrame(
            [{"source_id": s, "candidate": c} for s, c in pairs]
        )

    def test_an_identical_token_counts_as_exact_and_covered(self):
        got = score(self._claims(("a", "生姜")), self._unique(("a", "生姜")))
        assert bool(got.iloc[0]["exact"]) and bool(got.iloc[0]["covered"])

    def test_a_containing_span_is_covered_but_not_exact(self):
        got = score(self._claims(("a", "ゴボウ")), self._unique(("a", "ゴボウなどの根菜類")))
        assert not bool(got.iloc[0]["exact"])
        assert bool(got.iloc[0]["covered"])
        assert got.iloc[0]["covering_example"] == "ゴボウなどの根菜類"

    def test_a_candidate_from_another_source_does_not_count(self):
        got = score(self._claims(("a", "生姜")), self._unique(("b", "生姜")))
        assert not bool(got.iloc[0]["covered"])

    def test_a_partial_token_shorter_than_the_food_is_not_covered(self):
        # 「根菜」 does not put 「根菜類」 in front of a coder as its own row.
        got = score(self._claims(("a", "根菜類")), self._unique(("a", "根菜")))
        assert not bool(got.iloc[0]["covered"])


class TestCandidateCsv:
    """The enumeration has to leave the process as a file the batcher reads.

    RD-3 blocked on this: ``main()`` printed its counts and wrote nothing, so
    the batch generator had no input to start from.
    """

    def _unique(self):
        return pd.DataFrame(
            [
                {
                    "source_id": "a", "candidate": "生姜", "n_occurrences": 2,
                    "first_line_no": 7, "lines": [7, 41], "paths": "list|prose",
                    "heading": "体を温める", "line": "生姜、ねぎ",
                }
            ]
        )

    def test_renames_first_line_no_to_the_published_ledger_name(self):
        frame = ex.to_candidate_frame(self._unique())
        assert list(frame.columns) == [
            "source_id", "line_no", "candidate", "n_occurrences", "lines",
            "paths", "heading", "line",
        ]
        assert frame["line_no"].tolist() == [7]

    def test_raises_when_dedupe_output_lacks_a_needed_column(self):
        with pytest.raises(ValueError, match="missing"):
            ex.to_candidate_frame(self._unique().drop(columns=["paths"]))

    def test_write_candidates_round_trips_through_csv(self, tmp_path):
        path = tmp_path / "candidates.csv"
        written = ex.write_candidates(self._unique(), path)
        back = pd.read_csv(path)
        assert len(back) == len(written) == 1
        assert back["candidate"].tolist() == ["生姜"]
        assert back["line_no"].tolist() == [7]

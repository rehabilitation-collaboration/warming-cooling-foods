"""Tests for the §10 worksheet.

The worksheet changes how the audit is entered, not what it asks, so what these
pin is exactly that: the verdict vocabulary cannot grow by accident, the two
sources being read end to end stay hidden until they have been read, and the
files written are the ones the scorer reads.
"""

import pandas as pd
import pytest

from src import audit_sheet
from src.audit_sheet import (
    add_read,
    add_reads_bulk,
    delete_read,
    fragment_link,
    reads_complete,
    render,
    save_verdict,
    split_foods,
)
from src.human_audit import VERDICTS


@pytest.fixture
def sheets(tmp_path, monkeypatch):
    """The two sheets, redirected to a scratch copy so no real audit is touched."""
    results = tmp_path / "results.csv"
    reads = tmp_path / "reads.csv"
    pd.DataFrame({"source_id": ["basefood", "esse"], "food_en": ["chicken", "banana"],
                  "food_ja": ["鶏肉", "バナナ"], "direction": ["warm", "cool"],
                  "verdict": ["", ""], "note": ["", ""]}).to_csv(results, index=False)
    pd.DataFrame(columns=["source_id", "food_ja", "direction", "quote"]).to_csv(
        reads, index=False)
    monkeypatch.setattr(audit_sheet, "RESULTS_CSV", results)
    monkeypatch.setattr(audit_sheet, "READS_CSV", reads)
    return {"results": results, "reads": reads}


class TestFragmentLink:
    def test_a_link_carries_the_quotation_so_the_browser_scrolls_to_it(self):
        link = fragment_link("https://example.com/a", "体を温める食べ物")
        assert link.startswith("https://example.com/a#:~:text=")
        assert "%E4%BD%93" in link  # 体, percent-encoded

    def test_a_row_with_no_quotation_still_links_to_the_page(self):
        assert fragment_link("https://example.com/a", "") == "https://example.com/a"


class TestSaveVerdict:
    def test_a_verdict_lands_in_the_sheet_the_scorer_reads(self, sheets):
        save_verdict(0, "supported")
        assert pd.read_csv(sheets["results"])["verdict"][0] == "supported"

    @pytest.mark.parametrize("bad", ["たぶん合ってる", "Supported", "ok", ""])
    def test_a_value_outside_the_fixed_five_is_refused(self, sheets, bad):
        # The vocabulary was written down before any row was read. Storing a
        # sixth value would change the instrument without anyone deciding to.
        with pytest.raises(ValueError, match="unknown verdict"):
            save_verdict(0, bad)
        assert pd.read_csv(sheets["results"], dtype=str).fillna("")["verdict"][0] == ""

    def test_the_five_it_accepts_are_the_ones_the_protocol_fixed(self):
        assert set(audit_sheet.VERDICT_LABELS) == set(VERDICTS)
        assert set(audit_sheet.VERDICT_EXAMPLES) == set(VERDICTS)


class TestTheGuideDoesNotInventRules:
    def test_every_direction_word_shown_to_the_reader_is_in_the_protocol(self):
        # The worksheet tells the reader which words carry a direction. Those
        # words are §3's, and a term added here that §3 does not hold would be a
        # rule invented at the point of measurement — by the tool, in front of
        # the one human check the paper has.
        protocol = (audit_sheet.DATA_DIR / "coding_protocol.md").read_text(
            encoding="utf-8")
        for _, words in audit_sheet.DIRECTION_VOCABULARY:
            for term in words.split("／"):
                assert term in protocol, f"{term!r} is not in the coding protocol"

        # The worked example is instruction too, and a made-up page is exactly
        # where an invented rule would be hardest to spot. Every row names the
        # term that licenses it; each has to be one §3 holds.
        for food, _direction, _quote, term, _why in audit_sheet.READ_EXAMPLE_ROWS:
            assert term in protocol, f"{food}: {term!r} is not in the coding protocol"

        # The specimen beside the entry form is one of those rows, not a second
        # example able to say something else.
        assert audit_sheet.form_example() in audit_sheet.READ_EXAMPLE_ROWS

    def test_the_example_page_is_not_one_of_the_sources_being_read(self):
        # Quoting the two end-to-end sources in the instructions would hand the
        # reader the answer to the half that matters; quoting a third would
        # reveal part of that source's precision sample.
        page = audit_sheet.READ_EXAMPLE_PAGE
        for source_id in audit_sheet.load_sources()["source_id"]:
            assert source_id not in page


class TestReads:
    def test_a_food_is_appended_with_its_source_and_direction(self, sheets):
        add_read("basefood", "しょうが", "warm", "体を温める")
        row = pd.read_csv(sheets["reads"]).iloc[0]
        assert (row["source_id"], row["food_ja"], row["direction"]) == (
            "basefood", "しょうが", "warm")

    def test_a_blank_food_name_is_refused(self, sheets):
        with pytest.raises(ValueError, match="needs a food name"):
            add_read("basefood", "   ", "warm")

    def test_a_pasted_list_is_split_the_way_these_pages_are_written(self):
        # The sources lay foods out as lists, so the read is mostly transcription
        # and pasting a list is the fast path. A class with its members in
        # brackets becomes the class and the members, which is what the worked
        # example records.
        assert split_foods("にんじん、ごぼう、れんこん") == ["にんじん", "ごぼう", "れんこん"]
        assert split_foods("根菜類（にんじん、ごぼう）") == ["根菜類", "にんじん", "ごぼう"]
        assert split_foods("・しょうが\n・シナモン\n1. なつめ") == ["しょうが", "シナモン", "なつめ"]

    def test_a_pasted_list_lands_at_one_direction(self, sheets):
        assert add_reads_bulk("basefood", "しょうが、シナモン", "warm") == 2
        rows = pd.read_csv(sheets["reads"])
        assert list(rows["food_ja"]) == ["しょうが", "シナモン"]
        assert set(rows["direction"]) == {"warm"}

    def test_the_same_food_twice_is_kept_twice(self, sheets):
        # A page naming a food in two places is a fact about the page. Collapsing
        # it here would be the tool editing the read.
        add_reads_bulk("basefood", "しょうが、しょうが", "warm")
        assert len(pd.read_csv(sheets["reads"])) == 2

    def test_pasting_nothing_is_refused(self, sheets):
        with pytest.raises(ValueError, match="nothing to add"):
            add_reads_bulk("basefood", "　\n・\n", "warm")

    def test_a_row_can_be_taken_back(self, sheets):
        add_read("basefood", "しょうが", "warm")
        add_read("basefood", "誤入力", "cool")
        delete_read(1)
        assert list(pd.read_csv(sheets["reads"])["food_ja"]) == ["しょうが"]


class TestTheGateOnTheEndToEndSources:
    TARGETS = ["basefood", "macaroni"]

    def test_the_gate_stays_shut_until_both_sources_have_been_read(self):
        # The completeness half is worthless if the reader has already seen what
        # the ledger holds for these two, and seven of the sixty precision rows
        # come from them.
        empty = pd.DataFrame(columns=["source_id", "food_ja"])
        assert not reads_complete(empty, self.TARGETS)
        one = pd.DataFrame({"source_id": ["basefood"], "food_ja": ["しょうが"]})
        assert not reads_complete(one, self.TARGETS)
        both = pd.DataFrame({"source_id": ["basefood", "macaroni"],
                             "food_ja": ["しょうが", "きゅうり"]})
        assert reads_complete(both, self.TARGETS)

    def test_the_ledger_rows_for_those_sources_are_withheld_while_it_is_shut(self):
        state = {
            "sample": pd.DataFrame({
                "source_id": ["basefood", "esse"], "url": ["https://a", "https://b"],
                "food_en": ["chicken", "banana"], "food_ja": ["鶏肉", "バナナ"],
                "direction": ["warm", "cool"],
                "quote": ["鶏肉は体を温める", "バナナは体を冷やす"]}),
            "results": pd.DataFrame({"verdict": ["", ""], "note": ["", ""]}),
            "reads": pd.DataFrame(columns=["source_id", "food_ja", "direction", "quote"]),
            "targets": self.TARGETS,
        }
        shut = render(state)
        assert "鶏肉は体を温める" not in shut
        assert "バナナは体を冷やす" in shut

        state["reads"] = pd.DataFrame({
            "source_id": self.TARGETS, "food_ja": ["しょうが", "きゅうり"],
            "direction": ["warm", "cool"], "quote": ["", ""]})
        assert "鶏肉は体を温める" in render(state)

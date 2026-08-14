"""Tests for the positional prose check.

The table check gave a cell an address. These tests pin the same question for a
sentence: is the number it prints the quantity its own words name? Five of the
six numeric errors an external review found sat in prose and passed the token
walk, because each printed a number that was real somewhere else in the
pipeline.
"""

import pytest

from src.manuscript_prose import (
    COLLECTED,
    FACTS,
    OUT_OF_SCOPE,
    Fact,
    _agrees,
    check_prose,
    collected_tests,
    locate,
    spelled_census,
    token_value,
    word_value,
)
from src.verify_manuscript import MANUSCRIPT, pipeline_inputs, pipeline_values


class TestWordValue:
    def test_the_compound_forms_the_manuscript_uses_are_read(self):
        assert word_value("nine") == 9
        assert word_value("Twenty-four") == 24
        assert word_value("One hundred and three") == 103

    def test_a_fraction_names_its_proportion(self):
        assert word_value("three-quarters") == 0.75
        assert word_value("two-thirds") == pytest.approx(2 / 3)

    def test_a_word_that_counts_nothing_is_not_a_number(self):
        assert word_value("ginger") is None
        assert word_value("") is None

    def test_a_digit_token_keeps_its_thousands_separator(self):
        assert token_value("12,733") == 12733
        assert token_value("eight") == 8


class TestAgrees:
    def test_a_value_is_read_at_the_precision_the_sentence_prints(self):
        # 6.2439% may be written 6.2; it may not be written 6.3.
        assert _agrees("6.2", 6.2439, None)
        assert not _agrees("6.3", 6.2439, None)

    def test_a_spelled_value_is_compared_as_a_number(self):
        assert _agrees("nine", 9.0, None)
        assert not _agrees("eight", 9.0, None)

    def test_a_fraction_is_compared_within_the_tolerance_it_declares(self):
        assert _agrees("two-thirds", 0.6575, 0.05)
        assert not _agrees("two-thirds", 0.6575, 0.001)


class TestLocate:
    def test_a_sentence_that_moved_fails_loudly(self):
        # Silently checking nothing is the failure mode a list of line numbers
        # has every time it has been written for this manuscript.
        fact = Fact("gone", r"a sentence that is not there (\d+)")
        with pytest.raises(ValueError, match="locates 0 sentences"):
            locate("some other prose 5\n", fact)

    def test_a_locator_that_matches_twice_fails_loudly(self):
        fact = Fact("ambiguous", r"(\d+) foods")
        with pytest.raises(ValueError, match="locates 2 sentences"):
            locate("146 foods here and 190 foods there\n", fact)


class TestCheckProse:
    TEXT = "Of the 146 foods, 96 have none, and nine sources cover carrot.\n"

    def test_a_stale_value_is_reported_against_the_quantity_named(self):
        fact = Fact("zero", r"Of the (\d+) foods, (\d+) have none",
                    lambda c: [146, 97])
        findings = check_prose(self.TEXT, pipeline_inputs(), (fact,))
        assert [(f["printed"], f["expected"]) for f in findings] == [("96", "97")]

    def test_a_spelled_value_is_checked_where_a_digit_would_be(self):
        # The class the token walk cannot reach at all: "all nine sources" was
        # printed "eight of nine" and never entered the walk's token list.
        fact = Fact("carrot", r"and (\w+) sources cover carrot", lambda c: [8])
        findings = check_prose(self.TEXT, pipeline_inputs(), (fact,))
        assert [(f["printed"], f["expected"]) for f in findings] == [("nine", "8")]

    def test_a_fact_whose_captures_and_expectations_disagree_fails_loudly(self):
        fact = Fact("mismatched", r"Of the (\d+) foods, (\d+) have none",
                    lambda c: [146])
        with pytest.raises(ValueError, match="captures 2 values but expects 1"):
            check_prose(self.TEXT, pipeline_inputs(), (fact,))


class TestCollectedTests:
    def test_the_collector_line_is_read(self):
        assert COLLECTED.search("400 tests collected in 0.57s").group(1) == "400"
        assert COLLECTED.search("1 test collected in 0.1s").group(1) == "1"

    def test_a_collector_that_will_not_run_reports_unchecked_rather_than_guessing(
            self, monkeypatch):
        # A reader of the published repository need not have the test runner.
        # Guessing the number, or crashing the whole report over it, would both
        # be worse than saying the value was not checked here.
        collected_tests.cache_clear()
        monkeypatch.setattr("src.manuscript_prose.subprocess.run",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("no pytest")))
        try:
            assert collected_tests() is None
            fact = Fact("count", r"covered by (\d+) unit tests",
                        lambda c: [collected_tests()])
            findings = check_prose("covered by 342 unit tests\n",
                                   pipeline_inputs(), (fact,))
            assert findings[0]["expected"].startswith("unchecked")
        finally:
            collected_tests.cache_clear()


class TestSpelledCensus:
    def test_anchored_and_unchecked_exhaust_what_was_found(self):
        # Same property that makes the token walk auditable: no third, silent
        # bucket.
        census = spelled_census(MANUSCRIPT.read_text(encoding="utf-8"))
        assert census["anchored"] + sum(census["unanchored"].values()) == census["total"]
        assert census["anchored"] > 0

    def test_the_walk_could_not_have_vouched_for_these(self):
        # The measurement the design rests on. If this ever stops holding, the
        # reason spelled numerals are kept out of the token walk stops holding
        # with it, and the split should be revisited rather than inherited.
        values = pipeline_values(pipeline_inputs())
        assert all(str(n) in values for n in range(1, 21))


class TestCatchesWhatGotThrough:
    """Reintroduce errors that reached print, and require the check to find them.

    Each of these passed both the token walk and the table checks. The first is
    a digit the pipeline held as a different quantity, the second a number
    written as a word and therefore never tokenised at all, the third a derived
    interval left at the value its old inputs produced — the clue that exposed
    seven stale numbers in an earlier revision. The fourth reached an external
    reviewer: the count of unplanned analyses moved to seventeen and one of the
    three sentences stating it kept the old word. The fifth is the confusion the
    fourth invites, the exact-offset estimate written as the reported one.
    """

    MUTATIONS = [
        ("the same model with the same 50 events",
         "the same model with the same 49 events"),
        ("carrot at all nine Tier-1 sources",
         "carrot at all eight Tier-1 sources"),
        ("an odds ratio from 0.35 to 7.62",
         "an odds ratio from 0.35 to 8.21"),
        ("and seventeen reported analyses were computed outside it",
         "and fifteen reported analyses were computed outside it"),
        ("coverage at HR 1.035 (0.892–1.202)",
         "coverage at HR 1.036 (0.892–1.202)"),
    ]

    @pytest.mark.parametrize("original,stale", MUTATIONS)
    def test_a_reintroduced_error_is_reported(self, original, stale):
        text = MANUSCRIPT.read_text(encoding="utf-8")
        assert text.count(original) == 1, "the sentence this mutation edits moved"
        inputs = pipeline_inputs()
        clean = check_prose(text, inputs)
        assert len(check_prose(text.replace(original, stale), inputs)) > len(clean)


class TestAgainstTheRealManuscript:
    def test_every_fact_still_finds_the_sentence_it_checks(self):
        # Pins the locators to the text as it stands. A reworded sentence has to
        # be noticed here, not by the check quietly covering one fewer number.
        text = MANUSCRIPT.read_text(encoding="utf-8")
        for fact in FACTS + OUT_OF_SCOPE:
            locate(text, fact)

    def test_every_expectation_can_be_computed_from_the_pipeline(self):
        # Disagreements are `verify_manuscript`'s report to make, not this
        # suite's; what is pinned here is that each fact resolves against the
        # real frames at all.
        check_prose(MANUSCRIPT.read_text(encoding="utf-8"), pipeline_inputs())

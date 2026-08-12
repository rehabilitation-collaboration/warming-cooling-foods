"""Tests for the claims-independent half of the extraction check (RD-1b).

Recall against the frozen coding cannot speak for a food no coder ever
recorded. This check reads no coded data at all: it asks whether any line that
could be carrying an attribution went unexamined.
"""

import pandas as pd

from src.verify_candidate_recall import thermal_line_coverage


class TestThermalLineCoverage:
    def test_a_thermal_line_that_yielded_no_candidate_is_flagged(self):
        texts = {"s1": "体を温める食べ物\nしょうが\n"}
        occurrences = pd.DataFrame({"source_id": ["s1"], "line_no": [2]})
        thermal = thermal_line_coverage(occurrences, texts).query("thermal")
        assert list(thermal["line_no"]) == [1]
        assert not thermal["has_candidate"].any()

    def test_a_thermal_line_that_yielded_one_is_not(self):
        texts = {"s1": "体を温める食べ物\nしょうが\n"}
        occurrences = pd.DataFrame({"source_id": ["s1"], "line_no": [1]})
        thermal = thermal_line_coverage(occurrences, texts).query("thermal")
        assert thermal["has_candidate"].all()

    def test_a_line_without_thermal_vocabulary_is_outside_the_check(self):
        # §3 forbids coding a direction the source does not state, so a line
        # carrying no thermal vocabulary cannot be carrying an attribution.
        coverage = thermal_line_coverage(
            pd.DataFrame({"source_id": ["s1"], "line_no": [1]}), {"s1": "今日の天気\n"}
        )
        assert not coverage["thermal"].any()

    def test_markdown_headings_and_blank_lines_are_not_body_text(self):
        coverage = thermal_line_coverage(
            pd.DataFrame({"source_id": ["s1"], "line_no": [3]}),
            {"s1": "# 体を温める食べ物\n\nしょうが\n"},
        )
        assert list(coverage["line_no"]) == [3]

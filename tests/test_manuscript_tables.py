"""Tests for the positional table-cell check (RD-6).

The token walk in `verify_manuscript` asks whether a number occurs anywhere in
the pipeline's output. These tests pin the stronger question this module asks:
whether the number in *this* cell is the quantity *this* row and column name.
"""

import pandas as pd
import pytest

from src.manuscript_tables import _agrees, check_table, table4_expected, table_body

TABLE = """### Table X. Demo

| Set | n foods | Warming |
|---|---:|---:|
| All coded | 196 | — |
| — core | 51 | 31 |

trailing prose
"""

FOODS = "### T\n\n| Food | Sources |\n|---|---:|\n| green onion | 6 |\n"


class TestAgrees:
    def test_a_cell_is_read_at_the_precision_it_prints(self):
        # 98.62% may be written 98.6; 0.8068 may not be written 0.806, because
        # no rounding of the current value produces the printed one.
        assert _agrees("98.6%", [98.62])
        assert not _agrees("0.806", [0.8068])

    def test_a_cell_holding_a_different_count_of_numbers_disagrees(self):
        assert not _agrees("138 / 37", [146.0])
        assert _agrees("146 / 44", [146.0, 44.0])


class TestTableBody:
    def test_the_body_is_the_rows_between_the_rule_and_the_prose(self):
        header, body = table_body(TABLE, "### Table X.")
        assert header == ["Set", "n foods", "Warming"]
        assert [cells[0] for _, cells in body] == ["All coded", "— core"]

    def test_a_missing_table_fails_loudly(self):
        # A renamed table would otherwise check nothing and report nothing,
        # which is the failure this module exists to remove.
        with pytest.raises(ValueError, match="no table headed"):
            table_body(TABLE, "### Table Z.")


class TestCheckTable:
    def test_a_stale_cell_is_reported_against_the_expected_value(self):
        findings = check_table(TABLE, "### Table X.",
                               {"All coded": {"n foods": 301},
                                "core": {"n foods": 51, "Warming": 31}})
        assert [(f["printed"], f["expected"]) for f in findings] == [("196", "301")]

    def test_a_cell_the_manuscript_leaves_blank_is_not_a_disagreement(self):
        findings = check_table(TABLE, "### Table X.",
                               {"All coded": {"n foods": 196, "Warming": 78},
                                "core": {"n foods": 51, "Warming": 31}})
        assert findings == []

    def test_a_row_carrying_numbers_nobody_checks_is_reported_as_unchecked(self):
        findings = check_table(TABLE, "### Table X.", {"All coded": {"n foods": 196}})
        assert [f["row"] for f in findings] == ["core"]
        assert "unchecked" in findings[0]["expected"]

    def test_an_expected_row_that_vanished_is_reported(self):
        findings = check_table(TABLE, "### Table X.",
                               {"All coded": {"n foods": 196},
                                "core": {"n foods": 51, "Warming": 31},
                                "two-source": {"n foods": 25}})
        assert [f["printed"] for f in findings] == ["row absent"]

    def test_a_renamed_column_fails_loudly(self):
        with pytest.raises(ValueError, match="no column"):
            check_table(TABLE, "### Table X.", {"All coded": {"foods": 196}})

    def test_food_rows_need_exact_labels_because_one_name_contains_another(self):
        # Table 4 lists both `onion` and `green onion`; substring matching makes
        # the second row answer to the first food's expectation.
        with pytest.raises(ValueError, match="matches several"):
            check_table(FOODS, "### T",
                        {"onion": {"Sources": 5}, "green onion": {"Sources": 6}})
        assert check_table(FOODS, "### T", {"green onion": {"Sources": 6}},
                           exact=True) == []


class TestTable4Expected:
    def test_only_core_foods_with_no_screened_study_are_expected(self):
        frame = pd.DataFrame({
            "food_key": ["carrot", "ginger", "apple"],
            "n_sources": [9, 8, 1],
            "l1": [5702, 5730, 176],
            "l2_raw": [12, 70, 176],
            "l2_screened": [0, 12, 0],
        })
        expected = table4_expected(frame)
        assert list(expected) == ["carrot"]
        assert expected["carrot"] == {
            "Sources": 9, "Total literature (L1)": 5702,
            "Raw L2": 12, "On-construct (L2′)": 0,
        }

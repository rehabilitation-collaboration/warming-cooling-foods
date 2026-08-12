"""Tests for the manuscript-wide numeric cross-check (RD-6)."""

import pandas as pd
import pytest

from src.verify_manuscript import (
    _renderings,
    audit,
    counts_reference,
    pipeline_inputs,
    pipeline_values,
)


class TestRenderings:
    def test_a_value_matches_the_roundings_a_manuscript_would_print(self):
        assert {"0.539", "0.5389"} <= _renderings("0.5389")
        assert {"12733", "12,733"} <= _renderings("12733")

    def test_a_stale_value_does_not_match_the_current_one(self):
        # The whole point: 0.498 was the reported p for a coefficient now at
        # 0.5389, and no rounding of the new value produces the old one.
        assert "0.498" not in _renderings("0.5389")


class TestAudit:
    def test_every_token_is_either_matched_or_unmatched(self):
        # The report is only auditable if the two buckets exhaust the tokens; a
        # third, silent bucket is the failure mode this script exists to remove.
        text = "OR 1.062 across 146 foods, up from 1.070.\n12,733 records.\n"
        report = audit(text, {"1.062", "146"})
        assert len(report) == 4
        assert int(report["matched"].sum()) + int((~report["matched"]).sum()) == len(report)

    def test_a_stale_value_is_reported_with_its_line(self):
        text = "line one\nthe old estimate was OR 1.070 here\n"
        report = audit(text, {"1.062"})
        stale = report[~report["matched"]]
        assert list(stale["token"]) == ["1.070"]
        assert int(stale["line"].iloc[0]) == 2

    def test_an_access_date_is_one_identifier_not_three_numbers(self):
        report = audit("fetched on 2026-08-03 by hand\n", set())
        assert len(report) == 3
        assert report["looks_like_id"].all()

    def test_section_headings_are_carried_onto_the_tokens(self):
        text = "## Table 3. Primary statistics\n| OR 1.070 |\n"
        report = audit(text, set())
        assert report["section"].iloc[0] == "Table 3. Primary statistics"


class TestIdentifierSpans:
    def test_one_identifier_word_does_not_demote_the_whole_line(self):
        # "the analysis plan commits to reporting" matched the bare word
        # `commit` and marked all 61 numbers in Table 3's footnote as
        # identifiers — every one of which was stale.
        report = audit("the plan commits to reporting OR 1.070 at each level\n", set())
        assert not report["looks_like_id"].any()

    def test_a_model_version_is_an_identifier_and_its_neighbours_are_not(self):
        text = "Claude Sonnet 4.6 labelled 12,437 records at kappa 0.806\n"
        report = audit(text, set())
        assert list(report[report["looks_like_id"]]["token"]) == ["4.6"]

    def test_reference_list_numbers_are_not_ours_to_recompute(self):
        report = audit("## References\n1. Someone. Journal. 2021;12(3):45-67.\n", set())
        assert report["looks_like_id"].all()


class TestPipelineValues:
    def test_the_reference_set_covers_the_current_primary_estimate(self):
        # An end-to-end guard: if the reference set stops carrying what
        # verify_stats prints, every current number turns into a false positive
        # and the report becomes noise.
        values = pipeline_values(pipeline_inputs())
        assert "1.062" in values
        assert "146" in values

    def test_a_renamed_counts_column_fails_loudly(self):
        frame = pd.DataFrame({"n_pubmed": [10], "n_openalex": [1], "n_cinii": [2],
                              "L2_screened": [3], "n_sources": [4]})
        assert "10" in counts_reference(frame)
        with pytest.raises(ValueError, match="n_pubmed"):
            counts_reference(frame.rename(columns={"n_pubmed": "l1"}))

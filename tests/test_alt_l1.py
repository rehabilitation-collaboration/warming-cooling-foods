"""Tests for the alternative L1 covariate definitions (review round 3, item 5)."""

import pandas as pd
import pytest

from src import alt_l1, evidence_mapping as em


class TestQueryBuilding:
    def test_variant_filter_is_anded_onto_the_plain_l1_query(self):
        q = alt_l1.alt_l1_query("ginger", "L1_humans")
        assert q == "ginger[tiab] AND humans[mh]"

    def test_multi_term_food_keeps_its_or_group_intact(self):
        # The filter must apply to the whole OR-group, not bind to the last term.
        q = alt_l1.alt_l1_query("chili pepper", "L1_nutrition")
        assert q.startswith('("chili pepper"[tiab] OR ')
        assert q.endswith(') AND "diet, food, and nutrition"[mh]')

    def test_unknown_variant_fails_loudly(self):
        with pytest.raises(ValueError, match="unknown L1 variant"):
            alt_l1.alt_l1_query("ginger", "L1_rodents")

    def test_every_variant_narrows_rather_than_replaces_the_food_terms(self):
        for variant in alt_l1.ALT_L1_FILTERS:
            assert alt_l1.alt_l1_query("ginger", variant).startswith("ginger[tiab] AND ")


class TestCollect:
    def test_one_row_per_food_with_a_count_and_query_per_variant(self, monkeypatch, tmp_path):
        monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
        monkeypatch.setattr(alt_l1, "PUBMED_DELAY", 0)
        monkeypatch.setattr(
            alt_l1, "pubmed_count", lambda q: (7, {"esearchresult": {"count": "7"}})
        )

        out = alt_l1.collect_alt_l1(["ginger", "milk"], reuse_cache=False)
        assert list(out["food_key"]) == ["ginger", "milk"]
        for variant in alt_l1.ALT_L1_FILTERS:
            assert (out[variant] == 7).all()
            assert out[f"{variant}_query"].str.contains(r"\[tiab\]").all()

    def test_a_pubmed_failure_aborts_rather_than_leaving_a_gap(self, monkeypatch, tmp_path):
        # This is a covariate the primary model is refit on: a swallowed error
        # would drop the food from the refit instead of announcing itself.
        monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
        monkeypatch.setattr(alt_l1, "PUBMED_DELAY", 0)

        def boom(query):
            raise RuntimeError("503")

        monkeypatch.setattr(alt_l1, "pubmed_count", boom)
        with pytest.raises(RuntimeError):
            alt_l1.collect_alt_l1(["ginger"], reuse_cache=False)

    def test_cache_is_invalidated_when_the_filter_changes(self, monkeypatch, tmp_path):
        # Same failure mode that made the four-term L2 counts stale: the cache
        # filename is keyed on (api, food, layer) only, so a changed query has to
        # be caught by the stored _query tag.
        monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
        monkeypatch.setattr(alt_l1, "PUBMED_DELAY", 0)
        calls = []

        def counted(query):
            calls.append(query)
            return len(calls), {"esearchresult": {"count": str(len(calls))}}

        monkeypatch.setattr(alt_l1, "pubmed_count", counted)

        alt_l1.collect_alt_l1(["ginger"], reuse_cache=True)
        first = len(calls)
        # Re-running unchanged must hit the cache and issue no new requests.
        alt_l1.collect_alt_l1(["ginger"], reuse_cache=True)
        assert len(calls) == first

        monkeypatch.setitem(alt_l1.ALT_L1_FILTERS, "L1_humans", "humans[mh] AND english[la]")
        alt_l1.collect_alt_l1(["ginger"], reuse_cache=True)
        assert len(calls) == first + 1

    def test_collecting_does_not_write_the_main_counts_file(self, monkeypatch, tmp_path):
        # collect_counts rewrites pubmed_counts.csv wholesale and drops
        # L2_screened with it; this path must never do that.
        monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
        monkeypatch.setattr(alt_l1, "PUBMED_DELAY", 0)
        monkeypatch.setattr(
            alt_l1, "pubmed_count", lambda q: (1, {"esearchresult": {"count": "1"}})
        )
        before = alt_l1.PUBMED_COUNTS_CSV.read_bytes()
        alt_l1.collect_alt_l1(["ginger"], reuse_cache=False)
        assert alt_l1.PUBMED_COUNTS_CSV.read_bytes() == before


class TestLoad:
    def test_missing_file_returns_none_rather_than_an_empty_frame(self, monkeypatch, tmp_path):
        monkeypatch.setattr(alt_l1, "ALT_L1_CSV", tmp_path / "absent.csv")
        assert alt_l1.load_alt_l1() is None

    def test_present_file_is_read_back(self, monkeypatch, tmp_path):
        path = tmp_path / "alt.csv"
        pd.DataFrame([{"food_key": "ginger", "L1_humans": 3}]).to_csv(path, index=False)
        monkeypatch.setattr(alt_l1, "ALT_L1_CSV", path)
        assert alt_l1.load_alt_l1()["L1_humans"].iloc[0] == 3

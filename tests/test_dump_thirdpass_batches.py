"""Tests for the third-pass batch builder (src/dump_thirdpass_batches.py)."""

import json

import pandas as pd
import pytest

from src import dump_thirdpass_batches as dtb


def _frame():
    # Two core foods at zero (one with records, one without), one core food that
    # has a study, and one narrow-belief food at zero that is out of scope.
    return pd.DataFrame(
        [
            {"food_key": "cucumber", "n_sources": 8, "direction": "cool",
             "l1": 12174, "l2_raw": 67, "l2_screened": 0.0},
            {"food_key": "burdock", "n_sources": 7, "direction": "warm",
             "l1": 323, "l2_raw": 0, "l2_screened": 0.0},
            {"food_key": "ginger", "n_sources": 8, "direction": "warm",
             "l1": 5730, "l2_raw": 70, "l2_screened": 12.0},
            {"food_key": "amazake", "n_sources": 1, "direction": "warm",
             "l1": 40, "l2_raw": 4, "l2_screened": 0.0},
        ]
    )


def _ledger(tmp_path, rows):
    path = tmp_path / "screening.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _records(tmp_path, rows):
    path = tmp_path / "l2_records.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


class TestCoreZeroFoods:
    def test_selects_core_belief_foods_at_zero_and_nothing_else(self):
        out = dtb.core_zero_foods(_frame())
        assert set(out["food_key"]) == {"cucumber", "burdock"}

    def test_orders_by_coverage_so_the_foods_most_at_risk_come_first(self):
        out = dtb.core_zero_foods(_frame())
        assert list(out["food_key"]) == ["cucumber", "burdock"]

    def test_keeps_l2_raw_so_the_caller_can_split_off_the_unqueryable(self):
        out = dtb.core_zero_foods(_frame())
        assert int(out.loc[out["food_key"] == "burdock", "l2_raw"].iloc[0]) == 0


class TestCandidates:
    def test_offers_only_excluded_records(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dtb, "SCREENING_CSV", _ledger(tmp_path, [
            {"pmid": "1", "food_key": "cucumber", "final_label": "exclude"},
            {"pmid": "2", "food_key": "cucumber", "final_label": "exclude"},
        ]))
        monkeypatch.setattr(dtb, "L2_RECORDS_CSV", _records(tmp_path, [
            {"food_key": "cucumber", "pmid": "1", "title": "t1", "abstract": "a1", "pubtypes": "Journal Article"},
            {"food_key": "cucumber", "pmid": "2", "title": "t2", "abstract": "a2", "pubtypes": "Review"},
        ]))
        out = dtb.thirdpass_candidates(["cucumber"])
        assert list(out["pmid"]) == ["1", "2"]

    def test_an_include_in_scope_fails_loudly(self, tmp_path, monkeypatch):
        # The third pass is told everything in front of it was excluded. If the
        # food actually has an include, the scope is stale and that instruction
        # would be false, so this must not be filtered away quietly.
        monkeypatch.setattr(dtb, "SCREENING_CSV", _ledger(tmp_path, [
            {"pmid": "1", "food_key": "cucumber", "final_label": "exclude"},
            {"pmid": "2", "food_key": "cucumber", "final_label": "include"},
        ]))
        with pytest.raises(ValueError, match="already have an include"):
            dtb.thirdpass_candidates(["cucumber"])

    def test_a_ledger_row_with_no_retrieved_record_fails_loudly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dtb, "SCREENING_CSV", _ledger(tmp_path, [
            {"pmid": "1", "food_key": "cucumber", "final_label": "exclude"},
            {"pmid": "99", "food_key": "cucumber", "final_label": "exclude"},
        ]))
        monkeypatch.setattr(dtb, "L2_RECORDS_CSV", _records(tmp_path, [
            {"food_key": "cucumber", "pmid": "1", "title": "t1", "abstract": "a1", "pubtypes": "Journal Article"},
        ]))
        with pytest.raises(ValueError, match="no record in"):
            dtb.thirdpass_candidates(["cucumber"])


class TestWriteBatches:
    def test_batch_carries_text_only_and_no_label(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dtb, "BATCH_DIR", tmp_path / "c3_batches")
        candidates = pd.DataFrame([
            {"food_key": "cucumber", "pmid": "1", "title": "t1", "abstract": "a1", "pubtypes": "Journal Article"},
        ])
        files, total = dtb.write_batches(candidates)
        assert (files, total) == (1, 1)
        payload = json.loads(dtb.batch_path("cucumber").read_text(encoding="utf-8"))
        assert payload["food_key"] == "cucumber"
        assert set(payload["records"][0]) == {"pmid", "title", "pubtypes", "abstract"}

    def test_food_key_with_a_space_keeps_the_space_inside_the_file(self, tmp_path, monkeypatch):
        # The filename underscores the space, but the coder is told to use the
        # food_key from the JSON, so the value inside must stay unmodified.
        monkeypatch.setattr(dtb, "BATCH_DIR", tmp_path / "c3_batches")
        candidates = pd.DataFrame([
            {"food_key": "white rice", "pmid": "1", "title": "t", "abstract": "a", "pubtypes": "Journal Article"},
        ])
        dtb.write_batches(candidates)
        path = dtb.batch_path("white rice")
        assert path.name == "records_white_rice.json"
        assert json.loads(path.read_text(encoding="utf-8"))["food_key"] == "white rice"

    def test_the_extension_writes_to_its_own_directory(self, tmp_path, monkeypatch):
        # The 2026-08-09 pass's inputs must stay byte-identical, so §9's batches
        # go somewhere else and the caller says where.
        monkeypatch.setattr(dtb, "BATCH_DIR", tmp_path / "c3_batches")
        candidates = pd.DataFrame([
            {"food_key": "amazake", "pmid": "1", "title": "t", "abstract": "a", "pubtypes": "Journal Article"},
        ])
        dtb.write_batches(candidates, batch_dir=tmp_path / "c3_ext_batches")
        assert (tmp_path / "c3_ext_batches" / "records_amazake.json").exists()
        assert not (tmp_path / "c3_batches").exists()

    def _lamb(self, n: int) -> pd.DataFrame:
        return pd.DataFrame([
            {"food_key": "lamb", "pmid": str(i), "title": f"t{i}", "abstract": f"a{i}",
             "pubtypes": "Journal Article"}
            for i in range(n)
        ])

    def test_a_food_past_the_cap_is_split_into_indexed_ranges(self, tmp_path):
        files, total = dtb.write_batches(self._lamb(5), batch_dir=tmp_path, max_records=2)
        assert (files, total) == (3, 5)
        assert sorted(p.name for p in tmp_path.glob("*.json")) == [
            "records_lamb_000_001.json",
            "records_lamb_002_003.json",
            "records_lamb_004_004.json",
        ]

    def test_a_split_batch_names_the_range_it_holds(self, tmp_path):
        dtb.write_batches(self._lamb(5), batch_dir=tmp_path, max_records=2)
        payload = json.loads((tmp_path / "records_lamb_002_003.json").read_text(encoding="utf-8"))
        assert payload["food_key"] == "lamb"
        assert payload["range"] == "2-3"
        assert [r["pmid"] for r in payload["records"]] == ["2", "3"]

    def test_a_split_loses_and_duplicates_nothing(self, tmp_path):
        # Splitting is a delivery decision. If it dropped or repeated a record it
        # would change what the pass screened, which is not a delivery decision.
        dtb.write_batches(self._lamb(5), batch_dir=tmp_path, max_records=2)
        seen = [
            r["pmid"]
            for p in sorted(tmp_path.glob("*.json"))
            for r in json.loads(p.read_text(encoding="utf-8"))["records"]
        ]
        assert sorted(seen) == sorted({"0", "1", "2", "3", "4"})

    def test_a_food_at_or_under_the_cap_keeps_its_plain_name(self, tmp_path):
        dtb.write_batches(self._lamb(2), batch_dir=tmp_path, max_records=2)
        assert [p.name for p in tmp_path.glob("*.json")] == ["records_lamb.json"]


class TestRescreenScope:
    def test_keeps_the_low_coverage_zeros_the_core_scope_dropped(self):
        # §9's whole point: coverage is the explanatory variable, so it cannot
        # also decide which foods get the extra check. amazake carries one source
        # and was out of scope for the 2026-08-09 pass.
        out = dtb.rescreen_scope(_frame(), already_read=set())
        assert set(out["food_key"]) == {"cucumber", "amazake"}

    def test_subtracts_the_foods_an_earlier_pass_already_read(self):
        out = dtb.rescreen_scope(_frame(), already_read={"cucumber"})
        assert set(out["food_key"]) == {"amazake"}

    def test_drops_a_zero_food_whose_query_returned_nothing(self):
        # burdock is at zero with no retrieved record: a retrieval question, not
        # a screening one, so there is nothing for a re-screen to read.
        out = dtb.rescreen_scope(_frame(), already_read=set())
        assert "burdock" not in set(out["food_key"])

    def test_never_offers_a_food_that_already_has_a_study(self):
        out = dtb.rescreen_scope(_frame(), already_read=set())
        assert "ginger" not in set(out["food_key"])

    def test_already_read_is_read_from_the_published_ledger(self, tmp_path, monkeypatch):
        path = tmp_path / "screening_thirdpass.csv"
        pd.DataFrame([
            {"food_key": "cucumber", "pmid": "1"},
            {"food_key": "cucumber", "pmid": "2"},
            {"food_key": "carrot", "pmid": "3"},
        ]).to_csv(path, index=False)
        monkeypatch.setattr(dtb, "THIRDPASS_CSV", path)
        assert dtb.already_read_foods() == {"cucumber", "carrot"}

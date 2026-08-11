"""Behaviour tests for the Axis A ledger build step (Route D, RD-3).

``src/ledger.py`` is pure; this module is where the fan-out meets the disk. The
coding is spread over 55 batches per coder, and the failures that matter here
are the quiet ones — a batch that came back with the right number of rows but
not the right rows, and an author's ruling that reaches no candidate at all.

Both are quiet for the same structural reason. In the finished
``claims_ledger.csv`` a candidate nobody judged is indistinguishable from one
the coders excluded, and a ruling that matched nothing is indistinguishable
from a ruling nobody needed to file.
"""

import json

import pandas as pd
import pytest

from src import build_ledger as bl
from src import ledger as lg


def _coded(batch_id: str, candidates: list[str], source_id: str = "src") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_id": [source_id] * len(candidates),
            "candidate": candidates,
            "label": ["exclude"] * len(candidates),
            "reason": ["fragment"] * len(candidates),
            "batch_id": [batch_id] * len(candidates),
        }
    )


def _spans(batch_id: str, n: int) -> list[str]:
    return [f"{batch_id}-{i}" for i in range(n)]


@pytest.fixture
def batches(tmp_path, monkeypatch):
    """A two-batch enumeration, with the batch files the coders were handed."""
    index = tmp_path / "batch_index.csv"
    pd.DataFrame(
        {
            "batch_id": ["src_b1", "src_b2"],
            "source_id": ["src", "src"],
            "n_candidates": [3, 5],
        }
    ).to_csv(index, index=False)
    for batch_id, n in (("src_b1", 3), ("src_b2", 5)):
        (tmp_path / f"candidates_{batch_id}.json").write_text(
            json.dumps(
                {
                    "source_id": "src",
                    "candidates": [{"candidate": s} for s in _spans(batch_id, n)],
                }
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(bl, "BATCH_INDEX_CSV", index)
    monkeypatch.setattr(bl, "batch_path", lambda b: tmp_path / f"candidates_{b}.json")
    return tmp_path


# --- audit_batches --------------------------------------------------------
class TestAuditBatches:
    def test_reports_batches_not_yet_returned(self, batches):
        pending = bl.audit_batches(_coded("src_b1", _spans("src_b1", 3)), "c1")
        assert pending == ["src_b2"]

    def test_no_pending_when_every_batch_is_in(self, batches):
        coded = pd.concat(
            [_coded("src_b1", _spans("src_b1", 3)),
             _coded("src_b2", _spans("src_b2", 5))],
            ignore_index=True,
        )
        assert bl.audit_batches(coded, "c1") == []

    def test_short_batch_is_an_error_not_pending_work(self, batches):
        with pytest.raises(ValueError, match="2 missing"):
            bl.audit_batches(_coded("src_b2", _spans("src_b2", 3)), "c1")

    def test_right_count_wrong_rows_is_an_error(self, batches):
        # The reason this check compares candidates and not just their number:
        # one span returned twice and another not at all keeps the row count
        # intact. `_coder_frame` would later collapse the duplicate with a
        # warning on stderr, and the dropped span would reach the finished
        # ledger looking like an exclusion nobody questioned.
        swapped = _spans("src_b2", 5)
        swapped[4] = swapped[0]
        with pytest.raises(ValueError, match="1 missing"):
            bl.audit_batches(_coded("src_b2", swapped), "c1")

    def test_normalised_span_is_an_error(self, batches):
        # A coder that trims or rewrites a span has changed the key the whole
        # ledger is built on, so the comparison is byte-exact.
        edited = _spans("src_b1", 3)
        edited[1] = f" {edited[1]} "
        with pytest.raises(ValueError, match="unassigned"):
            bl.audit_batches(_coded("src_b1", edited), "c1")

    def test_extra_rows_are_an_error(self, batches):
        with pytest.raises(ValueError, match="unassigned"):
            bl.audit_batches(_coded("src_b1", _spans("src_b1", 4)), "c1")

    def test_wrong_source_id_is_an_error(self, batches):
        with pytest.raises(ValueError, match="but the batch is 'src'"):
            bl.audit_batches(
                _coded("src_b1", _spans("src_b1", 3), source_id="other"), "c1")

    def test_unknown_batch_id_is_an_error(self, batches):
        # A file named after no assigned batch means those rows belong to no
        # partition, so the enumeration was never covered the way it was cut.
        with pytest.raises(ValueError, match="absent from"):
            bl.audit_batches(_coded("src_b9", _spans("src_b9", 3)), "c2")

    def test_names_the_coder_in_the_error(self, batches):
        with pytest.raises(ValueError, match="coder c2"):
            bl.audit_batches(_coded("src_b2", _spans("src_b2", 1)), "c2")


# --- load_coder -----------------------------------------------------------
class TestLoadCoder:
    def test_concatenates_batches_and_attaches_batch_id(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bl, "WORK_DIR", tmp_path)
        (tmp_path / "c1").mkdir()
        for batch_id, n in (("src_b1", 3), ("src_b2", 5)):
            _coded(batch_id, _spans(batch_id, n)).drop(columns="batch_id").to_csv(
                tmp_path / "c1" / f"{batch_id}.csv", index=False)

        out = bl.load_coder("c1")

        assert len(out) == 8
        # The batch id is the file name, not something a coder writes; the audit
        # cannot check a batch against the slice it was handed without it.
        assert out.groupby("batch_id").size().to_dict() == {"src_b1": 3, "src_b2": 5}

    def test_a_coder_that_has_not_started_yields_an_empty_frame(
        self, tmp_path, monkeypatch
    ):
        # Not fatal. Coders are dispatched a wave at a time and a wave is often
        # all c1 or all c2; exiting here would mean the batch audit could not
        # run between waves — which is the only time it is cheap to act on.
        monkeypatch.setattr(bl, "WORK_DIR", tmp_path)
        (tmp_path / "c1").mkdir()

        out = bl.load_coder("c1")

        assert out.empty
        assert "batch_id" in out.columns

    def test_the_audit_still_runs_for_the_coder_that_is_ahead(
        self, tmp_path, monkeypatch, batches
    ):
        monkeypatch.setattr(bl, "WORK_DIR", tmp_path)
        (tmp_path / "c2").mkdir()

        assert bl.audit_batches(bl.load_coder("c2"), "c2") == ["src_b1", "src_b2"]


# --- load_rulings ---------------------------------------------------------
class TestLoadRulings:
    def test_absent_file_means_no_rulings(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bl, "RULINGS_CSV", tmp_path / "nope.csv")
        assert bl.load_rulings() == {}

    def test_header_only_file_means_no_rulings(self, tmp_path, monkeypatch):
        path = tmp_path / "ledger_rulings.csv"
        path.write_text("source_id,candidate,final_label,reason\n")
        monkeypatch.setattr(bl, "RULINGS_CSV", path)
        assert bl.load_rulings() == {}

    def test_carries_the_fields_an_include_needs(self, tmp_path, monkeypatch):
        # A ruling that flips an agreed exclusion to include arrives with
        # food_ja/food_en/direction empty — no coder ever filled them in — so
        # the ruling has to supply them (§9.3, enforced by adjudicate()).
        path = tmp_path / "ledger_rulings.csv"
        pd.DataFrame(
            [{
                "source_id": "kawashimaya", "candidate": "生姜",
                "final_label": "include", "reason": "",
                "food_ja": "生姜", "food_en": "ginger", "direction": "warm",
                "quote": "生姜は体を温める", "rationale": "§3 温活構文", "batch": "rd3",
            }]
        ).to_csv(path, index=False)
        monkeypatch.setattr(bl, "RULINGS_CSV", path)

        ruling = bl.load_rulings()[("kawashimaya", "生姜")]

        assert ruling["label"] == "include"
        assert ruling["direction"] == "warm"
        assert ruling["food_en"] == "ginger"

    def test_blank_columns_fall_back_to_the_coders(self, tmp_path, monkeypatch):
        path = tmp_path / "ledger_rulings.csv"
        pd.DataFrame(
            [{"source_id": "src", "candidate": "なす", "final_label": "exclude",
              "reason": "fragment"}]
        ).to_csv(path, index=False)
        monkeypatch.setattr(bl, "RULINGS_CSV", path)

        ruling = bl.load_rulings()[("src", "なす")]

        # Empty rather than absent: adjudicate() reads `rule.get(f, "") or
        # coder value`, so a blank column defers to what the coders wrote.
        assert ruling["food_ja"] == ""

    def test_key_is_normalised_like_the_coders(self, tmp_path, monkeypatch):
        # `_coder_frame` strips both key fields, so a ruling typed with a stray
        # space would key on something no candidate can equal.
        path = tmp_path / "ledger_rulings.csv"
        pd.DataFrame(
            [{"source_id": " src ", "candidate": " なす ", "final_label": "exclude",
              "reason": "fragment"}]
        ).to_csv(path, index=False)
        monkeypatch.setattr(bl, "RULINGS_CSV", path)

        assert ("src", "なす") in bl.load_rulings()

    def test_duplicate_key_is_an_error(self, tmp_path, monkeypatch):
        # Two rulings on one candidate mean one was never applied, and which one
        # won would depend on row order (the D41 rule, kept across both axes).
        path = tmp_path / "ledger_rulings.csv"
        pd.DataFrame(
            [
                {"source_id": "src", "candidate": "なす", "final_label": "exclude",
                 "reason": "fragment"},
                {"source_id": "src", "candidate": "なす", "final_label": "include",
                 "reason": ""},
            ]
        ).to_csv(path, index=False)
        monkeypatch.setattr(bl, "RULINGS_CSV", path)

        with pytest.raises(ValueError, match="duplicated"):
            bl.load_rulings()


# --- rulings actually reaching a candidate --------------------------------
def _agreed(candidate: str = "生姜") -> pd.DataFrame:
    row = {"source_id": "src", "candidate": candidate, "label": "include",
           "food_ja": candidate, "food_en": "ginger", "direction": "warm",
           "quote": "q"}
    return lg.reconcile([dict(row)], [dict(row)])


class TestRulingsLand:
    def test_stray_ruling_is_an_error(self):
        recon = _agreed()
        with pytest.raises(ValueError, match="match no candidate"):
            bl.check_rulings_land(recon, {("src", "しょうが"): {"label": "exclude"}})

    def test_silence_when_every_ruling_matches(self):
        recon = _agreed()
        bl.check_rulings_land(recon, {("src", "生姜"): {"label": "exclude"}})

    def test_an_override_on_an_agreed_row_would_otherwise_vanish(self):
        # Why check_rulings_land exists. adjudicate() raises for a candidate
        # that needs a ruling and has none, but an agreed row needs no ruling:
        # a key that fails to match falls straight through to the coders'
        # shared label, and the author's override disappears without a word.
        # That override is the only instrument for a judgment both coders got
        # wrong in the same direction (D42).
        recon = _agreed()
        mistyped = {("src", "生姜 "): {"label": "exclude", "reason": "fragment"}}

        out = lg.adjudicate(recon, mistyped)
        assert out["final_label"].tolist() == ["include"]   # silently unchanged
        assert out["adjudicated"].tolist() == [False]

        with pytest.raises(ValueError, match="match no candidate"):
            bl.check_rulings_land(recon, mistyped)

    def test_a_ruling_typed_with_a_stray_space_still_lands(self, tmp_path, monkeypatch):
        # The two halves of the fix together: load_rulings normalises the key,
        # so the same mistyped ruling now reaches the candidate and applies.
        path = tmp_path / "ledger_rulings.csv"
        pd.DataFrame(
            [{"source_id": "src", "candidate": "生姜 ", "final_label": "exclude",
              "reason": "fragment"}]
        ).to_csv(path, index=False)
        monkeypatch.setattr(bl, "RULINGS_CSV", path)

        recon = _agreed()
        rulings = bl.load_rulings()
        bl.check_rulings_land(recon, rulings)
        out = lg.adjudicate(recon, rulings)

        assert out["final_label"].tolist() == ["exclude"]
        assert out["adjudicated"].tolist() == [True]


# --- report_pending -------------------------------------------------------
class TestReportPending:
    def test_true_while_anything_is_outstanding(self, capsys):
        assert bl.report_pending({"c1": ["src_b2"], "c2": []}, total=2) is True
        out = capsys.readouterr().out
        assert "src_b2" in out and "waiting on c1" in out

    def test_false_when_both_coders_are_complete(self, capsys):
        assert bl.report_pending({"c1": [], "c2": []}, total=2) is False

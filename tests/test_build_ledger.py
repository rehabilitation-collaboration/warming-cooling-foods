"""Behaviour tests for the Axis A ledger build step (Route D, RD-3).

``src/ledger.py`` is pure; this module is where the fan-out meets the disk. The
coding is spread over 55 batches per coder, and the failure that matters here is
the quiet one: a batch that never came back, or came back short. In the finished
``claims_ledger.csv`` an unjudged candidate is indistinguishable from one the
coders excluded, which is precisely what the ledger exists to make visible.

``to_ledger_csv`` catches short returns at the end, against the whole
enumeration. These tests pin the earlier, per-batch check, because that is the
one that can be acted on while an agent is still cheap to re-run.
"""

import pandas as pd
import pytest

from src import build_ledger as bl


def _coded(batch_id: str, n: int, source_id: str = "src") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_id": [source_id] * n,
            "candidate": [f"{batch_id}-{i}" for i in range(n)],
            "label": ["exclude"] * n,
            "reason": ["fragment"] * n,
            "batch_id": [batch_id] * n,
        }
    )


@pytest.fixture
def index(tmp_path, monkeypatch):
    """A two-batch enumeration index, wired into the module under test."""
    path = tmp_path / "batch_index.csv"
    pd.DataFrame(
        {
            "batch_id": ["src_b1", "src_b2"],
            "source_id": ["src", "src"],
            "n_candidates": [3, 5],
        }
    ).to_csv(path, index=False)
    monkeypatch.setattr(bl, "BATCH_INDEX_CSV", path)
    return path


# --- audit_batches --------------------------------------------------------
class TestAuditBatches:
    def test_reports_batches_not_yet_returned(self, index):
        pending = bl.audit_batches(_coded("src_b1", 3), "c1")
        assert pending == ["src_b2"]

    def test_no_pending_when_every_batch_is_in(self, index):
        coded = pd.concat([_coded("src_b1", 3), _coded("src_b2", 5)], ignore_index=True)
        assert bl.audit_batches(coded, "c1") == []

    def test_short_batch_is_an_error_not_pending_work(self, index):
        # The failure mode the whole check exists for: the coder returned the
        # batch, but two of its candidates never reached the ledger.
        with pytest.raises(ValueError, match="returned 3, expected 5"):
            bl.audit_batches(_coded("src_b2", 3), "c1")

    def test_extra_rows_are_an_error(self, index):
        with pytest.raises(ValueError, match="wrong number of rows"):
            bl.audit_batches(_coded("src_b1", 4), "c1")

    def test_unknown_batch_id_is_an_error(self, index):
        # A file named after no assigned batch means those rows belong to no
        # partition, so the enumeration was never covered the way it was cut.
        with pytest.raises(ValueError, match="absent from"):
            bl.audit_batches(_coded("src_b9", 3), "c2")

    def test_names_the_coder_in_the_error(self, index):
        with pytest.raises(ValueError, match="coder c2"):
            bl.audit_batches(_coded("src_b2", 1), "c2")


# --- load_coder -----------------------------------------------------------
class TestLoadCoder:
    def test_concatenates_batches_and_attaches_batch_id(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bl, "WORK_DIR", tmp_path)
        (tmp_path / "c1").mkdir()
        _coded("src_b1", 3).drop(columns="batch_id").to_csv(
            tmp_path / "c1" / "src_b1.csv", index=False)
        _coded("src_b2", 5).drop(columns="batch_id").to_csv(
            tmp_path / "c1" / "src_b2.csv", index=False)

        out = bl.load_coder("c1")

        assert len(out) == 8
        # The batch id is the file name, not something a coder writes; the audit
        # cannot check a batch against its slice of the enumeration without it.
        assert out.groupby("batch_id").size().to_dict() == {"src_b1": 3, "src_b2": 5}

    def test_exits_when_a_coder_has_returned_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bl, "WORK_DIR", tmp_path)
        (tmp_path / "c1").mkdir()
        with pytest.raises(SystemExit):
            bl.load_coder("c1")


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


# --- report_pending -------------------------------------------------------
class TestReportPending:
    def test_true_while_anything_is_outstanding(self, capsys):
        assert bl.report_pending({"c1": ["src_b2"], "c2": []}, total=2) is True
        out = capsys.readouterr().out
        assert "src_b2" in out and "waiting on c1" in out

    def test_false_when_both_coders_are_complete(self, capsys):
        assert bl.report_pending({"c1": [], "c2": []}, total=2) is False

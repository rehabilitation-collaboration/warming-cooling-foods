"""Tests for the adversarial third screening pass aggregator.

The point of this module is that a flagged record must never be carried
silently as excluded, so the fail-loud path gets as much attention as the
happy one.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src import build_thirdpass as bt


def _write_batch(dirpath, name: str, payload: dict) -> None:
    (dirpath / name).write_text(json.dumps(payload))


def test_load_verdicts_reads_both_batch_shapes(tmp_path, monkeypatch):
    # Large foods were split into indexed ranges; small foods were not. Both
    # shapes must load into the same frame.
    monkeypatch.setattr(bt, "WORK_DIR", tmp_path)
    _write_batch(tmp_path, "chicken_000_001.json", {
        "food_key": "chicken", "range": "0-1",
        "verdicts": [{"pmid": "1", "verdict": "exclude-agreed", "reason": "animal"}],
    })
    _write_batch(tmp_path, "tuna.json", {
        "food_key": "tuna",
        "verdicts": [{"pmid": "2", "verdict": "exclude-agreed", "reason": "fish endothermy"}],
    })

    df = bt.load_verdicts()
    assert len(df) == 2
    assert set(df["food_key"]) == {"chicken", "tuna"}
    assert df["pmid"].tolist() == ["1", "2"]


def test_load_verdicts_keeps_pmid_as_string(tmp_path, monkeypatch):
    # PMIDs join against screening.csv as text; a numeric cast would drop the
    # match for any leading-zero identifier.
    monkeypatch.setattr(bt, "WORK_DIR", tmp_path)
    _write_batch(tmp_path, "sake.json", {
        "food_key": "sake",
        "verdicts": [{"pmid": 3576010, "verdict": "exclude-agreed", "reason": "name-only"}],
    })
    assert bt.load_verdicts()["pmid"].tolist() == ["3576010"]


def test_load_verdicts_refuses_an_empty_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(bt, "WORK_DIR", tmp_path)
    with pytest.raises(SystemExit):
        bt.load_verdicts()


def test_attach_rulings_leaves_agreed_excludes_blank(monkeypatch):
    monkeypatch.setattr(bt, "AUTHOR_RULINGS", {})
    df = pd.DataFrame(
        {"food_key": ["tuna"], "pmid": ["2"], "third_verdict": ["exclude-agreed"],
         "third_reason": ["fish endothermy"]}
    )
    out = bt.attach_rulings(df)
    assert out.loc[0, "author_ruling"] == ""
    assert out.loc[0, "author_reason"] == ""


def test_attach_rulings_fails_loud_on_an_unadjudicated_flag(monkeypatch):
    # A record the third pass would not clear, with no author ruling, is an
    # unfinished adjudication — it must not pass through as an exclude.
    monkeypatch.setattr(bt, "AUTHOR_RULINGS", {})
    df = pd.DataFrame(
        {"food_key": ["grape"], "pmid": ["20439553"], "third_verdict": ["uncertain"],
         "third_reason": ["outcome unconfirmable"]}
    )
    with pytest.raises(ValueError, match="flagged but not adjudicated"):
        bt.attach_rulings(df)


def test_attach_rulings_records_the_authors_verdict_and_reason(monkeypatch):
    monkeypatch.setattr(
        bt, "AUTHOR_RULINGS", {("grape", "20439553"): ("exclude", "hypothesis only")}
    )
    df = pd.DataFrame(
        {"food_key": ["grape", "tuna"], "pmid": ["20439553", "2"],
         "third_verdict": ["uncertain", "exclude-agreed"],
         "third_reason": ["outcome unconfirmable", "fish endothermy"]}
    )
    out = bt.attach_rulings(df).set_index("food_key")
    assert out.loc["grape", "author_ruling"] == "exclude"
    assert out.loc["grape", "author_reason"] == "hypothesis only"
    assert out.loc["tuna", "author_ruling"] == ""


def test_published_ledger_matches_the_shipped_batches():
    # Guards the numbers the manuscript reports for the 2026-08-09 pass over the
    # 22-term core-zero set: 388 records across 23 foods, 6 flagged, 1 overturned.
    # The earlier pass (419 records, 28 foods, 5 flagged, 0 overturned) covered the
    # four-term zero set, which the widened vocabulary replaced.
    df = bt.attach_rulings(bt.load_verdicts())
    assert len(df) == 388
    assert df["food_key"].nunique() == 23
    flagged = df[df["third_verdict"] != "exclude-agreed"]
    assert len(flagged) == 6
    # Every flagged record must carry a ruling; attach_rulings raises otherwise,
    # but assert it here so a silently-blank ruling cannot pass as adjudicated.
    assert (flagged["author_ruling"] != "").all()
    overturned = flagged[flagged["author_ruling"] == "include"]
    assert list(overturned["pmid"]) == ["36558358"]


def test_the_overturned_record_reaches_the_screening_ledger_as_an_include():
    # The third pass only records a verdict; the label that moves L2' lives in
    # screening_rulings.csv. If the two ever disagree, the published ledger says
    # a record was overturned while the count still treats it as excluded.
    import pandas as pd

    from src.screening import SCREENING_CSV

    rulings = pd.read_csv(bt.DATA_DIR / "screening_rulings.csv", dtype=str)
    row = rulings[(rulings["food_key"] == "watermelon") & (rulings["pmid"] == "36558358")]
    assert len(row) == 1 and row["final_label"].iloc[0] == "include"

    ledger = pd.read_csv(SCREENING_CSV, dtype=str)
    final = ledger[(ledger["food_key"] == "watermelon") & (ledger["pmid"] == "36558358")]
    assert len(final) == 1 and final["final_label"].iloc[0] == "include"

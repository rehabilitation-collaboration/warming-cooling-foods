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
    # Guards the number the manuscript reports: 419 records, 5 flagged, 0 overturned.
    df = bt.attach_rulings(bt.load_verdicts())
    assert len(df) == 419
    flagged = df[df["third_verdict"] != "exclude-agreed"]
    assert len(flagged) == 5
    assert (flagged["author_ruling"] == "exclude").all()
    assert df["food_key"].nunique() == 28

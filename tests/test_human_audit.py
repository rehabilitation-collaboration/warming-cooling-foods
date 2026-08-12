"""Behaviour tests for the human-audit materials (coding protocol §10).

The audit's value rests on it having been specified before it was performed, so
what is tested here is that the specification is mechanical: the sample is a
function of the seed, the verdict vocabulary is closed, `unlocatable` leaves the
denominator, and the completeness diff counts an unmatched food as missed rather
than quietly dropping it.
"""

import pandas as pd
import pytest

from src import human_audit as ha


ROWS = pd.DataFrame(
    {
        "source_id": ["a"] * 5 + ["b"] * 5,
        "food_en": [f"f{i}" for i in range(10)],
        "food_ja": [f"食{i}" for i in range(10)],
        "direction": ["warm"] * 10,
        "quote": ["…"] * 10,
    }
)


# --- sampling -------------------------------------------------------------
def test_sample_is_a_function_of_the_seed():
    a = ha.precision_sample(ROWS, n=4, seed=1)
    b = ha.precision_sample(ROWS, n=4, seed=1)
    c = ha.precision_sample(ROWS, n=4, seed=2)
    assert a["food_en"].tolist() == b["food_en"].tolist()
    assert a["food_en"].tolist() != c["food_en"].tolist()


def test_sample_draws_without_replacement_and_caps_at_the_frame():
    s = ha.precision_sample(ROWS, n=99, seed=ha.SEED)
    assert len(s) == len(ROWS)
    assert s["food_en"].is_unique


def test_completeness_pair_is_the_longest_plus_one_other(monkeypatch):
    sources = pd.DataFrame(
        {"source_id": list("abcde"), "tier": [1, 1, 1, 1, 2]}
    )
    lengths = {"a": 10, "b": 900, "c": 30, "d": 40, "e": 99999}
    monkeypatch.setattr(ha, "source_body_length", lambda sid: lengths[sid])
    picked = ha.completeness_sources(sources)
    assert len(picked) == 2
    assert picked[0] == "b"          # longest Tier-1, not the longer Tier-2 one
    assert picked[1] in {"a", "c", "d"}
    assert picked == ha.completeness_sources(sources)  # seeded, so reproducible


# --- precision scoring ----------------------------------------------------
def _results(verdicts):
    return pd.DataFrame({"verdict": verdicts, "note": [""] * len(verdicts)})


def test_precision_counts_supported_over_checkable():
    p = ha.score_precision(_results(
        ["supported", "supported", "wrong-direction", "not-in-source"]
    ))
    assert p["n_checkable"] == 4 and p["n_supported"] == 2
    assert p["precision"] == 0.5


def test_unlocatable_leaves_the_denominator():
    # A page edited since the freeze is a fact about the web, not the coding.
    p = ha.score_precision(_results(["supported", "supported", "unlocatable"]))
    assert p["n_judged"] == 3 and p["n_checkable"] == 2
    assert p["precision"] == 1.0


def test_blank_rows_are_not_counted_as_judged():
    p = ha.score_precision(_results(["supported", "", "  "]))
    assert p["n_sampled"] == 3 and p["n_judged"] == 1


def test_an_unknown_verdict_is_a_hard_error():
    with pytest.raises(ValueError, match="unknown verdicts"):
        ha.score_precision(_results(["supported", "probably fine"]))


def test_scoring_an_empty_sheet_is_a_hard_error():
    with pytest.raises(ValueError, match="no verdicts"):
        ha.score_precision(_results(["", ""]))


# --- completeness scoring -------------------------------------------------
def test_completeness_diff_names_both_directions():
    reads = pd.DataFrame(
        {
            "source_id": ["a", "a", "a"],
            "food_ja": ["食0", "食1", "新顔"],
            "direction": ["warm"] * 3,
            "quote": ["…"] * 3,
        }
    )
    out = ha.score_completeness(reads, ROWS)["a"]
    assert out["missed_by_ledger"] == ["新顔"]
    assert out["in_ledger_only"] == ["食2", "食3", "食4"]
    assert out["recall"] == pytest.approx(2 / 3)


def test_a_surface_form_mismatch_counts_as_missed():
    # The conservative direction: an unmatched name is a miss until the author
    # rules that the two forms are the same food.
    reads = pd.DataFrame(
        {"source_id": ["a"], "food_ja": ["食０"], "direction": ["warm"], "quote": ["…"]}
    )
    out = ha.score_completeness(reads, ROWS)["a"]
    assert out["missed_by_ledger"] == ["食０"]  # full-width zero, not 食0
    assert out["recall"] == 0.0

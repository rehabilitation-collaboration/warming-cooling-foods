"""Tests for the RB-5 models (src/gap_models.py).

Fixtures are constructed so the expected direction of each estimate is known in
advance, and the sparsity mirrors the real data (most foods have no screened
study), so a regression that quietly analyses the wrong subset shows up.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import gap_models as gm


def _frame(n_sources, l2_screened, l1=None) -> pd.DataFrame:
    n = len(n_sources)
    return pd.DataFrame(
        {
            "food_key": [f"f{i}" for i in range(n)],
            "n_sources": n_sources,
            "l1": l1 if l1 is not None else [1000] * n,
            "l2_screened": l2_screened,
        }
    )


# --- Frame preparation ----------------------------------------------------
def test_prepare_derives_has_study_and_log_l1():
    out = gm.prepare_model_frame(_frame([1, 5, 9], [0, 3, 0], l1=[0, 99, 9]))
    assert list(out["has_study"]) == [0, 1, 0]
    assert out["log_l1"].tolist() == pytest.approx([np.log(1), np.log(100), np.log(10)])


def test_prepare_drops_unscreened_foods_and_records_them():
    # A food queried but not yet screened is NaN: "not measured" is not "no
    # research", so it must leave the model rather than count as a zero.
    df = _frame([2, 4, 6], [0, np.nan, 5])
    out = gm.prepare_model_frame(df)
    assert len(out) == 2
    assert out.attrs["dropped_unscreened"] == ["f1"]
    assert list(out["has_study"]) == [0, 1]


def test_prepare_rejects_a_frame_missing_columns():
    with pytest.raises(ValueError, match="missing columns"):
        gm.prepare_model_frame(pd.DataFrame({"food_key": ["a"], "n_sources": [3]}))


# --- Spearman -------------------------------------------------------------
def test_spearman_reports_perfect_monotonic_association():
    r = gm.spearman_with_ci([1, 2, 3, 4, 5, 6], [2, 4, 6, 8, 10, 12])
    assert r["rho"] == pytest.approx(1.0)
    assert r["n"] == 6


def test_spearman_ci_is_nan_when_n_too_small():
    r = gm.spearman_with_ci([1, 2, 3], [3, 2, 1])
    assert np.isnan(r["ci_lo"]) and np.isnan(r["ci_hi"])


# --- Primary model --------------------------------------------------------
def test_presence_logit_recovers_a_positive_belief_effect():
    # Study presence rises with belief breadth; L1 held constant so the
    # covariate cannot absorb the signal.
    rng = np.random.default_rng(7)
    breadth = np.repeat([1, 3, 6, 10], 25)
    p = 1 / (1 + np.exp(-(-4.0 + 0.55 * breadth)))
    has = (rng.random(len(breadth)) < p).astype(int)
    res = gm.presence_logit(_frame(breadth, has).pipe(gm.prepare_model_frame))
    assert res["converged"]
    assert res["terms"]["n_sources"]["beta"] > 0
    assert res["terms"]["n_sources"]["or"] > 1
    assert res["n"] == len(breadth)


def test_presence_logit_can_run_unadjusted():
    rng = np.random.default_rng(3)
    breadth = np.repeat([1, 4, 8], 30)
    has = (rng.random(len(breadth)) < breadth / 12).astype(int)
    frame = gm.prepare_model_frame(_frame(breadth, has))
    res = gm.presence_logit(frame, adjust_l1=False)
    assert res["converged"]
    assert "log_l1" not in res["terms"]


def test_presence_logit_reports_failure_instead_of_raising():
    # Perfectly separated data: no finite MLE exists. The caller must be told,
    # not handed a silently meaningless fit.
    breadth = [1, 1, 1, 9, 9, 9]
    res = gm.presence_logit(gm.prepare_model_frame(_frame(breadth, [0, 0, 0, 4, 4, 4])))
    assert res["converged"] is False or res["terms"]["n_sources"]["p"] > 0.05


# --- Collinearity diagnostic ----------------------------------------------
def test_predictor_vif_is_one_for_an_orthogonal_design():
    # Belief breadth and literature volume crossed evenly: no shared variance,
    # so each predictor's VIF is exactly 1.
    frame = gm.prepare_model_frame(_frame([1, 1, 9, 9], [0, 1, 0, 1], l1=[10, 10_000, 10, 10_000]))
    res = gm.predictor_vif(frame)
    assert res["pearson_r"] == pytest.approx(0.0, abs=1e-12)
    assert res["vif"]["n_sources"] == pytest.approx(1.0, abs=1e-9)
    assert res["vif"]["log_l1"] == pytest.approx(1.0, abs=1e-9)


def test_predictor_vif_rises_when_the_predictors_track_each_other():
    # A VIF must come from the linear fit between predictors. Squaring a rank
    # correlation cannot produce this: the ranks here are perfectly monotonic in
    # both frames, yet only the near-linear one carries a large VIF.
    frame = gm.prepare_model_frame(_frame([1, 3, 6, 9], [0, 1, 0, 1], l1=[10, 100, 1_000, 10_000]))
    res = gm.predictor_vif(frame)
    assert res["pearson_r"] > 0.99
    assert res["vif"]["n_sources"] > 5
    assert res["vif"]["n_sources"] == pytest.approx(res["vif"]["log_l1"])


# --- Sensitivity model ----------------------------------------------------
def test_count_negbin_flags_overdispersion_and_fits():
    rng = np.random.default_rng(11)
    breadth = rng.integers(1, 15, 180)
    l1 = rng.integers(50, 20000, 180)
    counts = rng.negative_binomial(0.3, 0.75, 180) * (rng.random(180) < 0.2)
    res = gm.count_negbin(gm.prepare_model_frame(_frame(breadth, counts, l1=l1)))
    assert res["converged"]
    assert res["alpha"] > 0
    assert np.isfinite(res["poisson_dispersion"])
    assert "n_sources" in res["terms"]


def test_count_negbin_offset_uses_l1_not_a_covariate():
    # With the offset in place, doubling every L1 must not change the belief
    # coefficient's sign — the offset absorbs literature volume by construction.
    rng = np.random.default_rng(5)
    breadth = rng.integers(1, 12, 150)
    l1 = rng.integers(100, 5000, 150)
    counts = rng.poisson(0.5, 150) * (rng.random(150) < 0.25)
    a = gm.count_negbin(gm.prepare_model_frame(_frame(breadth, counts, l1=l1)))
    b = gm.count_negbin(gm.prepare_model_frame(_frame(breadth, counts, l1=l1 * 2)))
    assert a["converged"] and b["converged"]
    assert np.sign(a["terms"]["n_sources"]["beta"]) == np.sign(b["terms"]["n_sources"]["beta"])


# --- Adjusted prediction curve (the primary-result figure) ----------------
def test_presence_logit_curve_spans_the_breadth_range_at_each_l1_level():
    rng = np.random.default_rng(3)
    breadth = rng.integers(1, 10, 140)
    l1 = rng.integers(50, 30000, 140)
    counts = rng.poisson(0.4, 140) * (rng.random(140) < 0.25)
    curve = gm.presence_logit_curve(gm.prepare_model_frame(_frame(breadth, counts, l1=l1)))
    assert set(curve["l1_quantile"]) == {0.25, 0.5, 0.75}
    # One row per (quantile, breadth level) over the observed breadth range.
    assert sorted(curve["n_sources"].unique()) == list(range(1, 10))
    assert len(curve) == 3 * 9


def test_presence_logit_curve_keeps_probabilities_and_bounds_in_range():
    # Bounds are built on the linear predictor and transformed, so they must
    # never leave [0, 1] even where the data are sparse.
    rng = np.random.default_rng(4)
    breadth = rng.integers(1, 10, 120)
    l1 = rng.integers(10, 50000, 120)
    counts = rng.poisson(0.2, 120) * (rng.random(120) < 0.15)
    curve = gm.presence_logit_curve(gm.prepare_model_frame(_frame(breadth, counts, l1=l1)))
    for col in ("p", "lo", "hi"):
        assert curve[col].between(0, 1).all()
    assert (curve["lo"] <= curve["p"]).all() and (curve["p"] <= curve["hi"]).all()


def test_presence_logit_curve_separates_levels_when_l1_drives_the_outcome():
    # Build data where only literature volume predicts having a study: the
    # curves must stack by L1 level and stay flat across belief breadth.
    rng = np.random.default_rng(9)
    breadth = rng.integers(1, 10, 240)
    l1 = rng.integers(10, 100000, 240)
    # Strong but not deterministic: a hard threshold would separate the data and
    # the fit would not converge, so the test would be asserting on a fit the
    # code is supposed to refuse.
    p = 1 / (1 + np.exp(-(np.log(l1 + 1) - 9.0)))
    counts = rng.binomial(1, p)
    curve = gm.presence_logit_curve(gm.prepare_model_frame(_frame(breadth, counts, l1=l1)))
    by_q = curve.groupby("l1_quantile")["p"].mean()
    assert by_q[0.25] < by_q[0.5] < by_q[0.75]
    # Flat in breadth: the spread within a level is far smaller than between.
    within = curve.groupby("l1_quantile")["p"].agg(lambda s: s.max() - s.min()).max()
    assert within < (by_q[0.75] - by_q[0.25])

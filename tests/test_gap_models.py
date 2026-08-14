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


# --- Leave-one-food-out influence ----------------------------------------
def test_leave_one_out_refits_once_per_food_and_names_the_omitted_one():
    # Outcomes are drawn from a logistic model rather than set by a threshold on
    # n_sources: a deterministic rule separates the design perfectly and every
    # refit would fail, which would test nothing.
    rng = np.random.default_rng(0)
    n_sources = rng.integers(1, 9, 40)
    l1 = rng.integers(100, 50_000, 40)
    p = 1 / (1 + np.exp(-(-2 + 0.4 * n_sources)))
    l2 = (rng.random(40) < p).astype(int) * 2
    out = gm.leave_one_food_out(gm.prepare_model_frame(_frame(n_sources, l2, l1=l1)))
    assert len(out) == 40
    assert set(out["omitted"]) == {f"f{i}" for i in range(40)}
    assert out["converged"].all()


def test_leave_one_out_surfaces_the_food_that_carries_the_estimate():
    # One food sits alone at the top of the breadth range and has a study, while
    # the rest are narrow-belief and mixed. Dropping it must move the odds ratio
    # further than dropping any of the interchangeable rest — that is the whole
    # point of running the check on a frame this small.
    n_sources = [1, 1, 2, 2, 3, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 2, 1, 3] + [9]
    l2 = [0, 2, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 0] + [4]
    frame = gm.prepare_model_frame(_frame(n_sources, l2, l1=[1000] * 19))
    out = gm.leave_one_food_out(frame)
    base = gm.presence_logit(frame)["terms"]["n_sources"]["or"]
    shifts = (out.set_index("omitted")["or"] - base).abs()
    assert shifts.idxmax() == "f18"


def test_leave_one_out_keeps_a_failed_refit_instead_of_dropping_the_row():
    # Perfect separation is the realistic failure here. The row has to survive
    # with NaN estimates, or a frame where half the refits break would report a
    # reassuringly narrow range over only the half that converged.
    frame = gm.prepare_model_frame(_frame([1, 2, 8, 9], [0, 0, 3, 5], l1=[1000] * 4))
    out = gm.leave_one_food_out(frame)
    assert len(out) == 4
    assert set(out.columns) >= {"omitted", "or", "p", "converged", "l1", "l2_screened"}
    assert not out["converged"].any()  # the fixture is separated on purpose
    assert out.loc[~out["converged"], ["or", "p"]].isna().all().all()


# --- Functional form of the L1 adjustment ---------------------------------
def _l1_frame(curvature: float, seed: int = 0, n: int = 600):
    """A frame where L1 tracks breadth and breadth itself does nothing.

    The true breadth odds ratio is 1 in both variants. Because the predictors
    are correlated, any part of L1's shape the model fails to absorb has nowhere
    to go but the breadth term — which is the failure mode the functional-form
    refits exist to detect. ``curvature`` = 0 gives an outcome that really is
    linear in log(L1 + 1); a negative value bends it.
    """
    rng = np.random.default_rng(seed)
    n_sources = rng.integers(1, 10, n)
    l1 = np.exp(n_sources * 0.6 + rng.normal(0, 0.4, n)).astype(int) + 1
    log_l1 = np.log(l1 + 1.0)
    eta = -1.0 + 1.2 * log_l1 + curvature * log_l1**2
    outcome = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(int)
    return gm.prepare_model_frame(_frame(n_sources, outcome, l1=l1))


def test_l1_forms_fits_all_three_specifications_and_reports_their_cost():
    out = gm.presence_logit_l1_forms(_l1_frame(curvature=-0.20))
    assert set(out) == {"quadratic", "tertile", "spline"}
    assert all(r["converged"] for r in out.values())
    # The parameter count is what tells a reader what the events are buying.
    assert out["quadratic"]["n_params"] == 4
    assert out["tertile"]["n_params"] == 4
    assert out["spline"]["n_params"] == 5


def test_l1_forms_reports_curvature_only_where_a_curvature_term_exists():
    out = gm.presence_logit_l1_forms(_l1_frame(curvature=-0.20))
    assert "curvature_p" in out["quadratic"]
    assert "curvature_p" not in out["tertile"]
    assert "curvature_p" not in out["spline"]


def test_l1_forms_move_the_breadth_estimate_when_the_outcome_bends():
    # The check has to be able to move. If a mis-specified linear adjustment
    # could never shift the breadth estimate, agreement between the forms would
    # not be evidence of anything.
    frame = _l1_frame(curvature=-0.20)
    linear = gm.presence_logit(frame)["terms"]["n_sources"]["or"]
    out = gm.presence_logit_l1_forms(frame)
    assert out["quadratic"]["curvature_p"] < 0.01
    assert abs(np.log(out["quadratic"]["or"] / linear)) > 0.05
    assert abs(np.log(out["spline"]["or"] / linear)) > 0.05


def test_l1_forms_leave_the_breadth_estimate_alone_when_it_does_not_bend():
    # And it has to stay still otherwise, which is the case the paper is in:
    # agreement across the forms only means something if disagreement was
    # available and did not happen.
    frame = _l1_frame(curvature=0.0)
    linear = gm.presence_logit(frame)["terms"]["n_sources"]["or"]
    out = gm.presence_logit_l1_forms(frame)
    assert out["quadratic"]["curvature_p"] > 0.05
    for spec in ("quadratic", "spline"):
        assert abs(np.log(out[spec]["or"] / linear)) < 0.05


def _cloglog_frame(gamma: float, n: int = 600, seed: int = 11) -> pd.DataFrame:
    """Foods whose chance of holding a study follows 1 - exp(-exp(g*log(L1+1))).

    ``gamma`` is what the offset asserts to be 1: at 1.0 the offset is the true
    model, away from 1.0 it is false and the test has something to detect.
    """
    rng = np.random.default_rng(seed)
    l1 = rng.integers(1, 5000, n).astype(float)
    log_l1 = np.log(l1 + 1.0)
    eta = -5.0 + gamma * log_l1
    y = (rng.random(n) < (1.0 - np.exp(-np.exp(eta)))).astype(float)
    return pd.DataFrame(
        {"n_sources": rng.integers(1, 10, n).astype(float), "log_l1": log_l1, "has_study": y}
    )


def test_cloglog_keeps_the_offset_when_volume_really_is_proportional():
    out = gm.presence_cloglog_opportunity(_cloglog_frame(gamma=1.0))
    assert out["converged"]
    assert out["lr"]["rejects_offset"] is False
    assert out["lr"]["offset_in_ci"] is True


def test_cloglog_rejects_the_offset_when_volume_is_not_proportional():
    # Without this the paired fit would be decoration: a test that cannot fire
    # is not evidence that the constraint holds.
    out = gm.presence_cloglog_opportunity(_cloglog_frame(gamma=0.5))
    assert out["lr"]["rejects_offset"] is True
    assert out["lr"]["offset_in_ci"] is False
    assert out["l1_free"]["ci_hi"] < 1.0


def test_cloglog_lr_is_the_gap_between_the_two_fits():
    out = gm.presence_cloglog_opportunity(_cloglog_frame(gamma=0.7))
    expected = 2 * (out["free"]["llf"] - out["offset"]["llf"])
    assert out["lr"]["stat"] == pytest.approx(expected)
    assert out["lr"]["df"] == 1


def test_cloglog_reports_the_same_coverage_term_from_both_fits():
    # The paper reads the coverage estimate off this model, so both fits have to
    # carry it — otherwise dropping the offset would change the question.
    out = gm.presence_cloglog_opportunity(_cloglog_frame(gamma=1.0))
    for side in ("offset", "free"):
        assert {"hr", "hr_lo", "hr_hi", "p"} <= set(out[side])


def test_the_real_frame_rejects_the_proportional_offset():
    # Pins what the manuscript says about the reviewer's proposed model: it fits
    # and it agrees on coverage, but the proportionality it assumes is not one
    # this frame supports, so the offset version is not reported on its own.
    from src.analysis import _read_counts, prepare_scatter_data
    from src.claim_mapping import load_claims, load_sources

    frame = gm.prepare_model_frame(
        prepare_scatter_data(load_claims(), load_sources(), _read_counts())
    )
    out = gm.presence_cloglog_opportunity(frame)
    assert out["converged"]
    assert out["lr"]["rejects_offset"] is True
    assert out["l1_free"]["ci_hi"] < 1.0
    # Both fits leave coverage where the primary logistic leaves it: null.
    for side in ("offset", "free"):
        assert out[side]["hr_lo"] < 1.0 < out[side]["hr_hi"]

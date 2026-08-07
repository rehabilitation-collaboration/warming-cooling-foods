"""Behaviour tests for Phase 3 attention-gap analysis.

Tests the data-prep contract, not the pixels: the Axis A/B join takes belief
direction and breadth from Axis A without an n_sources column clash, the log
transform keeps zero-study foods at y=0 (not dropped), zero-study is flagged,
and the bottom-right selection returns the wide-belief low-research foods in
breadth order. A single smoke test confirms a Figure is produced.
"""

import numpy as np
import pandas as pd
import pytest

from src import analysis as an


def _frame():
    """Two Tier-1 sources; three foods spanning the interesting cases."""
    sources = pd.DataFrame({"source_id": ["s0", "s1", "s2"], "tier": [1, 1, 1]})
    rows = []
    # carrot: 3 sources warm — wide belief.
    for sid in ("s0", "s1", "s2"):
        rows.append({"food_en": "carrot", "food_ja": "にんじん", "source_id": sid, "direction": "warm"})
    # ginger: 2 sources warm — sensitivity.
    for sid in ("s0", "s1"):
        rows.append({"food_en": "ginger", "food_ja": "しょうが", "source_id": sid, "direction": "warm"})
    # cucumber: 2 sources cool.
    for sid in ("s0", "s1"):
        rows.append({"food_en": "cucumber", "food_ja": "きゅうり", "source_id": sid, "direction": "cool"})
    return pd.DataFrame(rows), sources


def _counts_l2():
    """Per-food Axis B frame: carrot 0 screened studies, ginger 43, cucumber 2.

    Raw L2 is deliberately larger than L2′ (ginger 61 → 43) so a regression that
    plots the unscreened count instead of the screened one is visible.
    """
    return pd.DataFrame(
        {
            "food_key": ["carrot", "ginger", "cucumber"],
            "food_ja": ["にんじん", "しょうが", "きゅうり"],
            "scope": ["core", "sensitivity", "sensitivity"],
            "l2_raw": [11, 61, 5],
            "n_openalex": [2391, 3172, ""],
            "l2_screened": [0, 43, 2],
            "l1": [7842, 4210, 3300],
        }
    )


def test_prepare_joins_without_n_sources_clash():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2())
    # No merge suffix leak — the single n_sources column survives.
    assert "n_sources" in df.columns
    assert "n_sources_x" not in df.columns and "n_sources_y" not in df.columns
    assert set(df["direction"]) == {"warm", "cool"}


def test_prepare_takes_direction_from_axis_a():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2()).set_index("food_key")
    assert df.loc["carrot", "direction"] == "warm"
    assert df.loc["cucumber", "direction"] == "cool"
    assert df.loc["carrot", "n_sources"] == 3


def test_log_transform_keeps_zero_at_origin():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2()).set_index("food_key")
    # log10(0+1) == 0 — the zero-study food is plotted, not dropped.
    assert df.loc["carrot", "y"] == 0.0
    assert df.loc["carrot", "is_zero"]
    # log10(43+1) ≈ 1.64 — from L2′ (43), not raw L2 (61).
    assert np.isclose(df.loc["ginger", "y"], np.log10(44))
    assert not df.loc["ginger", "is_zero"]


def test_measure_is_screened_l2_not_the_raw_count():
    # The construct-validity rebuild is the whole point: a food whose raw L2 is
    # non-zero but whose screened count is zero must read as zero research.
    claims, sources = _frame()
    counts = _counts_l2()
    df = an.prepare_scatter_data(claims, sources, counts).set_index("food_key")
    assert df.loc["carrot", "l2_raw"] == 11  # raw count kept for comparison
    assert df.loc["carrot", an.MEASURE] == 0
    assert df.loc["carrot", "is_zero"]
    assert df.loc["carrot", "y"] == 0.0


def test_l1_is_carried_through_for_the_adjusted_models():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2()).set_index("food_key")
    assert df.loc["ginger", "l1"] == 4210


def test_bottom_right_returns_wide_belief_zero_study_in_order():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2())
    gap = an.bottom_right_foods(df)
    # Only carrot: n_sources ≥ 3 (core) AND 0 L2 studies. ginger has studies;
    # cucumber is below the core threshold.
    assert list(gap["food_key"]) == ["carrot"]


def test_bottom_right_orders_by_breadth_desc():
    # Two zero-study core foods → widest belief first.
    df = pd.DataFrame(
        {
            "food_key": ["a", "b"],
            "n_sources": [5, 9],
            "l2_screened": [0, 0],
            "direction": ["warm", "cool"],
        }
    )
    gap = an.bottom_right_foods(df)
    assert list(gap["food_key"]) == ["b", "a"]


def test_prepare_raises_when_axis_b_food_missing_from_axis_a():
    # A food present in Axis B but not Axis A must fail loudly, not silently
    # drop from the figure (guards against editing claims without regenerating
    # pubmed_counts.csv).
    claims, sources = _frame()
    counts = _counts_l2()
    counts.loc[len(counts)] = {
        "food_key": "ghost", "food_ja": "ゴースト", "scope": "core",
        "l2_raw": 0, "n_openalex": 1, "l2_screened": 0, "l1": 12,
    }
    with pytest.raises(ValueError, match="ghost"):
        an.prepare_scatter_data(claims, sources, counts)


def test_point_counts_collapses_the_zero_pile_up():
    # Most foods sit at y=0; the figure must encode how many, not draw 144
    # markers on one spot and imply a handful.
    df = pd.DataFrame(
        {
            "food_key": ["a", "b", "c", "d"],
            "x": [5, 5, 5, 9],
            "y": [0.0, 0.0, 0.0, 0.6],
            "is_zero": [True, True, True, False],
            "direction": ["warm", "warm", "cool", "cool"],
        }
    )
    pts = an.point_counts(df)
    assert len(pts) == 3  # (warm,5,0), (cool,5,0), (cool,9,0.6)
    warm_zero = pts[(pts["direction"] == "warm") & (pts["x"] == 5)].iloc[0]
    assert warm_zero["n_foods"] == 2
    assert warm_zero["is_zero"]
    assert pts["n_foods"].sum() == len(df)  # no food dropped or double-counted


def test_make_scatter_returns_figure():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2())
    fig = an.make_scatter(df)
    assert fig is not None
    assert len(fig.axes) == 1


def test_make_scatter_core_scope_smoke():
    # The core-only figure path (attention_gap_core.png) must render.
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2())
    fig = an.make_scatter(df, scope="core")
    assert fig is not None


def test_wilson_interval_stays_in_range_at_zero_successes():
    # Most groups have few studied foods; a normal-approximation interval would
    # dip below zero there and imply a negative share.
    lo, hi = an.wilson_interval(0, 40)
    assert lo == 0.0
    assert 0 < hi < 1


def test_breadth_bins_pool_the_thin_upper_tail():
    df = pd.DataFrame({"n_sources": [1, 2, 3, 4, 5, 8, 9, 14]})
    labels = list(an.breadth_bin_labels(df))
    assert labels == ["1", "2", "3-4", "3-4", "5-8", "5-8", "9+", "9+"]


def test_l1_tertiles_split_the_volume_range():
    df = pd.DataFrame({"l1": [1, 2, 3, 100, 200, 300, 10000, 20000, 30000]})
    labels = list(an.l1_tertile_labels(df))
    assert labels[0] == "low" and labels[-1] == "high"
    assert set(labels) == {"low", "mid", "high"}


def test_make_presence_plot_returns_two_panels():
    claims, sources = _frame()
    df = an.prepare_scatter_data(claims, sources, _counts_l2())
    fig = an.make_presence_plot(df)
    assert len(fig.axes) == 2

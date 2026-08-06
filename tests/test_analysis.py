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
    """L2 counts: carrot studied 0×, ginger 43×, cucumber 2×."""
    return pd.DataFrame(
        {
            "food_key": ["carrot", "ginger", "cucumber"],
            "food_ja": ["にんじん", "しょうが", "きゅうり"],
            "scope": ["core", "sensitivity", "sensitivity"],
            "layer": ["L2", "L2", "L2"],
            "n_pubmed": [0, 43, 2],
            "n_openalex": [2391, 3172, ""],
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
    # log10(43+1) ≈ 1.64.
    assert np.isclose(df.loc["ginger", "y"], np.log10(44))
    assert not df.loc["ginger", "is_zero"]


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
            "n_pubmed": [0, 0],
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
        "layer": "L2", "n_pubmed": 0, "n_openalex": 1,
    }
    with pytest.raises(ValueError, match="ghost"):
        an.prepare_scatter_data(claims, sources, counts)


def test_annotation_targets_dedups_by_x():
    # Two zero-study foods share x=5 → only one is labelled; x=9 adds one more.
    df = pd.DataFrame(
        {
            "food_key": ["a", "b", "c"],
            "x": [5, 5, 9],
            "n_sources": [5, 5, 9],
            "n_pubmed": [0, 0, 0],
            "direction": ["warm", "warm", "cool"],
        }
    )
    targets = an._annotation_targets(df)
    assert targets["x"].nunique() == len(targets)  # no duplicate x column
    assert set(targets["x"]) == {5, 9}


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

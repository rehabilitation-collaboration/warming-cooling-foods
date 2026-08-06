"""Phase 3: the attention-gap scatter plot.

Joins Axis A (belief breadth = how many independent sources call a food
warming/cooling) with Axis B (research attention = PubMed L2 hits, i.e. studies
that examine the food in a thermal-effect context) and plots one against the
other. The story is the **bottom-right void**: foods believed by many sources
but studied by almost no one.

Data prep is separated from drawing so the join, the log transform, and the
bottom-right selection are pure and unit-tested; matplotlib only renders what
those functions produce. Figure labels are English-only (food_key), avoiding CJK
glyph problems in the PDF pipeline.

Axis choices:
- x = n_sources (belief breadth), linear — the range is small (2–14).
- y = log10(n_pubmed_L2 + 1), so zero-study foods land at y=0 instead of being
  dropped by a log scale; they are the core attention-gap cases and are drawn
  with a distinct marker rather than hidden.

Direction is encoded by BOTH colour and marker shape (secondary encoding), so
identity never rests on colour alone — required because "contested" is a low-
chroma grey. OpenAlex/CiNii are auxiliary and are not plotted on the main axes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .claim_mapping import CONTESTED, aggregate_axis_a, load_claims, load_sources
from .definitions import COOL, NEUTRAL, PLOTS_DIR, PUBMED_COUNTS_CSV, WARM
from .evidence_mapping import CORE_MIN_SOURCES

# --- Direction styling (colour + shape; colour alone is never load-bearing) --
# Okabe-Ito colour-blind-safe hues: warm=vermillion, cool=blue, contested=grey.
DIRECTION_COLOR = {
    WARM: "#D55E00",
    COOL: "#0072B2",
    CONTESTED: "#999999",
    NEUTRAL: "#999999",
}
DIRECTION_MARKER = {
    WARM: "o",       # circle
    COOL: "^",       # triangle
    CONTESTED: "s",  # square
    NEUTRAL: "D",    # diamond
}

# The claimed-context research count lives on the L2 PubMed layer.
Y_LAYER = "L2"


def _read_counts(path=PUBMED_COUNTS_CSV) -> pd.DataFrame:
    """Load the Axis B counts, keeping only the L2 (claimed-context) rows."""
    counts = pd.read_csv(path)
    return counts[counts["layer"] == Y_LAYER].copy()


def prepare_scatter_data(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    counts_l2: pd.DataFrame,
) -> pd.DataFrame:
    """Join belief breadth (Axis A) with L2 research counts (Axis B).

    ``counts_l2`` must already be filtered to layer == L2 (see ``_read_counts``).
    Only the Axis A ``direction``/``n_sources`` are taken — Axis B carries its own
    ``n_sources`` copy, so we select the A columns explicitly to avoid a
    ``n_sources_x/_y`` split on merge.

    Returns one row per food with: food_key, food_ja, scope, direction,
    n_sources, n_pubmed (L2), n_openalex, x (=n_sources), y (=log10(L2+1)),
    is_zero (L2 == 0).
    """
    a = aggregate_axis_a(claims, sources, max_tier=2)
    a_slim = a[["food_key", "direction", "n_sources"]]

    b = counts_l2[["food_key", "food_ja", "scope", "n_pubmed", "n_openalex"]]
    df = b.merge(a_slim, on="food_key", how="left")

    # Every Axis B food must match an Axis A row; a mismatch (e.g. claims edited
    # without regenerating pubmed_counts.csv) would silently drop points from the
    # figure. Fail loudly instead.
    missing = df.loc[df["direction"].isna(), "food_key"].tolist()
    if missing:
        raise ValueError(f"Axis B foods with no Axis A match: {missing}")

    df["x"] = df["n_sources"]
    df["y"] = np.log10(df["n_pubmed"] + 1)
    df["is_zero"] = df["n_pubmed"] == 0
    return df.reset_index(drop=True)


def bottom_right_foods(
    df: pd.DataFrame,
    *,
    min_sources: int = CORE_MIN_SOURCES,
    max_pubmed: int = 0,
) -> pd.DataFrame:
    """The attention-gap targets: wide belief (n_sources ≥ min) × little/no research.

    Defaults to the sharpest cases — core beliefs (n_sources ≥ 3) with zero L2
    studies — sorted by belief breadth so the most-believed, least-studied foods
    come first (used to pick which points to annotate).
    """
    hit = df[(df["n_sources"] >= min_sources) & (df["n_pubmed"] <= max_pubmed)]
    return hit.sort_values("n_sources", ascending=False).reset_index(drop=True)


def _annotation_targets(df: pd.DataFrame, n: int = 7) -> pd.DataFrame:
    """Foods to label: the widest-belief zero-study cases, one per x column.

    Zero-study foods pile up on the y=0 baseline, so many share an x value
    (e.g. green onion and lotus root both at n_sources=9). We keep the
    widest-belief food per column and cap the count, so labels stay legible
    (selective direct labels, per the dataviz method).
    """
    gap = bottom_right_foods(df)  # already sorted by breadth desc
    picked, seen_x = [], set()
    for _, r in gap.iterrows():
        if r["x"] in seen_x:
            continue
        seen_x.add(r["x"])
        picked.append(r)
        if len(picked) >= n:
            break
    return pd.DataFrame(picked)


def make_scatter(df: pd.DataFrame, *, scope: str | None = None, title: str | None = None):
    """Render the attention-gap scatter and return the matplotlib Figure.

    ``scope`` filters to "core"/"sensitivity" if given (else all foods are drawn).
    Direction is shown by colour + marker shape; zero-study foods get a hollow
    face so the bottom-right void reads at a glance. A handful of the widest-
    belief zero-study foods are directly labelled.
    """
    import matplotlib

    matplotlib.use("Agg")  # headless: no display needed
    import matplotlib.pyplot as plt

    data = df if scope is None else df[df["scope"] == scope]
    if data.empty:
        raise ValueError(f"no rows to plot (scope={scope!r})")

    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    # Fix limits up front so the shaded region can be placed in data coordinates.
    x_hi = data["x"].max() + 0.8
    y_hi = data["y"].max() + 0.25
    ax.set_xlim(1.3, x_hi)
    ax.set_ylim(-0.12, y_hi)

    # Shade the bottom-right "void" (wide belief × little research) — the region
    # this paper indicts. Data coordinates; drawn under the points.
    ax.add_patch(
        plt.Rectangle(
            (CORE_MIN_SOURCES - 0.5, -0.12), x_hi - (CORE_MIN_SOURCES - 0.5),
            np.log10(2) + 0.12, color="#F0D9C9", alpha=0.5, zorder=0, linewidth=0,
        )
    )
    ax.axvline(CORE_MIN_SOURCES - 0.5, color="#C8A48A", linewidth=0.8, zorder=0)

    for direction, grp in data.groupby("direction"):
        color = DIRECTION_COLOR.get(direction, "#999999")
        marker = DIRECTION_MARKER.get(direction, "o")
        zero = grp[grp["is_zero"]]
        nonzero = grp[~grp["is_zero"]]
        # Studied foods: filled. Zero-study foods: hollow, so the void stands out.
        ax.scatter(
            nonzero["x"], nonzero["y"], s=70, c=color, marker=marker,
            edgecolors="white", linewidths=0.8, alpha=0.85, label=direction, zorder=3,
        )
        ax.scatter(
            zero["x"], zero["y"], s=95, facecolors="none", edgecolors=color,
            marker=marker, linewidths=1.7, zorder=4,
        )

    # Direct-label the sharpest cases, staggered upward with leader lines so the
    # baseline pile-up stays legible.
    targets = _annotation_targets(data).sort_values("x")
    for i, (_, r) in enumerate(targets.iterrows()):
        y_text = 0.35 + 0.42 * (i % 3)  # 3-level vertical stagger
        ax.annotate(
            r["food_key"], (r["x"], r["y"]),
            xytext=(r["x"], y_text), fontsize=8, color="#333333", ha="center",
            arrowprops=dict(arrowstyle="-", color="#B0B0B0", linewidth=0.6),
        )

    ax.set_xlabel("Belief breadth (number of independent sources)")
    ax.set_ylabel("Research attention  log10(PubMed L2 hits + 1)")
    ax.set_title(title or "Attention gap: widely believed foods are rarely studied")
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.legend(title="Lay direction", frameon=False, loc="upper right")
    fig.tight_layout()
    return fig


def main() -> None:
    claims, sources = load_claims(), load_sources()
    counts_l2 = _read_counts()
    df = prepare_scatter_data(claims, sources, counts_l2)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    # Main figure (all foods) + a core-only cut for the sensitivity claim.
    for scope, name in ((None, "attention_gap_all"), ("core", "attention_gap_core")):
        fig = make_scatter(df, scope=scope)
        out = PLOTS_DIR / f"{name}.png"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")

    # Tracked table backing the figure (data availability; also the WARN relief
    # for the low-contrast contested/neutral grey — identity is legible in text).
    table = PLOTS_DIR / "attention_gap_data.csv"
    df.sort_values(["n_sources", "n_pubmed"], ascending=[False, True]).to_csv(table, index=False)
    print(f"wrote {table}")

    gap = bottom_right_foods(df)
    print(f"\nbottom-right void — {len(gap)} core beliefs with 0 L2 studies:")
    for _, r in gap.iterrows():
        print(f"  {r['food_key']:16s} n_sources={int(r['n_sources'])} dir={r['direction']}")


if __name__ == "__main__":
    main()

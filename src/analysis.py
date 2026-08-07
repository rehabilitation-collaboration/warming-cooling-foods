"""Phase 3 / RB-5: the attention-gap scatter plot.

Joins Axis A (belief breadth = how many independent sources call a food
warming/cooling) with Axis B (research attention) and plots one against the
other, keeping a **bottom-right void** in view — foods believed by many sources
but studied by almost no one.

**Axis B is L2′, not the raw L2 count.** The raw keyword co-occurrence count was
shown not to measure the intended construct (poultry heat-stress papers under
`chicken`, missed thermic-effect studies under `ginger`), so every L2 record was
screened by two independent coders and L2′ — the studies that survive — is what
this module plots. Raw L2 stays on the frame as `l2_raw` for the before/after
comparison only; nothing downstream should use it as the measure.

Data prep is separated from drawing so the join, the log transform, and the
bottom-right selection are pure and unit-tested; matplotlib only renders what
those functions produce. Figure labels are English-only (food_key), avoiding CJK
glyph problems in the PDF pipeline.

Axis choices:
- x = n_sources (belief breadth), linear — the range is small (1–14).
- y = log10(L2′ + 1), so zero-study foods land at y=0 instead of being dropped by
  a log scale; they are the core attention-gap cases and are drawn with a
  distinct marker rather than hidden.

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

# The claimed-context research count lives on the L2 PubMed layer; L1 (the
# food's total literature) is the exposure the models offset against.
Y_LAYER = "L2"
L1_LAYER = "L1"

# The measure plotted and modelled: screened L2, i.e. on-construct studies.
MEASURE = "l2_screened"

# Marker area encodes how many foods share a plotted position (see point_counts).
MARKER_BASE = 28
MARKER_PER_FOOD = 22
SIZE_KEY = (1, 5, 15)


def _read_counts(path=PUBMED_COUNTS_CSV) -> pd.DataFrame:
    """Load Axis B as one row per food, with L1, raw L2 and screened L2′.

    ``pubmed_counts.csv`` is long (one row per food × layer). The analysis needs
    L1 and L2 side by side, so they are pivoted here rather than in every caller.
    ``l2_screened`` is NaN for a food that was queried but not screened — that is
    "not measured", which is not the same as "no research", so it is preserved
    rather than filled with 0.
    """
    counts = pd.read_csv(path)
    l2 = counts[counts["layer"] == Y_LAYER][
        ["food_key", "food_ja", "scope", "n_pubmed", "n_openalex", "L2_screened"]
    ].rename(columns={"n_pubmed": "l2_raw", "L2_screened": MEASURE})
    l1 = counts[counts["layer"] == L1_LAYER][["food_key", "n_pubmed"]].rename(
        columns={"n_pubmed": "l1"}
    )
    return l2.merge(l1, on="food_key", how="left").reset_index(drop=True)


def prepare_scatter_data(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    counts: pd.DataFrame,
) -> pd.DataFrame:
    """Join belief breadth (Axis A) with screened research counts (Axis B).

    ``counts`` is the per-food frame from ``_read_counts`` (l1, l2_raw,
    l2_screened). Only the Axis A ``direction``/``n_sources`` are taken — Axis B
    carries its own ``n_sources`` copy, so we select the A columns explicitly to
    avoid a ``n_sources_x/_y`` split on merge.

    Returns one row per food with: food_key, food_ja, scope, direction,
    n_sources, l1, l2_raw, l2_screened, n_openalex, x (=n_sources),
    y (=log10(L2′+1)), is_zero (L2′ == 0).
    """
    a = aggregate_axis_a(claims, sources, max_tier=2)
    a_slim = a[["food_key", "direction", "n_sources"]]

    df = counts.merge(a_slim, on="food_key", how="left")

    # Every Axis B food must match an Axis A row; a mismatch (e.g. claims edited
    # without regenerating pubmed_counts.csv) would silently drop points from the
    # figure. Fail loudly instead.
    missing = df.loc[df["direction"].isna(), "food_key"].tolist()
    if missing:
        raise ValueError(f"Axis B foods with no Axis A match: {missing}")

    df["x"] = df["n_sources"]
    df["y"] = np.log10(df[MEASURE] + 1)
    df["is_zero"] = df[MEASURE] == 0
    return df.reset_index(drop=True)


def bottom_right_foods(
    df: pd.DataFrame,
    *,
    min_sources: int = CORE_MIN_SOURCES,
    max_studies: int = 0,
) -> pd.DataFrame:
    """The attention-gap targets: wide belief (n_sources ≥ min) × little/no research.

    Defaults to the sharpest cases — core beliefs (n_sources ≥ 3) with zero
    on-construct studies — sorted by belief breadth so the most-believed,
    least-studied foods come first (used to pick which points to annotate).
    """
    hit = df[(df["n_sources"] >= min_sources) & (df[MEASURE] <= max_studies)]
    return hit.sort_values("n_sources", ascending=False).reset_index(drop=True)


def point_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the frame to one row per plotted position with a food count.

    With most foods at zero, a plain scatter draws 144 markers on top of each
    other and the void reads as a handful of points. Every (direction, x, y)
    position is therefore drawn once, sized by how many foods sit there, and the
    counts are returned so a caller can state them rather than imply them.
    """
    grouped = (
        df.groupby(["direction", "x", "y"], dropna=False)
        .agg(n_foods=("food_key", "size"), is_zero=("is_zero", "first"))
        .reset_index()
    )
    return grouped.sort_values("n_foods", ascending=False).reset_index(drop=True)


def make_scatter(df: pd.DataFrame, *, scope: str | None = None, title: str | None = None):
    """Render the attention-gap scatter and return the matplotlib Figure.

    ``scope`` filters to one belief tier if given (else all foods are drawn).
    Direction is shown by colour + marker shape; zero-study foods get a hollow
    face so the void reads at a glance, and **marker area encodes how many foods
    share the position**, because the zero baseline holds most of the dataset.

    Individual foods are not labelled here. Direct labels on the baseline would
    need leader lines that cross studied foods higher up, which reads as though
    the label belongs to the point it passes. The foods are named in
    ``attention_gap_data.csv`` and in the manuscript table instead.
    """
    import matplotlib

    matplotlib.use("Agg")  # headless: no display needed
    import matplotlib.pyplot as plt

    data = df if scope is None else df[df["scope"] == scope]
    if data.empty:
        raise ValueError(f"no rows to plot (scope={scope!r})")

    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    # Fix limits up front so the shaded region can be placed in data coordinates.
    # The lower bound is derived from the data, not fixed: the universe now
    # reaches n_sources = 1, and a hard-coded floor would push those foods off
    # the axes — silently dropping the least-believed end of the range, which is
    # the range restriction this analysis exists to remove.
    x_lo = data["x"].min() - 0.7
    x_hi = data["x"].max() + 0.8
    y_hi = data["y"].max() + 0.25
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(-0.12, y_hi)

    # Shade the region this paper indicts: wide belief, at most one study.
    ax.add_patch(
        plt.Rectangle(
            (CORE_MIN_SOURCES - 0.5, -0.12), x_hi - (CORE_MIN_SOURCES - 0.5),
            np.log10(2) + 0.12, color="#F0D9C9", alpha=0.5, zorder=0, linewidth=0,
        )
    )
    ax.axvline(CORE_MIN_SOURCES - 0.5, color="#C8A48A", linewidth=0.8, zorder=0)
    ax.set_xticks(range(int(np.ceil(x_lo)), int(x_hi) + 1))

    points = point_counts(data)
    for direction, grp in points.groupby("direction"):
        color = DIRECTION_COLOR.get(direction, "#999999")
        marker = DIRECTION_MARKER.get(direction, "o")
        size = MARKER_BASE + MARKER_PER_FOOD * grp["n_foods"]
        zero, nonzero = grp[grp["is_zero"]], grp[~grp["is_zero"]]
        # Studied foods: filled. Zero-study foods: hollow, so the void stands out.
        ax.scatter(
            nonzero["x"], nonzero["y"], s=size[~grp["is_zero"]], c=color, marker=marker,
            edgecolors="white", linewidths=0.8, alpha=0.85, label=direction, zorder=3,
        )
        ax.scatter(
            zero["x"], zero["y"], s=size[grp["is_zero"]], facecolors="none",
            edgecolors=color, marker=marker, linewidths=1.7, zorder=4,
        )

    # Marker area is load-bearing, so say what it means and give a size key.
    for n in SIZE_KEY:
        ax.scatter([], [], s=MARKER_BASE + MARKER_PER_FOOD * n, facecolors="none",
                   edgecolors="#555555", marker="o", linewidths=1.2,
                   label=f"{n} food" + ("s" if n > 1 else ""))

    ax.set_xlabel("Belief breadth (number of independent sources)")
    ax.set_ylabel("Research attention  log10(screened studies + 1)")
    ax.set_title(title or "Belief breadth and on-construct research attention")
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.legend(title="Lay direction / marker size", frameon=False, loc="upper right",
              labelspacing=1.1, borderpad=0.9)
    fig.tight_layout()
    return fig


def main() -> None:
    claims, sources = load_claims(), load_sources()
    df = prepare_scatter_data(claims, sources, _read_counts())

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    # Figure 1 — the primary result: belief breadth vs literature volume as
    # predictors of having any on-construct study.
    fig = make_presence_plot(df)
    out = PLOTS_DIR / "presence_by_breadth_and_volume.png"
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")

    # Figure 2 — the per-food scatter (all foods) + a core-only cut.
    for scope, name in ((None, "attention_gap_all"), ("core", "attention_gap_core")):
        fig = make_scatter(df, scope=scope)
        out = PLOTS_DIR / f"{name}.png"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")

    # Tracked table backing the figure (data availability; also the WARN relief
    # for the low-contrast contested/neutral grey — identity is legible in text).
    table = PLOTS_DIR / "attention_gap_data.csv"
    df.sort_values(["n_sources", MEASURE], ascending=[False, True]).to_csv(table, index=False)
    print(f"wrote {table}")

    gap = bottom_right_foods(df)
    print(f"\nbottom-right void — {len(gap)} core beliefs with 0 screened studies:")
    for _, r in gap.iterrows():
        print(f"  {r['food_key']:16s} n_sources={int(r['n_sources'])} dir={r['direction']}")



# --- Primary-result figure -----------------------------------------------
# Belief-breadth bins. The upper tiers are pooled because breadth thins out
# quickly (one food at 14), and a per-level proportion there is one food wide.
BREADTH_BINS = ((1, 1, "1"), (2, 2, "2"), (3, 4, "3-4"), (5, 8, "5-8"), (9, 99, "9+"))


def wilson_interval(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a proportion — stays inside [0, 1] at k=0."""
    if n == 0:
        return float("nan"), float("nan")
    from scipy import stats as _st

    z = _st.norm.ppf(1 - (1 - conf) / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _proportion_by_group(df: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    """Share of foods with at least one screened study, per group label."""
    rows = []
    for label, grp in df.groupby(labels, observed=True):
        n = len(grp)
        k = int((~grp["is_zero"]).sum())
        lo, hi = wilson_interval(k, n)
        rows.append({"label": label, "n": n, "k": k, "p": k / n, "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def breadth_bin_labels(df: pd.DataFrame) -> pd.Series:
    """Assign each food its belief-breadth bin label (see BREADTH_BINS)."""
    def _bin(n):
        for lo, hi, name in BREADTH_BINS:
            if lo <= n <= hi:
                return name
        return BREADTH_BINS[-1][2]

    order = [name for _, _, name in BREADTH_BINS]
    return pd.Categorical(df["n_sources"].map(_bin), categories=order, ordered=True)


def l1_tertile_labels(df: pd.DataFrame) -> pd.Series:
    """Assign each food an L1 tertile label (how much it is studied at all)."""
    q = df["l1"].quantile([1 / 3, 2 / 3]).to_numpy()
    def _bin(v):
        if v <= q[0]:
            return "low"
        return "mid" if v <= q[1] else "high"

    return pd.Categorical(df["l1"].map(_bin), categories=["low", "mid", "high"], ordered=True)


def make_presence_plot(df: pd.DataFrame):
    """The primary result: what predicts having any on-construct study at all.

    Left panel varies belief breadth, right panel varies the food's total
    literature volume (L1). Both show the same outcome on the same y scale, so
    the contrast — a flat line against a rising one — is the finding, and the
    per-group food counts are printed on the axis so no proportion is read
    without its denominator.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    panels = (
        ("Belief breadth (independent sources)", breadth_bin_labels(df), "#D55E00"),
        ("Total literature on the food (L1 tertile)", l1_tertile_labels(df), "#0072B2"),
    )
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharey=True)
    for ax, (xlabel, labels, colour) in zip(axes, panels):
        prop = _proportion_by_group(df, labels)
        xs = np.arange(len(prop))
        ax.errorbar(
            xs, prop["p"],
            yerr=[prop["p"] - prop["lo"], prop["hi"] - prop["p"]],
            fmt="o", color=colour, ecolor=colour, elinewidth=1.2,
            capsize=4, markersize=8, markeredgecolor="white",
        )
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{r.label}\n(n={r.n})" for r in prop.itertuples()])
        ax.set_xlim(-0.5, len(prop) - 0.5)
        ax.set_xlabel(xlabel)
        ax.grid(True, axis="y", linewidth=0.4, alpha=0.4)

    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Share of foods with ≥1 screened study")
    fig.suptitle("What predicts whether a food has been studied for a thermal effect")
    fig.tight_layout()
    return fig

if __name__ == "__main__":
    main()

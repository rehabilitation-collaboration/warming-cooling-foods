"""One-time statistical confirmation for the manuscript (Phase 4).

Recomputes every number the manuscript will assert, directly from the pipeline
output (not from any hand-recorded value), so the written claims are grounded in
what a reviewer would obtain by re-running the code:

- Spearman rho / p (and 95% CI) for belief breadth (n_sources) vs research
  attention (PubMed L2 hits), on the core (n_sources>=3) subset and on all foods.
- Zero-research rate overall and split by lay direction (warm vs cool).
- Mann-Whitney U for warm-vs-cool difference in research attention.
- Fisher exact test (with odds-ratio 95% CI) on the warm-vs-cool
  zero-attention contrast.
- High-belief (n_sources>=11) zero-research rate.
- Tier1-only vs Tier1+2 sensitivity: rho and core zero-rate under each frame.

Run: python3 -m src.verify_stats  (from the project root)
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from .analysis import Y_LAYER, _read_counts, prepare_scatter_data
from .claim_mapping import aggregate_axis_a, load_claims, load_sources
from .definitions import COOL, TIER_INDIVIDUAL, TIER_ORG, WARM
from .evidence_mapping import CORE_MIN_SOURCES


def _spearman(df):
    rho, p = stats.spearmanr(df["n_sources"], df["n_pubmed"])
    return rho, p, len(df)


def _spearman_ci(rho: float, n: int, conf: float = 0.95):
    """95% CI for a Spearman rho via Fisher z, with the Bonett-Wright
    variance correction ((1 + rho**2 / 2) / (n - 3)) for rank correlations.

    Returns (lo, hi). Requires n > 3; NaN bounds otherwise.
    """
    if n <= 3 or not np.isfinite(rho):
        return float("nan"), float("nan")
    z = np.arctanh(rho)
    se = np.sqrt((1 + rho**2 / 2) / (n - 3))
    crit = stats.norm.ppf(1 - (1 - conf) / 2)
    return np.tanh(z - crit * se), np.tanh(z + crit * se)


def _or_ci_woolf(a: int, b: int, c: int, d: int, conf: float = 0.95):
    """Sample odds ratio (ad/bc) and its 95% CI via Woolf's logit method.

    Table is [[a, b], [c, d]] = [[warm-zero, warm-nonzero],
    [cool-zero, cool-nonzero]]. No cell is zero in this fixed 2x2
    (min cell = 3), so no continuity correction is applied and the point
    estimate matches the sample OR reported in Table 2 (= scipy.fisher_exact's
    OR). Returns (or, lo, hi).
    """
    or_s = (a * d) / (b * c)
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    crit = stats.norm.ppf(1 - (1 - conf) / 2)
    lo = np.exp(np.log(or_s) - crit * se)
    hi = np.exp(np.log(or_s) + crit * se)
    return or_s, lo, hi


def _core_from_axis_a(claims, sources, counts_l2, max_tier):
    """Axis A (belief breadth) at ``max_tier`` inner-joined to L2 counts, then
    cut to the core (n_sources >= CORE_MIN_SOURCES).

    Used for the Tier sensitivity check: unlike ``prepare_scatter_data`` (which
    fixes max_tier=2 and fails loud on any Axis-B food missing from Axis A), this
    re-derives belief breadth under each frame and inner-joins, so a food that
    drops below the frame simply leaves that frame's set.
    """
    a = aggregate_axis_a(claims, sources, max_tier=max_tier)[
        ["food_key", "direction", "n_sources"]
    ]
    b = counts_l2[["food_key", "n_pubmed"]]
    df = a.merge(b, on="food_key", how="inner")
    df["is_zero"] = df["n_pubmed"] == 0
    return df[df["n_sources"] >= CORE_MIN_SOURCES].copy()


def main() -> None:
    claims, sources = load_claims(), load_sources()
    df = prepare_scatter_data(claims, sources, _read_counts())

    core = df[df["n_sources"] >= CORE_MIN_SOURCES].copy()

    print("=" * 64)
    print("N foods total:", len(df))
    print("N core (n_sources >= %d):" % CORE_MIN_SOURCES, len(core))
    print("=" * 64)

    # --- Spearman: belief breadth vs research attention ------------------
    for label, d in (("core (n_sources>=3)", core), ("all foods", df)):
        rho, p, n = _spearman(d)
        lo, hi = _spearman_ci(rho, n)
        print(f"[Spearman] {label:22s} n={n:3d}  rho={rho:+.4f}  "
              f"p={p:.4f}  95%CI=[{lo:+.3f}, {hi:+.3f}]")

    # Also Pearson on log-transformed y for completeness (reported as robustness).
    rho_l, p_l = stats.spearmanr(core["n_sources"], core["y"])
    print(f"[Spearman] core, n_sources vs y=log10(L2+1): rho={rho_l:+.4f} p={p_l:.4f}")

    print("-" * 64)

    # --- Zero-research rate ---------------------------------------------
    n_zero = int(core["is_zero"].sum())
    print(f"[Zero rate] core: {n_zero}/{len(core)} = {100*n_zero/len(core):.1f}%")

    all_zero = int(df["is_zero"].sum())
    print(f"[Zero rate] all:  {all_zero}/{len(df)} = {100*all_zero/len(df):.1f}%")

    print("-" * 64)

    # --- Warm vs cool zero-research rate (core) --------------------------
    for direction in (WARM, COOL):
        grp = core[core["direction"] == direction]
        z = int(grp["is_zero"].sum())
        print(f"[Zero by dir] {direction:5s}: {z}/{len(grp)} = {100*z/len(grp):.1f}%")

    # Direction breakdown of the core set (sanity).
    print("[Direction counts, core]:")
    print(core["direction"].value_counts().to_string())

    print("-" * 64)

    # --- Mann-Whitney U: warm vs cool research attention (core) ----------
    warm_hits = core.loc[core["direction"] == WARM, "n_pubmed"].to_numpy()
    cool_hits = core.loc[core["direction"] == COOL, "n_pubmed"].to_numpy()
    u, p_mw = stats.mannwhitneyu(warm_hits, cool_hits, alternative="two-sided")
    print(f"[Mann-Whitney] warm(n={len(warm_hits)}) vs cool(n={len(cool_hits)}) "
          f"research attention: U={u:.1f} p={p_mw:.4f}")
    print(f"  median L2 hits: warm={np.median(warm_hits):.1f} cool={np.median(cool_hits):.1f}")

    print("-" * 64)

    # --- Fisher exact: warm vs cool zero-attention contrast (core) --------
    warm = core[core["direction"] == WARM]
    cool = core[core["direction"] == COOL]
    a = int(warm["is_zero"].sum())          # warm, zero L2
    b = len(warm) - a                       # warm, >0 L2
    c = int(cool["is_zero"].sum())          # cool, zero L2
    d = len(cool) - c                       # cool, >0 L2
    or_fisher, p_fisher = stats.fisher_exact([[a, b], [c, d]], alternative="two-sided")
    or_c, or_lo, or_hi = _or_ci_woolf(a, b, c, d)
    print(f"[Fisher] warm-zero {a}/{a+b} vs cool-zero {c}/{c+d}: "
          f"OR={or_fisher:.3f} p={p_fisher:.4f}")
    print(f"  Woolf-logit OR = {or_c:.3f}  95%CI=[{or_lo:.3f}, {or_hi:.3f}]")

    print("-" * 64)

    # --- High-belief zero rate (n_sources >= 11) -------------------------
    for thr in (11, 9):
        hb = core[core["n_sources"] >= thr]
        z = int(hb["is_zero"].sum())
        print(f"[High-belief zero] n_sources>={thr}: {z}/{len(hb)} = "
              f"{100*z/len(hb):.1f}%")

    print("-" * 64)

    # --- The bottom-right void foods (for the manuscript's exemplar list) -
    void = core[core["is_zero"]].sort_values("n_sources", ascending=False)
    print(f"[Void] {len(void)} core foods with 0 L2 studies:")
    for _, r in void.iterrows():
        print(f"  {r['food_key']:16s} n_sources={int(r['n_sources']):2d} dir={r['direction']}")

    print("=" * 64)
    # --- Flagship examples (coffee, ginger, green tea) -------------------
    for key in ("coffee", "ginger", "green tea"):
        r = df[df["food_key"] == key]
        if len(r):
            r = r.iloc[0]
            print(f"[Flagship] {key:10s} dir={r['direction']:5s} "
                  f"n_sources={int(r['n_sources']):2d} L2={int(r['n_pubmed'])}")

    print("=" * 64)
    # --- Tier sensitivity: Tier1-only vs Tier1+2 -------------------------
    # The primary axis uses Tier1+2 (max_tier=2). This checks the core pattern
    # holds under the Tier1-only frame (max_tier=1), re-deriving belief breadth
    # and the core set under each frame.
    counts_l2 = _read_counts()
    print(f"[Tier sensitivity] core = n_sources>={CORE_MIN_SOURCES}, y-layer={Y_LAYER}")
    for label, mt in (("Tier1 only (max_tier=1)", TIER_ORG),
                      ("Tier1+2   (max_tier=2)", TIER_INDIVIDUAL)):
        c = _core_from_axis_a(claims, sources, counts_l2, max_tier=mt)
        rho, p = stats.spearmanr(c["n_sources"], c["n_pubmed"])
        lo, hi = _spearman_ci(rho, len(c))
        nz = int(c["is_zero"].sum())
        print(f"  {label}: n_core={len(c):3d}  rho={rho:+.4f} p={p:.4f} "
              f"95%CI=[{lo:+.3f}, {hi:+.3f}]  zero-rate={nz}/{len(c)}="
              f"{100*nz/len(c):.1f}%")


if __name__ == "__main__":
    main()

"""One-time statistical confirmation for the manuscript (Phase 4).

Recomputes every number the manuscript will assert, directly from the pipeline
output (not from any hand-recorded value), so the written claims are grounded in
what a reviewer would obtain by re-running the code:

- Spearman rho / p for belief breadth (n_sources) vs research attention
  (PubMed L2 hits), on the core (n_sources>=3) subset and on all foods.
- Zero-research rate overall and split by lay direction (warm vs cool).
- Mann-Whitney U for warm-vs-cool difference in research attention.
- High-belief (n_sources>=11) zero-research rate.

Run: python3 -m src.verify_stats  (from the project root)
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from .analysis import _read_counts, prepare_scatter_data
from .claim_mapping import load_claims, load_sources
from .definitions import COOL, WARM
from .evidence_mapping import CORE_MIN_SOURCES


def _spearman(df):
    rho, p = stats.spearmanr(df["n_sources"], df["n_pubmed"])
    return rho, p, len(df)


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
        print(f"[Spearman] {label:22s} n={n:3d}  rho={rho:+.4f}  p={p:.4f}")

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


if __name__ == "__main__":
    main()

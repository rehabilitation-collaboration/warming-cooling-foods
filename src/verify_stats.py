"""Recompute every number the manuscript asserts, from the pipeline output.

Nothing here is read from a hand-recorded value: a reviewer re-running the code
should obtain exactly the figures in the text. Route B version — the research
measure is **L2′ (screened, on-construct studies)**, not the raw keyword
co-occurrence count, and the belief effect is estimated with the models fixed in
PLAN Phase RB-5 before any estimate was computed:

- primary: logistic regression of "has any on-construct study" on belief
  breadth, adjusted for log(L1 + 1); the unadjusted fit is printed beside it.
- alongside: Spearman rho on L2′, on raw L2, and on the L2′/L1 ratio, so the
  effect of screening and of literature volume are both legible.
- sensitivity: negative binomial regression of L2′ with log(L1 + 1) as offset,
  after a Poisson over-dispersion check.
- descriptive: zero-research rates overall, by belief tier and by lay direction,
  plus the widest-belief zero-research foods behind the figure.

Run: python3 -m src.verify_stats  (from the project root)
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from .analysis import MEASURE, _read_counts, bottom_right_foods, prepare_scatter_data
from .claim_mapping import aggregate_axis_a, load_claims, load_sources
from .definitions import COOL, TIER_INDIVIDUAL, TIER_ORG, WARM
from .evidence_mapping import CORE_MIN_SOURCES
from .gap_models import count_negbin, prepare_model_frame, presence_logit, spearman_with_ci

RULE = "=" * 72
THIN = "-" * 72


def _or_ci_woolf(a: int, b: int, c: int, d: int, conf: float = 0.95):
    """Sample odds ratio (ad/bc) and its CI via Woolf's logit method.

    Table is [[a, b], [c, d]] = [[warm-zero, warm-nonzero], [cool-zero,
    cool-nonzero]]. Returns (or, lo, hi); NaN bounds if any cell is zero, where
    the logit CI is undefined and a continuity correction would silently change
    the estimand.
    """
    if min(a, b, c, d) == 0:
        return (a * d) / (b * c) if b and c else float("nan"), float("nan"), float("nan")
    or_s = (a * d) / (b * c)
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    crit = stats.norm.ppf(1 - (1 - conf) / 2)
    return or_s, np.exp(np.log(or_s) - crit * se), np.exp(np.log(or_s) + crit * se)


def _print_spearman(label: str, x, y) -> None:
    s = spearman_with_ci(x, y)
    print(f"[Spearman] {label:28s} n={s['n']:3d}  rho={s['rho']:+.4f}  "
          f"p={s['p']:.4f}  95%CI=[{s['ci_lo']:+.3f}, {s['ci_hi']:+.3f}]")


def _print_logit(label: str, res: dict) -> None:
    if not res.get("converged"):
        print(f"[Logit] {label}: DID NOT CONVERGE — {res.get('error', 'no finite MLE')}")
        return
    print(f"[Logit] {label} (n={res['n']}, with study={res['n_with_study']}, "
          f"pseudo-R2={res['pseudo_r2']:.4f})")
    for name, t in res["terms"].items():
        if name == "const":
            continue
        print(f"    {name:10s} beta={t['beta']:+.4f}  OR={t['or']:.3f} "
              f"[{t['or_lo']:.3f}, {t['or_hi']:.3f}]  p={t['p']:.4f}")


def main() -> None:
    claims, sources = load_claims(), load_sources()
    df = prepare_scatter_data(claims, sources, _read_counts())
    frame = prepare_model_frame(df)

    dropped = frame.attrs["dropped_unscreened"]
    print(RULE)
    print(f"N foods queried: {len(df)}   modelled: {len(frame)}   "
          f"dropped as unscreened: {len(dropped)}")
    if dropped:
        print(f"  (not measured, so not counted as zero: {dropped})")
    print(f"L2' total studies: {int(frame['l2_screened'].sum())}   "
          f"foods with >=1 study: {int(frame['has_study'].sum())}   "
          f"foods with none: {int((frame['has_study'] == 0).sum())}")
    print(RULE)

    # --- PRIMARY: does belief breadth predict having any study at all? ----
    print_ = _print_logit
    print_("adjusted for log(L1+1)", presence_logit(frame))
    print_("unadjusted", presence_logit(frame, adjust_l1=False))
    print(THIN)

    # --- Alongside: rank correlations -------------------------------------
    _print_spearman("n_sources vs L2' (screened)", frame["n_sources"], frame["l2_screened"])
    _print_spearman("n_sources vs L2 (raw)", frame["n_sources"], frame["l2_raw"])
    _print_spearman("n_sources vs L2'/L1 ratio",
                    frame["n_sources"], frame["l2_screened"] / (frame["l1"] + 1))
    _print_spearman("n_sources vs L1 (volume)", frame["n_sources"], frame["l1"])
    print(THIN)

    # --- SENSITIVITY: NB with log(L1+1) offset ----------------------------
    nb = count_negbin(frame)
    if nb["converged"]:
        print(f"[NB] Poisson deviance/df = {nb['poisson_dispersion']:.3f} "
              f"(over-dispersed: {nb['overdispersed']})   alpha={nb['alpha']:.3f}")
        for name, t in nb["terms"].items():
            if name == "const":
                continue
            print(f"    {name:10s} beta={t['beta']:+.4f}  IRR={t['irr']:.3f} "
                  f"[{t['irr_lo']:.3f}, {t['irr_hi']:.3f}]  p={t['p']:.4f}")
    else:
        # Planned fallback: report non-convergence, do not substitute a
        # zero-inflated model this data cannot identify (PLAN Phase RB-5).
        print(f"[NB] DID NOT CONVERGE — {nb.get('error')}")
        print("     Reported as such; the primary logistic model stands alone.")
    print(RULE)

    # --- Descriptive: zero-research rates ---------------------------------
    n_zero = int(df["is_zero"].sum())
    print(f"[Zero rate] all foods: {n_zero}/{len(df)} = {100 * n_zero / len(df):.1f}%")
    for scope in ("core", "sensitivity", "single"):
        s = df[df["scope"] == scope]
        if len(s):
            z = int(s["is_zero"].sum())
            print(f"  scope={scope:12s} n={len(s):3d}  zero={z:3d} ({100 * z / len(s):5.1f}%)"
                  f"  L2' total={int(s[MEASURE].sum()):3d}")
    core = df[df["n_sources"] >= CORE_MIN_SOURCES]
    cz = int(core["is_zero"].sum())
    print(f"  core (n_sources>={CORE_MIN_SOURCES}): {cz}/{len(core)} = "
          f"{100 * cz / len(core):.1f}%")
    for thr in (9, 11):
        hb = df[df["n_sources"] >= thr]
        z = int(hb["is_zero"].sum())
        print(f"  high belief (n_sources>={thr}): {z}/{len(hb)} = {100 * z / len(hb):.1f}%")
    print(THIN)

    # --- Descriptive: warm vs cool (core) ---------------------------------
    warm, cool = core[core["direction"] == WARM], core[core["direction"] == COOL]
    a, b = int(warm["is_zero"].sum()), len(warm) - int(warm["is_zero"].sum())
    c, d = int(cool["is_zero"].sum()), len(cool) - int(cool["is_zero"].sum())
    or_f, p_f = stats.fisher_exact([[a, b], [c, d]], alternative="two-sided")
    or_w, lo, hi = _or_ci_woolf(a, b, c, d)
    print(f"[Warm vs cool, core] warm-zero {a}/{a + b} vs cool-zero {c}/{c + d}: "
          f"OR={or_f:.3f} p={p_f:.4f}")
    print(f"  Woolf-logit OR = {or_w:.3f}  95%CI=[{lo:.3f}, {hi:.3f}]")
    u, p_mw = stats.mannwhitneyu(warm[MEASURE], cool[MEASURE], alternative="two-sided")
    print(f"  Mann-Whitney on L2': U={u:.1f} p={p_mw:.4f}  "
          f"median warm={np.median(warm[MEASURE]):.1f} cool={np.median(cool[MEASURE]):.1f}")
    print(THIN)

    # --- The void: widest-belief foods with no on-construct study ---------
    gap = bottom_right_foods(df)
    print(f"[Void] {len(gap)} core-belief foods with 0 screened studies "
          f"(showing the 12 widest):")
    for _, r in gap.head(12).iterrows():
        print(f"  {r['food_key']:16s} n_sources={int(r['n_sources']):2d} "
              f"{r['direction']:9s} L1={int(r['l1']):6d} rawL2={int(r['l2_raw']):4d}")
    print(RULE)

    # --- Screening effect on the flagship foods ---------------------------
    print("[Screening effect] raw L2 -> L2' for the foods the review named:")
    for key in ("chicken", "ginger", "milk", "green tea", "coffee", "chili pepper"):
        r = df[df["food_key"] == key]
        if len(r):
            r = r.iloc[0]
            print(f"  {key:14s} L1={int(r['l1']):6d}  L2={int(r['l2_raw']):4d} -> "
                  f"L2'={int(r[MEASURE]):3d}   n_sources={int(r['n_sources']):2d} "
                  f"({r['direction']})")
    print(RULE)

    # --- Tier sensitivity: Tier1-only vs Tier1+2 --------------------------
    # The primary frame is Tier1+2. This re-derives belief breadth under the
    # Tier1-only frame and refits the primary model, so the reader can see the
    # belief measure's frame is not carrying the result.
    print("[Tier sensitivity] primary model refit under each source frame")
    b_slim = df[["food_key", MEASURE, "l1", "l2_raw"]]
    for label, mt in (("Tier1 only ", TIER_ORG), ("Tier1+Tier2", TIER_INDIVIDUAL)):
        a_frame = aggregate_axis_a(claims, sources, max_tier=mt)[["food_key", "n_sources"]]
        merged = a_frame.merge(b_slim, on="food_key", how="inner")
        f = prepare_model_frame(merged)
        res = presence_logit(f)
        t = res["terms"]["n_sources"] if res.get("converged") else None
        z = int((f["has_study"] == 0).sum())
        head = (f"  {label}: n={len(f):3d}  zero={z:3d} ({100 * z / len(f):.1f}%)")
        if t:
            print(f"{head}  n_sources OR={t['or']:.3f} "
                  f"[{t['or_lo']:.3f}, {t['or_hi']:.3f}] p={t['p']:.4f}")
        else:
            print(f"{head}  model did not converge")


if __name__ == "__main__":
    main()

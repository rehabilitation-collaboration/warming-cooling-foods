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
- framing sensitivity: belief breadth recounted within each attribution
  vocabulary — stated bodily effect, five-natures/yin-yang, plain warm/cool
  label — and the primary model refit on each, since Axis A pools all three.
- covariate sensitivity: the same model under two narrower L1 definitions, and a
  leave-one-food-out refit, since log(L1 + 1) is what the result rests on.

Run: python3 -m src.verify_stats  (from the project root)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import claim_framing
from .alt_l1 import ALT_L1_FILTERS, load_alt_l1
from .analysis import MEASURE, _read_counts, bottom_right_foods, prepare_scatter_data
from .claim_mapping import load_claims, load_sources
from .definitions import COOL, TIER_INDIVIDUAL, TIER_ORG, WARM
from .evidence_mapping import CORE_MIN_SOURCES
from .gap_models import (
    count_negbin,
    leave_one_food_out,
    predictor_vif,
    prepare_model_frame,
    presence_logit,
    spearman_with_ci,
)
from .screening import SCREENING_CSV, l2_screened

# Narrower readings of "an on-construct study", each dropping one class of
# record the primary count keeps. Both classes are defensible for "has this
# claim been examined at all" and both are arguable, so the primary model is
# refit without each rather than the choice being asserted.
DEFINITION_SENSITIVITY = (
    ("as reported (all includes)", ()),
    ("whole food only (drop constituent)", ("constituent",)),
    ("primary reports only (drop review)", ("review",)),
    ("whole food + primary only", ("constituent", "review")),
)

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
    outside = df.attrs["outside_frame"]
    print(RULE)
    print(f"PRIMARY FRAME = Tier 1 ({TIER_ORG}) — coding_protocol.md §1")
    print(f"N foods in frame: {len(df)}   modelled: {len(frame)}   "
          f"dropped as unscreened: {len(dropped)}")
    if outside:
        print(f"  outside the Tier-1 frame (queried but Tier-2 only): {len(outside)} foods")
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
    # Collinearity read off the fit's own design matrix. The rank correlation
    # printed below is the reported association between the predictors; it is
    # not what a VIF is computed from, so the two are printed separately.
    vif = predictor_vif(frame)
    print(f"[Collinearity] Pearson r(n_sources, log(L1+1)) = {vif['pearson_r']:+.4f}   "
          + "   ".join(f"VIF[{k}]={v:.3f}" for k, v in vif["vif"].items()))
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
    # Every breadth level, not a pair of chosen cut-points: the claim is that the
    # zero rate does not fall as belief widens, and picking two thresholds after
    # seeing the data would let the frame choose the most striking pair. The
    # frame also fixes the top of the scale (9 sources on Tier 1, 14 on Tier 1+2),
    # so hard-coded thresholds silently empty out when the frame changes.
    print("  zero rate at each belief-breadth threshold:")
    for thr in sorted(df["n_sources"].unique()):
        hb = df[df["n_sources"] >= thr]
        z = int(hb["is_zero"].sum())
        print(f"    n_sources>={int(thr):2d}: {z:3d}/{len(hb):3d} = {100 * z / len(hb):5.1f}%")
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

    # --- Definition sensitivity: narrower readings of "on-construct" -------
    # L2′ as reported counts studies of a food's principal dietary constituent
    # (caffeine for coffee, capsaicin for chili pepper) and reviews of human
    # thermal-ingestion evidence alongside primary reports. Each is defensible
    # for "has this claim been examined at all" and each is arguable, so the
    # primary model is refit without each rather than the choice being asserted.
    print("[Definition sensitivity] primary model refit under narrower L2' definitions")
    screening = pd.read_csv(SCREENING_CSV)
    measured = df["l2_screened"].notna()
    for label, excl in DEFINITION_SENSITIVITY:
        narrowed = l2_screened(screening, exclude_sublabels=excl)
        d = df.copy()
        # A narrower definition removes records; it does not turn a food that
        # was never screened into a zero, so unmeasured foods stay missing.
        d["l2_screened"] = d["food_key"].map(narrowed).fillna(0).where(measured)
        f = prepare_model_frame(d)
        res = presence_logit(f)
        z = int((f["has_study"] == 0).sum())
        print(f"  {label:36s} L2'={int(f['l2_screened'].sum()):3d}  "
              f"with study={int(f['has_study'].sum()):3d}  "
              f"zero={z:3d} ({100 * z / len(f):.1f}%)")
        if res.get("converged"):
            t, v = res["terms"]["n_sources"], res["terms"]["log_l1"]
            print(f"{'':4s}n_sources OR={t['or']:.3f} [{t['or_lo']:.3f}, {t['or_hi']:.3f}] "
                  f"p={t['p']:.4f}    log_l1 OR={v['or']:.3f} "
                  f"[{v['or_lo']:.3f}, {v['or_hi']:.3f}] p={v['p']:.4f}")
        else:
            print(f"{'':4s}model did not converge")
    print(RULE)

    # --- Frame sensitivity: Tier1 (primary) vs Tier1+2 --------------------
    # The primary frame is Tier 1 per coding_protocol.md §1. Widening it to
    # Tier 1+2 re-derives belief breadth over 15 sources instead of 9 and adds
    # the foods only individual bloggers mention, so refitting the primary model
    # there shows the source frame is not carrying the result.
    print("[Frame sensitivity] primary model refit under each source frame")
    counts = _read_counts()
    for label, mt in (("Tier1 (primary)", TIER_ORG), ("Tier1+2 (sens.)", TIER_INDIVIDUAL)):
        d = prepare_scatter_data(claims, sources, counts, max_tier=mt)
        f = prepare_model_frame(d)
        res = presence_logit(f)
        t = res["terms"]["n_sources"] if res.get("converged") else None
        z = int((f["has_study"] == 0).sum())
        head = (f"  {label}: n={len(f):3d}  zero={z:3d} ({100 * z / len(f):.1f}%)")
        if t:
            print(f"{head}  n_sources OR={t['or']:.3f} "
                  f"[{t['or_lo']:.3f}, {t['or_hi']:.3f}] p={t['p']:.4f}")
        else:
            print(f"{head}  model did not converge")
    print(RULE)

    # --- Framing sensitivity: what kind of attribution is being counted ----
    # Axis A pools a stated bodily effect, a five-natures/yin-yang
    # classification, and a bare warm/cool food label into one warm/cool
    # variable, while Axis B measures a physiological outcome. The identity of
    # those constructs is assumed, not shown, so belief breadth is recounted
    # within each vocabulary and the primary model refit on each.
    # Classified on the frozen hand-coded claims, not on the ledger projection the
    # rest of this script uses: the ledger's quote is a candidate span, which the
    # vocabularies cannot read. `claim_framing.load_framing_claims` carries the
    # measurements behind that choice; the population it costs is printed below.
    framing_claims = claim_framing.load_framing_claims()
    tier1 = framing_claims[
        framing_claims["source_id"].isin(set(sources.loc[sources["tier"] <= TIER_ORG, "source_id"]))
    ]
    tagged = claim_framing.classify_claims(tier1)
    print("[Framing] how each Tier-1 source words the attribution (per quote)")
    print(claim_framing.framing_counts(tier1).to_string(index=False))
    print(f"  Tier-1 quotes={len(tagged)}  physio={int(tagged['is_physio'].sum())}  "
          f"tcm={int(tagged['is_tcm'].sum())}  "
          f"both={int((tagged['is_physio'] & tagged['is_tcm']).sum())}  "
          f"label={int(tagged['is_label'].sum())}  "
          f"context={int(tagged['is_context'].sum())}")
    gap = claim_framing.framing_population_gap(framing_claims, claims, sources)
    print(f"  classified on the frozen coding — Tier-1 (source, food) pairs: "
          f"shared with the ledger={gap['shared']}  frozen only={gap['framing_only']}  "
          f"ledger only (no framing label)={gap['ledger_only']}")
    print(THIN)
    print("[Framing sensitivity] primary model refit within each attribution vocabulary")
    for framing in claim_framing.FRAMINGS:
        d = claim_framing.framed_model_frame(framing_claims, sources, counts, framing)
        f = prepare_model_frame(d)
        events = int(f["has_study"].sum())
        z = len(f) - events
        print(f"  {framing:8s} n={len(f):3d}  with study={events:3d}  "
              f"zero={z:3d} ({100 * z / len(f):.1f}%)  "
              f"breadth range={int(f['n_sources'].min())}-{int(f['n_sources'].max())}  "
              f"foods outside this framing={len(d.attrs['outside_framing'])}")
        # Fit rule fixed before any of these models was run: ten events per
        # predictor, two predictors. Below it the frame is described, not fitted.
        if events < claim_framing.MIN_EVENTS_TO_FIT:
            print(f"{'':4s}not fitted — {events} events < {claim_framing.MIN_EVENTS_TO_FIT}")
            continue
        for tag, adj in (("adjusted  ", True), ("unadjusted", False)):
            res = presence_logit(f, adjust_l1=adj)
            if not res.get("converged"):
                print(f"{'':4s}{tag} did not converge")
                continue
            t = res["terms"]["n_sources"]
            line = (f"{'':4s}{tag} n_sources OR={t['or']:.3f} "
                    f"[{t['or_lo']:.3f}, {t['or_hi']:.3f}] p={t['p']:.4f}")
            if adj:
                v = res["terms"]["log_l1"]
                line += (f"    log_l1 OR={v['or']:.3f} "
                         f"[{v['or_lo']:.3f}, {v['or_hi']:.3f}] p={v['p']:.4g}")
            print(line)
    print(RULE)

    # --- Covariate sensitivity: alternative readings of L1 ------------------
    # log(L1 + 1) is what carries the primary model, and L1 is a bare title and
    # abstract count of the food name, so what it contains varies by food. Two
    # narrower L1s are refit here; see src/alt_l1.py for how they are built.
    alt = load_alt_l1()
    if alt is None:
        print("[Covariate sensitivity] alt_l1_counts.csv absent — run python3 -m src.alt_l1")
    else:
        print("[Covariate sensitivity] primary model refit under narrower L1 definitions")
        merged = df.merge(alt, on="food_key", how="left")
        missing = int(merged[list(ALT_L1_FILTERS)].isna().any(axis=1).sum())
        if missing:
            raise ValueError(f"{missing} foods in the frame have no alternative L1 count")
        for label, col in [("L1 as reported", "l1")] + [(f"L1 | {v}", v) for v in ALT_L1_FILTERS]:
            d = merged.copy()
            d["l1"] = d[col]
            f = prepare_model_frame(d)
            res = presence_logit(f)
            share = "" if col == "l1" else (
                f"  median share of L1={float((merged[col] / merged['l1']).median()):.3f}")
            print(f"  {label:20s} total={int(merged[col].sum()):>9,}{share}")
            if not res.get("converged"):
                print(f"{'':4s}model did not converge")
                continue
            t, v = res["terms"]["n_sources"], res["terms"]["log_l1"]
            print(f"{'':4s}n_sources OR={t['or']:.3f} [{t['or_lo']:.3f}, {t['or_hi']:.3f}] "
                  f"p={t['p']:.4f}    log_l1 OR={v['or']:.3f} "
                  f"[{v['or_lo']:.3f}, {v['or_hi']:.3f}] p={v['p']:.4g}")
    print(RULE)

    # --- Influence: can one food carry the coverage estimate? ---------------
    print("[Leave-one-food-out] primary model refit with each food removed in turn")
    loo = leave_one_food_out(frame)
    base_or = presence_logit(frame)["terms"]["n_sources"]["or"]
    failed = int((~loo["converged"]).sum())
    print(f"  refits={len(loo)}  did not converge={failed}  "
          f"full-frame OR={base_or:.3f}")
    print(f"  OR range across refits: {loo['or'].min():.3f} to {loo['or'].max():.3f}   "
          f"p range: {loo['p'].min():.4f} to {loo['p'].max():.4f}   "
          f"refits reaching p<0.05: {int((loo['p'] < 0.05).sum())}")
    widest = loo.reindex((loo["or"] - base_or).abs().sort_values(ascending=False).index)
    print("  largest shifts (and the highest-L1 foods, which is what prompted the check):")
    named = pd.concat([widest.head(4), loo.nlargest(4, "l1")]).drop_duplicates("omitted")
    for _, r in named.iterrows():
        print(f"    omit {r['omitted']:14s} L1={int(r['l1']):>7,} L2'={int(r['l2_screened']):3d}  "
              f"OR={r['or']:.3f} (delta {r['or'] - base_or:+.3f})  p={r['p']:.4f}")


if __name__ == "__main__":
    main()

"""RB-5 models: does belief breadth predict on-construct research attention?

L2' — the number of studies that survive construct screening — is a sparse,
over-dispersed count: a handful of foods carry almost all of it and most foods
have none. Two things follow. Correlating it directly lets those few foods drive
the whole estimate, and an unadjusted comparison ignores that a food with a large
general literature (L1) has more opportunities to be studied thermally at all.
So the analysis is specified as:

- **primary**: logistic regression of "has any on-construct study" on belief
  breadth, adjusted for log(L1 + 1). A binary outcome is what this sparsity can
  actually support, and "which foods have no direct research" is the paper's claim.
- **reported alongside**: Spearman rho on the raw counts, so the effect of moving
  from raw L2 to screened L2' stays legible against the earlier analysis.
- **sensitivity**: negative binomial regression of L2' with log(L1 + 1) as an
  offset, preceded by a Poisson over-dispersion check (Green 2021).

The model set and the fallback were fixed before any estimate was computed (see
PLAN Phase RB-5). The fallback is explicit: if the negative binomial fails to
converge it is reported as not converged rather than swapped for a zero-inflated
model, which this many zeros over this few foods cannot identify.

Pure statistics — takes a prepared frame, returns plain dicts. No I/O, no plots.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# Columns every model function expects on the input frame.
REQUIRED = ("food_key", "n_sources", "l1", "l2_screened")


def prepare_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the analysis frame and derive the model's working columns.

    Adds ``has_study`` (L2' > 0) and ``log_l1`` (log(L1 + 1)). Foods whose L2'
    is missing — queried but not yet screened — are dropped, because "not
    measured" is not "no research"; the count of dropped foods is attached as
    ``frame.attrs["dropped_unscreened"]`` so a caller can report it rather than
    silently analysing a subset.
    """
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"model frame is missing columns: {missing}")

    out = df.copy()
    unscreened = out["l2_screened"].isna()
    dropped = sorted(out.loc[unscreened, "food_key"])
    out = out[~unscreened].copy()

    out["l2_screened"] = out["l2_screened"].astype(int)
    out["has_study"] = (out["l2_screened"] > 0).astype(int)
    out["log_l1"] = np.log(out["l1"].astype(float) + 1.0)
    out.attrs["dropped_unscreened"] = dropped
    return out.reset_index(drop=True)


def spearman_with_ci(x, y, conf: float = 0.95) -> dict:
    """Spearman rho with a Fisher-z CI (Bonett-Wright rank variance)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rho, p = stats.spearmanr(x, y)
    n = len(x)
    if n <= 3 or not np.isfinite(rho):
        lo = hi = float("nan")
    else:
        se = np.sqrt((1 + rho**2 / 2) / (n - 3))
        crit = stats.norm.ppf(1 - (1 - conf) / 2)
        lo, hi = np.tanh(np.arctanh(rho) - crit * se), np.tanh(np.arctanh(rho) + crit * se)
    return {"rho": float(rho), "p": float(p), "n": n, "ci_lo": float(lo), "ci_hi": float(hi)}


def presence_logit(frame: pd.DataFrame, *, adjust_l1: bool = True) -> dict:
    """PRIMARY: logistic regression of has_study on belief breadth.

    ``adjust_l1`` adds log(L1 + 1) as a covariate — the unadjusted fit is
    reported next to it so the reader can see what the adjustment does.
    Returns coefficients, odds ratios with 95% CIs, p-values and convergence.
    """
    import statsmodels.api as sm

    cols = ["n_sources"] + (["log_l1"] if adjust_l1 else [])
    X = sm.add_constant(frame[cols], has_constant="add")
    y = frame["has_study"]

    try:
        fit = sm.Logit(y, X).fit(disp=0)
    except Exception as exc:  # separation / singular design
        return {"converged": False, "error": f"{type(exc).__name__}: {exc}", "terms": cols}

    ci = fit.conf_int()
    terms = {
        name: {
            "beta": float(fit.params[name]),
            "p": float(fit.pvalues[name]),
            "or": float(np.exp(fit.params[name])),
            "or_lo": float(np.exp(ci.loc[name, 0])),
            "or_hi": float(np.exp(ci.loc[name, 1])),
        }
        for name in X.columns
    }
    return {
        "converged": bool(fit.mle_retvals.get("converged", False)),
        "n": int(len(frame)),
        "n_with_study": int(y.sum()),
        "pseudo_r2": float(fit.prsquared),
        "terms": terms,
    }


def count_negbin(frame: pd.DataFrame) -> dict:
    """SENSITIVITY: NB regression of L2' with log(L1 + 1) as offset.

    Fits Poisson first and reports deviance/df as the over-dispersion check that
    motivates NB (Green 2021). ``alpha`` is estimated by profiling the NB
    log-likelihood over a grid, because statsmodels' GLM takes alpha as fixed.
    Non-convergence is returned, not worked around.
    """
    import statsmodels.api as sm

    X = sm.add_constant(frame[["n_sources"]], has_constant="add")
    y = frame["l2_screened"].astype(float)
    offset = frame["log_l1"].to_numpy()

    try:
        poisson = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit()
    except Exception as exc:
        return {"converged": False, "error": f"poisson: {type(exc).__name__}: {exc}"}

    dispersion = float(poisson.deviance / poisson.df_resid) if poisson.df_resid else float("nan")

    best = None
    for alpha in np.geomspace(0.05, 50.0, 60):
        try:
            cand = sm.GLM(
                y, X, family=sm.families.NegativeBinomial(alpha=float(alpha)), offset=offset
            ).fit()
        except Exception:
            continue
        if cand.converged and (best is None or cand.llf > best[1].llf):
            best = (float(alpha), cand)

    if best is None:
        return {
            "converged": False,
            "error": "negative binomial did not converge at any alpha on the grid",
            "poisson_dispersion": dispersion,
        }

    alpha, nb = best
    ci = nb.conf_int()
    return {
        "converged": True,
        "n": int(len(frame)),
        "poisson_dispersion": dispersion,
        "overdispersed": bool(np.isfinite(dispersion) and dispersion > 1.0),
        "alpha": alpha,
        "terms": {
            name: {
                "beta": float(nb.params[name]),
                "p": float(nb.pvalues[name]),
                "irr": float(np.exp(nb.params[name])),
                "irr_lo": float(np.exp(ci.loc[name, 0])),
                "irr_hi": float(np.exp(ci.loc[name, 1])),
            }
            for name in X.columns
        },
    }

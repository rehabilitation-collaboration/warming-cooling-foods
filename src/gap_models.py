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


def leave_one_food_out(frame: pd.DataFrame, *, term: str = "n_sources") -> pd.DataFrame:
    """Refit the primary model once per food, each time with that food removed.

    An influence check for a frame small enough that one food could carry the
    estimate: milk, salt and chicken sit two orders of magnitude above the median
    in L1, so an odds ratio that only holds while one of them is in the frame is
    not a result. Returns one row per omitted food with the refitted odds ratio
    and p-value for ``term``, plus its own L1 and L2′ so a large shift can be
    read against the food that caused it. Non-converged refits are kept with NaN
    estimates rather than dropped, so the caller counts them.
    """
    rows = []
    for food in frame["food_key"]:
        reduced = frame[frame["food_key"] != food]
        res = presence_logit(reduced)
        t = res["terms"][term] if res.get("converged") else None
        rows.append(
            {
                "omitted": food,
                "l1": int(frame.loc[frame["food_key"] == food, "l1"].iloc[0]),
                "l2_screened": int(frame.loc[frame["food_key"] == food, "l2_screened"].iloc[0]),
                "or": float(t["or"]) if t else float("nan"),
                "p": float(t["p"]) if t else float("nan"),
                "converged": bool(res.get("converged")),
            }
        )
    return pd.DataFrame(rows)


def predictor_vif(frame: pd.DataFrame) -> dict:
    """Collinearity diagnostic for the primary model's two predictors.

    Each predictor is regressed on the other and VIF = 1/(1 - R²), which is the
    definition. A rank correlation between the predictors does not give one:
    Spearman's rho measures monotone association, so squaring it is not the R²
    of the linear fit the VIF is built from. The Pearson correlation actually
    entering that fit is returned beside it.
    """
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    cols = ["n_sources", "log_l1"]
    X = sm.add_constant(frame[cols].astype(float), has_constant="add")
    values = X.to_numpy()
    vif = {
        name: float(variance_inflation_factor(values, i))
        for i, name in enumerate(X.columns)
        if name != "const"
    }
    r = float(np.corrcoef(X["n_sources"], X["log_l1"])[0, 1])
    return {"vif": vif, "pearson_r": r}


def presence_logit_curve(
    frame: pd.DataFrame,
    l1_quantiles: tuple[float, ...] = (0.25, 0.5, 0.75),
    conf: float = 0.95,
) -> pd.DataFrame:
    """Fitted P(has study) across belief breadth, at fixed literature volumes.

    Same specification as the primary ``presence_logit`` — this only evaluates
    it. Marginal proportions cannot show the adjusted result (a food believed by
    many sources also tends to have a large general literature), so the figure
    needs the model's own prediction: hold L1 at a quantile, sweep belief
    breadth, and read whether the curve tilts.

    Returns one row per (l1_quantile, n_sources) with ``p``, ``lo``, ``hi``.
    Confidence bounds are computed on the linear predictor and then transformed,
    so they stay inside [0, 1].
    """
    import statsmodels.api as sm

    X = sm.add_constant(frame[["n_sources", "log_l1"]], has_constant="add")
    fit = sm.Logit(frame["has_study"], X).fit(disp=0)
    crit = stats.norm.ppf(1 - (1 - conf) / 2)

    grid = np.arange(int(frame["n_sources"].min()), int(frame["n_sources"].max()) + 1)
    rows = []
    for q in l1_quantiles:
        log_l1 = float(frame["log_l1"].quantile(q))
        design = np.column_stack([np.ones_like(grid, dtype=float), grid.astype(float),
                                  np.full(grid.shape, log_l1)])
        eta = design @ fit.params.to_numpy()
        se = np.sqrt(np.einsum("ij,jk,ik->i", design, fit.cov_params().to_numpy(), design))
        for n, e, s in zip(grid, eta, se):
            rows.append({
                "l1_quantile": q,
                "l1": float(np.exp(log_l1) - 1.0),
                "n_sources": int(n),
                "p": float(1 / (1 + np.exp(-e))),
                "lo": float(1 / (1 + np.exp(-(e - crit * s)))),
                "hi": float(1 / (1 + np.exp(-(e + crit * s)))),
            })
    return pd.DataFrame(rows)


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

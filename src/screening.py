"""L2 abstract screening: turn keyword co-occurrence counts into a valid metric.

Axis B's raw L2 count (food × four thermal terms) does not measure the intended
construct — *studies of the thermal effect on a human of ingesting the food*.
The GPT review (2026-08-07) showed it is dominated by poultry heat-stress /
avian thermoregulation (chicken false positives) and misses ginger's
thermic-effect-of-food studies (false negatives). This module screens each L2
record ``include``/``exclude`` per ``data/screening_protocol.md`` and derives
**L2′** = per-food count of included (genuinely on-construct) studies.

Two coders label every record independently; this module reconciles them on the
``pmid`` key, computes Cohen's κ **on the co-coded records only** (coverage
differences are reported separately and adjudicated — the Axis A / GPT #4
lesson), and, after adjudication, aggregates L2′ per food. It also scores a
coder against a hand-labelled golden set (precision/recall/F1) so the coding's
validity is measured, not assumed.

Pure functions over DataFrames (no network, no LLM call here): the actual
include/exclude labelling is produced by coder agents and fed in as CSVs, so the
statistics are fully reproducible and unit-testable offline. Mirrors
``reconcile_coders.py`` (Axis A) in shape.

Label vocabulary: ``include`` / ``exclude`` (see ``screening_protocol.md`` §2).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .definitions import DATA_DIR, PUBMED_COUNTS_CSV

INCLUDE = "include"
EXCLUDE = "exclude"
LABELS = (INCLUDE, EXCLUDE)

# Reason flags a coder writes when the record itself does not carry enough to
# judge on — the abstract never states the subject species, or there is no
# abstract at all. Rows carrying one go to the author even if both coders agree,
# because agreement reached on absent information is not evidence (protocol
# §2/§5).
UNCERTAIN_SPECIES = "uncertain-species"
NO_ABSTRACT = "no-abstract"
AUTHOR_FLAGS = (UNCERTAIN_SPECIES, NO_ABSTRACT)

L2_RECORDS_CSV = DATA_DIR / "l2_records.csv"
SCREENING_CSV = DATA_DIR / "screening.csv"
GOLDEN_CSV = DATA_DIR / "screening_golden.csv"


def _norm_label(value) -> str:
    """Normalise a coder's raw label to ``include``/``exclude`` or ``""``."""
    s = str(value or "").strip().lower()
    if s in ("include", "inc", "in", "1", "true", "yes"):
        return INCLUDE
    if s in ("exclude", "exc", "ex", "out", "0", "false", "no"):
        return EXCLUDE
    return ""


def _coder_frame(records: list[dict] | pd.DataFrame, coder: str) -> pd.DataFrame:
    """One coder's labels → [pmid, food_key, label_/reason_/sublabels_<coder>].

    Keyed on (food_key, pmid): the same PMID can be an L2 hit for several foods
    (e.g. a study naming both ginger and chili), and the judgment can differ by
    food, so screening is per (food, pmid), not per pmid alone.
    """
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "food_key", "pmid",
                f"label_{coder}", f"reason_{coder}", f"sublabels_{coder}",
            ]
        )

    def _optional(col: str):
        """Free-text column, absent for coders that did not supply it."""
        if col not in df.columns:
            return ""
        return df[col].fillna("").astype(str).str.strip()

    out = pd.DataFrame(
        {
            "food_key": df["food_key"].astype(str).str.strip(),
            "pmid": df["pmid"].astype(str).str.strip(),
            f"label_{coder}": df["label"].map(_norm_label),
            f"reason_{coder}": _optional("reason"),
            f"sublabels_{coder}": _optional("sublabels"),
        }
    )
    # A within-coder duplicate on the identity key is itself worth surfacing.
    key = ["food_key", "pmid"]
    dups = out[out.duplicated(key, keep=False)]
    if not dups.empty:
        print(
            f"[warn] coder {coder} has {len(dups)} rows on duplicated (food,pmid) keys",
            file=sys.stderr,
        )
    return out.drop_duplicates(key, keep="first")


def reconcile(coder1, coder2) -> pd.DataFrame:
    """Outer-join two codings on (food_key, pmid) with a ``status`` column.

    status ∈ {agree, disagree, only_c1, only_c2}. ``label`` columns are
    ``include``/``exclude``/``"" `` (missing from that coder).
    """
    df1 = _coder_frame(coder1, "c1")
    df2 = _coder_frame(coder2, "c2")
    key = ["food_key", "pmid"]
    merged = df1.merge(df2, on=key, how="outer")
    for c in (
        "label_c1", "label_c2", "reason_c1", "reason_c2",
        "sublabels_c1", "sublabels_c2",
    ):
        if c not in merged.columns:
            merged[c] = ""
        merged[c] = merged[c].fillna("")

    def _status(row) -> str:
        has1 = row["label_c1"] in LABELS
        has2 = row["label_c2"] in LABELS
        if has1 and has2:
            return "agree" if row["label_c1"] == row["label_c2"] else "disagree"
        if has1:
            return "only_c1"
        return "only_c2"

    merged["status"] = merged.apply(_status, axis=1)
    return merged.sort_values(["status", "food_key", "pmid"]).reset_index(drop=True)


def cohen_kappa(recon: pd.DataFrame) -> dict:
    """Cohen's κ on records BOTH coders labelled (agree + disagree rows).

    Categories = {include, exclude}. Coverage differences (only_c1/only_c2) are
    excluded from κ — they are coverage, not rating disagreements — and reported
    separately. The denominator is the co-coded count, never the full record
    count (GPT #4 lesson).
    """
    both = recon[recon["status"].isin(["agree", "disagree"])]
    n = len(both)
    if n == 0:
        return {"kappa": float("nan"), "n_both": 0, "po": float("nan"), "pe": float("nan")}

    c1 = both["label_c1"]
    c2 = both["label_c2"]
    po = (c1.values == c2.values).mean()
    pe = 0.0
    for lab in LABELS:
        pe += (c1 == lab).mean() * (c2 == lab).mean()
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan")
    return {"kappa": float(kappa), "n_both": int(n), "po": float(po), "pe": float(pe)}


def _split_ruling(value) -> tuple[str, str]:
    """A ruling is ``"include"`` or ``("include", "author's rationale")``."""
    if isinstance(value, (tuple, list)):
        label = value[0]
        reason = value[1] if len(value) > 1 else ""
    else:
        label, reason = value, ""
    return _norm_label(label), str(reason).strip()


def _needs_ruling(row) -> bool:
    """Rows the author must settle: divergences and judgments made blind.

    Agreement reached on information the record does not contain is not evidence
    (protocol §2/§5) — ginger/29259648 read as human from its acupoint names but
    is a 33-rabbit study — so an ``uncertain-species`` or ``no-abstract`` flag
    from either coder goes to the author even when both coders wrote the same
    label.
    """
    if row["status"] != "agree":
        return True
    flags = f"{row.get('reason_c1', '')} {row.get('reason_c2', '')}".lower()
    return any(f in flags for f in AUTHOR_FLAGS)


def adjudicate(recon: pd.DataFrame, rulings: dict | None = None) -> pd.DataFrame:
    """Resolve every record to a ``final_label``, adding an ``adjudicated`` flag.

    - Rows where both coders agree (and neither flagged ``uncertain-species``)
      take the shared label.
    - Every other row requires an author ruling in ``rulings`` keyed by
      (food_key, pmid) → ``"include"`` or ``("include", "why")``. A missing
      ruling is a hard error (fail-loud: no silent default), so the author
      cannot forget to settle a divergence.
    """
    rulings = rulings or {}
    finals: list[str] = []
    reasons: list[str] = []
    settled: list[bool] = []
    for _, r in recon.iterrows():
        key = (r["food_key"], r["pmid"])
        coder_reason = r["reason_c1"] or r["reason_c2"]
        if _needs_ruling(r):
            if key not in rulings:
                raise ValueError(
                    f"record needs an author ruling ({r['status']}): {key}"
                )
            label, why = _split_ruling(rulings[key])
            if label not in LABELS:
                raise ValueError(f"invalid ruling for {key}: {rulings[key]!r}")
            finals.append(label)
            reasons.append(why or coder_reason)
            settled.append(True)
        else:
            finals.append(r["label_c1"])
            reasons.append(coder_reason)
            settled.append(False)
    out = recon.copy()
    out["final_label"] = finals
    out["reason"] = reasons
    out["adjudicated"] = settled
    return out


def to_screening_csv(adjudicated: pd.DataFrame) -> pd.DataFrame:
    """Adjudicated frame → the published ``screening.csv`` schema (protocol §6).

    ``pmid, food_key, coder1, coder2, adjudicated, final_label, reason,
    sublabels`` — one row per (food, pmid), where ``sublabels`` is the union of
    the sub-labels either coder attached (``review``, ``constituent``,
    ``supradose``, ``confounded``).
    """

    def _union(row) -> str:
        parts: list[str] = []
        for col in ("sublabels_c1", "sublabels_c2"):
            for part in str(row.get(col, "") or "").split(";"):
                part = part.strip()
                if part and part not in parts:
                    parts.append(part)
        return ";".join(parts)

    out = pd.DataFrame(
        {
            "pmid": adjudicated["pmid"],
            "food_key": adjudicated["food_key"],
            "coder1": adjudicated["label_c1"],
            "coder2": adjudicated["label_c2"],
            "adjudicated": adjudicated["adjudicated"],
            "final_label": adjudicated["final_label"],
            "reason": adjudicated["reason"],
            "sublabels": adjudicated.apply(_union, axis=1),
        }
    )
    return out.sort_values(["food_key", "pmid"]).reset_index(drop=True)


def l2_screened(adjudicated: pd.DataFrame) -> pd.Series:
    """Per-food L2′ = count of final_label == include. Indexed by food_key."""
    inc = adjudicated[adjudicated["final_label"] == INCLUDE]
    return (
        inc.groupby("food_key").size().rename("L2_screened").sort_index()
    )


def golden_scores(coder: list[dict] | pd.DataFrame, golden: list[dict] | pd.DataFrame) -> dict:
    """Precision/recall/F1 of a coder vs a hand-labelled golden set.

    Positive class = ``include``. Compared on the (food_key, pmid) records the
    golden set covers; a coder record with no gold counterpart is ignored.
    """
    gf = _coder_frame(
        [{**g, "label": g.get("gold_label", g.get("label"))} for g in
         (golden.to_dict("records") if isinstance(golden, pd.DataFrame) else golden)],
        "gold",
    )
    cf = _coder_frame(coder, "c")
    m = gf.merge(cf, on=["food_key", "pmid"], how="inner")
    y_true = m["label_gold"] == INCLUDE
    y_pred = m["label_c"] == INCLUDE
    tp = int((y_true & y_pred).sum())
    fp = int((~y_true & y_pred).sum())
    fn = int((y_true & ~y_pred).sum())
    tn = int((~y_true & ~y_pred).sum())
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision == precision and recall == recall and (precision + recall) > 0
        else float("nan")
    )
    accuracy = (tp + tn) / len(m) if len(m) else float("nan")
    return {
        "n": int(len(m)),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1, "accuracy": accuracy,
    }


def attach_l2_screened(
    pubmed_counts: pd.DataFrame,
    l2s: pd.Series,
    screened_foods=None,
) -> pd.DataFrame:
    """Add an ``L2_screened`` column to the L2 layer rows of pubmed_counts.

    Non-L2 rows get NaN. L2 rows get their L2′ (0 where a screened food has no
    included records). Does not mutate the input.

    ``screened_foods`` names the foods whose records have actually been coded.
    Only those get the zero fill; a food outside the set keeps NaN, because
    *not yet screened* is not the same claim as *zero on-construct studies* —
    and that distinction is exactly what the headline "N foods with no direct
    research" rests on. Defaults to None = every L2 food has been screened.
    """
    out = pubmed_counts.copy()
    is_l2 = out["layer"] == "L2"
    out["L2_screened"] = out["food_key"].map(l2s.to_dict()).where(is_l2)
    fillable = is_l2 if screened_foods is None else (
        is_l2 & out["food_key"].isin(set(screened_foods))
    )
    out.loc[fillable & out["L2_screened"].isna(), "L2_screened"] = 0
    return out


def summarize(recon: pd.DataFrame) -> None:
    counts = recon["status"].value_counts().to_dict()
    print(f"Screening reconciliation over {len(recon)} (food, pmid) records:")
    for st in ("agree", "disagree", "only_c1", "only_c2"):
        print(f"  {st:10s}: {counts.get(st, 0)}")
    k = cohen_kappa(recon)
    print(
        f"\nCohen's kappa (on {k['n_both']} co-coded records): "
        f"{k['kappa']:.3f} (observed agreement {k['po']:.3f})"
    )
    needs = recon[recon.apply(_needs_ruling, axis=1)]
    if not needs.empty:
        print(f"\n{len(needs)} records need adjudication.")


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import argparse

    ap = argparse.ArgumentParser(description="Reconcile two L2 screening codings")
    ap.add_argument("coder1_csv")
    ap.add_argument("coder2_csv")
    args = ap.parse_args()
    c1 = pd.read_csv(args.coder1_csv, dtype=str).to_dict("records")
    c2 = pd.read_csv(args.coder2_csv, dtype=str).to_dict("records")
    summarize(reconcile(c1, c2))

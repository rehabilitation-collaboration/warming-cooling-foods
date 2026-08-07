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
    """One coder's labels → columns [pmid, food_key, label_<coder>, reason_<coder>].

    Keyed on (food_key, pmid): the same PMID can be an L2 hit for several foods
    (e.g. a study naming both ginger and chili), and the judgment can differ by
    food, so screening is per (food, pmid), not per pmid alone.
    """
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            columns=["food_key", "pmid", f"label_{coder}", f"reason_{coder}"]
        )
    out = pd.DataFrame(
        {
            "food_key": df["food_key"].astype(str).str.strip(),
            "pmid": df["pmid"].astype(str).str.strip(),
            f"label_{coder}": df["label"].map(_norm_label),
            f"reason_{coder}": df.get("reason", "").astype(str).str.strip()
            if "reason" in df.columns
            else "",
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
    for c in ("label_c1", "label_c2", "reason_c1", "reason_c2"):
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


def adjudicate(recon: pd.DataFrame, rulings: dict | None = None) -> pd.DataFrame:
    """Resolve every record to a ``final_label``.

    - ``agree`` rows take the shared label.
    - ``disagree`` / ``only_c1`` / ``only_c2`` rows require an author ruling in
      ``rulings`` keyed by (food_key, pmid) → include/exclude. A missing ruling
      for a non-agree row is a hard error (fail-loud: no silent default), so the
      author cannot forget to settle a divergence.
    """
    rulings = rulings or {}
    finals: list[str] = []
    reasons: list[str] = []
    for _, r in recon.iterrows():
        status = r["status"]
        key = (r["food_key"], r["pmid"])
        if status == "agree":
            finals.append(r["label_c1"])
            reasons.append(r["reason_c1"] or r["reason_c2"])
        else:
            if key not in rulings:
                raise ValueError(
                    f"unadjudicated {status} record needs a ruling: {key}"
                )
            ruling = _norm_label(rulings[key])
            if ruling not in LABELS:
                raise ValueError(f"invalid ruling for {key}: {rulings[key]!r}")
            finals.append(ruling)
            reasons.append(r["reason_c1"] or r["reason_c2"])
    out = recon.copy()
    out["final_label"] = finals
    out["reason"] = reasons
    return out


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


def attach_l2_screened(pubmed_counts: pd.DataFrame, l2s: pd.Series) -> pd.DataFrame:
    """Add an ``L2_screened`` column to the L2 layer rows of pubmed_counts.

    Non-L2 rows get NaN. L2 rows get their L2′ (0 where a food has no included
    records). Does not mutate the input.
    """
    out = pubmed_counts.copy()
    is_l2 = out["layer"] == "L2"
    mapped = out["food_key"].map(l2s.to_dict())
    out["L2_screened"] = mapped.where(is_l2)
    # L2 foods with zero includes should read 0, not NaN.
    out.loc[is_l2 & out["L2_screened"].isna(), "L2_screened"] = 0
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
    nonagree = recon[recon["status"] != "agree"]
    if not nonagree.empty:
        print(f"\n{len(nonagree)} records need adjudication.")


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import argparse

    ap = argparse.ArgumentParser(description="Reconcile two L2 screening codings")
    ap.add_argument("coder1_csv")
    ap.add_argument("coder2_csv")
    args = ap.parse_args()
    c1 = pd.read_csv(args.coder1_csv, dtype=str).to_dict("records")
    c2 = pd.read_csv(args.coder2_csv, dtype=str).to_dict("records")
    summarize(reconcile(c1, c2))

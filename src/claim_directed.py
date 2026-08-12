"""Screening protocol §8: is the thermal question the study's own question?

§2 decides whether a record is *on-construct* — a human ingesting the food, with
a qualifying thermal outcome. It does not decide whether the study set out to ask
what the lay sources answer, and the external review of 2026-08-12 pressed on the
gap: two of the surviving chicken records are enriched-meat trials with
microvascular outcomes, and the manuscript itself says neither was designed to
ask whether chicken warms the body.

This module carries the sub-label that closes the gap for a sensitivity analysis:
every included record is coded ``claim-directed`` or ``incidental`` per protocol
§8, and the primary model is refit with the incidental records dropped.

Two things about the design are deliberate and load-bearing:

- **It cannot move L2′.** ``screening.csv`` is not rewritten. The sub-label lives
  in its own published ledger and is folded into the ``sublabels`` column *in
  memory* by :func:`attach`, so the reported measure is unchanged by construction
  rather than by inspection — ``git diff`` on the screening ledger proves it.
- **It mirrors ``screening.py`` rather than reusing it.** The vocabularies differ
  ({claim-directed, incidental} vs {include, exclude}) and mapping one onto the
  other would let a coder's stray "include" pass ``_norm_label`` and be counted.
  The repository already runs two parallel reconciliation modules for the two
  axes (``screening.py`` and ``ledger.py``); this is the same shape a third time,
  and the isolation is worth the repetition when the thing being protected is the
  primary result.

Pure functions over DataFrames: the labelling is produced by coder agents and fed
in as CSVs, so everything here is reproducible and unit-testable offline.
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import DATA_DIR
from .screening import INCLUDE

CLAIM_DIRECTED = "claim-directed"
INCIDENTAL = "incidental"
SUB_LABELS = (CLAIM_DIRECTED, INCIDENTAL)

# Flags routing a record to the author even when both coders agree, for the same
# reason §5 does it for the screening pass: agreement reached on information the
# record does not carry is not evidence about that information. ``no-abstract``
# is the §5 flag reappearing (three of the 298 includes have no abstract);
# ``unclear-question`` is new here — the abstract reports outcomes but never says
# what was being asked.
UNCLEAR_QUESTION = "unclear-question"
NO_ABSTRACT = "no-abstract"
AUTHOR_FLAGS = (UNCLEAR_QUESTION, NO_ABSTRACT)

LEDGER_CSV = DATA_DIR / "screening_claim_directed.csv"
RULINGS_CSV = DATA_DIR / "screening_claim_directed_rulings.csv"


def _norm(value) -> str:
    """Normalise a coder's raw sub-label, or return ``""`` for anything else.

    Only the two canonical tokens are accepted, after case and separator
    normalisation. Nothing is guessed: an unrecognised string becomes ``""``,
    which :func:`adjudicate` then treats as a missing label and refuses to
    resolve without an author ruling. A permissive reader here would be a silent
    misread of the one judgment this pass exists to make.
    """
    s = str(value or "").strip().lower().replace("_", "-").replace(" ", "-")
    return s if s in SUB_LABELS else ""


def _coder_frame(records: list[dict] | pd.DataFrame, coder: str) -> pd.DataFrame:
    """One coder's sub-labels → [food_key, pmid, sub_<coder>, reason_<coder>]."""
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            columns=["food_key", "pmid", f"sub_{coder}", f"reason_{coder}"]
        )
    reason = (
        df["reason"].fillna("").astype(str).str.strip()
        if "reason" in df.columns
        else ""
    )
    out = pd.DataFrame(
        {
            "food_key": df["food_key"].astype(str).str.strip(),
            "pmid": df["pmid"].astype(str).str.strip(),
            f"sub_{coder}": df["sub_label"].map(_norm),
            f"reason_{coder}": reason,
        }
    )
    key = ["food_key", "pmid"]
    dups = out[out.duplicated(key, keep=False)]
    if not dups.empty:
        print(
            f"[warn] coder {coder} has {len(dups)} rows on duplicated (food,pmid) keys",
            file=sys.stderr,
        )
    return out.drop_duplicates(key, keep="first")


def reconcile(coder1, coder2) -> pd.DataFrame:
    """Outer-join two sub-labellings on (food_key, pmid) with a ``status``.

    status ∈ {agree, disagree, only_c1, only_c2}, as in ``screening.reconcile``.
    """
    df1 = _coder_frame(coder1, "c1")
    df2 = _coder_frame(coder2, "c2")
    merged = df1.merge(df2, on=["food_key", "pmid"], how="outer")
    for c in ("sub_c1", "sub_c2", "reason_c1", "reason_c2"):
        if c not in merged.columns:
            merged[c] = ""
        merged[c] = merged[c].fillna("")

    def _status(row) -> str:
        has1 = row["sub_c1"] in SUB_LABELS
        has2 = row["sub_c2"] in SUB_LABELS
        if has1 and has2:
            return "agree" if row["sub_c1"] == row["sub_c2"] else "disagree"
        if has1:
            return "only_c1"
        return "only_c2"

    merged["status"] = merged.apply(_status, axis=1)
    return merged.sort_values(["status", "food_key", "pmid"]).reset_index(drop=True)


def cohen_kappa(recon: pd.DataFrame) -> dict:
    """Cohen's κ on the co-coded rows, categories = {claim-directed, incidental}.

    Coverage differences are excluded from the denominator, as in §5 — they are
    coverage, not rating disagreements.
    """
    both = recon[recon["status"].isin(["agree", "disagree"])]
    n = len(both)
    if n == 0:
        return {"kappa": float("nan"), "n_both": 0, "po": float("nan"), "pe": float("nan")}
    c1, c2 = both["sub_c1"], both["sub_c2"]
    po = (c1.values == c2.values).mean()
    pe = sum((c1 == lab).mean() * (c2 == lab).mean() for lab in SUB_LABELS)
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan")
    return {"kappa": float(kappa), "n_both": int(n), "po": float(po), "pe": float(pe)}


def _split_ruling(value) -> tuple[str, str]:
    """A ruling is ``"incidental"`` or ``("incidental", "author's rationale")``."""
    if isinstance(value, (tuple, list)):
        label = value[0]
        reason = value[1] if len(value) > 1 else ""
    else:
        label, reason = value, ""
    return _norm(label), str(reason).strip()


def _needs_ruling(row) -> bool:
    """Divergences, coverage gaps, and judgments made on absent information."""
    if row["status"] != "agree":
        return True
    flags = f"{row.get('reason_c1', '')} {row.get('reason_c2', '')}".lower()
    return any(f in flags for f in AUTHOR_FLAGS)


def adjudicate(recon: pd.DataFrame, rulings: dict | None = None) -> pd.DataFrame:
    """Resolve every row to a ``sub_label``, adding an ``adjudicated`` flag.

    Fail-loud on a missing ruling, exactly as the screening pass is: a divergence
    the author forgot to settle raises rather than defaulting to either coder.
    A ruling filed on an agreed row overrides it and still reports
    ``adjudicated=True``, so the override is visible in the published ledger.
    """
    rulings = rulings or {}
    finals: list[str] = []
    reasons: list[str] = []
    settled: list[bool] = []
    for _, r in recon.iterrows():
        key = (r["food_key"], r["pmid"])
        coder_reason = r["reason_c1"] or r["reason_c2"]
        if _needs_ruling(r) or key in rulings:
            if key not in rulings:
                raise ValueError(
                    f"record needs an author ruling ({r['status']}): {key}"
                )
            label, why = _split_ruling(rulings[key])
            if label not in SUB_LABELS:
                raise ValueError(f"invalid ruling for {key}: {rulings[key]!r}")
            finals.append(label)
            reasons.append(why or coder_reason)
            settled.append(True)
        else:
            finals.append(r["sub_c1"])
            reasons.append(coder_reason)
            settled.append(False)
    out = recon.copy()
    out["sub_label"] = finals
    out["reason"] = reasons
    out["adjudicated"] = settled
    return out


def to_ledger_csv(adjudicated: pd.DataFrame) -> pd.DataFrame:
    """Adjudicated frame → the published ledger schema (protocol §8)."""
    out = pd.DataFrame(
        {
            "pmid": adjudicated["pmid"],
            "food_key": adjudicated["food_key"],
            "coder1": adjudicated["sub_c1"],
            "coder2": adjudicated["sub_c2"],
            "adjudicated": adjudicated["adjudicated"],
            "sub_label": adjudicated["sub_label"],
            "reason": adjudicated["reason"],
        }
    )
    return out.sort_values(["food_key", "pmid"]).reset_index(drop=True)


def load_rulings() -> dict:
    """Read the author ruling ledger into {(food_key, pmid): (sub_label, why)}.

    A duplicated key is a hard error rather than last-write-wins: two rulings for
    one record means one was never applied, and which one won would depend on row
    order.
    """
    if not RULINGS_CSV.exists():
        return {}
    df = pd.read_csv(RULINGS_CSV, dtype=str).fillna("")
    dups = df[df.duplicated(["food_key", "pmid"], keep=False)]
    if not dups.empty:
        raise ValueError(
            f"{RULINGS_CSV.name} carries {len(dups)} rows on duplicated "
            f"(food_key, pmid) keys: {sorted(set(zip(dups.food_key, dups.pmid)))}"
        )
    return {
        (r.food_key, r.pmid): (r.sub_label, r.rationale) for r in df.itertuples()
    }


def load_ledger() -> pd.DataFrame | None:
    """The published §8 ledger, or None where the pass has not been run."""
    if not LEDGER_CSV.exists():
        return None
    return pd.read_csv(LEDGER_CSV, dtype=str)


def attach(screening: pd.DataFrame, ledger: pd.DataFrame | None) -> pd.DataFrame:
    """Fold the §8 sub-label into a copy of the screening ledger's ``sublabels``.

    Returns the input unchanged when ``ledger`` is None, so every caller works
    before the pass has been run. Otherwise the join is checked in both
    directions and fails loudly, because the two ways it can rot are silent:

    - an included record with no sub-label would be counted as claim-directed by
      any ``exclude_sublabels=("incidental",)`` reading, turning a gap in the
      coding into evidence;
    - a sub-label whose record is no longer an include means a later screening
      ruling moved the record and the §8 pass was not re-run over it.

    The screening frame itself is never mutated — the caller's copy is the only
    thing that carries the token.
    """
    if ledger is None:
        return screening
    dups = ledger[ledger.duplicated(["food_key", "pmid"], keep=False)]
    if not dups.empty:
        raise ValueError(
            f"{LEDGER_CSV.name} carries {len(dups)} rows on duplicated keys: "
            f"{sorted(set(zip(dups.food_key, dups.pmid)))}"
        )
    bad = sorted(set(ledger["sub_label"]) - set(SUB_LABELS))
    if bad:
        raise ValueError(f"{LEDGER_CSV.name} carries unknown sub-labels: {bad}")

    out = screening.copy()
    is_inc = out["final_label"] == INCLUDE
    keys = list(zip(out["food_key"].astype(str), out["pmid"].astype(str)))
    coded = dict(
        zip(zip(ledger["food_key"].astype(str), ledger["pmid"].astype(str)),
            ledger["sub_label"])
    )
    missing = sorted({k for k, inc in zip(keys, is_inc) if inc and k not in coded})
    if missing:
        raise ValueError(
            f"{len(missing)} included records carry no §8 sub-label "
            f"(first: {missing[:5]})"
        )
    orphans = sorted(set(coded) - {k for k, inc in zip(keys, is_inc) if inc})
    if orphans:
        raise ValueError(
            f"{len(orphans)} §8 sub-labels name records that are not includes "
            f"(first: {orphans[:5]})"
        )

    def _fold(existing: str, key) -> str:
        token = coded.get(key)
        if token is None:
            return existing
        parts = [p.strip() for p in str(existing or "").split(";") if p.strip()]
        if token not in parts:
            parts.append(token)
        return ";".join(parts)

    out["sublabels"] = [
        _fold(s, k) for s, k in zip(out["sublabels"].fillna(""), keys)
    ]
    return out


def ledger_agreement(ledger: pd.DataFrame) -> dict:
    """Recompute the pass's reported figures from the published ledger alone.

    The per-coder CSVs are working files and are not redistributed, so every
    figure the manuscript reports for this pass has to be recoverable from the
    ``coder1`` and ``coder2`` columns of the published ledger. That is what makes
    them checkable by a reader who has only the repository, and it is why
    ``verify_manuscript`` reads them from here rather than from the build.
    """
    recon = ledger.rename(columns={"coder1": "sub_c1", "coder2": "sub_c2"}).copy()
    recon["status"] = [
        "agree" if a == b else "disagree"
        for a, b in zip(recon["sub_c1"], recon["sub_c2"])
    ]
    k = cohen_kappa(recon)
    # The ledger is read back with dtype=str, so the flag arrives as "True" /
    # "False" rather than as a boolean; pandas 3 gives string columns their own
    # dtype, which makes an `== object` test the wrong way to tell the two apart.
    settled = ledger["adjudicated"]
    if not pd.api.types.is_bool_dtype(settled):
        settled = settled.astype(str).str.strip().str.lower() == "true"
    return {
        "n": len(ledger),
        "kappa": k["kappa"],
        "po": k["po"],
        "adjudicated": int(settled.sum()),
        "divergences": int((recon["sub_c1"] != recon["sub_c2"]).sum()),
        CLAIM_DIRECTED: int((ledger["sub_label"] == CLAIM_DIRECTED).sum()),
        INCIDENTAL: int((ledger["sub_label"] == INCIDENTAL).sum()),
    }


def summarize(recon: pd.DataFrame) -> None:
    counts = recon["status"].value_counts().to_dict()
    print(f"§8 reconciliation over {len(recon)} (food, pmid) records:")
    for st in ("agree", "disagree", "only_c1", "only_c2"):
        print(f"  {st:10s}: {counts.get(st, 0)}")
    k = cohen_kappa(recon)
    print(
        f"\nCohen's kappa (on {k['n_both']} co-coded records): "
        f"{k['kappa']:.4f} (observed agreement {k['po']:.4f})"
    )
    needs = recon[recon.apply(_needs_ruling, axis=1)]
    if not needs.empty:
        print(f"\n{len(needs)} records need adjudication.")

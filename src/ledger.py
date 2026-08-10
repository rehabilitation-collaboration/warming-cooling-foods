"""Axis A candidate ledger: reconcile two codings of the enumerated candidates.

``coding_protocol.md`` §9 asks Axis A for what Axis B already publishes — both
sides of the judgment. ``extract_candidates.py`` enumerates every candidate the
frame sources present; this module turns two independent codings of that
enumeration into one auditable ledger: reconcile on the candidate key, Cohen's κ
over the include/exclude decision, author adjudication of everything the coders
did not settle between them, and the published ``claims_ledger.csv`` schema
(§9.7).

**Why this is not ``reconcile_coders.py``.** That module keys on
(source_id, food identity, condition) and compares *directions* — it answers
"did the coders call ginger warm or cool", on rows both had already extracted.
Route D changes the question: both coders now see the *same* enumerated
candidates, so extraction is no longer a source of divergence (§8's Jaccard 0.54
problem), and the statistic that matters is agreement on include/exclude across
all candidates. The direction is still coded, but only on the includes, and it
is carried through to ``claims.csv`` rather than being the unit of comparison.

Pure functions over DataFrames, mirroring ``screening.py`` in shape: no network,
no LLM call, so the statistics are reproducible and testable offline. The coder
agents produce CSVs; the I/O and the author's rulings file live in the build
step, as they do for Axis B.

Label vocabulary: ``include`` / ``exclude`` (§9.3). Exclusion reason codes are
the seven of §9.4 and nothing else — an unrecognised code is an error, because a
reason with no basis in the protocol is exactly what the Route D goal
declaration counts as a failure.
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import DIRECTIONS

INCLUDE = "include"
EXCLUDE = "exclude"
LABELS = (INCLUDE, EXCLUDE)

# coding_protocol.md §9.4. Every code is grounded in a rule or an adjudication
# the protocol already records; none was introduced for the ledger alone.
REASON_CODES = (
    "serving-temperature",
    "no-direction",
    "not-verbatim",
    "not-food",
    "navigation",
    "fragment",
    "duplicate",
)

# A coder writes this when the span cannot be judged from the source at all.
# Like Axis B's uncertain-species flag, it goes to the author even when both
# coders agree, because agreement reached on absent information is not evidence
# (§9.6, mirroring screening_protocol.md §5).
UNCERTAIN = "uncertain"

KEY = ["source_id", "candidate"]

# What a coder returns on an include, per §9.3, so the ledger's include rows can
# regenerate claims.csv. The first three are required; ``quote`` is carried
# because §9.7's schema has a column for it, but §9.3 does not demand it.
CODED_FIELDS = ("food_ja", "food_en", "direction", "quote")


def _norm_label(value) -> str:
    """Normalise a coder's raw label to ``include``/``exclude`` or ``""``."""
    s = str(value or "").strip().lower()
    if s in ("include", "inc", "in", "1", "true", "yes"):
        return INCLUDE
    if s in ("exclude", "exc", "ex", "out", "0", "false", "no"):
        return EXCLUDE
    return ""


def _coder_frame(records: list[dict] | pd.DataFrame, coder: str) -> pd.DataFrame:
    """One coder's labels → key columns plus that coder's judgment columns.

    Keyed on (source_id, candidate): the same span can occur in several sources
    and is judged separately in each, because the unit of coding is a
    (food, source) pair (§2).
    """
    df = pd.DataFrame(records)
    suffixed = [
        f"label_{coder}", f"reason_{coder}", f"sublabels_{coder}",
        f"food_ja_{coder}", f"food_en_{coder}", f"direction_{coder}",
        f"quote_{coder}",
    ]
    if df.empty:
        return pd.DataFrame(columns=KEY + suffixed)

    def _optional(col: str, *, lower: bool = False):
        """Free-text column, absent for coders that did not supply it.

        Returns a Series when the column exists and a scalar when it does not
        (pandas broadcasts it), so any case-folding has to happen here rather
        than on the result.
        """
        if col not in df.columns:
            return ""
        s = df[col].fillna("").astype(str).str.strip()
        return s.str.lower() if lower else s

    out = pd.DataFrame(
        {
            "source_id": df["source_id"].astype(str).str.strip(),
            "candidate": df["candidate"].astype(str).str.strip(),
            f"label_{coder}": df["label"].map(_norm_label),
            f"reason_{coder}": _optional("reason", lower=True),
            f"sublabels_{coder}": _optional("sublabels"),
            f"food_ja_{coder}": _optional("food_ja"),
            f"food_en_{coder}": _optional("food_en"),
            f"direction_{coder}": _optional("direction", lower=True),
            f"quote_{coder}": _optional("quote"),
        }
    )
    dups = out[out.duplicated(KEY, keep=False)]
    if not dups.empty:
        print(
            f"[warn] coder {coder} has {len(dups)} rows on duplicated "
            f"(source_id, candidate) keys",
            file=sys.stderr,
        )
    return out.drop_duplicates(KEY, keep="first")


def validate_codes(coded: pd.DataFrame, coder: str) -> None:
    """Fail loudly on a reason code or direction outside the protocol.

    The goal declaration counts "an exclusion reason code with no basis in the
    protocol" as a failure of Route D, so an unknown code cannot be allowed to
    reach the ledger and be read later as though §9.4 sanctioned it. A code the
    coders genuinely need is a protocol revision, not a silent addition.
    """
    excluded = coded[coded[f"label_{coder}"] == EXCLUDE]
    bad = sorted(
        {
            r for r in excluded[f"reason_{coder}"]
            if r and r != UNCERTAIN and r not in REASON_CODES
        }
    )
    if bad:
        raise ValueError(
            f"coder {coder} used exclusion reason code(s) outside "
            f"coding_protocol.md §9.4: {bad}"
        )
    missing = int(((excluded[f"reason_{coder}"] == "")).sum())
    if missing:
        raise ValueError(
            f"coder {coder} left {missing} exclusions without a reason code "
            "(§9.3 requires one on every exclude)"
        )
    included = coded[coded[f"label_{coder}"] == INCLUDE]
    bad_dir = sorted(
        {d for d in included[f"direction_{coder}"] if d and d not in DIRECTIONS}
    )
    if bad_dir:
        raise ValueError(
            f"coder {coder} used direction(s) outside {DIRECTIONS}: {bad_dir}"
        )


def reconcile(coder1, coder2) -> pd.DataFrame:
    """Outer-join two codings on (source_id, candidate) with a ``status`` column.

    status ∈ {agree, disagree, only_c1, only_c2}. ``label`` columns are
    ``include``/``exclude``/``""`` (missing from that coder).

    Validation is not optional: the protocol-bound vocabularies are checked on
    the way in, so no later stage has to trust that a caller remembered to ask
    for them.
    """
    df1 = _coder_frame(coder1, "c1")
    df2 = _coder_frame(coder2, "c2")
    validate_codes(df1, "c1")
    validate_codes(df2, "c2")
    merged = df1.merge(df2, on=KEY, how="outer")
    for col in merged.columns:
        if col not in KEY:
            merged[col] = merged[col].fillna("")

    def _status(row) -> str:
        has1 = row["label_c1"] in LABELS
        has2 = row["label_c2"] in LABELS
        if has1 and has2:
            return "agree" if row["label_c1"] == row["label_c2"] else "disagree"
        if has1:
            return "only_c1"
        return "only_c2"

    merged["status"] = merged.apply(_status, axis=1)
    return merged.sort_values(["status"] + KEY).reset_index(drop=True)


def cohen_kappa(recon: pd.DataFrame) -> dict:
    """Cohen's κ on candidates BOTH coders labelled (agree + disagree rows).

    Categories = {include, exclude}. Coverage differences (only_c1/only_c2) are
    excluded from κ — they are coverage, not rating disagreements — and reported
    separately. The denominator is the co-coded count, never the full candidate
    count (the GPT #4 lesson, kept from Axis B).

    Unlike §8's κ, this one is computed over a candidate set both coders were
    handed, so it measures the decision rather than the overlap of two
    independent extractions.
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


def _split_ruling(value) -> dict:
    """Normalise an author ruling to a dict of the fields it settles.

    Three forms are accepted, in increasing order of what the author is
    overriding::

        "exclude"                              # label only
        ("exclude", "fragment")                # label + reason code
        {"label": "include", "direction": "cool", "food_ja": "きゅうり", ...}

    The dict form exists because a ruling can change *what is coded*, not only
    whether it is kept: settling a direction the coders split on, or turning an
    agreed exclusion into an include, leaves fields that no coder ever filled in.
    """
    if isinstance(value, dict):
        out = {k: str(v).strip() for k, v in value.items() if k != "label"}
        out["label"] = _norm_label(value.get("label"))
        out.setdefault("reason", "")
        return out
    if isinstance(value, (tuple, list)):
        label = value[0]
        reason = value[1] if len(value) > 1 else ""
    else:
        label, reason = value, ""
    return {"label": _norm_label(label), "reason": str(reason).strip()}


def _needs_ruling(row) -> bool:
    """Rows the author must settle: divergences, unjudgeable spans, split directions.

    The third case is not covered by ``status``, which compares include/exclude
    only. Two coders can agree a span is an attribution and still disagree on
    *what it attributes* — RD-1b found three such candidates in
    macrobiotic_rashinban (ジネンジョ / 玉ねぎ / きゅうり). Direction is Axis A's
    construct, so a split there is a disagreement about the measurement itself
    and cannot be resolved by taking the first coder's word for it.
    """
    if row["status"] != "agree":
        return True
    flags = f"{row.get('reason_c1', '')} {row.get('reason_c2', '')}".lower()
    if UNCERTAIN in flags:
        return True
    if row["label_c1"] == INCLUDE:
        d1 = str(row.get("direction_c1", "") or "")
        d2 = str(row.get("direction_c2", "") or "")
        if d1 and d2 and d1 != d2:
            return True
    return False


def adjudicate(recon: pd.DataFrame, rulings: dict | None = None) -> pd.DataFrame:
    """Resolve every candidate to a ``final_label``, adding an ``adjudicated`` flag.

    - Rows where both coders agree (and neither flagged ``uncertain``) take the
      shared label, *unless* the author filed a ruling on that key.
    - Every other row requires an author ruling in ``rulings`` keyed by
      (source_id, candidate) → ``"exclude"`` or ``("exclude", "fragment")``. A
      missing ruling is a hard error (fail-loud: no silent default), so a
      divergence cannot be forgotten.
    - A ruling on an *agreed* row overrides the shared label, and reports
      ``adjudicated=True`` so the override is visible in the published ledger
      rather than silent (the D42 behaviour, kept identical across the axes).
    """
    rulings = rulings or {}
    finals: list[str] = []
    reasons: list[str] = []
    settled: list[bool] = []
    coded: dict[str, list[str]] = {f: [] for f in CODED_FIELDS}
    for _, r in recon.iterrows():
        key = (r["source_id"], r["candidate"])
        coder_reason = r["reason_c1"] or r["reason_c2"]
        if _needs_ruling(r) or key in rulings:
            if key not in rulings:
                raise ValueError(
                    f"candidate needs an author ruling ({r['status']}): {key}"
                )
            rule = _split_ruling(rulings[key])
            label = rule["label"]
            if label not in LABELS:
                raise ValueError(f"invalid ruling for {key}: {rulings[key]!r}")
            reason = rule["reason"] or coder_reason
            if label == EXCLUDE and reason not in REASON_CODES:
                raise ValueError(
                    f"ruling for {key} excludes with reason {reason!r}, which is "
                    f"not one of coding_protocol.md §9.4's codes"
                )
            fields = {f: rule.get(f, "") or _agreed_field(r, f) for f in CODED_FIELDS}
            is_ruled = True
        else:
            label = r["label_c1"]
            reason = coder_reason
            fields = {f: _agreed_field(r, f) for f in CODED_FIELDS}
            is_ruled = False

        if label == INCLUDE:
            # §9.3: an include carries the coding that regenerates claims.csv.
            # A ruling that flips an agreed exclusion to include reaches here
            # with every field empty, because no coder ever filled one in.
            blank = [f for f in ("food_ja", "food_en", "direction") if not fields[f]]
            if blank:
                raise ValueError(
                    f"{key} is included but carries no {blank} — §9.3 requires "
                    "them on every include, so the ledger's include rows can "
                    "regenerate claims.csv. A ruling that flips an exclusion to "
                    "include has to supply them: {'label': 'include', ...}"
                )
            if fields["direction"] not in DIRECTIONS:
                raise ValueError(
                    f"{key} has direction {fields['direction']!r}, outside {DIRECTIONS}"
                )

        finals.append(label)
        reasons.append(reason if label == EXCLUDE else "")
        settled.append(is_ruled)
        for f in CODED_FIELDS:
            coded[f].append(fields[f] if label == INCLUDE else "")
    out = recon.copy()
    out["final_label"] = finals
    out["reason"] = reasons
    out["adjudicated"] = settled
    for f in CODED_FIELDS:
        out[f"final_{f}"] = coded[f]
    return out


def _union(row, prefix: str) -> str:
    """Union of a ``;``-joined field across both coders, order preserved."""
    parts: list[str] = []
    for col in (f"{prefix}_c1", f"{prefix}_c2"):
        for part in str(row.get(col, "") or "").split(";"):
            part = part.strip()
            if part and part not in parts:
                parts.append(part)
    return ";".join(parts)


def _agreed_field(row, prefix: str) -> str:
    """A field the coders supply on includes; c1's value, falling back to c2.

    The two can differ (one writes 生姜, the other しょうが). That is a naming
    difference on an agreed include, not a disagreement about the decision, and
    §3 already leaves naming to the coder — so the ledger keeps c1's and the
    author's ruling overrides it where it matters.

    ``direction`` is different in kind and is deliberately not left to this
    rule: a split there routes to the author through ``_needs_ruling``, so by
    the time this function supplies one the coders agree, or a ruling has
    already settled it.
    """
    return str(row.get(f"{prefix}_c1", "") or "") or str(row.get(f"{prefix}_c2", "") or "")


def to_ledger_csv(adjudicated: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    """Adjudicated frame + enumeration → the published schema (§9.7).

    ``source_id, line_no, candidate, paths, coder1, coder2, adjudicated,
    final_label, reason, sublabels, food_ja, food_en, direction, quote`` — one
    row per (source_id, candidate). ``line_no`` and ``paths`` come from the
    enumeration rather than from a coder, so the ledger records where the span
    was found independently of how it was judged.

    The enumeration and the judgments must match **in both directions**:

    - a judgment on a span that was never enumerated means a coder invented it;
    - an enumerated candidate that carries no judgment never reached a coder, or
      was dropped from the CSV a coder returned — and in the finished ledger
      that is indistinguishable from a candidate the coders excluded.

    The second direction is the whole point of the ledger, and nothing upstream
    catches it: ``reconcile`` builds its frame from the two submitted CSVs and
    has no knowledge of the enumeration, so a coder omitting rows from a batch
    of 400 would otherwise publish a silently short ledger.
    """
    keys = candidates[KEY + ["line_no", "paths"]].drop_duplicates(KEY)
    merged = adjudicated.merge(keys, on=KEY, how="outer", indicator=True)
    invented = merged[merged["_merge"] == "left_only"]
    if not invented.empty:
        sample = list(zip(invented["source_id"], invented["candidate"]))[:5]
        raise ValueError(
            f"{len(invented)} judged candidates are not in the enumeration, "
            f"e.g. {sample}"
        )
    unjudged = merged[merged["_merge"] == "right_only"]
    if not unjudged.empty:
        sample = list(zip(unjudged["source_id"], unjudged["candidate"]))[:5]
        raise ValueError(
            f"{len(unjudged)} enumerated candidates carry no judgment, "
            f"e.g. {sample} — an unjudged candidate reads as an exclusion in "
            "the published ledger, which is what it exists to prevent"
        )
    included = merged["final_label"] == INCLUDE
    out = pd.DataFrame(
        {
            "source_id": merged["source_id"],
            "line_no": merged["line_no"],
            "candidate": merged["candidate"],
            "paths": merged["paths"],
            "coder1": merged["label_c1"],
            "coder2": merged["label_c2"],
            "adjudicated": merged["adjudicated"],
            "final_label": merged["final_label"],
            "reason": merged["reason"],
            "sublabels": merged.apply(_union, prefix="sublabels", axis=1),
            "food_ja": merged["final_food_ja"].where(included, ""),
            "food_en": merged["final_food_en"].where(included, ""),
            "direction": merged["final_direction"].where(included, ""),
            "quote": merged["final_quote"].where(included, ""),
        }
    )
    return out.sort_values(["source_id", "line_no", "candidate"]).reset_index(drop=True)


def exclusion_breakdown(ledger: pd.DataFrame) -> pd.DataFrame:
    """Excluded candidates per reason code, with their share — the §9.1 artefact."""
    exc = ledger[ledger["final_label"] == EXCLUDE]
    counts = exc.groupby("reason").size().sort_values(ascending=False)
    return pd.DataFrame(
        {
            "reason": counts.index,
            "n": counts.values,
            "share": (counts / len(exc)).values if len(exc) else [],
        }
    )


def summarize(recon: pd.DataFrame) -> None:
    counts = recon["status"].value_counts().to_dict()
    print(f"Ledger reconciliation over {len(recon)} (source, candidate) candidates:")
    for st in ("agree", "disagree", "only_c1", "only_c2"):
        print(f"  {st:10s}: {counts.get(st, 0)}")
    k = cohen_kappa(recon)
    print(
        f"\nCohen's kappa (on {k['n_both']} co-coded candidates): "
        f"{k['kappa']:.4f} (observed agreement {k['po']:.4f})"
    )
    needs = recon[recon.apply(_needs_ruling, axis=1)]
    if not needs.empty:
        print(f"\n{len(needs)} candidates need adjudication.")


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import argparse

    ap = argparse.ArgumentParser(description="Reconcile two Axis A ledger codings")
    ap.add_argument("coder1_csv")
    ap.add_argument("coder2_csv")
    args = ap.parse_args()
    c1 = pd.read_csv(args.coder1_csv, dtype=str).to_dict("records")
    c2 = pd.read_csv(args.coder2_csv, dtype=str).to_dict("records")
    summarize(reconcile(c1, c2))

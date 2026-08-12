"""Coding protocol §10: the materials for the author's human audit of Axis A.

Every judgment on both axes was made by a language model. The external review of
2026-08-12 pressed on what that costs a null result: if coverage is measured with
error, the error attenuates the association towards zero, and a paper whose
headline is "no association was detected" cannot answer that objection with an
agreement statistic between two models of one vendor's line. Only a human reading
the sources can.

This module builds the audit and scores it. It does not perform it.

Two halves, because the two failure directions are not the same measurement:

- **Precision** — a random sample of published Tier-1 claims, read back against
  the live source. Answers "is what we assert there?"
- **Completeness** — two Tier-1 sources read end to end, every food the source
  gives a direction listed without reference to the ledger, then diffed against
  it. Answers "is what is there asserted?" This is the half that matters most for
  the review's objection: a missed claim lowers that food's ``n_sources``,
  compresses the spread of the predictor, and pulls the estimate towards null.

Sampling is seeded and the seed is published, so the sample is not a choice made
after seeing which rows would look good. Run:

    python3 -m src.human_audit            # write the sheets
    python3 -m src.human_audit --score    # score them once they are filled in
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from .claim_mapping import load_claims, load_sources
from .definitions import DATA_DIR, SOURCES_RAW_DIR, TIER_ORG

# The date the audit was specified, used as the seed so that the number is
# traceable to something other than the author's preference.
SEED = 20260813
PRECISION_N = 60
COMPLETENESS_N = 2

SAMPLE_CSV = DATA_DIR / "human_audit_sample.csv"
RESULTS_CSV = DATA_DIR / "human_audit_results.csv"
READS_CSV = DATA_DIR / "human_audit_source_reads.csv"

# What the reader may write in the `verdict` column, fixed before any row was
# read (the RD-2 rule: the decision rule is written before the decisions).
VERDICTS = (
    "supported",        # the source says this food has this direction
    "wrong-direction",  # the food is there, the direction is not
    "not-in-source",    # the source does not attribute this food at all
    "wrong-food",       # the span was read as the wrong food
    "unlocatable",      # the page has changed and the claim cannot be checked
)


def tier1_claims() -> pd.DataFrame:
    """The published Tier-1 claim rows — the ones that make up `n_sources`."""
    claims, sources = load_claims(), load_sources()
    merged = claims.merge(
        sources[["source_id", "tier", "url"]], on="source_id", how="left"
    )
    return merged[merged["tier"] <= TIER_ORG].reset_index(drop=True)


def precision_sample(rows: pd.DataFrame, n: int = PRECISION_N,
                     seed: int = SEED) -> pd.DataFrame:
    """A seeded simple random sample of claim rows, in ledger order.

    Simple rather than stratified: stratifying by source or direction would make
    the sample easier to defend on balance and harder to defend on selection,
    and the quantity being estimated — the share of published claims the source
    supports — is a proportion over all of them.
    """
    rng = np.random.default_rng(seed)
    take = min(n, len(rows))
    picked = rng.choice(len(rows), size=take, replace=False)
    return rows.iloc[sorted(picked)].reset_index(drop=True)


def source_body_length(source_id: str) -> int:
    """Characters of extracted body text, or -1 when the file is absent."""
    path = SOURCES_RAW_DIR / f"{source_id}.txt"
    return len(path.read_text(encoding="utf-8")) if path.exists() else -1


def completeness_sources(sources: pd.DataFrame, seed: int = SEED) -> list[str]:
    """The two Tier-1 sources to read end to end: the longest, plus one at random.

    The longest is where an omission is most likely, since it offers the most
    text to miss something in; the random draw from the remaining eight keeps the
    pair from being only a worst case. Picking two at random would be cleaner to
    describe but would leave the densest source unaudited by luck, and picking
    the two longest would measure only the hard tail.
    """
    tier1 = sources[sources["tier"] <= TIER_ORG]["source_id"].tolist()
    lengths = {sid: source_body_length(sid) for sid in tier1}
    longest = max(tier1, key=lambda sid: lengths[sid])
    rest = sorted(sid for sid in tier1 if sid != longest)
    drawn = np.random.default_rng(seed).choice(rest)
    return [longest, str(drawn)]


def write_sheets() -> None:
    """Write the sample, the empty verdict sheet, and the source-read sheet."""
    rows = tier1_claims()
    sample = precision_sample(rows)
    sample_out = sample[
        ["source_id", "url", "food_en", "food_ja", "direction", "quote"]
    ].copy()
    sample_out.to_csv(SAMPLE_CSV, index=False)
    print(f"wrote {SAMPLE_CSV.name}: {len(sample_out)} of {len(rows)} Tier-1 claims "
          f"(seed {SEED})")

    if RESULTS_CSV.exists():
        print(f"  {RESULTS_CSV.name} already exists — left untouched")
    else:
        blank = sample_out[["source_id", "food_en", "food_ja", "direction"]].copy()
        blank["verdict"] = ""
        blank["note"] = ""
        blank.to_csv(RESULTS_CSV, index=False)
        print(f"wrote {RESULTS_CSV.name}: empty verdict sheet "
              f"(one of {', '.join(VERDICTS)} per row)")

    chosen = completeness_sources(load_sources())
    print(f"\nend-to-end reads ({COMPLETENESS_N} of the 9 Tier-1 sources): "
          f"{', '.join(chosen)}")
    for sid in chosen:
        print(f"  {sid:14s} {source_body_length(sid):7d} chars   "
              f"{int((tier1_claims()['source_id'] == sid).sum()):3d} claims in the ledger")
    if READS_CSV.exists():
        print(f"  {READS_CSV.name} already exists — left untouched")
    else:
        pd.DataFrame(columns=["source_id", "food_ja", "direction", "quote"]).to_csv(
            READS_CSV, index=False
        )
        print(f"wrote {READS_CSV.name}: empty sheet — list every food the source "
              f"gives a direction, without consulting the ledger")


def score_precision(results: pd.DataFrame) -> dict:
    """Share of sampled claims the source supports, and the failure breakdown."""
    verdicts = results["verdict"].fillna("").str.strip().str.lower()
    unknown = sorted(set(verdicts) - set(VERDICTS) - {""})
    if unknown:
        raise ValueError(f"{RESULTS_CSV.name} carries unknown verdicts: {unknown}")
    filled = verdicts[verdicts != ""]
    if filled.empty:
        raise ValueError(f"{RESULTS_CSV.name} has no verdicts filled in yet")
    # `unlocatable` leaves the denominator, because a page that has changed since
    # the freeze is a fact about the web, not about the coding.
    checkable = filled[filled != "unlocatable"]
    supported = int((checkable == "supported").sum())
    return {
        "n_sampled": int(len(results)),
        "n_judged": int(len(filled)),
        "n_checkable": int(len(checkable)),
        "n_supported": supported,
        "precision": supported / len(checkable) if len(checkable) else float("nan"),
        "breakdown": filled.value_counts().to_dict(),
    }


def score_completeness(reads: pd.DataFrame, rows: pd.DataFrame) -> dict:
    """Diff a human end-to-end read against the ledger, per source.

    Matching is on ``food_ja`` as the reader wrote it, because that is what the
    source prints; a food the reader names that the ledger records under a
    different Japanese surface form counts as missed until the author says
    otherwise, which is the conservative direction for a completeness claim.
    """
    out: dict[str, dict] = {}
    for sid, group in reads.groupby("source_id"):
        read = {str(f).strip() for f in group["food_ja"] if str(f).strip()}
        held = {str(f).strip() for f in rows[rows["source_id"] == sid]["food_ja"]}
        out[str(sid)] = {
            "read_by_human": len(read),
            "in_ledger": len(held),
            "missed_by_ledger": sorted(read - held),
            "in_ledger_only": sorted(held - read),
            "recall": len(read & held) / len(read) if read else float("nan"),
        }
    return out


def main(score: bool = False) -> None:
    if not score:
        write_sheets()
        return
    rows = tier1_claims()
    if RESULTS_CSV.exists():
        p = score_precision(pd.read_csv(RESULTS_CSV, dtype=str))
        print(f"precision: {p['n_supported']}/{p['n_checkable']} = "
              f"{100 * p['precision']:.1f}%  (sampled {p['n_sampled']}, "
              f"judged {p['n_judged']})")
        for verdict, n in sorted(p["breakdown"].items()):
            print(f"  {verdict:16s} {n}")
    if READS_CSV.exists():
        reads = pd.read_csv(READS_CSV, dtype=str)
        if len(reads):
            print()
            for sid, r in score_completeness(reads, rows).items():
                print(f"{sid}: human read {r['read_by_human']}, ledger holds "
                      f"{r['in_ledger']}, recall {100 * r['recall']:.1f}%")
                if r["missed_by_ledger"]:
                    print(f"  missed by the ledger: {r['missed_by_ledger']}")
                if r["in_ledger_only"]:
                    print(f"  in the ledger only:   {r['in_ledger_only']}")


if __name__ == "__main__":
    main(score="--score" in sys.argv[1:])

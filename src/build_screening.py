"""Adjudicate the two independent L2 codings into the published screening.csv.

Coder 1 (Claude Sonnet) and Coder 2 (Claude Opus) labelled every L2 record
independently from ``data/screening_protocol.md``, blind to each other and to
the golden set. This script reconciles the two codings, applies the author's
rulings to the records they diverged on, and writes:

- ``data/screening.csv`` — the published per-record judgments (protocol §6)
- ``L2_screened`` on the L2 rows of ``data/pubmed_counts.csv`` — L2′, the count
  of on-construct studies per food, which is Axis B's rebuilt measure

The author ruling ledger ``data/screening_rulings.csv`` *is* the provenance of
every author decision: each divergence was settled by reading the title +
abstract (and, where the abstract does not state the subject species, the PubMed
MeSH headings or the full text) against protocol §2-§3. Foods are read from
whichever per-coder CSVs exist, so the same script serves the golden-food batch
and the full run.

Run: ``python3 -m src.build_screening``
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import DATA_DIR, PUBMED_COUNTS_CSV
from .screening import (
    GOLDEN_CSV,
    SCREENING_CSV,
    adjudicate,
    attach_l2_screened,
    cohen_kappa,
    golden_scores,
    l2_screened,
    reconcile,
    to_screening_csv,
)

WORK_DIR = DATA_DIR / "screening_work"

# --- author rulings -------------------------------------------------------
# The author's decisions live in ``data/screening_rulings.csv``
# (food_key, pmid, final_label, rationale, batch) and that file *is* their
# provenance: each row was settled by reading the title + abstract — and, where
# the abstract does not state the subject species, the PubMed MeSH headings or
# the full text — against protocol §2-§3.
#
# They were a dict literal here until 2026-08-08. The recall rebuild added 210
# rulings to the original 56, which is past the size where a literal stays
# readable, and the ledger is more useful published than compiled: the review
# that asked for the judgments to be auditable gets a file it can read, in the
# same form as ``screening_thirdpass.csv``. The pre-migration grouping comments
# remain in the git history; every rule they stated is restated in the rationale
# of each row that used it, with its protocol section.
RULINGS_CSV = DATA_DIR / "screening_rulings.csv"


def load_rulings() -> dict:
    """Read the author ruling ledger into {(food_key, pmid): (label, why)}.

    A duplicated key is a hard error rather than a last-write-wins: two rulings
    for one record means one of them was never applied, and which one silently
    won would depend on row order.
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
        (r.food_key, r.pmid): (r.final_label, r.rationale)
        for r in df.itertuples()
    }


def load_coder(coder: str) -> pd.DataFrame:
    """Concatenate one coder's per-food CSVs from data/screening_work/<coder>/."""
    files = sorted((WORK_DIR / coder).glob("*.csv"))
    if not files:
        sys.exit(f"no coder CSVs under {WORK_DIR / coder}")
    return pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)


def exclusion_breakdown(ledger: pd.DataFrame) -> pd.DataFrame:
    """Counts of excluded records by reason class, largest first.

    The ``reason`` field carries a class followed by optional free text
    ("animal: mice", "species-mismatch: Capsicum annuum, not Piper nigrum"), so
    the class is the part before the first colon. Table 2 of the manuscript
    reports these counts and cites this module for them, which it could not do
    while the aggregation lived in a one-off script.
    """
    excluded = ledger[ledger["final_label"] == "exclude"]
    cls = excluded["reason"].fillna("").str.split(":").str[0].str.strip()
    counts = cls.value_counts()
    return pd.DataFrame(
        {"reason": counts.index, "n": counts.to_numpy(),
         "pct": (100 * counts / len(excluded)).round(1).to_numpy()}
    )


def main() -> None:
    c1 = load_coder("c1")
    c2 = load_coder("c2")
    recon = reconcile(c1.to_dict("records"), c2.to_dict("records"))
    counts = recon["status"].value_counts().to_dict()
    print(f"reconciled {len(recon)} (food, pmid) records: {counts}")

    k = cohen_kappa(recon)
    print(f"Cohen's kappa = {k['kappa']:.4f} on {k['n_both']} co-coded records "
          f"(observed agreement {k['po']:.4f})")

    golden = pd.read_csv(GOLDEN_CSV, dtype=str).to_dict("records")
    for name, df in (("coder1", c1), ("coder2", c2)):
        s = golden_scores(df.to_dict("records"), golden)
        print(f"  {name} vs golden (n={s['n']}): precision {s['precision']:.4f} "
              f"recall {s['recall']:.4f} F1 {s['f1']:.4f}")

    adjudicated = adjudicate(recon, load_rulings())
    out = to_screening_csv(adjudicated)
    out.to_csv(SCREENING_CSV, index=False)
    print(f"\nwrote {SCREENING_CSV} ({len(out)} records, "
          f"{int(out['adjudicated'].sum())} author-adjudicated)")

    l2s = l2_screened(adjudicated)
    counts_df = pd.read_csv(PUBMED_COUNTS_CSV)
    l2_rows = counts_df[counts_df["layer"] == "L2"]
    l2_foods = set(l2_rows["food_key"])
    coded = set(adjudicated["food_key"])
    # A food whose L2 query returned nothing has no records to screen, so its
    # L2′ is 0 by construction — screening only ever removes records. Those
    # foods are as measured as the coded ones and belong in the denominator of
    # "N foods with no direct research". Read that off the L2 count itself
    # rather than off which foods appear in l2_records.csv: once the food
    # universe is widened, a food can have L2 hits that have not been fetched or
    # screened yet, and those must stay NaN rather than be silently called zero.
    zero_hit = set(l2_rows.loc[l2_rows["n_pubmed"] == 0, "food_key"])
    screened = sorted(coded | zero_hit)
    unscreened = sorted(l2_foods - set(screened))
    if unscreened:
        print(f"\n{len(unscreened)} foods have L2 hits that are not screened yet "
              f"(L2_screened stays blank): {unscreened}")
    updated = attach_l2_screened(counts_df, l2s, screened_foods=screened)
    updated.to_csv(PUBMED_COUNTS_CSV, index=False)

    print(f"\nL2' over {len(screened)} of {len(l2_foods)} L2 foods "
          f"({len(coded)} coded, {len(zero_hit)} with no L2 hit to screen):")
    nonzero = [f for f in screened if l2s.get(f, 0)]
    for food in sorted(nonzero, key=lambda f: -l2s.get(f, 0)):
        raw = counts_df[(counts_df.food_key == food) & (counts_df.layer == "L2")]
        n_raw = int(raw["n_pubmed"].iloc[0]) if len(raw) else -1
        print(f"  {food:14s} L2 {n_raw:4d} → L2' {int(l2s.get(food, 0)):3d}")
    print(f"  ... and {len(screened) - len(nonzero)} foods with L2' = 0")

    breakdown = exclusion_breakdown(out)
    total_excluded = int(breakdown["n"].sum())
    print(f"\nexclusion reasons (n = {total_excluded}):")
    for _, r in breakdown.iterrows():
        print(f"  {r['reason']:20s} {int(r['n']):6d}  {r['pct']:5.1f}%")
    animalish = breakdown[breakdown["reason"].isin(["animal", "livestock-heat"])]["n"].sum()
    print(f"  animal + livestock-heat = {int(animalish)} "
          f"({100 * animalish / total_excluded:.1f}%)")


if __name__ == "__main__":
    main()

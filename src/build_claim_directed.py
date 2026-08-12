"""Adjudicate the two §8 codings into data/screening_claim_directed.csv.

Coder 1 (`claude-sonnet-5`) and coder 2 (`claude-opus-5`) sub-labelled every
included record independently from ``data/screening_protocol.md`` §8, blind to
each other. This script reconciles them, reports κ, applies the author's rulings
from ``screening_claim_directed_rulings.csv``, and writes the published ledger.

It does **not** write ``screening.csv`` and does not recompute L2′. The sub-label
reaches the analysis through ``claim_directed.attach()``, which folds it into a
read-time copy, so the primary measure cannot move as a result of anything
decided here.

Run: ``python3 -m src.build_claim_directed``
"""

from __future__ import annotations

import sys

import pandas as pd

from .claim_directed import (
    CLAIM_DIRECTED,
    INCIDENTAL,
    LEDGER_CSV,
    adjudicate,
    attach,
    cohen_kappa,
    load_rulings,
    reconcile,
    to_ledger_csv,
)
from .definitions import DATA_DIR
from .screening import INCLUDE, SCREENING_CSV, l2_screened

WORK_DIR = DATA_DIR / "screening_work"


def load_coder(coder: str) -> pd.DataFrame:
    """Concatenate one coder's batch CSVs from data/screening_work/<coder>/."""
    files = sorted((WORK_DIR / coder).glob("*.csv"))
    if not files:
        sys.exit(f"no coder CSVs under {WORK_DIR / coder}")
    return pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)


def main() -> None:
    c1 = load_coder("cd1")
    c2 = load_coder("cd2")
    recon = reconcile(c1.to_dict("records"), c2.to_dict("records"))
    counts = recon["status"].value_counts().to_dict()
    print(f"reconciled {len(recon)} (food, pmid) records: {counts}")

    k = cohen_kappa(recon)
    print(f"Cohen's kappa = {k['kappa']:.4f} on {k['n_both']} co-coded records "
          f"(observed agreement {k['po']:.4f})")

    adjudicated = adjudicate(recon, load_rulings())
    out = to_ledger_csv(adjudicated)
    out.to_csv(LEDGER_CSV, index=False)
    print(f"\nwrote {LEDGER_CSV} ({len(out)} records, "
          f"{int(out['adjudicated'].sum())} author-adjudicated)")

    split = out["sub_label"].value_counts()
    print(f"  {CLAIM_DIRECTED}: {int(split.get(CLAIM_DIRECTED, 0))}   "
          f"{INCIDENTAL}: {int(split.get(INCIDENTAL, 0))}")

    # The attach is run here as well as in the analysis, so a coverage gap
    # between the two ledgers surfaces at build time rather than at read time.
    screening = pd.read_csv(SCREENING_CSV)
    joined = attach(screening, out)
    full = l2_screened(joined)
    narrow = l2_screened(joined, exclude_sublabels=(INCIDENTAL,))
    print(f"\nL2' as reported: {int(full.sum())} over {len(full)} foods")
    print(f"L2' claim-directed only: {int(narrow.sum())} over {len(narrow)} foods")
    moved = [
        f"{food} {int(full.get(food, 0))}->{int(narrow.get(food, 0))}"
        for food in full.index
        if int(full.get(food, 0)) != int(narrow.get(food, 0))
    ]
    print(f"foods whose count changes: {len(moved)}")
    for line in moved:
        print(f"  {line}")

    unchanged = (screening[screening["final_label"] == INCLUDE].shape[0], len(out))
    print(f"\nincludes / sub-labelled: {unchanged[0]} / {unchanged[1]}")


if __name__ == "__main__":
    main()

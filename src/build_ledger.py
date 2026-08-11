"""Aggregate the two Axis A codings into the published claims_ledger.csv.

Coder 1 (Claude Sonnet) and Coder 2 (Claude Opus) judged every enumerated
candidate independently against ``data/coding_protocol.md`` §9, one batch at a
time, blind to each other. This script is the other end of that fan-out: it
concatenates the per-batch CSVs, reconciles them on (source_id, candidate),
reports Cohen's κ, applies the author's rulings to everything the coders did not
settle between them, and writes:

- ``data/claims_ledger.csv`` — the published per-candidate judgments (§9.7),
  the artefact Route D exists to produce
- the exclusion breakdown §9.1 offers the reader as the check on "was this a
  finding we missed, or an exclusion the protocol called for?"

``src/ledger.py`` holds the pure functions. The I/O, the author's ruling file and
the batch bookkeeping live here, exactly as they do for Axis B in
``build_screening.py``.

The coding is fanned out over 55 batches per coder, so the first thing this does
is check that every batch came back, and came back whole. ``to_ledger_csv``
catches dropped rows at the end against the full enumeration, but by then every
agent has run; caught per batch, the repair is one re-run of one batch.

Run: ``python3 -m src.build_ledger``
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import DATA_DIR
from .dump_ledger_batches import BATCH_INDEX_CSV, WORK_DIR, load_candidates
from .ledger import (
    CODED_FIELDS,
    KEY,
    adjudicate,
    cohen_kappa,
    exclusion_breakdown,
    reconcile,
    to_ledger_csv,
)

LEDGER_CSV = DATA_DIR / "claims_ledger.csv"

# --- author rulings -------------------------------------------------------
# The author's decisions live in ``data/ledger_rulings.csv``
# (source_id, candidate, final_label, reason, food_ja, food_en, direction,
# quote, rationale, batch) and that file *is* their provenance, as
# ``screening_rulings.csv`` is for Axis B. Externalised from the start rather
# than grown as a dict literal first (project decision D41): the review that
# asked for Axis A's judgments to be auditable gets a file it can read.
RULINGS_CSV = DATA_DIR / "ledger_rulings.csv"


def load_rulings() -> dict:
    """Read the author ruling ledger into {(source_id, candidate): ruling}.

    A ruling may settle more than the label. ``adjudicate`` accepts a dict, so a
    ruling that turns an agreed exclusion into an include can carry the
    ``food_ja`` / ``food_en`` / ``direction`` that no coder ever filled in —
    §9.3 requires them on every include, and a flipped exclusion arrives with
    them empty. Columns left blank fall back to what the coders wrote.

    A duplicated key is a hard error rather than last-write-wins: two rulings on
    one candidate mean one of them was never applied, and which one won would
    depend on row order.
    """
    if not RULINGS_CSV.exists():
        return {}
    df = pd.read_csv(RULINGS_CSV, dtype=str).fillna("")
    if df.empty:
        return {}
    dups = df[df.duplicated(KEY, keep=False)]
    if not dups.empty:
        raise ValueError(
            f"{RULINGS_CSV.name} carries {len(dups)} rows on duplicated "
            f"(source_id, candidate) keys: "
            f"{sorted(set(zip(dups['source_id'], dups['candidate'])))}"
        )
    rulings = {}
    for row in df.to_dict("records"):
        ruling = {"label": row.get("final_label", ""), "reason": row.get("reason", "")}
        ruling.update({f: row.get(f, "") for f in CODED_FIELDS})
        rulings[(row["source_id"], row["candidate"])] = ruling
    return rulings


def load_coder(coder: str) -> pd.DataFrame:
    """Concatenate one coder's per-batch CSVs from data/ledger_work/<coder>/.

    The batch id is not a column a coder writes — it is the file name it was
    told to use — so it is attached here. ``audit_batches`` needs it to check a
    returned batch against the slice of the enumeration it was cut from.
    """
    files = sorted((WORK_DIR / coder).glob("*.csv"))
    if not files:
        sys.exit(f"no coder CSVs under {WORK_DIR / coder}")
    frames = []
    for path in files:
        df = pd.read_csv(path, dtype=str)
        df["batch_id"] = path.stem
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def audit_batches(coded: pd.DataFrame, coder: str) -> list[str]:
    """Check what one coder returned against ``batch_index.csv``.

    Returns the batch ids that have not come back yet — pending work, not an
    error. Two things *are* errors:

    - a batch id absent from the index: the coder wrote to a name nobody
      assigned, so those rows belong to no partition;
    - a returned batch whose row count differs from its candidate count: rows
      were dropped or invented. A dropped row is the failure mode the ledger
      exists to prevent, because in the finished file it is indistinguishable
      from a candidate the coders chose to exclude.
    """
    index = pd.read_csv(BATCH_INDEX_CSV)
    expected = {str(b): int(n) for b, n in zip(index["batch_id"], index["n_candidates"])}
    got = coded.groupby("batch_id").size().to_dict()

    unknown = sorted(set(got) - set(expected))
    if unknown:
        raise ValueError(
            f"coder {coder} returned batch(es) absent from "
            f"{BATCH_INDEX_CSV.name}: {unknown}"
        )
    wrong = {b: n for b, n in sorted(got.items()) if n != expected[b]}
    if wrong:
        detail = ", ".join(f"{b} returned {n}, expected {expected[b]}"
                           for b, n in wrong.items())
        raise ValueError(
            f"coder {coder} returned the wrong number of rows for "
            f"{len(wrong)} batch(es): {detail}"
        )
    return sorted(set(expected) - set(got))


def report_pending(pending: dict[str, list[str]], total: int) -> bool:
    """Print per-coder batch progress; True when anything is still outstanding."""
    for coder, missing in pending.items():
        print(f"{coder}: {total - len(missing)}/{total} batches in, "
              f"{len(missing)} pending")
    outstanding = sorted(set().union(*pending.values()))
    if not outstanding:
        return False
    print(f"\n{len(outstanding)} batch(es) not yet coded by both coders:")
    for batch in outstanding:
        waiting = ", ".join(c for c in sorted(pending) if batch in pending[c])
        print(f"  {batch:28s} waiting on {waiting}")
    return True


def main() -> None:
    c1 = load_coder("c1")
    c2 = load_coder("c2")
    pending = {"c1": audit_batches(c1, "c1"), "c2": audit_batches(c2, "c2")}
    total = len(pd.read_csv(BATCH_INDEX_CSV))
    if report_pending(pending, total):
        sys.exit("\nledger not written: the enumeration is not fully judged yet")

    recon = reconcile(c1.to_dict("records"), c2.to_dict("records"))
    counts = recon["status"].value_counts().to_dict()
    print(f"\nreconciled {len(recon)} (source_id, candidate) candidates: {counts}")

    k = cohen_kappa(recon)
    print(f"Cohen's kappa = {k['kappa']:.4f} on {k['n_both']} co-coded candidates "
          f"(observed agreement {k['po']:.4f})")

    adjudicated = adjudicate(recon, load_rulings())
    out = to_ledger_csv(adjudicated, load_candidates())
    out.to_csv(LEDGER_CSV, index=False)
    n_include = int((out["final_label"] == "include").sum())
    print(f"\nwrote {LEDGER_CSV} ({len(out)} candidates, {n_include} include, "
          f"{int(out['adjudicated'].astype(bool).sum())} author-adjudicated)")

    breakdown = exclusion_breakdown(out)
    print(f"\nexclusion reasons (n = {int(breakdown['n'].sum())}):")
    for _, row in breakdown.iterrows():
        print(f"  {row['reason']:22s} {int(row['n']):6d}  {100 * row['share']:5.1f}%")


if __name__ == "__main__":
    main()

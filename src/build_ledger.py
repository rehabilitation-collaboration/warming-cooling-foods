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

import json
import sys
from collections import Counter

import pandas as pd

from .definitions import DATA_DIR
from .dump_ledger_batches import (
    BATCH_INDEX_CSV,
    WORK_DIR,
    batch_path,
    load_candidates,
)
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

# What a coder CSV carries, plus the batch id this module attaches from the
# file name. Used to shape the empty frame for a coder that has not started.
COLUMNS = ["source_id", "candidate", "label", "reason", "sublabels",
           "food_ja", "food_en", "direction", "quote", "batch_id"]

# --- author rulings -------------------------------------------------------
# The author's decisions live in ``data/ledger_rulings.csv``
# (source_id, candidate, final_label, reason, food_ja, food_en, direction,
# quote, rationale, batch) and that file *is* their provenance, as
# ``screening_rulings.csv`` is for Axis B. Externalised from the start rather
# than grown as a dict literal first (project decision D41): the review that
# asked for Axis A's judgments to be auditable gets a file it can read.
RULINGS_CSV = DATA_DIR / "ledger_rulings.csv"


def _key(source_id, candidate) -> tuple[str, str]:
    """A candidate's identity, normalised the way ``ledger.py`` normalises it.

    ``_coder_frame`` strips both fields before keying, so anything that has to
    meet a coder's row on that key has to strip too. The rulings file is the one
    input a person types, and it carries free-text Japanese spans; a stray space
    there would otherwise produce a key that matches nothing.
    """
    return (str(source_id).strip(), str(candidate).strip())


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
        rulings[_key(row["source_id"], row["candidate"])] = ruling
    return rulings


def check_rulings_land(recon: pd.DataFrame, rulings: dict) -> None:
    """Fail loudly on a ruling whose key matches no candidate.

    ``adjudicate`` raises when a candidate that needs a ruling has none. It
    cannot raise for the reverse — a ruling that reaches nothing — and the case
    that matters is precisely the one it stays quiet about: an override filed on
    a row where *both coders agreed*. There ``_needs_ruling`` is False, so a key
    that fails to match simply falls through to the coders' shared label, and
    the author's decision disappears without a word.

    That override is the only instrument for a judgment the coders got wrong in
    the same direction (D42), so losing one silently is the worst outcome this
    build step can produce.
    """
    known = {_key(s, c) for s, c in zip(recon["source_id"], recon["candidate"])}
    stray = sorted(k for k in rulings if k not in known)
    if stray:
        raise ValueError(
            f"{len(stray)} ruling(s) in {RULINGS_CSV.name} match no candidate: "
            f"{stray[:5]} — a ruling that reaches nothing was never applied"
        )


def load_coder(coder: str) -> pd.DataFrame:
    """Concatenate one coder's per-batch CSVs from data/ledger_work/<coder>/.

    The batch id is not a column a coder writes — it is the file name it was
    told to use — so it is attached here. ``audit_batches`` needs it to check a
    returned batch against the slice of the enumeration it was cut from.
    """
    files = sorted((WORK_DIR / coder).glob("*.csv"))
    if not files:
        # Empty rather than fatal: the coders are dispatched a wave at a time,
        # and a wave is often all c1 or all c2. Dying here would mean the batch
        # audit — the whole reason to run this between waves — could not fire
        # until both coders had returned something.
        return pd.DataFrame(columns=COLUMNS)
    frames = []
    for path in files:
        df = pd.read_csv(path, dtype=str)
        df["batch_id"] = path.stem
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def assigned_candidates(batch_id: str) -> list[str]:
    """The candidate spans a batch actually handed its coder.

    Read from the batch file rather than reconstructed from ``candidates.csv``,
    because the batch file *is* what the agent was given: if the two ever
    disagree, the coder's answer belongs to the batch file.
    """
    batch = json.loads(batch_path(batch_id).read_text(encoding="utf-8"))
    return [c["candidate"] for c in batch["candidates"]]


def audit_batches(coded: pd.DataFrame, coder: str) -> list[str]:
    """Check what one coder returned against the batches it was handed.

    Returns the batch ids that have not come back yet — pending work, not an
    error. Three things *are* errors:

    - a batch id absent from ``batch_index.csv``: the coder wrote to a name
      nobody assigned, so those rows belong to no partition;
    - a returned batch whose candidates are not exactly the ones it was handed;
    - a row whose ``source_id`` is not the batch's own.

    Comparing the multiset of candidates rather than only its size is what makes
    this worth running per batch. A batch that returns one candidate twice and
    another not at all has the right row count, and ``_coder_frame`` will later
    collapse the duplicate with a warning on stderr, so the dropped candidate
    reaches the end of the run looking like an exclusion nobody questioned. The
    comparison is byte-exact because that is what the coder was told to return;
    a coder that normalises a span has changed the key the ledger is built on.
    """
    index = pd.read_csv(BATCH_INDEX_CSV)
    source_of = {str(b): str(s) for b, s in zip(index["batch_id"], index["source_id"])}
    got = {str(b): rows for b, rows in coded.groupby("batch_id")}

    unknown = sorted(set(got) - set(source_of))
    if unknown:
        raise ValueError(
            f"coder {coder} returned batch(es) absent from "
            f"{BATCH_INDEX_CSV.name}: {unknown}"
        )

    problems: list[str] = []
    for batch_id, rows in sorted(got.items()):
        assigned = Counter(assigned_candidates(batch_id))
        returned = Counter(rows["candidate"].astype(str))
        if returned != assigned:
            missing = sorted((assigned - returned).elements())
            extra = sorted((returned - assigned).elements())
            problems.append(
                f"{batch_id}: returned {sum(returned.values())} rows for "
                f"{sum(assigned.values())} candidates; "
                f"{len(missing)} missing (e.g. {missing[:3]}), "
                f"{len(extra)} unassigned (e.g. {extra[:3]})"
            )
        stray = sorted(set(rows["source_id"].astype(str)) - {source_of[batch_id]})
        if stray:
            problems.append(
                f"{batch_id}: rows carry source_id {stray}, "
                f"but the batch is {source_of[batch_id]!r}"
            )
    if problems:
        raise ValueError(
            f"coder {coder} returned {len(problems)} batch(es) that do not match "
            "what they were handed:\n  " + "\n  ".join(problems)
        )
    return sorted(set(source_of) - set(got))


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
    total = len(pd.read_csv(BATCH_INDEX_CSV))
    if c1.empty and c2.empty:
        sys.exit(
            f"neither coder has returned anything under {WORK_DIR} — 0 of "
            f"{total} batches judged.\nThe batches are already generated; what "
            f"is missing is the coding. Send a coder agent per batch using the "
            f"prompt in data/ledger_coder_prompt.md (substitute {{N}} and "
            f"{{BATCH}}), then run this again."
        )
    pending = {"c1": audit_batches(c1, "c1"), "c2": audit_batches(c2, "c2")}
    if report_pending(pending, total):
        sys.exit("\nledger not written: the enumeration is not fully judged yet")

    recon = reconcile(c1.to_dict("records"), c2.to_dict("records"))
    counts = recon["status"].value_counts().to_dict()
    print(f"\nreconciled {len(recon)} (source_id, candidate) candidates: {counts}")

    k = cohen_kappa(recon)
    print(f"Cohen's kappa = {k['kappa']:.4f} on {k['n_both']} co-coded candidates "
          f"(observed agreement {k['po']:.4f})")

    rulings = load_rulings()
    check_rulings_land(recon, rulings)
    adjudicated = adjudicate(recon, rulings)
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

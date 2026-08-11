"""Split the Axis A candidate enumeration into the batches the coders read.

Each coder agent receives one batch as
``data/ledger_work/candidates_<source>_b<i>.json``::

    {"batch_id": "kawashimaya_b2", "source_id": "kawashimaya",
     "source_text": "<the source's full body text>",
     "candidates": [{"line_no", "candidate", "paths"}]}

**Why the whole source text goes in every batch.** Only 38.7% of the 18,659
candidates sit on a line that itself carries thermal vocabulary; 59.7% carry it
only in the enclosing heading, and a further 1.6% only in an adjacent line
(``THERM_WINDOW``). A span shown on its own — or even with its line — therefore
cannot be assigned a direction for roughly six candidates in ten, and the
line-straddling and in-scope-prose blind spots found in RD-1b need the
neighbouring lines to resolve at all. The cost of carrying the text is small:
the whole frame is 93,812 characters and the largest source is 10,615, so
repeating a source across its batches is cheaper than any partial-context scheme
that loses judgments.

**Why the batch carries no ``heading`` or ``line``.** The enumeration has both,
and both mislead a coder who reads them as "the section this span sits under"
and "the line this span came from". ``heading`` is the last *thermal* short line
seen, which is what opens an extraction scope — not the nearest section title:
in kawashimaya it is a call-to-action (`温活に関する商品はこちら`) for a third of
the batch, and a list item (`冷やし中華`) governs the warming-recipe section.
``line`` is the line the emission started on, so a ``wrapped`` candidate — one
recovered from two joined lines — reports a line that does not contain it
(`かき氷` reports `冷たい食べ物`). Both canary coders independently flagged this
and judged against ``source_text`` instead. Neither field is dropped from the
enumeration, where they record how the span was found; they are simply not shown
to the coder, whose context is the text itself. ``line_no`` stays, as the
position to read from, with ``paths`` naming how the span was produced.

Batching rules:

- **A line group is never split.** The extractor emits overlapping granularities
  from one line (5.82 candidates per line on average, up to 75), and judging one
  granularity without its siblings would break the ``duplicate`` and
  ``fragment`` codes of ``coding_protocol.md`` §9.4.
- **Batches stay inside one source**, so a coder holds one document in mind.
- **Even split**: a source of *n* candidates becomes ``ceil(n / target)`` batches
  of roughly equal size, rather than filling batches to ``target`` and leaving a
  short tail — an even split keeps every agent's workload comparable.
- ``target`` defaults to 400, the per-assignment size used for Axis B screening
  (project decision D40), so both axes are judged in comparable portions.

Every batch write is followed by a check that the batches partition the
enumeration exactly — same multiset of (source_id, candidate) keys, no
duplicates, nothing dropped — which fails loudly rather than letting a silently
unassigned candidate look like an exclusion.

Run: ``python3 -m src.dump_ledger_batches`` (``--target=N``, or source ids to
limit which sources are written).
"""

from __future__ import annotations

import json
import math
import sys

import pandas as pd

from .definitions import DATA_DIR, SOURCES_RAW_DIR
from .extract_candidates import CANDIDATES_CSV, extract_all, dedupe, write_candidates

WORK_DIR = DATA_DIR / "ledger_work"
BATCH_INDEX_CSV = WORK_DIR / "batch_index.csv"
FIELDS = ["line_no", "candidate", "paths"]
DEFAULT_TARGET = 400


def load_candidates(path=CANDIDATES_CSV) -> pd.DataFrame:
    """Read the enumeration, generating it first if it has not been written."""
    if not path.exists():
        return write_candidates(dedupe(extract_all()), path)
    df = pd.read_csv(path, dtype={"source_id": str, "candidate": str})
    df["line_no"] = df["line_no"].astype(int)
    for col in ("paths", "heading", "line"):
        df[col] = df[col].fillna("").astype(str)
    return df


def source_text(source_id: str) -> str:
    """The source's extracted body text — the same input the enumeration read."""
    path = SOURCES_RAW_DIR / f"{source_id}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — Route D's input is git-ignored; restore it from "
            "the backup rather than re-fetching (the page may have changed)."
        )
    return path.read_text(encoding="utf-8")


def plan_batches(candidates: pd.DataFrame, target: int = DEFAULT_TARGET) -> list[list[int]]:
    """Group one source's line numbers into batches of about ``target`` rows.

    Returns a list of line-number lists, in reading order. Line groups are kept
    whole, so a batch overshoots ``target`` rather than splitting the line that
    crosses it; the last batch takes whatever is left.
    """
    sizes = candidates.groupby("line_no").size().sort_index()
    total = int(sizes.sum())
    if total == 0:
        return []
    k = max(1, math.ceil(total / target))
    per = total / k
    batches: list[list[int]] = []
    current: list[int] = []
    running = 0
    for line_no, count in sizes.items():
        # Start a new batch once this one is full, unless we are already filling
        # the last batch — everything remaining belongs there.
        if current and running + count > per and len(batches) < k - 1:
            batches.append(current)
            current, running = [], 0
        current.append(int(line_no))
        running += int(count)
    if current:
        batches.append(current)
    return batches


def build_batch(candidates: pd.DataFrame, source_id: str, batch_id: str, lines: list[int]) -> dict:
    """One batch: the source's full text plus the candidates on ``lines``."""
    rows = candidates[candidates["line_no"].isin(set(lines))].sort_values(
        ["line_no", "candidate"]
    )
    return {
        "batch_id": batch_id,
        "source_id": source_id,
        "source_text": source_text(source_id),
        "candidates": [
            {f: (int(r[f]) if f == "line_no" else str(r[f])) for f in FIELDS}
            for _, r in rows.iterrows()
        ],
    }


def batch_path(batch_id: str):
    return WORK_DIR / f"candidates_{batch_id}.json"


def verify_partition(candidates: pd.DataFrame, batches: list[dict]) -> None:
    """Fail loudly unless the batches partition the enumeration exactly.

    An unassigned candidate is the failure mode this guards: it never reaches a
    coder, so it acquires no label, and a ledger that is silently short of rows
    is indistinguishable from one whose coders excluded those rows. Two
    forgotten sources in one session (第26) is why this runs on every write.
    """
    assigned: list[tuple[str, str]] = []
    for batch in batches:
        assigned += [
            (batch["source_id"], c["candidate"]) for c in batch["candidates"]
        ]
    expected = list(zip(candidates["source_id"], candidates["candidate"]))

    dups = [k for k, n in pd.Series(assigned).value_counts().items() if n > 1]
    if dups:
        raise ValueError(
            f"{len(dups)} candidates assigned to more than one batch, e.g. {dups[:5]}"
        )
    missing = set(expected) - set(assigned)
    if missing:
        sample = sorted(missing)[:5]
        raise ValueError(
            f"{len(missing)} candidates were assigned to no batch, e.g. {sample}"
        )
    extra = set(assigned) - set(expected)
    if extra:
        raise ValueError(
            f"{len(extra)} assigned candidates are not in the enumeration, "
            f"e.g. {sorted(extra)[:5]}"
        )


def main(only: list[str] | None = None, target: int = DEFAULT_TARGET) -> None:
    candidates = load_candidates()
    sources = only or sorted(candidates["source_id"].unique())
    unknown = set(sources) - set(candidates["source_id"].unique())
    if unknown:
        raise ValueError(f"no candidates for source(s): {sorted(unknown)}")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    batches: list[dict] = []
    index: list[dict] = []
    for source_id in sources:
        sub = candidates[candidates["source_id"] == source_id]
        for i, lines in enumerate(plan_batches(sub, target), 1):
            batch_id = f"{source_id}_b{i}"
            batch = build_batch(sub, source_id, batch_id, lines)
            batches.append(batch)
            index.append(
                {
                    "batch_id": batch_id,
                    "source_id": source_id,
                    "n_candidates": len(batch["candidates"]),
                    "first_line_no": min(lines),
                    "last_line_no": max(lines),
                    "n_line_groups": len(lines),
                }
            )

    # Verify before writing: a partition error means the plan is wrong, and
    # half-written batches would be worse than none.
    scope = candidates[candidates["source_id"].isin(set(sources))]
    verify_partition(scope, batches)

    for batch in batches:
        batch_path(batch["batch_id"]).write_text(
            json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    idx = pd.DataFrame(index)
    idx.to_csv(BATCH_INDEX_CSV, index=False)

    print(
        f"wrote {len(batches)} batches covering {len(scope)} candidates "
        f"({idx['n_line_groups'].sum()} line groups) under {WORK_DIR}"
    )
    print(
        f"batch size: min {idx['n_candidates'].min()} / "
        f"median {idx['n_candidates'].median():.0f} / max {idx['n_candidates'].max()}"
    )
    print(f"index: {BATCH_INDEX_CSV}")


if __name__ == "__main__":  # pragma: no cover - thin CLI
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    size = next(
        (int(f.split("=")[1]) for f in flags if f.startswith("--target=")),
        DEFAULT_TARGET,
    )
    main(args or None, target=size)

"""Split data/l2_records.csv into the per-food JSON batches the coders read.

Each coder agent is given one food at a time as
``data/screening_work/records_<food>.json``::

    {"food_key": "ginger", "records": [{"pmid", "title", "pubtypes", "abstract"}]}

so it sees titles and abstracts only — no counts, no other coder's labels, no
golden set. The batches are derived from ``l2_records.csv`` (written by
``fetch_l2_records.py``), not re-fetched, so a re-run cannot silently change
what was coded. Both the file and its inputs are git-ignored raw content; the
published artefact is ``screening.csv``.

Run: ``python3 -m src.dump_screening_batches`` (add food keys to limit).
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from .definitions import DATA_DIR
from .screening import L2_RECORDS_CSV, SCREENING_CSV

WORK_DIR = DATA_DIR / "screening_work"
FIELDS = ["pmid", "title", "pubtypes", "abstract"]


def batch_path(food_key: str):
    """Per-food batch file; spaces become underscores ("chili pepper")."""
    return WORK_DIR / f"records_{food_key.replace(' ', '_')}.json"


def judged_pairs() -> set[tuple[str, str]]:
    """(food_key, pmid) pairs that already carry a two-coder judgment.

    Widening the effect vocabulary (2026-08-08) grew L2 from 2,887 to 12,437
    records while leaving the inclusion protocol untouched, so the records that
    were already coded must be reused verbatim rather than re-coded: a second,
    independent pass over the same record would create two judgments for one
    (food, pmid), and ``reconcile`` outer-joins on exactly that key — duplicates
    there inflate the merge instead of failing.
    """
    if not SCREENING_CSV.exists():
        return set()
    done = pd.read_csv(SCREENING_CSV, dtype=str)
    return set(zip(done["food_key"], done["pmid"]))


def drop_judged(records: pd.DataFrame) -> pd.DataFrame:
    """Keep only records with no existing judgment."""
    done = judged_pairs()
    if not done:
        return records
    keep = [
        (f, p) not in done
        for f, p in zip(records["food_key"], records["pmid"])
    ]
    return records[pd.Series(keep, index=records.index)]


def build_batch(records: pd.DataFrame, food_key: str) -> dict:
    rows = records[records["food_key"] == food_key]
    return {
        "food_key": food_key,
        "records": [
            {f: ("" if pd.isna(r[f]) else str(r[f])) for f in FIELDS}
            for _, r in rows.iterrows()
        ],
    }


def _write(path, food_key: str, rows: list[dict]) -> None:
    path.write_text(
        json.dumps({"food_key": food_key, "records": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def main(
    only: list[str] | None = None,
    max_records: int = 0,
    new_only: bool = False,
) -> None:
    """Write one batch per food, splitting any food over ``max_records``.

    A split food becomes ``records_<food>_p1.json``, ``_p2.json``, … and the
    unsplit file is removed so no agent can read the same records twice. The
    food_key inside every part stays the same, so the parts recombine on their
    own downstream.

    ``new_only`` restricts the batches to records that have no judgment in
    ``screening.csv`` yet — the incremental pass after a query widening.
    """
    records = pd.read_csv(L2_RECORDS_CSV, dtype=str)
    if new_only:
        before = len(records)
        records = drop_judged(records)
        print(f"new-only: {before:,} records → {len(records):,} unjudged "
              f"({before - len(records):,} reused from screening.csv)")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    foods = only or sorted(records["food_key"].unique())
    total = 0
    written = 0
    for food in foods:
        rows = build_batch(records, food)["records"]
        if not rows:
            print(f"[warn] no L2 records for {food!r}, skipped", file=sys.stderr)
            continue
        total += len(rows)
        if max_records and len(rows) > max_records:
            for i, start in enumerate(range(0, len(rows), max_records), 1):
                part = batch_path(food).with_name(
                    batch_path(food).stem + f"_p{i}.json"
                )
                _write(part, food, rows[start:start + max_records])
                written += 1
            batch_path(food).unlink(missing_ok=True)
            print(f"  split {food}: {len(rows)} records over {i} parts")
        else:
            _write(batch_path(food), food, rows)
            written += 1
    print(f"wrote {written} batch files, {total} records, under {WORK_DIR}")


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cap = next((int(f.split("=")[1]) for f in flags if f.startswith("--max=")), 0)
    main(args or None, max_records=cap, new_only="--new-only" in flags)

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
from .screening import L2_RECORDS_CSV

WORK_DIR = DATA_DIR / "screening_work"
FIELDS = ["pmid", "title", "pubtypes", "abstract"]


def batch_path(food_key: str):
    """Per-food batch file; spaces become underscores ("chili pepper")."""
    return WORK_DIR / f"records_{food_key.replace(' ', '_')}.json"


def build_batch(records: pd.DataFrame, food_key: str) -> dict:
    rows = records[records["food_key"] == food_key]
    return {
        "food_key": food_key,
        "records": [
            {f: ("" if pd.isna(r[f]) else str(r[f])) for f in FIELDS}
            for _, r in rows.iterrows()
        ],
    }


def main(only: list[str] | None = None) -> None:
    records = pd.read_csv(L2_RECORDS_CSV, dtype=str)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    foods = only or sorted(records["food_key"].unique())
    total = 0
    for food in foods:
        batch = build_batch(records, food)
        if not batch["records"]:
            print(f"[warn] no L2 records for {food!r}, skipped", file=sys.stderr)
            continue
        batch_path(food).write_text(
            json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        total += len(batch["records"])
    print(f"wrote {len(foods)} batches, {total} records, under {WORK_DIR}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)

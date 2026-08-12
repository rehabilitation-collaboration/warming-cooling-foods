"""Split the included L2 records into the batches the §8 coders read.

Protocol §8 runs only over records already settled as ``include`` in
``screening.csv``. Each batch is JSON::

    {"batch": "p1", "records": [{"pmid", "food_key", "title", "pubtypes",
                                 "abstract", "sublabels"}]}

``sublabels`` is the §3 sub-label set already settled for the record (``review``,
``constituent``, ``supradose``, ``confounded``), which §8's boundary rules refer
to by name. It is part of the screening judgment this pass builds on, not another
coder's opinion about the question at issue, so withholding it would only make
the coder re-derive it. Withheld are the other coder's labels, the reconciliation
code and the golden set.

Records are ordered by food so that a food's records stay together in one batch,
and the record text comes from ``l2_records.csv`` rather than being re-fetched,
so a re-run cannot silently change what was coded.

Run: ``python3 -m src.dump_claim_directed_batches [--parts=4] [--canary]``
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from .definitions import DATA_DIR
from .screening import INCLUDE, L2_RECORDS_CSV, SCREENING_CSV

WORK_DIR = DATA_DIR / "screening_work"
BATCH_DIR = WORK_DIR / "cd_batches"
FIELDS = ["pmid", "food_key", "title", "pubtypes", "abstract", "sublabels"]

# The canary stresses the boundary rules rather than sampling at random: one
# stratum per §8 boundary clause, so a rule that cannot be applied shows up
# before 298 records have been coded under it (the D55 canary pattern).
CANARY_STRATA = (
    ("review", lambda d: d["sublabels"].str.contains("review")),
    ("constituent", lambda d: d["sublabels"].str.contains("constituent")),
    ("confounded", lambda d: d["sublabels"].str.contains("confounded")),
    ("no-abstract", lambda d: d["abstract"].str.strip() == ""),
    ("multi-food", lambda d: d["pmid"].duplicated(keep=False)),
    ("plain", lambda d: d["sublabels"] == ""),
)
CANARY_PER_STRATUM = 4


def included_records() -> pd.DataFrame:
    """The included (food_key, pmid) rows, joined to their title and abstract.

    Fails loudly when a judgment has no record text: §8 cannot be coded from the
    key alone, and a silently dropped record would shrink the denominator of the
    sensitivity analysis without saying so.
    """
    screening = pd.read_csv(SCREENING_CSV, dtype=str)
    included = screening[screening["final_label"] == INCLUDE].copy()
    included["sublabels"] = included["sublabels"].fillna("")
    records = pd.read_csv(L2_RECORDS_CSV, dtype=str)
    merged = included.merge(
        records[["pmid", "food_key", "title", "pubtypes", "abstract"]],
        on=["pmid", "food_key"],
        how="left",
    )
    orphan = merged[merged["title"].isna()]
    if not orphan.empty:
        raise ValueError(
            f"{len(orphan)} included records have no row in {L2_RECORDS_CSV.name}: "
            f"{sorted(set(zip(orphan.food_key, orphan.pmid)))[:5]}"
        )
    for col in ("title", "pubtypes", "abstract"):
        merged[col] = merged[col].fillna("")
    return merged.sort_values(["food_key", "pmid"]).reset_index(drop=True)


def canary_sample(records: pd.DataFrame, per_stratum: int = CANARY_PER_STRATUM):
    """One slice per boundary clause, deduplicated, order deterministic."""
    picked: list[int] = []
    for _, predicate in CANARY_STRATA:
        hits = records[predicate(records)]
        for idx in hits.index[:per_stratum]:
            if idx not in picked:
                picked.append(idx)
    return records.loc[picked]


def _write(name: str, rows: pd.DataFrame) -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "batch": name,
        "records": [
            {f: str(r[f]) for f in FIELDS} for _, r in rows.iterrows()
        ],
    }
    path = BATCH_DIR / f"claim_directed_{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  wrote {path.name}: {len(rows)} records")


def main(parts: int = 4, canary: bool = False) -> None:
    records = included_records()
    print(f"{len(records)} included records over {records['food_key'].nunique()} foods")
    if canary:
        sample = canary_sample(records)
        _write("canary", sample)
        print(f"canary: {len(sample)} records across {len(CANARY_STRATA)} strata")
        return
    size = -(-len(records) // parts)  # ceiling, so the last part is the short one
    for i, start in enumerate(range(0, len(records), size), 1):
        _write(f"p{i}", records.iloc[start:start + size])


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    n = next((int(f.split("=")[1]) for f in flags if f.startswith("--parts=")), 4)
    main(parts=n, canary="--canary" in flags)

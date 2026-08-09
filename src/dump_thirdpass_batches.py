"""Build the input batches for the adversarial third screening pass.

The two-coder pass plus author adjudication leaves one failure mode untested: a
record both coders excluded for the same wrong reason. No agreement statistic
can surface it, and because the primary outcome is binary a single such record
flips a whole food's result. The third pass tests it by inverting the
instruction — every record here was excluded; find the ones where that was
wrong — so its input is the *excluded* records of the foods that stand to flip.

Scope is recomputed rather than fixed: the foods at risk are the core-belief
foods (>= 3 Tier-1 sources) currently at L2' = 0. That set is a function of the
current ledger, and it moved when the effect vocabulary was widened (37 foods
under the four-term query, 25 now), which is why the earlier pass's 419 records
cannot be reused. Foods whose query returned nothing have no record to re-read;
their zero is a retrieval question rather than a screening one, and they are
reported here rather than silently absent.

Batches carry title and abstract only — no counts, no existing label, no reason
code, no golden set — and are read from ``l2_records.csv`` rather than
re-fetched, so a re-run cannot change what was judged.

Run: ``python3 -m src.dump_thirdpass_batches`` (from the project root).
"""

from __future__ import annotations

import json

import pandas as pd

from .analysis import _read_counts, prepare_scatter_data
from .claim_mapping import load_claims, load_sources
from .definitions import DATA_DIR
from .evidence_mapping import CORE_MIN_SOURCES
from .screening import L2_RECORDS_CSV, SCREENING_CSV

BATCH_DIR = DATA_DIR / "screening_work" / "c3_batches"
FIELDS = ["pmid", "title", "pubtypes", "abstract"]


def batch_path(food_key: str):
    """Per-food batch file; spaces become underscores ("chili pepper")."""
    return BATCH_DIR / f"records_{food_key.replace(' ', '_')}.json"


def core_zero_foods(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """The core-belief foods currently at L2′ = 0, widest coverage first.

    ``l2_raw`` is carried through so the caller can separate the foods with
    nothing to re-read from the ones with candidates.
    """
    if frame is None:
        frame = prepare_scatter_data(load_claims(), load_sources(), _read_counts())
    zero = frame[
        (frame["n_sources"] >= CORE_MIN_SOURCES) & (frame["l2_screened"] == 0)
    ].copy()
    return zero.sort_values(
        ["n_sources", "l2_raw"], ascending=[False, False]
    ).reset_index(drop=True)


def thirdpass_candidates(foods: list[str]) -> pd.DataFrame:
    """Every excluded record belonging to ``foods``, with title and abstract.

    Includes are deliberately not offered to the third pass: its instruction is
    that everything in front of it was excluded, and slipping an include in
    would make that instruction false. Raises if the ledger holds an include for
    a food this function was asked about, since that would mean the food is not
    at L2′ = 0 and the caller's scope is stale.
    """
    ledger = pd.read_csv(SCREENING_CSV, dtype=str)
    ledger = ledger[ledger["food_key"].isin(foods)]

    kept = ledger[ledger["final_label"] == "include"]
    if len(kept):
        raise ValueError(
            "asked for third-pass candidates on foods that already have an "
            f"include: {sorted(set(kept['food_key']))}"
        )

    records = pd.read_csv(L2_RECORDS_CSV, dtype=str)
    merged = ledger[["food_key", "pmid"]].merge(
        records[["food_key", "pmid", *[c for c in FIELDS if c != "pmid"]]],
        on=["food_key", "pmid"],
        how="left",
    )
    missing = merged[merged["title"].isna()]
    if len(missing):
        raise ValueError(
            f"{len(missing)} ledger rows have no record in {L2_RECORDS_CSV.name}; "
            "re-run fetch_l2_records before dumping batches"
        )
    return merged


def write_batches(candidates: pd.DataFrame) -> tuple[int, int]:
    """Write one JSON batch per food. Returns (files, records)."""
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    files = 0
    for food, grp in candidates.groupby("food_key"):
        payload = {
            "food_key": food,
            "records": grp[FIELDS].fillna("").to_dict(orient="records"),
        }
        batch_path(food).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files += 1
    return files, len(candidates)


def main() -> None:
    zero = core_zero_foods()
    has_records = zero[zero["l2_raw"] > 0]
    no_records = zero[zero["l2_raw"] == 0]

    candidates = thirdpass_candidates(list(has_records["food_key"]))
    files, total = write_batches(candidates)

    print(f"core-zero foods: {len(zero)} (>= {CORE_MIN_SOURCES} Tier-1 sources, L2' = 0)")
    print(f"  with retrieved records: {len(has_records)}  -> {total} records in {files} batches")
    print(f"  with no L2 hit at all:  {len(no_records)}  -> nothing to re-screen: "
          f"{', '.join(no_records['food_key']) or 'none'}")
    print(f"batches under {BATCH_DIR}")
    for _, r in has_records.iterrows():
        n = int((candidates["food_key"] == r["food_key"]).sum())
        print(f"  {r['food_key']:16s} n_sources={int(r['n_sources']):2d} {r['direction']:9s} "
              f"records={n:3d}")


if __name__ == "__main__":
    main()

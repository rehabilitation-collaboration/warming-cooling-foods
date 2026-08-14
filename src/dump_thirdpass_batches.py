"""Build the input batches for the adversarial third screening pass.

The two-coder pass plus author adjudication leaves one failure mode untested: a
record both coders excluded for the same wrong reason. No agreement statistic
can surface it, and because the primary outcome is binary a single such record
flips a whole food's result. The third pass tests it by inverting the
instruction — every record here was excluded; find the ones where that was
wrong — so its input is the *excluded* records of the foods that stand to flip.

The pass first ran (2026-08-09) over the core-belief foods (>= 3 Tier-1 sources)
then at L2' = 0. Screening protocol §9 removes that coverage threshold: coverage
is the analysis's explanatory variable, so re-reading only the high-coverage
zeros would make the detection rate for misclassified outcomes a function of the
variable under test. ``rescreen_scope`` therefore takes every zero food with
records to re-read and subtracts the ones a pass has already read, and writes to
its own batch directory so the earlier pass's inputs stay untouched.

Foods whose query returned nothing have no record to re-read; their zero is a
retrieval question rather than a screening one, and they are reported here
rather than silently absent.

Batches carry title and abstract only — no counts, no existing label, no reason
code, no golden set — and are read from ``l2_records.csv`` rather than
re-fetched, so a re-run cannot change what was judged.

Run: ``python3 -m src.dump_thirdpass_batches`` (from the project root).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .analysis import _read_counts, prepare_scatter_data
from .build_thirdpass import THIRDPASS_CSV
from .claim_mapping import load_claims, load_sources
from .definitions import DATA_DIR
from .evidence_mapping import CORE_MIN_SOURCES
from .screening import L2_RECORDS_CSV, SCREENING_CSV

BATCH_DIR = DATA_DIR / "screening_work" / "c3_batches"
EXT_BATCH_DIR = DATA_DIR / "screening_work" / "c3_ext_batches"
FIELDS = ["pmid", "title", "pubtypes", "abstract"]

# One food (lamb, 620 records) holds nearly half the §9 scope, and a coder asked
# for that many verdicts in one response runs into the output ceiling — a
# truncated batch is a silently short pass, which is the one outcome this check
# cannot afford. Splitting is a delivery decision and touches no judgment: every
# record is still read exactly once, under the same instruction.
MAX_BATCH_RECORDS = 200


def batch_path(
    food_key: str, batch_dir: Path | None = None, span: tuple[int, int] | None = None
) -> Path:
    """Per-food batch file; spaces become underscores ("chili pepper").

    ``span`` names the record range when a food was split, so the filenames sort
    in reading order and a missing chunk is visible.
    """
    stem = f"records_{food_key.replace(' ', '_')}"
    if span is not None:
        stem += f"_{span[0]:03d}_{span[1]:03d}"
    return (batch_dir or BATCH_DIR) / f"{stem}.json"


def core_zero_foods(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """The core-belief foods currently at L2′ = 0, widest coverage first.

    The 2026-08-09 pass's scope, kept so that pass remains reproducible. §9
    supersedes it for new work; see ``rescreen_scope``.

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


def already_read_foods() -> set[str]:
    """Food keys some third pass has already re-read, from its published ledger."""
    return set(pd.read_csv(THIRDPASS_CSV, dtype=str)["food_key"])


def rescreen_scope(
    frame: pd.DataFrame | None = None, *, already_read: set[str] | None = None
) -> pd.DataFrame:
    """Every zero food with records to re-read that no third pass has read yet.

    Protocol §9: no coverage threshold. Foods already read are subtracted rather
    than re-read, because a second reading of a settled record would replace a
    judgment instead of testing one.
    """
    if frame is None:
        frame = prepare_scatter_data(load_claims(), load_sources(), _read_counts())
    if already_read is None:
        already_read = already_read_foods()
    zero = frame[(frame["l2_screened"] == 0) & (frame["l2_raw"] > 0)]
    out = zero[~zero["food_key"].isin(already_read)].copy()
    return out.sort_values(
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


def write_batches(
    candidates: pd.DataFrame,
    *,
    batch_dir: Path | None = None,
    max_records: int | None = None,
) -> tuple[int, int]:
    """Write one JSON batch per food, splitting past ``max_records``.

    Returns (files, records).
    """
    target = batch_dir or BATCH_DIR
    target.mkdir(parents=True, exist_ok=True)
    files = 0
    for food, grp in candidates.groupby("food_key"):
        if max_records is None or len(grp) <= max_records:
            spans = [(None, grp)]
        else:
            spans = [
                ((i, min(i + max_records, len(grp)) - 1), grp.iloc[i : i + max_records])
                for i in range(0, len(grp), max_records)
            ]
        for span, chunk in spans:
            payload = {
                "food_key": food,
                "records": chunk[FIELDS].fillna("").to_dict(orient="records"),
            }
            if span is not None:
                payload["range"] = f"{span[0]}-{span[1]}"
            batch_path(food, target, span).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            files += 1
    return files, len(candidates)


def main() -> None:
    frame = prepare_scatter_data(load_claims(), load_sources(), _read_counts())
    read_already = already_read_foods()
    scope = rescreen_scope(frame, already_read=read_already)

    zero = frame[frame["l2_screened"] == 0]
    nothing_to_read = zero[zero["l2_raw"] == 0]

    candidates = thirdpass_candidates(list(scope["food_key"]))
    files, total = write_batches(
        candidates, batch_dir=EXT_BATCH_DIR, max_records=MAX_BATCH_RECORDS
    )

    print(f"primary frame: {len(frame)} foods, {len(zero)} at L2' = 0")
    print(f"  already re-screened by an earlier pass: {len(read_already)}")
    print(f"  no L2 hit at all, nothing to re-screen:  {len(nothing_to_read)}")
    print(f"  in scope under protocol §9:              {len(scope)}"
          f"  -> {total} records in {files} batches")
    print(f"batches under {EXT_BATCH_DIR}")
    for _, r in scope.iterrows():
        n = int((candidates["food_key"] == r["food_key"]).sum())
        print(f"  {r['food_key']:16s} n_sources={int(r['n_sources']):2d} {r['direction']:9s} "
              f"records={n:3d}")


if __name__ == "__main__":
    main()

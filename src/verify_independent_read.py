"""Check the candidate enumeration against an independent full read (Route D, RD-1b).

`verify_candidate_recall.py` measures recall against `claims.csv`, and that is a
necessary but not a sufficient check: `claims.csv` is itself suspected of being
incomplete — that suspicion is why Route D exists — so it cannot certify that a
food no coder ever recorded would be found.

This module supplies the reference the coded rows cannot. One agent per source
read the source text in full against `coding_protocol.md` §1–§8 and listed every
food the source assigns a direction to, with the enumeration, the extractor and
`claims.csv` all withheld from it. Its answers live in `data/independent_read/`.

Three things are reported per source:

``grounding``
    Does each listed food occur verbatim in the source, on the line cited? A
    read that fails here is not usable as a reference at all.
``coverage``
    Does the enumeration surface each food the independent read found? This is
    the claims-independent recall figure.
``ledger gap``
    What the independent read found that `claims.csv` does not carry, and the
    reverse. These are candidates for Route D's re-coding, not verdicts: the
    author adjudicates each one against the source.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from .definitions import CLAIMS_CSV, DATA_DIR, SOURCES_CSV, SOURCES_RAW_DIR
from .extract_candidates import dedupe, extract_all

INDEPENDENT_READ_DIR = DATA_DIR / "independent_read"


def load_reads(path=INDEPENDENT_READ_DIR) -> pd.DataFrame:
    """One row per (source_id, food_ja) the independent read reported."""
    rows = []
    for f in sorted(path.glob("*.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))
        for item in payload.get("foods", []):
            rows.append(
                {
                    "source_id": payload["source_id"],
                    "food_ja": str(item["food_ja"]).strip(),
                    "direction": item.get("direction", ""),
                    "line_no": item.get("line_no"),
                }
            )
    if not rows:
        raise FileNotFoundError(f"no independent reads under {path}")
    return pd.DataFrame(rows)


def check(reads: pd.DataFrame, candidates: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    """Annotate each independently-read food with grounding, coverage and novelty."""
    by_source_cand = {s: g["candidate"].tolist() for s, g in candidates.groupby("source_id")}
    claims_dir = {
        (r.source_id, str(r.food_ja).strip()): r.direction for r in claims.itertuples()
    }
    # A source may state both directions for one food (jsfca's しょうが is 陽性 in
    # prose and sits in a 陰性 list twice; prezo says 大豆 has no effect and then
    # lists it under warming). The independent read records both per §3, so a
    # clash is only real when NONE of its readings matches the coded one.
    read_dirs: dict[tuple[str, str], set[str]] = {}
    for r in reads.itertuples():
        read_dirs.setdefault((r.source_id, r.food_ja), set()).add(r.direction)
    texts, lines = {}, {}
    for sid in reads["source_id"].unique():
        text = (SOURCES_RAW_DIR / f"{sid}.txt").read_text(encoding="utf-8")
        texts[sid], lines[sid] = text, text.split("\n")

    out = []
    for r in reads.itertuples():
        cited = lines[r.source_id]
        line_ok = (
            isinstance(r.line_no, int)
            and 0 < r.line_no <= len(cited)
            and r.food_ja in cited[r.line_no - 1]
        )
        key = (r.source_id, r.food_ja)
        out.append(
            {
                "source_id": r.source_id,
                "food_ja": r.food_ja,
                "direction": r.direction,
                "verbatim": r.food_ja in texts[r.source_id],
                "line_ok": line_ok,
                "covered": any(r.food_ja in c for c in by_source_cand.get(r.source_id, [])),
                "in_claims": key in claims_dir,
                "direction_clash": key in claims_dir
                and claims_dir[key] not in read_dirs[key],
            }
        )
    return pd.DataFrame(out)


def claims_only(reads: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    """Rows `claims.csv` carries that the independent read did not report."""
    read_keys = {(r.source_id, r.food_ja) for r in reads.itertuples()}
    done = set(reads["source_id"])
    sub = claims[claims["source_id"].isin(done)]
    mask = [
        (r.source_id, str(r.food_ja).strip()) not in read_keys for r in sub.itertuples()
    ]
    return sub[mask][["source_id", "food_ja", "food_en", "direction"]]


def main() -> None:
    reads = load_reads()
    claims = pd.read_csv(CLAIMS_CSV).fillna("")
    candidates = dedupe(extract_all())
    scored = check(reads, candidates, claims)
    missing = claims_only(reads, claims)

    # Name the frame sources that have no read yet. Printing only a count let
    # two sources (gveggie, attaka_navi) sit un-launched unnoticed while the
    # totals still looked healthy.
    frame = set(pd.read_csv(SOURCES_CSV)["source_id"])
    done = sorted(scored["source_id"].unique())
    pending = sorted(frame - set(done))
    print(f"independent reads: {len(done)}/{len(frame)} — {', '.join(done)}")
    if pending:
        print(f"⚠ NOT YET READ ({len(pending)}): {', '.join(pending)}")

    per = (
        scored.groupby("source_id")
        .agg(
            foods=("food_ja", "size"),
            verbatim=("verbatim", "sum"),
            line_ok=("line_ok", "sum"),
            covered=("covered", "sum"),
            new_vs_claims=("in_claims", lambda s: int((~s).sum())),
            dir_clash=("direction_clash", "sum"),
        )
        .assign(coverage=lambda d: (d["covered"] / d["foods"]).round(4))
    )
    print("\n=== per source ===")
    print(per.to_string())
    print(
        f"\nTOTAL foods {len(scored)} | verbatim {scored.verbatim.sum()} | "
        f"line_ok {scored.line_ok.sum()} | "
        f"★coverage {scored.covered.sum()}/{len(scored)} = {scored.covered.mean():.4f}"
    )

    holes = scored[~scored["covered"]]
    print(f"\n=== 抽出の穴 ({len(holes)}) — 独立読解が見つけ、候補に無い ===")
    if not holes.empty:
        print(holes[["source_id", "food_ja", "direction"]].to_string(index=False))

    new = scored[~scored["in_claims"]]
    print(f"\n=== claims.csv に無い ({len(new)}) — Route D の再コーディング候補 ===")
    if not new.empty:
        print(new[["source_id", "food_ja", "direction"]].to_string(index=False))

    print(f"\n=== 独立読解が報告せず claims.csv にある ({len(missing)}) ===")
    if not missing.empty:
        print(missing.to_string(index=False))

    clashes = scored[scored["direction_clash"]]
    print(f"\n=== 方向の食い違い ({len(clashes)}) ===")
    if not clashes.empty:
        print(clashes[["source_id", "food_ja", "direction"]].to_string(index=False))

    ungrounded = scored[~scored["verbatim"]]
    sys.exit(1 if not ungrounded.empty or not holes.empty else 0)


if __name__ == "__main__":
    main()

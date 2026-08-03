"""Inter-coder reconciliation for Axis A hand-coding (reproducibility guard).

Two independent coders code each source's warm/cool food attributions. This
module compares them and reports where they agree, disagree, or one missed a
food the other found. Only disagreements need human adjudication against the
source text; agreement is the reproducibility evidence (reported as Cohen's
kappa on the shared items).

Why beyond ``verify_claims.py``: the grounding check only confirms a food label
exists in the source. It cannot catch a *direction* error (coding coffee warm
when the source says cool), a missed food, or an inclusion-rule slip (coding a
served-cold dish). Two independent codings catch those; the machine only
flags the divergences for a human to settle.

Usage::

    python3 -m src.reconcile_coders coder1.json coder2.json

where each JSON file is a list of {food_en, food_ja, source_id, direction,
quote, condition} objects. ``coder1.json`` is typically exported from the
current build_claims.CLAIMS (the incumbent coding) via --dump-incumbent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .claim_mapping import normalize_food

# Match granularity: a claim is identified by (source_id, food identity,
# condition). Coders may spell food_en differently for the same food, so we
# fold both food_en and food_ja through a shared normalizer to build the
# identity key before comparing DIRECTION.


def _food_identity(food_en: str, food_ja: str) -> str:
    """Stable identity for a food across coders.

    Prefer a normalized food_en (lowercased, stripped); fall back to a
    normalized food_ja. This tolerates English-spelling drift and JA synonym
    drift so that a genuine direction disagreement is not masked as two
    different foods.
    """
    en = (food_en or "").strip().lower()
    if en:
        return en
    return normalize_food((food_ja or "").strip())


def _to_frame(records: list[dict], coder: str) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append(
            {
                "source_id": str(r.get("source_id", "")).strip(),
                "food_id": _food_identity(r.get("food_en", ""), r.get("food_ja", "")),
                "food_en": str(r.get("food_en", "")).strip(),
                "food_ja": str(r.get("food_ja", "")).strip(),
                "condition": str(r.get("condition", "")).strip(),
                f"direction_{coder}": str(r.get("direction", "")).strip(),
                f"quote_{coder}": str(r.get("quote", "")).strip(),
            }
        )
    df = pd.DataFrame(rows)
    # Collapse accidental within-coder duplicates on the identity key, keeping
    # the first direction (a within-coder dup is itself worth surfacing, so we
    # warn).
    key = ["source_id", "food_id", "condition"]
    dups = df[df.duplicated(key, keep=False)]
    if not dups.empty:
        print(
            f"[warn] coder {coder} has {len(dups)} rows on duplicated identity keys:",
            file=sys.stderr,
        )
        print(dups[key + [f"direction_{coder}"]].to_string(index=False), file=sys.stderr)
    return df.drop_duplicates(key, keep="first")


def reconcile(coder1: list[dict], coder2: list[dict]) -> pd.DataFrame:
    """Outer-join the two codings on (source_id, food identity, condition).

    Returns one row per distinct claim with both coders' directions and a
    ``status`` in {agree, disagree, only_c1, only_c2}.
    """
    df1 = _to_frame(coder1, "c1")
    df2 = _to_frame(coder2, "c2")
    key = ["source_id", "food_id", "condition"]
    merged = df1.merge(df2, on=key, how="outer", suffixes=("", "_dup"))

    # Coalesce the traceability columns present in only one side.
    for col in ("food_en", "food_ja"):
        dup = f"{col}_dup"
        if dup in merged.columns:
            merged[col] = merged[col].fillna(merged[dup])
            merged = merged.drop(columns=[dup])

    def _status(row) -> str:
        d1, d2 = row.get("direction_c1"), row.get("direction_c2")
        has1 = isinstance(d1, str) and d1 != ""
        has2 = isinstance(d2, str) and d2 != ""
        if has1 and has2:
            return "agree" if d1 == d2 else "disagree"
        if has1:
            return "only_c1"
        return "only_c2"

    merged["status"] = merged.apply(_status, axis=1)
    cols = key + [
        "food_en",
        "food_ja",
        "direction_c1",
        "direction_c2",
        "status",
        "quote_c1",
        "quote_c2",
    ]
    cols = [c for c in cols if c in merged.columns]
    return merged[cols].sort_values(["status", "source_id", "food_id"]).reset_index(
        drop=True
    )


def cohen_kappa(recon: pd.DataFrame) -> dict:
    """Cohen's kappa on items BOTH coders coded (agree + disagree rows).

    Categories are the coded directions (warm/cool/neutral). Items only one
    coder found are excluded from kappa (they are coverage differences, not
    rating disagreements) but reported separately.
    """
    both = recon[recon["status"].isin(["agree", "disagree"])]
    n = len(both)
    if n == 0:
        return {"kappa": float("nan"), "n_both": 0, "po": float("nan")}

    d1 = both["direction_c1"]
    d2 = both["direction_c2"]
    cats = sorted(set(d1) | set(d2))

    po = (d1.values == d2.values).mean()
    # Expected agreement under independence.
    pe = 0.0
    for c in cats:
        p1 = (d1 == c).mean()
        p2 = (d2 == c).mean()
        pe += p1 * p2
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan")
    return {"kappa": kappa, "n_both": int(n), "po": float(po), "pe": float(pe)}


def summarize(recon: pd.DataFrame) -> None:
    counts = recon["status"].value_counts().to_dict()
    total = len(recon)
    print(f"Reconciliation over {total} distinct claims:")
    for st in ("agree", "disagree", "only_c1", "only_c2"):
        print(f"  {st:10s}: {counts.get(st, 0)}")

    k = cohen_kappa(recon)
    print(
        f"\nCohen's kappa (on {k['n_both']} co-coded items): "
        f"{k['kappa']:.3f} (observed agreement {k['po']:.3f})"
    )

    needs_human = recon[recon["status"] != "agree"]
    if not needs_human.empty:
        print(f"\n--- {len(needs_human)} claims need human adjudication ---")
        show = needs_human[
            ["source_id", "food_en", "food_ja", "direction_c1", "direction_c2", "status"]
        ]
        print(show.to_string(index=False))


def _dump_incumbent() -> list[dict]:
    """Export the current build_claims.CLAIMS as coder-1 JSON records."""
    from .build_claims import CLAIMS, COLUMNS

    return [dict(zip(COLUMNS, row)) for row in CLAIMS]


def main(argv: list[str]) -> None:
    if argv and argv[0] == "--dump-incumbent":
        out = Path(argv[1]) if len(argv) > 1 else Path("data/coder1_incumbent.json")
        recs = _dump_incumbent()
        out.write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {len(recs)} incumbent claims to {out}")
        return

    if len(argv) < 2:
        print(
            "usage: python3 -m src.reconcile_coders <coder1.json> <coder2.json>\n"
            "       python3 -m src.reconcile_coders --dump-incumbent [out.json]",
            file=sys.stderr,
        )
        sys.exit(2)

    coder1 = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    coder2 = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    recon = reconcile(coder1, coder2)
    summarize(recon)


if __name__ == "__main__":
    main(sys.argv[1:])

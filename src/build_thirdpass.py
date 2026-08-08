"""Aggregate the adversarial third screening pass into a published ledger.

The two-coder pass labelled every L2 record and the author adjudicated the
divergences. That leaves one failure mode untested: a record both coders
excluded for the same wrong reason. Because the primary outcome is binary
(L2' > 0), a single such record would flip a whole food's outcome, so the foods
that stand to be flipped — the core-belief foods currently at zero — were
re-screened by a third agent that was told the opposite thing from the first
two: every record you are about to read was excluded, find the ones where that
was wrong.

Scope: the 419 candidate records belonging to the 28 core foods (>= 3 Tier-1
sources) whose L2' is zero and whose L2 query returned anything at all. The
remaining nine core-zero foods returned no L2 hits, so they have nothing to
re-screen; their zero is a question about the search vocabulary (Limitations,
third point), not about screening.

The third pass could not see the existing labels, the golden set, or the
reconciliation code. Its verdicts are ``exclude-agreed`` / ``uncertain`` /
``include-candidate``; anything other than ``exclude-agreed`` was then read by
the author against title, abstract and MEDLINE indexing, and those rulings are
recorded in ``AUTHOR_RULINGS`` below with their reasons.

Run: ``python3 -m src.build_thirdpass`` (from the project root).
"""

from __future__ import annotations

import json

import pandas as pd

from .definitions import DATA_DIR

WORK_DIR = DATA_DIR / "screening_work" / "c3"
THIRDPASS_CSV = DATA_DIR / "screening_thirdpass.csv"

# Author adjudication of every record the third pass did not agree to exclude.
# Each was read against the title, the abstract and the MEDLINE indexing before
# the ruling was made; none changed its label, so no food changed outcome.
AUTHOR_RULINGS: dict[tuple[str, str], tuple[str, str]] = {
    ("white rice", "15447894"): (
        "exclude",
        "Human, oral, indirect calorimetry run 3.5 h before and 8 h after ingestion, but the "
        "reported outcomes are glucose kinetics and substrate oxidation. MEDLINE indexes "
        "Calorimetry, Indirect as a method and does not index Thermogenesis, Energy Metabolism "
        "or Body Temperature, and the abstract reports no energy expenditure in a thermogenic "
        "context, so condition 3 is not met. Publisher full text was not retrievable; the "
        "ruling rests on the abstract and the MeSH record.",
    ),
    ("grape", "20439553"): (
        "exclude",
        "12-week RCT of Concord grape juice in 76 adults, but thermogenesis appears only as a "
        "hypothesis in the conclusions ('it is hypothesized to be a result of ... effects on "
        "thermogenesis and substrate oxidation'). The measured outcomes are anthropometry, "
        "appetite, lipids, ORAC and OGTT, so condition 3 has no measurement behind it.",
    ),
    ("sake", "3576010"): (
        "exclude",
        "Case report of a two-month-old given formula mistakenly made with sake. Ingestion and "
        "human subject are met, but body temperature enters only as a negative clinical sign "
        "('without low body temperature') among poisoning findings, not as a measured thermal "
        "outcome attributed to the food, so condition 3 is not met.",
    ),
    ("spinach", "1745900"): (
        "exclude",
        "Scientific American feature on iron deficiency. It does state that iron deficiency "
        "lowers metabolic rate and body temperature on cold exposure, but spinach appears only "
        "as an example of poorly absorbed plant iron, so it is not the exposure of interest "
        "(condition 4), and the piece is not a primary report.",
    ),
    ("pineapple", "12265792"): (
        "exclude",
        "Report on a natural family planning programme. 'Pineapple plantation' locates the site "
        "and 'basal body temperature' names a contraceptive method; neither is an ingestion or "
        "a thermal outcome. Name-only match.",
    ),
}


def load_verdicts() -> pd.DataFrame:
    """Read every third-pass batch file into one frame, in file order."""
    rows = []
    for path in sorted(WORK_DIR.glob("*.json")):
        batch = json.loads(path.read_text())
        food_key = batch["food_key"]
        for v in batch["verdicts"]:
            rows.append(
                {
                    "food_key": food_key,
                    "pmid": str(v["pmid"]),
                    "third_verdict": v["verdict"],
                    "third_reason": v.get("reason", ""),
                }
            )
    if not rows:
        raise SystemExit(f"no third-pass batches under {WORK_DIR}")
    return pd.DataFrame(rows)


def attach_rulings(df: pd.DataFrame) -> pd.DataFrame:
    """Add the author's ruling to every record the third pass did not clear.

    Fail-loud: a flagged record with no ruling is an unfinished adjudication,
    not a record to quietly carry as excluded.
    """
    out = df.copy()
    flagged = out["third_verdict"] != "exclude-agreed"
    keys = list(zip(out["food_key"], out["pmid"]))
    missing = [k for k, f in zip(keys, flagged) if f and k not in AUTHOR_RULINGS]
    if missing:
        raise ValueError(f"third-pass records flagged but not adjudicated: {missing}")

    out["author_ruling"] = [
        AUTHOR_RULINGS.get(k, ("", ""))[0] if f else "" for k, f in zip(keys, flagged)
    ]
    out["author_reason"] = [
        AUTHOR_RULINGS.get(k, ("", ""))[1] if f else "" for k, f in zip(keys, flagged)
    ]
    return out.sort_values(["food_key", "pmid"]).reset_index(drop=True)


def main() -> None:
    df = attach_rulings(load_verdicts())
    df.to_csv(THIRDPASS_CSV, index=False)

    counts = df["third_verdict"].value_counts().to_dict()
    print(f"third pass over {len(df)} records across {df['food_key'].nunique()} foods")
    print(f"  verdicts: {counts}")

    flagged = df[df["third_verdict"] != "exclude-agreed"]
    print(f"  flagged for the author: {len(flagged)}")
    for _, r in flagged.iterrows():
        print(f"    {r['food_key']:12s} {r['pmid']:>9s}  {r['third_verdict']:18s} "
              f"-> author: {r['author_ruling']}")

    overturned = flagged[flagged["author_ruling"] == "include"]
    print(f"\n  labels overturned: {len(overturned)}")
    print(f"wrote {THIRDPASS_CSV}")


if __name__ == "__main__":
    main()

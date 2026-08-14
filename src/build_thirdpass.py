"""Aggregate the adversarial third screening passes into a published ledger.

The two-coder pass labelled every L2 record and the author adjudicated the
divergences. That leaves one failure mode untested: a record both coders
excluded for the same wrong reason. Because the primary outcome is binary
(L2' > 0), a single such record would flip a whole food's outcome, so the foods
that stand to be flipped — the ones at zero — were re-screened by a third agent
that was told the opposite thing from the first two: every record you are about
to read was excluded, find the ones where that was wrong.

Two passes are aggregated here and every published row carries the one that
produced it.

- **2026-08-09, core-zero.** The 388 candidate records of the 23 core foods
  (>= 3 Tier-1 sources) then at L2' = 0 whose L2 query returned anything at all.
  The two remaining core-zero foods returned no L2 hits, so they had nothing to
  re-screen. One record was overturned (watermelon/36558358), which moved that
  food out of the zero set.
- **2026-08-14, every zero food (screening protocol §9).** External review noted
  that scoping the first pass by coverage — the analysis's own explanatory
  variable — makes the detection rate for misclassified outcomes a function of
  the variable under test. §9 drops the threshold: every food in the primary
  frame at L2' = 0 with at least one retrieved record that no pass has read yet,
  which is 47 foods and 1,331 records. Its verdicts live in their own directory
  so the earlier pass's files stay untouched, and a record judged by both passes
  is an error rather than a second opinion (``load_verdicts`` fails loud on it).

Foods at L2' = 0 whose query returned nothing are outside both passes; their
zero is a question about the search vocabulary (Limitations, third point), not
about screening.

Neither pass could see the existing labels, the golden set, or the
reconciliation code. Verdicts are ``exclude-agreed`` / ``uncertain`` /
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
EXT_WORK_DIR = DATA_DIR / "screening_work" / "c3_ext"
THIRDPASS_CSV = DATA_DIR / "screening_thirdpass.csv"

PASS_CORE = "2026-08-09 core-zero"
PASS_ALL_ZERO = "2026-08-14 all-zero"

# Author adjudication of every record a third pass did not agree to exclude.
# Each was read against the title, the abstract and the MEDLINE indexing before
# the ruling was made.
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
        "a thermal outcome. Name-only match. (Flagged again by the 2026-08-09 pass, which could "
        "not see this ruling; the record reaches l2_records.csv without an abstract because the "
        "fetcher reads Abstract/AbstractText only and this 1981 record carries its text in "
        "OtherAbstract. The ruling is unchanged and was made against the full PubMed record.)",
    ),
    # --- 2026-08-09 pass over the 22-term core-zero set (388 records) ---------
    ("watermelon", "36558358"): (
        "include",
        "The one overturned exclusion. Randomised double-blind crossover, 12 healthy women, "
        "acute oral ingestion of 90 g wild watermelon extract juice, with blood flow in the "
        "posterior tibial artery significantly increased against placebo at 30/60/90 min supine. "
        "All four conditions hold on the abstract's own text, and the bed is an extremity one, "
        "which 2.3 lists among those peripheral circulation reaches and whose rationale calls the "
        "substrate of felt warmth. This record had been excluded by the 2026-08-08 author sweep "
        "citing the reactivity-probe rule, but none of that rule's named triggers is present: no "
        "occlusion, no pharmacological probe, no flow-mediated dilatation. Of the 39 limb- or "
        "skin-bed records that sweep excluded, every other one carries an organ or skeletal-muscle "
        "bed or a named probe, so restoring this one removes an inconsistency rather than making "
        "one. The paper frames itself on arterial stiffness and nitric oxide rather than warmth, "
        "but 2.3 makes the bed and the probe decisive, and rewriting that rule once it is known "
        "which record it decides is the failure this protocol exists to prevent.",
    ),
    ("watermelon", "36839167"): (
        "exclude",
        "Watermelon-juice crossover with indirect calorimetry during an oral glucose challenge. "
        "The primary endpoint is heart-rate variability, the calorimetry is described as 'the "
        "metabolic response to the OGC' with no thermogenesis, diet-induced thermogenesis or "
        "thermic-effect language anywhere, and the energy-expenditure result was null. MeSH "
        "indexes Heart Rate, Glucose and Cardiovascular Diseases and no thermal heading. That is "
        "the 2.3 energy-expenditure carve-out as written.",
    ),
    ("onion", "27087901"): (
        "exclude",
        "Twelve-week randomised placebo-controlled trial of quercetin-rich onion peel extract. "
        "Resting energy expenditure is measured, but the stated objective is the anti-obesity "
        "effect and body composition, the keywords are overweight, body fat percent and obesity, "
        "and no thermogenic framing appears. Two grounds, either sufficient: 2.3 makes energy "
        "expenditure inside a body-composition trial no-thermal, and the REE rise occurred in the "
        "placebo arm as well (p = 0.003) so no thermal outcome is attributable to the exposure.",
    ),
    ("pumpkin", "41695112"): (
        "exclude",
        "Acute crossover in 15 adults of whey against a pea, brown-rice and pumpkin-seed protein "
        "blend, with postprandial energy expenditure over 3 h. Pumpkin seed is one of three "
        "protein sources in the blend and no pumpkin-specific readout is reported, so condition 4 "
        "fails, and the outcomes are framed as postprandial metabolism and appetite alongside "
        "insulin, GLP-1 and NEFA with no thermogenesis language, so 2.3 excludes the energy "
        "expenditure independently. The same record is excluded under brown rice on the same "
        "grounds.",
    ),
    ("tuna", "15603203"): (
        "exclude",
        "Randomised double-blind crossover in 10 healthy women with oral liquid histamine, "
        "measuring skin temperature and flush. Conditions 1, 3 and 4 hold for the agent actually "
        "ingested, but tuna was not ingested and histamine is not tuna's principal dietary "
        "constituent: the abstract lists it across cheese, sausages, sauerkraut, tuna, tomatoes "
        "and alcoholic beverages, and MeSH indexes Histamine with no fish heading. Crediting it "
        "would attach one study to six unrelated food keys, which is not what the constituent "
        "rule is for.",
    ),
}


def load_verdicts() -> pd.DataFrame:
    """Read every third-pass batch file into one frame, tagged with its pass.

    Fail-loud on a record judged by more than one pass: §9 subtracts the foods an
    earlier pass read rather than re-reading them, so an overlap means a scope
    was stale, and silently keeping one of the two verdicts would replace a
    settled judgment instead of testing it.
    """
    rows = []
    for work_dir, pass_id in ((WORK_DIR, PASS_CORE), (EXT_WORK_DIR, PASS_ALL_ZERO)):
        if not work_dir.is_dir():
            continue
        for path in sorted(work_dir.glob("*.json")):
            batch = json.loads(path.read_text())
            food_key = batch["food_key"]
            for v in batch["verdicts"]:
                rows.append(
                    {
                        "pass_id": pass_id,
                        "food_key": food_key,
                        "pmid": str(v["pmid"]),
                        "third_verdict": v["verdict"],
                        "third_reason": v.get("reason", ""),
                    }
                )
    if not rows:
        raise SystemExit(f"no third-pass batches under {WORK_DIR} or {EXT_WORK_DIR}")

    out = pd.DataFrame(rows)
    clash = out[out.duplicated(subset=["food_key", "pmid"], keep=False)]
    if len(clash):
        raise ValueError(
            "the same record was judged by more than one third pass: "
            f"{sorted(set(zip(clash['food_key'], clash['pmid'])))}"
        )
    return out


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
    order = [k for k in ("pass_id", "food_key", "pmid") if k in out.columns]
    return out.sort_values(order).reset_index(drop=True)


def main() -> None:
    df = attach_rulings(load_verdicts())
    df.to_csv(THIRDPASS_CSV, index=False)

    print(f"third pass over {len(df)} records across {df['food_key'].nunique()} foods")
    for pass_id, grp in df.groupby("pass_id"):
        flagged = grp[grp["third_verdict"] != "exclude-agreed"]
        overturned = flagged[flagged["author_ruling"] == "include"]
        print(f"  {pass_id}: {len(grp)} records / {grp['food_key'].nunique()} foods / "
              f"{len(flagged)} flagged / {len(overturned)} overturned")
        print(f"    verdicts: {grp['third_verdict'].value_counts().to_dict()}")

    flagged = df[df["third_verdict"] != "exclude-agreed"]
    print(f"\nflagged for the author: {len(flagged)}")
    for _, r in flagged.iterrows():
        print(f"  {r['food_key']:12s} {r['pmid']:>9s}  {r['third_verdict']:18s} "
              f"-> author: {r['author_ruling']}")

    overturned = flagged[flagged["author_ruling"] == "include"]
    print(f"\n  labels overturned: {len(overturned)}")
    print(f"wrote {THIRDPASS_CSV}")


if __name__ == "__main__":
    main()

"""Adjudicate the two independent L2 codings into the published screening.csv.

Coder 1 (Claude Sonnet) and Coder 2 (Claude Opus) labelled every L2 record
independently from ``data/screening_protocol.md``, blind to each other and to
the golden set. This script reconciles the two codings, applies the author's
rulings to the records they diverged on, and writes:

- ``data/screening.csv`` — the published per-record judgments (protocol §6)
- ``L2_screened`` on the L2 rows of ``data/pubmed_counts.csv`` — L2′, the count
  of on-construct studies per food, which is Axis B's rebuilt measure

The ``RULINGS`` map below *is* the provenance of every author decision: each
divergence was settled by reading the title + abstract (and, where the abstract
does not state the subject species, the PubMed MeSH headings or the full text)
against protocol §2-§3. Foods are read from whichever per-coder CSVs exist, so
the same script serves the golden-food batch and the full run.

Run: ``python3 -m src.build_screening``
"""

from __future__ import annotations

import sys

import pandas as pd

from .definitions import DATA_DIR, PUBMED_COUNTS_CSV
from .screening import (
    GOLDEN_CSV,
    SCREENING_CSV,
    adjudicate,
    attach_l2_screened,
    cohen_kappa,
    golden_scores,
    l2_screened,
    reconcile,
    to_screening_csv,
)

WORK_DIR = DATA_DIR / "screening_work"

# --- author rulings: {(food_key, pmid): (final_label, rationale)} ----------
# Every record the two coders did not agree on, settled 2026-08-07 against
# title + abstract per protocol §2-§3. All ten fall inside the golden set, so
# each also has a hand label to check against; the one place the ruling departs
# from the original gold label is ginger/29259648, where the gold label itself
# was wrong (see below) and has since been corrected in build_golden.py.
RULINGS = {
    ("chili pepper", "33789250"): (
        "include",
        "review-subject: stated objective is the effect on energy metabolism (§3 review rule), human evidence",
    ),
    ("chili pepper", "40092148"): (
        "exclude",
        "name-only: broad cold-weather military nutrition review, red pepper not the subject",
    ),
    ("coffee", "39519525"): (
        "exclude",
        "name-only: bibliometric mapping of the caffeine-in-heat literature, not thermal-ingestion evidence",
    ),
    ("ginger", "29259648"): (
        "exclude",
        "animal: 33 rabbits per PMC full text (IACUC BUCM-3-2015032502-1002); abstract states no species",
    ),
    ("ginger", "33789250"): (
        "include",
        "review-subject: stated objective is the effect on energy metabolism (§3 review rule), human evidence",
    ),
    ("ginger", "39259072"): (
        "exclude",
        "no-thermal: ginger RCT in COVID-19 outpatients, outcomes are viral clearance and symptoms",
    ),
    ("ginger", "40092148"): (
        "exclude",
        "name-only: broad cold-weather military nutrition review, ginger not the subject",
    ),
    ("salt", "23253191"): (
        "include",
        "human RCT, 10 cyclists: oral sodium+water, forearm skin blood flow and sweat rate measured [constituent]",
    ),
    ("salt", "25729305"): (
        "include",
        "human, 11 endurance athletes: oral sodium supplementation, thermoregulation indices [constituent]",
    ),
    ("salt", "3349990"): (
        "exclude",
        "name-only: the exposure of interest is forced water intake (phase II is water alone), not salt (§2 criterion 4)",
    ),
    # --- remaining 76 foods, settled 2026-08-07 -----------------------------
    # (a) Food identity. `pepper` is 黒胡椒 (Piper nigrum; query `pepper[tiab]`),
    # and 唐辛子 / パプリカ are their own food_keys (`chili pepper`,
    # `bell pepper`). Capsicum records therefore belong to those keys, not this
    # one — counting them here would double-count the same studies under two
    # foods and attach them to a belief Axis A recorded separately (§3
    # botanical species identity, the ginger sensu-stricto rule).
    **{
        ("pepper", pmid): (
            "exclude",
            "species-mismatch: Capsicum study; `pepper` is Piper nigrum and chili/bell pepper are separate food_keys (§3)",
        )
        for pmid in (
            "10211048", "11227803", "11676017", "17341828", "20925950",
            "21093467", "23179202", "23844093", "24100669", "24267043",
            "33063385", "33789250", "38571755", "3957721", "42186269",
        )
    },
    ("orange", "26856274"): (
        "exclude",
        "species-mismatch: the thermogenic agent reviewed is bitter orange (Citrus aurantium/p-synephrine), not sweet orange",
    ),
    ("green tea", "10702779"): (
        "exclude",
        "animal: MeSH Animals/Rats (Dulloo 2000); the abstract states no species, so coder 2's uncertain-species hold was right",
    ),
    # (b) The food is present but is not the exposure of interest (§2
    # criterion 4): comparator arms, vehicles, placebos, tracers. Its thermal
    # readout exists only as the baseline another substance is tested against.
    **{
        key: (
            "exclude",
            "name-only: the food is the comparator/vehicle arm, not the exposure of interest (§2 criterion 4)",
        )
        for key in (
            ("rapeseed oil", "11756059"), ("rapeseed oil", "12775122"),
            ("rapeseed oil", "14718746"), ("rapeseed oil", "27430386"),
            ("soybean", "12775122"),
            ("orange", "1885267"), ("orange", "7816004"),
            ("white sugar", "8508195"),
        )
    },
    # (c) Reviews whose stated objective is obesity / weight loss / fat
    # reduction, with thermogenesis only one listed mechanism (§3 review rule).
    **{
        key: (
            "exclude",
            "name-only: review whose stated objective is obesity/weight-loss, thermogenesis only a listed mechanism (§3)",
        )
        for key in (
            ("green tea", "11924761"), ("green tea", "20156466"),
            ("green tea", "26421678"), ("green tea", "37450930"),
            ("orange", "34409177"),
        )
    },
    ("corn", "23941499"): (
        "exclude",
        "name-only: high-fructose sweeteners are an industrial isomerisation product, not a food-form of corn (cf. corn oil/starch)",
    ),
    # (d) Individually settled.
    ("bell pepper", "23179202"): (
        "exclude",
        "name-only: bell pepper is the non-pungent control arm against chilli, not the exposure of interest (§2 criterion 4)",
    ),
    ("beer", "29501558"): (
        "exclude",
        "name-only: sensory-acceptability study; biometrics index liking, and no thermal MeSH is indexed",
    ),
    ("milk", "4002723"): (
        "exclude",
        "no-thermal: neonatal feeding RCT on drinking behaviour/weight; body temperature is routine monitoring, no thermal MeSH",
    ),
    # (e) Records flagged uncertain-species / no-abstract, settled against MeSH
    # (protocol §2/§5: agreement on absent information is not evidence).
    ("cinnamon", "33388379"): ("exclude", "animal: MeSH Animals/Mice/Rats; abstract states no species"),
    ("cinnamon", "32980484"): ("exclude", "animal: MeSH Animals/Mice; abstract states no species"),
    ("egg", "6552612"): ("exclude", "name-only: midwifery forum piece, no thermal MeSH indexed"),
    ("milk", "14115557"): (
        "exclude",
        "name-only: body temperature is the febrile response to measles vaccine, not a thermal effect of the milk",
    ),
    ("milk", "14314552"): ("exclude", "name-only: brain temperature and arousal, unrelated to milk ingestion"),
    ("milk", "2428285"): ("exclude", "name-only: review of low-birthweight infant care, no thermal outcome indexed"),
    ("milk", "3478916"): ("exclude", "name-only: neonatal care service report, no thermal outcome indexed"),
    ("milk", "38486985"): ("exclude", "name-only: commentary on mammary beige-adipocyte biology, not milk ingestion"),
    ("spinach", "1745900"): ("exclude", "name-only: iron deficiency review, no thermal outcome indexed"),
    ("wakame", "11365014"): (
        "exclude",
        "uncertain-species: seaweed-extract product notice; no MeSH, no species, no study design stated",
    ),
    ("white sugar", "36745510"): (
        "exclude",
        "no-thermal: the exposure is a whole obesogenic diet, with no sugar-specific thermal readout (§3 whole-diet rule)",
    ),
}


def load_coder(coder: str) -> pd.DataFrame:
    """Concatenate one coder's per-food CSVs from data/screening_work/<coder>/."""
    files = sorted((WORK_DIR / coder).glob("*.csv"))
    if not files:
        sys.exit(f"no coder CSVs under {WORK_DIR / coder}")
    return pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)


def main() -> None:
    c1 = load_coder("c1")
    c2 = load_coder("c2")
    recon = reconcile(c1.to_dict("records"), c2.to_dict("records"))
    counts = recon["status"].value_counts().to_dict()
    print(f"reconciled {len(recon)} (food, pmid) records: {counts}")

    k = cohen_kappa(recon)
    print(f"Cohen's kappa = {k['kappa']:.4f} on {k['n_both']} co-coded records "
          f"(observed agreement {k['po']:.4f})")

    golden = pd.read_csv(GOLDEN_CSV, dtype=str).to_dict("records")
    for name, df in (("coder1", c1), ("coder2", c2)):
        s = golden_scores(df.to_dict("records"), golden)
        print(f"  {name} vs golden (n={s['n']}): precision {s['precision']:.4f} "
              f"recall {s['recall']:.4f} F1 {s['f1']:.4f}")

    adjudicated = adjudicate(recon, RULINGS)
    out = to_screening_csv(adjudicated)
    out.to_csv(SCREENING_CSV, index=False)
    print(f"\nwrote {SCREENING_CSV} ({len(out)} records, "
          f"{int(out['adjudicated'].sum())} author-adjudicated)")

    l2s = l2_screened(adjudicated)
    screened = sorted(adjudicated["food_key"].unique())
    counts_df = pd.read_csv(PUBMED_COUNTS_CSV)
    updated = attach_l2_screened(counts_df, l2s, screened_foods=screened)
    updated.to_csv(PUBMED_COUNTS_CSV, index=False)

    print(f"\nL2' per screened food ({len(screened)} of "
          f"{(counts_df['layer'] == 'L2').sum()} L2 foods; the rest stay blank "
          "until screened):")
    for food in screened:
        raw = counts_df[(counts_df.food_key == food) & (counts_df.layer == "L2")]
        n_raw = int(raw["n_pubmed"].iloc[0]) if len(raw) else -1
        print(f"  {food:14s} L2 {n_raw:4d} → L2' {int(l2s.get(food, 0)):3d}")


if __name__ == "__main__":
    main()

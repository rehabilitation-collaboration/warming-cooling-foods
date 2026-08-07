# Axis B — L2 Abstract Screening Protocol (measurement rebuild, RB-2)

Agreed 2026-08-07. This document fixes how each Layer-2 (L2) PubMed hit is judged
**include / exclude** so that Axis B measures the intended construct — *research
on the thermal effect of a human ingesting the food* — rather than raw keyword
co-occurrence. It is the RB-2 core of the Route B rebuild triggered by the GPT
review (2026-08-07): the L2 count is precise but does not measure that construct
(`chicken[tiab] AND body temperature` returns poultry heat-stress and avian
thermoregulation studies, not humans eating chicken; ginger's thermic-effect-of-food
studies are missed).

It mirrors the two-coder reconciliation approach used for Axis A
(`coding_protocol.md` §8, `reconcile_coders.py`, κ = 1.000) and the bibliographic
coding of García-Hernández et al. (2023).

## 0. Input

`data/l2_records.csv` — one row per (food_key, pmid): title, abstract, journal,
pubtypes. 2,772 records across 81 foods (2026-08-07 fetch; record count equals
the esearch hit count for every food, 0 mismatch vs `pubmed_counts.csv` L2).
This is the complete L2 hit set; screening covers **all** queryable foods'
records (not the GPT minimum of zero-count + top-count foods).

## 1. Construct being measured

**Axis B (L2′) = the number of studies that examined the thermal effect on a
human of ingesting the food (or its principal dietary constituent).**

"Thermal effect" is read broadly, because the four seed terms
(thermogenesis / body temperature / peripheral circulation / thermoregulation)
under-capture how the effect is actually measured in nutrition trials (e.g.
diet-induced thermogenesis, resting energy expenditure, subjective warmth).
Reading it narrowly would re-introduce the ginger false-negative the rebuild
exists to fix.

## 2. Decision (2 values only)

Each record gets `include` or `exclude`. **No quality grading** (this is not
GRADE/PRISMA risk-of-bias; it is construct-validity screening only). A short
`reason` code accompanies each judgment.

### INCLUDE — all four must hold

1. **Human subjects** (healthy volunteers or patients), *in vivo*.
2. **Oral ingestion** of the food, a food-form of it, or its principal dietary
   constituent (see §3 boundary rules) — as an actual intake, not merely named.
3. **A thermal-related physiological outcome is measured**, from this set:
   - core / peripheral / skin / tympanic / axillary body temperature
   - thermogenesis, diet-induced thermogenesis / thermic effect of food (TEF)
   - resting/postprandial energy expenditure *reported in a thermogenesis or
     body-warming context*
   - peripheral circulation / blood flow / microcirculation / extremity warming
   - thermoregulation / cold tolerance / cold-induced responses
   - subjective thermal sensation (warmth / coldness perception, cold-sensitivity 冷え)
4. **The outcome is attributable to the food/constituent** (single-arm or
   controlled; the food is the exposure of interest).

### EXCLUDE — any one triggers exclusion

- `animal` — non-human subjects (poultry, rodents, livestock, fish, companion
  animals, etc.). Covers the dominant chicken/egg/milk/beef/lamb false positives.
- `livestock-heat` — farm-animal heat stress / heat tolerance / thermotolerance
  / production under heat (a subset of `animal`; kept as its own code because it
  is the single largest false-positive class).
- `invitro` — cell/tissue/enzyme only, no human ingestion.
- `agri` — agronomy: crop cold tolerance, storage temperature, post-harvest
  physiology, chilling injury.
- `name-only` — food term matches but the study is unrelated to a thermal
  ingestion effect (allergy, contamination, composition assay, epidemiology with
  no thermal physiological outcome, food named incidentally). Includes `salt`
  hits that are saline/sodium-clinical, not "eating salt warms/cools you".
- `no-thermal` — human ingestion study but no thermal-related outcome measured.
- `mechanism-only` — human-derived but ex vivo / biomarker only, no in vivo
  thermal outcome.

### When the abstract does not state the subject species

Some records name no subject species in the abstract (typically a
Chinese-medicine or physiology paper whose methods sit only in the full text).
**Do not infer the species from indirect cues** — acupoint names, clinical
phrasing, or the journal's scope. Label the record `exclude` with the
`uncertain-species` reason, which routes it to author adjudication regardless of
whether the two coders agree (§5); the author settles it against the PubMed
Humans/Animals MeSH headings, or the full text where the record carries no MeSH.

Added 2026-08-07: ginger/29259648 ("The Effects of ... Dried Ginger Rhizome ...
on Rectal and Skin Temperatures at Acupuncture Points") was hand-labelled
`include` on the inference that its acupoint names (Dazhui, Zhongwan) implied
human subjects. It carries no MeSH, and the PMC full text states 33 rabbits
(IACUC BUCM-3-2015032502-1002) — so the correct label is `exclude` (`animal`).
Coder 2 labelled it `animal`; the coder disagreement is what surfaced the error.

### When the record has no abstract

40 of the 2,772 L2 records (1.4%) are title-only, mostly older indexed articles.
Judge those on title and publication types. Where the title alone settles it —
"Ultradian rhythm of chicken body temperature", say — label it normally. Where
the title cannot establish all four INCLUDE conditions and the record might
belong in L2′, label it `exclude` with the `no-abstract` reason, which routes it
to the author (§5) rather than resolving an unknown by guessing. All 18
title-only records among the golden foods were unambiguous animal studies, so
this is expected to be rare.

## 3. Boundary rules

- **Isolated constituents** (capsaicin, caffeine, catechins, gingerols, menthol):
  `include` when given as a dietary dose standing in for the food's intake, with
  `constituent` sub-label. **Pharmacological / supra-dietary doses divorced from
  food intake** → `include` with `constituent` sub-label but flagged
  `supradose`, so a sensitivity analysis can drop them. (Rationale: capsaicin ↔
  chili pepper, caffeine ↔ coffee are the mechanism by which the food's belief
  is tested; excluding them would re-create false negatives.)
- **Botanical species identity** (added during golden labelling, 2026-08-07):
  a food term is counted only for its own species, *sensu stricto*, in the
  primary L2′. For `ginger` this means *Zingiber officinale* and its own
  pungent principles (gingerol / shogaol / zingerone). Related but distinct
  Zingiberaceae — **grains of paradise** (*Aframomum melegueta* / 6-paradol) and
  **black ginger** (*Kaempferia parviflora*) — are `exclude` with the
  `species-mismatch` reason, because the folk belief and the web-source coverage
  (Axis A) concern culinary ginger, not those species. They are recovered in a
  `sensu-lato` sensitivity variant. (Rationale: including *Aframomum*/*Kaempferia*
  BAT studies under "ginger" would inflate L2′ with a construct Axis A never
  measured; the ginger false-negatives the rebuild must fix — thermic effect of
  food / REE / DIT — are all genuine *Z. officinale* studies and are recovered
  regardless.) This is a species-identity rule, distinct from the constituent
  rule above: an *isolated constituent of the food's own species* is `include`
  (constituent); a *different species in the same family* is `exclude`
  (species-mismatch).
- **Reviews / meta-analyses of human thermal-ingestion evidence**: `include`
  with `review` sub-label (counted, but flagged so a primary-only sensitivity
  count is possible — avoids double-counting concerns). A review is on-construct
  only when its stated objective is the thermal / thermogenic / energy-metabolism
  effect itself; a review whose objective is obesity / weight-loss / exercise
  performance (with thermogenesis merely one listed mechanism) is `exclude`
  `name-only`.
- **Mixed interventions** (food + exercise + cold exposure) where the food's
  independent effect is not separable: `include` with `confounded` sub-label.
- **Food eaten hot/cold as a vehicle for serving temperature** (e.g. warm water,
  a hot drink where the thermal effect is the serving temperature, not the
  food's nature): `exclude` `name-only` — this matches Axis A's rule that serving
  temperature ≠ the food's thermal nature (`coding_protocol.md` §3).
- **Whole-diet studies** that include the food only as one component with no
  food-specific thermal readout: `exclude` `no-thermal`.

## 4. Golden set (protocol validation before full coding)

Before any automated coding, the author (using an LLM in the main session,
reading each title + abstract — disclosed in Methods) hand-labels a golden
reference set to (a) pin the boundary rules on real records and (b) measure
coder precision/recall. Where a record's abstract does not state the subject
species, the gold label is set from the PubMed Humans/Animals MeSH headings, or
from the full text when the record carries no MeSH — never from inference (§2).
Every gold `include` was re-verified this way on 2026-08-07, which corrected one
label (ginger/29259648). Foods where the include boundary actually lives are
labelled in full; the near-uniform false-positive classes are labelled on a
stratified sample large enough to estimate coder specificity:

- **`ginger` — all 35 records** (false-negative stress test; expect several
  `include`, incl. TEF/energy-expenditure records the 4 seed terms nearly miss).
- **`coffee` — all 24** and **`chili pepper` — all 30** (constituent boundary:
  caffeine/capsaicin — where true includes concentrate).
- **`chicken` — stratified 40** (false-positive stress test): every
  human-signal record (title/abstract mentioning humans/RCT/energy expenditure)
  plus a random fill to 40, so any rare true include is caught and coder
  specificity on the dominant `animal`/`livestock-heat` class is estimated.
- **`salt` — stratified 40** (name-only vs genuine sodium/thermoregulation),
  same human-signal-oversampled sampling.

Rationale for sampling chicken/salt rather than all records: both are
near-uniform exclude classes (poultry heat-stress; saline/sodium-clinical), so a
stratified sample estimates coder specificity without the author reading ~950k
characters, which would degrade labelling quality. The full chicken/salt record
sets are still screened by the coders (§5) — only the golden *reference* is
sampled. Golden labels are stored in `data/screening_golden.csv`
(food_key, pmid, gold_label, gold_reason). Coder precision/recall/F1 vs gold is
reported in Methods.

## 5. Two independent coders + reconciliation

- Every record is coded **independently by two coders** into
  `{pmid, food_key, label, reason}`. Both coders are LLM agents run under the
  author's direction, and coder 2 is **not** a confirmer of coder 1: the two are
  different capability tiers of one vendor's model line, and each agent is given
  only the protocol and its assigned records — coder 1's labels, the golden set,
  and the reconciliation code are all withheld.
- **What this pairing can and cannot support.** Two models from one vendor and
  one release generation share pretraining data, tokenizer and alignment
  methodology, so their errors should be expected to correlate. The resulting
  kappa is a **within-lineage consistency** statistic: it bounds how stably this
  family applies the protocol. It is *not* an independence-based reliability
  estimate, it is not comparable to a kappa between human raters, and it is a
  weaker design than the three-vendor arrangement of Hilkenmeier et al. (2026).
  Do not describe the pair as "different model families" — that phrase is used
  in the cited literature to mean different vendors, and by that standard all of
  Claude is one family. Accuracy evidence comes from the golden set
  (precision/recall against hand labels), not from coder agreement.

  | Batch | Records | Coder 1 | Coder 2 |
  |---|---|---|---|
  | Golden foods (chicken, ginger, coffee, chili pepper, salt) | 623 | `claude-sonnet-4-6` | `claude-opus-4-7` |
  | Remaining 76 foods (8 bundles) | 2,149 | `claude-sonnet-5` | `claude-opus-5` |
  | Universe extension (26 foods) | 115 | `claude-sonnet-5` | `claude-opus-5` |

  The model versions differ between batches because the screening ran across
  several working sessions as the available models changed; within every batch
  the two coders are contemporaneous. Kappa is computed over
  all 2,887 co-coded records regardless of batch.
- Codings are reconciled on the `pmid` key. **Cohen's κ is computed on the
  co-coded records** (both coders labelled), categories = {include, exclude}.
  Coverage differences (a pmid only one coder returned) are reported separately
  and adjudicated by the author, exactly as Axis A did — the κ denominator is the
  co-coded count, never inflated to the full record count (the GPT #4 lesson).
- **Disagreements** are adjudicated by the author against title + abstract per
  §2–§3; the adjudicated label is `final_label`. Records either coder marked
  `uncertain-species` or `no-abstract` are adjudicated too, **even when the
  coders agree**, since agreement reached on information the record does not
  contain is not evidence about that information.
- Divergence target: κ ≥ 0.60. If lower, refine §2–§3 definitions and re-code; if
  still low, the author hand-adjudicates every record (PLAN branch condition).

## 6. Output

- `data/screening.csv` — `pmid, food_key, coder1, coder2, adjudicated,
  final_label, reason, sublabels`. One row per (food_key, pmid). `coder1` /
  `coder2` are the two independent labels; `adjudicated` is `True` on the rows
  the author settled (divergences, coverage differences, and
  `uncertain-species` records) and `False` where the coders agreed; `reason`
  carries the author's adjudication rationale on those rows and the coders'
  reason elsewhere; `sublabels` is the union of the sub-labels either coder
  attached (`review`, `constituent`, `supradose`, `confounded`).
- **L2′** = per food, count of `final_label == include`. Written to
  `pubmed_counts.csv` as an `L2_screened` column on the L2 layer rows.
- Sensitivity variants recorded but not primary: L2′ excluding `review`, and
  L2′ excluding `supradose`.
- Explicit validity checks reported: chicken L2′ (poultry false positives
  removed) and ginger L2′ (TEF false negatives recovered), cross-checked against
  a targeted `ginger AND (thermic effect of food OR energy expenditure)` query.

## 7. Provenance / reproducibility

Raw efetch responses per food are under `data/query_log/pubmed_*_L2_records.json`
(saved by `fetch_l2_records.py`). `screening.csv`, `screening_golden.csv`, and
`screening_protocol.md` are committed to the analysis repository so the
include/exclude judgments are auditable (the GPT reproducibility ask).

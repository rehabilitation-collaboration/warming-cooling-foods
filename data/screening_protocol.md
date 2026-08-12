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

**Extended after the food universe was widened (see §5):** the universe extension
added 115 records across 26 further foods, so the screened set was
**2,887 records across 107 foods** (2,772 + 115 = 2,887; 81 + 26 = 107).

**Extended again by the recall rebuild (2026-08-08, third review round).** The
effect vocabulary was four terms while §2 condition 3 accepted a far wider
outcome set, so the query was narrower than its own inclusion rule and could not
measure absence — demonstrably, since Fagundes 2021 (PMID 33487261), a
randomised crossover trial of ginger measuring TEF, indirect calorimetry and
axillary temperature, was retrieved by none of the four. The vocabulary was
widened to 22 terms in one-to-one correspondence with the outcome classes §2.3
accepts, and L2 was refetched for all 175 queryable foods:

| | records | foods |
|---|---|---|
| four-term query (2026-08-07) | 2,887 | 107 |
| 22-term query (2026-08-08) | **12,437** | **138** |
| Route D universe extension (2026-08-12) | **12,733** | **147** |

The 22 terms are an OR-superset of the original four, verified against the
records rather than the counts: every one of the 2,887 already-judged
(food_key, pmid) pairs is still retrieved, none was lost, and the delta is
**9,550 new pairs across 134 foods**. Those 9,550 are coded by two fresh coders
under this same protocol; the 2,887 existing judgments are reused verbatim,
because re-coding a record already judged would put two labels on one
(food_key, pmid) key.

**Extended a third time by the Axis A ledger rebuild (2026-08-12, Route D).**
Rebuilding Axis A from a full candidate ledger admitted foods the hand-coded
`claims.csv` had not carried, so the food universe grew and L2 was fetched for
them. That added **296 unjudged records across 9 foods** — `cream` 220, `yogurt`
35, `ice cream` 15, `avocado` 9, `fennel` 7, `pheasant` 4, `papaya` 3,
`long pepper` 2, `star anise` 1 — screened by the same two coder tiers under
this protocol, bringing the set to **12,733 records across 147 foods**. The
previously judged records are reused verbatim for the same reason as before.
The κ in §5 and every count in the manuscript are computed over the full 12,733.

A food can also leave the L2 universe after its records have been screened, in
which case its judgments stay in `screening.csv` as provenance but sit outside
the L2 denominator. As of 2026-08-12 that is one food: `white fish`, which was
reclassified as a class label rather than a food, and whose single judgment is
therefore not part of the 190-food count. `build_screening.py` derives that list
on each run and prints whatever is in it, so this paragraph is a snapshot of the
list rather than a statement of what it will contain.

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

#### What condition 3 does and does not reach (clarified 2026-08-08)

The widened query multiplied the number of records where a *vascular* or an
*energy-expenditure* measurement exists but is not a thermal readout, and the two
coders drew the line differently: 148 of the 174 divergences in the recall-rebuild
batch turn on this one question. The wording above already settles it — these
three notes make explicit what "peripheral", "extremity" and "reported in a
thermogenesis or body-warming context" were doing, and no outcome class is added
or removed by them.

- **Vascular bed.** "Peripheral circulation / blood flow / microcirculation /
  extremity warming" reaches the **skin and the limbs** — cutaneous perfusion,
  skin blood flow, forearm / calf / hand / foot flow, skin microcirculation,
  extremity rewarming. It does **not** reach organ-specific perfusion measured
  for a non-thermal purpose: cerebral, coronary, renal, hepatic, retinal or
  ocular, and sublingual flow are `no-thermal`. (Rationale: Axis A's claim is that
  the body feels warm or cold, and skin and extremity perfusion is that
  sensation's substrate; cerebral or renal perfusion is not. Without this line any
  vascular-function trial of any food becomes an include and L2′ fills with
  endothelial-function literature that the folk claim never addressed.)
- **Energy expenditure.** EE / RMR / BMR qualifies where it is an endpoint of the
  study in its own right — what the food was given in order to move. EE appearing
  as a covariate, as the denominator of an exercise energy balance, as a
  body-composition or weight-loss endpoint, or as a frailty criterion is
  `no-thermal`: there the measurement serves another question.

  Wording such as thermogenesis, diet-induced thermogenesis, thermic effect of
  food or the food's thermogenic effect is the clearest evidence that a paper is
  in the first case, but it is evidence, not the test. **Restated on 2026-08-12
  to describe the rule the corpus was actually built on, not to change it.** The
  earlier wording — "qualifies only where the paper frames it as thermogenesis,
  [DIT], [TEF]" — reads as a vocabulary test, and 63 of the 292 includes standing
  before that date use no such wording (`chili pepper`/8926537, "Effects of
  red-pepper diet on the energy metabolism in men"; `corn`/29193741; `potato`/
  3059793; `lotus root`/24045789). The rulings filed on 2026-08-07 and 2026-08-08
  state the role test outright and predate the restatement: `green tea`/16418760
  ("metabolic rate over 6 h supine rest is **the primary outcome** of a
  thermogenic formula **rather than an energy-expenditure covariate of another
  endpoint**"), `green tea`/17919327, and `green tea`/36558368, which the §2.3
  sweep re-read and kept on that ground. Every exclusion filed under this clause
  names a subordinate role; none names a missing word. No label was changed by
  the restatement.
- **Reactivity probes.** A pharmacological endothelial probe — acetylcholine,
  sodium nitroprusside, methacholine or insulin-stimulated limb flow, or
  flow-mediated dilatation — read in a hypertension or endothelial-function
  framing is an endothelial endpoint, not a thermal one: `no-thermal`. **Local
  thermal hyperaemia** (the skin's perfusion response to local heating) is thermal
  by construction and qualifies.

Because coders who *agree* on a wrong include are never routed to adjudication
(§5), these three notes have to be applied as a single sweep across every include
in the ledger, not only across the divergences: the coding pass (15:54–16:51 on
2026-08-08) ran before these notes were written down (17:27), so agreed includes
could not have been judged against them.

**That sweep ran on 2026-08-08, after the 210 divergence and information-gap
rulings were complete.** All 380 agreed includes were re-read against each
record's own title and abstract in `l2_records.csv` — not against the coders'
reason text. **115 of the 380 are `exclude` under §2.3**, and 11 that a keyword
pass had flagged are confirmed `include`. One of the 115 was restored on
2026-08-09 after the adversarial third pass challenged it — watermelon/36558358,
excluded here by citing the reactivity-probe rule although the record contains
no occlusion, no pharmacological probe and no flow-mediated dilatation, and
whose bed (posterior tibial artery) is one this section names as in scope. That
row now carries the batch `2026-08-09 third pass`, so the sweep stands at 114
exclusions and 12 confirmations. Both sets are filed in
`data/screening_rulings.csv` under the batch `2026-08-08 §2.3 sweep`, so every
override is auditable, and `adjudicate()` reports these rows as `adjudicated`
in `screening.csv` rather than overriding them silently. The four agreed
includes named as violations before the sweep — black tea/23486295 (regional
cerebral blood flow by ASL-MRI), black tea/33934371 (retinal microvascular
density by OCT-A), egg/38703228 (cerebral blood flow for a cognitive
assessment) and beer/10589240 (optic-nerve-head microcirculation) — are all now
`exclude`. Where a record measures local thermal hyperaemia the sweep keeps it:
chicken/41901102 and milk/27180680 are `include` on that basis.

The largest class the sweep removed is the endothelial-function trial
(flow-mediated dilation, acetylcholine or sodium-nitroprusside iontophoresis,
post-occlusive reactive hyperaemia): 103 of the 115 exclusions carry the
`no-thermal` code and cocoa alone lost 23 records. That is the outcome the
vascular-bed and reactivity-probe notes exist to produce — without them L2′
would have been dominated by vascular-function literature the folk claim never
addressed.

### EXCLUDE — any one triggers exclusion

- `animal` — non-human subjects (poultry, rodents, livestock, fish, companion
  animals, etc.). Covers the dominant chicken/egg/milk/beef/lamb false positives.
- `livestock-heat` — farm-animal heat stress / heat tolerance / thermotolerance
  / production under heat (a subset of `animal`; kept as its own code because it
  is the single largest false-positive class).
- `invitro` — cell/tissue/enzyme only, no human ingestion.
- `agri` — agronomy: crop cold tolerance, storage temperature, post-harvest
  physiology, chilling injury.
- `not-ingestion` — the food reaches the subject by a route other than eating
  it (footbath, topical cream, inhalation, IV infusion), or is present in the
  setting without being consumed (occupational exposure in an orchard, food
  antigens applied in a skin test). Condition 2 is what fails, not condition 3,
  so these do not belong under `name-only`. The code has been in use since the
  golden set — `build_golden.py` defines it and `screening_golden.csv` carries
  8 rows of it — and 180 records in `screening.csv` are labelled with it; it is
  written into this list on 2026-08-12 because it was in the data and not in the
  protocol. No record's include/exclude decision turns on it: every use is an
  exclude either way, and the code only says which condition failed.
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
- **Sibling processed forms of one species** (added 2026-08-08 during the recall
  rebuild, when the widened query put green-tea trials into `black tea`'s
  candidate set): where two food_keys are *sibling* processed forms — neither is
  a food-form of the other, they are alternative treatments of the same raw
  material — a study of one is `exclude` (`species-mismatch`, naming the form)
  under the other. This covers the *Camellia sinensis* keys `green tea`,
  `black tea`, `oolong tea`, `pu-erh tea`, `hojicha`.
  (Rationale: these are not merely distinct food_keys, they carry **opposite**
  lay attributions — in `claims.csv`, green tea is cool 5/5 while black tea is
  warm 6/7 and hojicha warm 5/6 — so crediting a green-tea trial to black tea
  would attach evidence to the opposite claim, not just double-count it. The
  rule is already implicit in the existing ledger: green tea/16366740, a
  black-tea-extract supplement trial, is `include` under `black tea` and
  `species-mismatch` under `green tea`. It is stated here because the four-term
  query rarely produced cross-form candidates and the 22-term query does. It is
  the same logic as `pepper` (*Piper nigrum*) versus `chili pepper` /
  `bell pepper` (*Capsicum*), which are separate keys for the same reason.)
  Where a record genuinely studies more than one form, or is a review whose
  stated objective covers several, it is `include` under each form it actually
  examines — as green tea/16580033 and black tea/16580033 already are.
- **This is NOT a rule about base and derived forms.** Where one food_key is a
  food-form *of* another, §2 condition 2 ("the food, a food-form of it, or its
  principal dietary constituent") governs and the study counts for both. Worked
  example: `mugicha` (roasted-barley infusion) is a food-form of `barley`, so
  the roasted-barley-extract skin-temperature trials count under both keys —
  as barley/30814418 and mugicha/30814418 already do. Sibling forms exclude each
  other; a derived form does not exclude its base. The two cases are separated
  here because the widened query surfaced both at once and they pull opposite
  ways. (Consequence to keep in view: a handful of records are therefore counted
  under two foods. This is a deliberate consequence of §2.2, not an error, but it
  means L2′ across foods is not a partition of the record set.)
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
  | Recall rebuild — records the 22-term query added (134 foods, 24 bundles) | 9,550 | `claude-sonnet-5` | `claude-opus-5` |
  | Route D universe extension (9 foods, 2 bundles) | 296 | `claude-sonnet-5` | `claude-opus-5` |

  The model versions differ between batches because the screening ran across
  several working sessions as the available models changed; within every batch
  the two coders are contemporaneous. The recall-rebuild and Route D batches
  deliberately reuse the same two tiers as the batches that carry most of the
  existing judgments, so the widened record set is judged by the same instrument
  as the set it extends. Kappa is computed over all co-coded records regardless
  of batch. The instruction the coder agents receive is published as
  `screening_coder_prompt.md`; the file records the wording used for the Route D
  batch, the earlier batches having been composed per session from the same
  independence conditions and output schema without the text being kept.
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
  `coder2` are the two independent labels; `adjudicated` is `True` on every row
  carrying an author ruling and `False` where the coders agreed and no ruling was
  filed. Rulings are of five kinds, and the flag does not distinguish them —
  read `screening_rulings.csv`'s `batch` and `rationale` columns for that:
  (a) divergences, (b) coverage differences, (c) records either coder flagged
  `uncertain-species` or `no-abstract`, (d) agreed includes the §2.3 sweep
  overrode, and — since 2026-08-12 — (e) agreed excludes where the ruling fixes
  only the reason code and leaves the label untouched. (e) covers 156 `cream`
  records; 11 rows of (d) are confirmations that changed nothing either. So 167
  of the 499 flagged rows carry the same label the coders agreed on. `reason`
  carries the author's adjudication rationale on ruled rows and the coders'
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
(saved by `fetch_l2_records.py`). `screening.csv`, `screening_golden.csv`,
`screening_rulings.csv`, `screening_protocol.md` and `screening_coder_prompt.md`
are committed to the analysis repository so the include/exclude judgments are
auditable (the GPT reproducibility ask).

**Known limit of the published `reason` column.** Where both coders exclude a
record but write different codes, `adjudicate()` records coder 1's, because it
reads `reason_c1 or reason_c2`; no rule in this protocol selects between them.
Over the full ledger that applies to **1,825 of the 12,557 rows the two coders
agreed on (14.5%)**, or 15.0% of the 12,172 they both excluded; before the Route
D batch it was 1,628 of 12,263 (13.3%), or 13.7% of 11,883. The largest classes
are pairs where both codes are literally true of the record — `animal`/
`name-only` 424, `name-only`/`no-thermal` 297, `animal`/`invitro` 143,
`animal`/`livestock-heat` 136, `invitro`/`name-only` 109, counted over the
pre-Route-D agreed exclusions.

Agreed *includes* are excluded from those counts. Their `reason` is a free-text
description of the study rather than a code, so it differs between coders in 371
of 380 cases and would inflate the figure to 1,999 without saying anything about
the exclusion breakdown, which is the only thing this limit reaches. It touches
no include/exclude decision, no κ and no L2′.

Unlike Axis A, whose §9.4 already fixed an order the codes could be resolved in,
§2 states no order, so settling this would mean writing a new rule rather than
applying an existing one. It is recorded here rather than resolved.

## 8. Claim-directed vs incidental sub-label (added 2026-08-12)

§2 asks whether a record is *on-construct* — a human ingesting the food, with a
qualifying thermal outcome. It does not ask whether the study set out to answer
the question the lay sources answer, and the two come apart. `chicken`/41901102
and `chicken`/42072392 are ingestion trials of chicken meat with microvascular
outcomes, and neither was designed to ask whether chicken warms the body. The
external review of 2026-08-12 named the gap — *on-construct is not the same as an
explicit test of the folk claim* — and this section adds the sub-label under
which the primary model can be refit on the narrower reading.

**Scope.** The pass runs over the records already settled as `include` (298 at
the time of writing, 284 of them in the Tier-1 primary frame) and over nothing
else. It **cannot change a `final_label`**. A coder who thinks a record should
never have been included says so in `reason`; the author then handles it as a
§2.3-style ruling in `screening_rulings.csv`, where such a change belongs, and
not here. `screening.csv` itself is not rewritten by this pass: the sub-label is
published as its own ledger (below) and joined by the analysis code at read time,
so L2′ as reported is provably untouched by anything decided under this section.

**Unit.** (food_key, pmid), as in §2 — the question is about *this* food, and a
record can be claim-directed for one food and incidental for another. The 298
rows cover 263 distinct records; 32 of those records are judged under more than
one food.

### The two values

- **`claim-directed`** — the study's own research question is whether ingesting
  this food, a food form of it, or its principal dietary constituent (§3) changes
  a thermal outcome of §2 condition 3. Operationally: the thermal outcome is a
  primary or co-primary endpoint **and** the food is the exposure the study is
  about.
- **`incidental`** — the record qualifies under §2, but the study is asking
  something else, and the qualifying outcome is measured in service of that
  question or reported alongside it. Questions seen in this corpus include weight
  loss and body composition, endothelial or cardiovascular function, exercise
  performance, glycaemic control, metabolisable-energy accounting and disease
  markers; the list is illustrative and not a closed set, so a question that is
  none of these is still `incidental` if the thermal outcome is not what the
  study was built to move.

**Where the question is read from** (added after the canary rounds, 2026-08-12).
The study's own framing is its **title and the aim or objective sentences of its
abstract** — the two *places* the authors state what the report is about. Not the
journal's scope, not what studies of that food usually ask, not the discussion's
speculation about implications. The review clause below already read the
judgment off the "stated objective"; that is the general test, and it is stated
here so it is not applied to reviews alone. Where an abstract is unstructured and
carries no aim sentence — common in older reviews — its opening topic sentence is
its framing; the absence of a labelled objective is not by itself an
`unclear-question`.

The `claim-directed` conjunction therefore has two **conditions**, and a record
is `incidental` when **either** fails. (Conditions and places are different
things: the two conditions are what must be true, the two places are where to
look for them.)

1. **The framing names this food** — the food, a food form of it, or its
   principal dietary constituent — **as what is given or varied.** A record where
   the food is present in every arm while something else is what varies fails
   here: it is the vehicle, not the exposure. Worked example — `cheese`/20613890,
   "Postprandial energy expenditure in whole-food and processed-food meals",
   contrasts two meals differing in processing, with cheese in both, so its
   subject is processing rather than cheese: `incidental`. Varying the *amount*
   or the *form* of the food itself does not fail this condition;
   `barley`/23742725 varies the molecular weight of barley β-glucan and its
   subject is still the β-glucan. Neither does being one component of a
   fixed-combination product: the `confounded` clause below keeps such records in
   play, so `chicken`/14974736 and `black tea`/16366740 both pass condition 1 and
   are separated by condition 2.
2. **The framing names a thermal outcome of §2 condition 3 as something being
   measured.** A record where the title and aim name a different outcome, and the
   qualifying measurement appears only further down the results, fails here. The
   §2 include already settled that the record's measurement *is* thermal, so this
   condition asks only whether the framing names it, not whether it qualifies.

**One class this does not settle, by design.** Where the framing names a
*category* — dietary protein source, a festive meal — and this food is the
instance chosen to stand for it, the two canary coders divided and neither
reading is forced by the text above: the category is what the study is about, and
the food is named inside it. `beef`/26821042 ("Effects of Dietary Protein Source
and Quantity during Weight Loss") is the instance. Rather than write a rule that
would settle it by fiat after seeing how the coders split, records of this shape
are left to divide and the author adjudicates them, which is what §5's machinery
is for.

**The test is the study's question, not its motivation.** Almost nothing in this
corpus cites a Japanese warming or cooling belief, so a rule that required the
citation would return `incidental` for nearly every record and would be measuring
the citation habits of nutrition journals rather than what was studied.
`claim-directed` is the closest observable proxy for *the claim was put to the
test*: the thermal effect of eating the food is the thing the study set out to
measure. Any report of this sub-label must say so. It does not license the phrase
"tested the folk claim", and the §2 sentence it refines — the construct is the
study's outcome, not its motivation — stands.

**The test is not study quality.** §2 refuses quality grading and this section
keeps that refusal. A small single-arm trial whose question is the thermal effect
is `claim-directed`; a large well-controlled trial that measures skin blood flow
as one secondary outcome of a lipid study is `incidental`.

### Boundary rules

- **Reviews** (`review`, §3). Judge the review's stated objective by the same
  test. §3 already admits a review only where its objective is the thermal,
  thermogenic or energy-metabolism effect itself, so a review that survived
  screening is normally `claim-directed`; it is `incidental` where the stated
  objective is broader and the thermal material is one strand within it.
- **Isolated constituents and supra-dietary doses** (`constituent`, `supradose`,
  §3). The constituent stands in for the food, so a study asking whether
  capsaicin raises energy expenditure is `claim-directed` under `chili pepper`.
  Dose does not enter this judgment: `supradose` already carries it and is
  dropped in its own sensitivity variant.
- **Mixed interventions** (`confounded`, §3). Confounding is a property of the
  design, not of the question. A trial asking whether a ginger drink taken with
  exercise raises energy expenditure, with no way to separate the two, is
  `claim-directed` and stays `confounded`.
- **Multi-arm and multi-food studies.** Judge per food. Where several foods are
  arms of one trial whose question is their thermal effect, each is
  `claim-directed`. Where this food is a comparator chosen to answer a question
  about something else, it is `incidental`. (A food present only as a vehicle is
  an §2 exclusion, not an incidental include.)
- **Secondary analyses and sub-studies.** Judge the report in hand, not its
  parent trial. A secondary analysis whose own question is the thermal outcome is
  `claim-directed` even where the parent trial was about weight loss.
- **Composite metabolic endpoints.** Resting and postprandial energy expenditure
  is the recurring hard case, and the role test of §2.3 settles it here too:
  where energy expenditure, DIT or TEF is the endpoint the study is built around
  and reports as its result, `claim-directed`; where it is one of a panel of
  measures supporting a conclusion about something else, `incidental`. The
  conclusion being supported is not always about weight — gastric emptying and
  glycaemic response are the other panel this corpus contains — so read the
  framing rather than matching against a list of rival outcomes. Where the
  thermal outcome is named in **both places — the title and the aim** — being one
  of several co-equal aims does not demote it: `agar`/23872837 and
  `barley`/23742725 each name diet-induced thermogenesis in the title and in the
  aim, alongside gastric emptying and glycaemic response, and both are
  `claim-directed`. Where this pulls against the review clause's "one strand
  within a broader objective", **this clause governs** — a thermal aim named in
  both places is not demoted by having company, and `chili pepper`/33789250
  ("Effects of Red Pepper, Ginger, and Turmeric on Energy Metabolism", objective
  naming weight control, weight loss and energy metabolism) is `claim-directed`
  on that order. Worked
  example the other way — `chicken`/11676025, "Effects of chicken essence tablets
  on resting metabolic rate", is `claim-directed`; the two enriched-meat trials
  above are `incidental`, their framing naming microvascular and endothelial
  function.

### When the record does not say

- `no-abstract` — three of the 298 carry no abstract. The coder gives its best
  label from the title and flags the record **unconditionally**, which routes it
  to the author as in §5. ★ This is deliberately stricter than §2's version of
  the flag, which lets a sufficient title settle the record: §2 asks four
  questions a title can answer, while §8 asks what the study was built to
  measure, and a title states the titled question without ruling out that an
  unnamed endpoint shared primacy with it. Both canary coders read "Effect of
  ginger on metabolic rate" as settling the question and did not flag it, which
  is why the rule is written out here rather than left to the analogy with §2.
- `unclear-question` — the abstract reports outcomes but never states what was
  being asked. Flag it rather than guessing; the author settles it from the full
  text. This flag exists only in this section.

Neither flag is a third value: `sub_label` always carries one of the two labels
and the flag travels in `reason`, so a routed record still records what the
coders thought rather than a blank.

### Output

- `data/screening_claim_directed.csv` — `pmid, food_key, coder1, coder2,
  adjudicated, sub_label, reason`, one row per included (food_key, pmid).
- `data/screening_claim_directed_rulings.csv` — `food_key, pmid, sub_label,
  rationale, batch`, the author's ruling ledger, in the same shape and the same
  role as `screening_rulings.csv`.
- The analysis joins the ledger onto the screening ledger in memory and refits
  the primary model with the `incidental` records dropped (`src/claim_directed.py`,
  reported by `src/verify_stats.py` beside the other definition-sensitivity
  variants). This is a **sensitivity analysis, not a redefinition of L2′**.

### Coders and agreement

The instrument is the one §5 describes: two coders, `claude-sonnet-5` (c1) and
`claude-opus-5` (c2), each given this protocol and its assigned records, with the
other coder's labels and the reconciliation code withheld. Each record is
presented with its title, abstract, publication types and the §3 sub-labels
already settled for it, since those are part of the screening judgment this pass
builds on rather than another coder's opinion about the question at issue. κ is
computed on the co-coded records, categories = {claim-directed, incidental}, and
the within-lineage caveat of §5 applies unchanged — the pair bounds how stably
one model family applies this section, and is not an independence-based
reliability estimate. Divergence target κ ≥ 0.60; below it the definitions here
are refined and the pass re-run, rather than the labels being hand-fixed.

### Canary rounds (2026-08-12)

This section was written before any record was judged under it. It was then
calibrated the way the Axis A coding protocol was (project decision D55): a
20-record canary stratified over the boundary clauses above — reviews,
constituents, confounded designs, absent abstracts, records judged under more
than one food, and plain cases — was coded by both coders twice, and both times
the coders were asked to report every clause they had to stretch rather than only
to label.

| Round | κ (20 records) | Observed agreement | Divergences |
|---|---:|---:|---:|
| 1 | 0.588 | 80.0% | 4 |
| 2 | 0.886 | 95.0% | 1 |

**Round 1** fell below the 0.60 target, and its four divergences were two classes
the coders had independently named: records whose framing lists a thermal outcome
among several co-equal aims (`agar`/23872837, `black tea`/16580033,
`chili pepper`/33789250), and one where the food sits in every arm while
something else varies (`cheese`/20613890). Both coders also reported that the
`no-abstract` clause, written as an analogy to §5, left them importing §2's
"a sufficient title settles it" carve-out — which neither §8 nor the instruction
they were given actually stated.

The revisions those findings produced are restatements of what this section
already said rather than new criteria: the "where the question is read from"
paragraph generalises the review clause's own "stated objective"; the conjunction
was already a conjunction; the composite-endpoint clause lost a weight-loss
trigger it should never have been specific to; the illustrative list of rival
questions had been closed by accident; and the `no-abstract` rule was written out
instead of being left to an analogy.

**Round 2** left one divergence, `beef`/26821042, and coder 2 named it as the
judgment it had stretched furthest. It is the category-instance class recorded
above as deliberately unsettled, so it was not legislated away. Round 2 also
found a genuine defect introduced by the round-1 revision — the word "halves" had
been used for both the conditions and the places, and the ambiguity was
load-bearing on at least one record. That wording is fixed above; the fix states
the reading both round-2 coders had already adopted, so it is not expected to
move labels, and the full pass re-codes these 20 records, which makes it
checkable rather than assumed.

**No canary label was carried forward.** All 20 records are re-coded in the full
pass under the final text, so no record's sub-label was decided under a
superseded reading. The canary outputs are retained under
`data/screening_work/cd_canary/` (git-ignored, like the other coder
intermediates) as the evidence for the revisions.

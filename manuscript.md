# Widely Believed, Rarely Tested: A Screened Bibliometric Map of Warming and Cooling Food Claims in Japan

**Running title:** Research attention to warm/cool food claims tracks literature volume, not lay coverage

## Authors

Mizuki Shirai, MHS^1^

^1^ Specified Nonprofit Corporation Rehabilitation Collaboration, Suita, Osaka, Japan

<p style="text-align: left;"><strong>Corresponding author:</strong> Mizuki Shirai, MHS, Specified Nonprofit Corporation Rehabilitation Collaboration, Suita, Osaka, Japan. Email: rehabilitation.collaboration@gmail.com. ORCID: 0009-0005-3615-0670.</p>

---

## Abstract

**Background:** In Japan, the folk practice of *onkatsu* ("warming care") rests on a widely shared belief that particular foods warm or cool the body. Prior reviews establish that scientific support for hot–cold food theory is heterogeneous rather than absent, but none has asked, food by food, whether the claims that circulate most widely are the ones that have actually been examined.

**Methods:** We built a two-axis bibliometric map. Axis A counts, per food, how many independent Japanese lay-facing sources assign it a warming or cooling direction, from a frame of 15 sources frozen in advance; the nine corporate/association sources form the primary frame. Axis B counts PubMed hits for each food co-occurring with four thermal-effect terms, then screens every hit, because the raw count measures keyword co-occurrence rather than the intended construct. Two independent large language models from different families labelled all 2,887 records include/exclude, with the author adjudicating divergences (Cohen's κ = 0.811). The planned primary analysis regressed "has any surviving study" on lay-source coverage, adjusted for log total literature volume (L1).

**Results:** Screening removed 96% of the raw signal: 2,718 raw hits across 146 foods became 102 on-construct studies, and 118 foods (80.8%) had none. Lay-source coverage did not predict whether a food had been studied (OR 1.015, 95% CI 0.824–1.251, p = 0.888), whereas literature volume did (OR 1.728, 95% CI 1.321–2.260, p < 0.001). The unadjusted rank correlation was positive (ρ = +0.211, p = 0.011) and did not survive adjustment. Chicken, believed warming by six sources, returned 278 raw hits and no on-construct study.

**Conclusions:** How widely a warming/cooling claim circulates is unrelated to whether it has been directly examined; what predicts examination is how much the food is studied for any reason.

**Keywords:** attention gap; bibliometrics; folk nutrition; warming and cooling foods; thermoregulation; abstract screening; Japan

---

## Introduction

The idea that individual foods "warm" or "cool" the body is a durable feature of everyday health culture in Japan, where it underpins the popular practice of *onkatsu* (温活, "warming care") and lay reasoning about *hiesho* (冷え症, habitual cold sensitivity). Corporate wellness media, food manufacturers, and individual practitioners routinely publish lists that sort ginger, carrot, and burdock as "warming" and cucumber, tomato, and coffee as "cooling," and these attributions circulate widely enough to shape ordinary purchasing and seasonal eating advice. That the belief is culturally established, rather than niche, is visible both in the volume of lay-facing sources that maintain such lists and in the fact that Japanese epidemiology has taken the classification seriously: Nagata et al. (2017), analyzing the Takayama cohort (n = 28,356), applied four independent warm/cool food-classification lists to real dietary data. The premise of the belief is therefore neither obscure nor recent.

Crucially, the scientific literature on warm/cool food theory is not empty, and this study does not claim that it is. Ormsby (2021), in a scoping review of the nutritional evidence, characterized the support as "heterogeneous and of mixed quality" while identifying partial mechanistic correlates — heating foods associated with higher caloric density, sympathetic activation, and vasodilation, and cooling foods with higher water and fiber content and anti-inflammatory processes. Namiranian et al. (2021), a companion review in the same volume, surveyed the physiological basis of hot/cold theory across Persian medicine, traditional Chinese medicine, and Ayurveda. Zhou & Xu (2021) integrated candidate molecular mechanisms (for example, differential NF-κB and MAPK signaling) linking the cold/hot nature of foods to biological effects — while explicitly noting that research applying these mechanisms to foods is scarce relative to research on Chinese medicines. Any framing of the field as an "evidential desert" is thus untenable; the appropriate description is fragmentary, unintegrated, and unevenly attended.

At the level of individual foods, the available evidence is not only fragmentary but sometimes contradictory or opposite to belief. Ginger, the archetypal "warming" food, showed a significantly enhanced thermic effect of food in one small randomized crossover pilot (Mansour et al. 2012, n = 10 overweight men), yet a larger, double-blind crossover trial in a different population reported no such increase (Fagundes et al. 2021, n = 20 normal-weight women). Coffee, popularly classified as "cooling" (or "yin") in Japan, is dominated by caffeine, whose best-powered synthesis under thermal stress — a meta-analysis of k = 30 studies — found that caffeine significantly *raises* peak core temperature (Hedges' g = 0.44; Peel et al. 2025). The physiological direction most relevant to coffee's principal active compound therefore runs opposite to the folk attribution, even after allowing for the distinct measurement context (heat-exposure performance settings rather than everyday thermal sensation).

Methodologically, the practice of mapping a hot–cold belief system bibliometrically has direct precedent. García-Hernández et al. (2023) assembled and classified 101 academic publications spanning roughly a century to characterize Mexico's hot–cold system by research approach, depth, and conceptual domain. Nagata et al. (2017) demonstrated, within Japan, that the four extant warm/cool classification lists disagree with one another when applied to cohort data — an internal inconsistency that is itself a symptom of the field's uneven development. These works establish that belief systems of this kind can be quantified and that the classification schemes underlying them are neither unified nor exhaustively validated.

What remains unquantified is the *asymmetry* between the two facts above: that certain foods are very widely presented as warming or cooling, and that the direct scientific attention paid to those specific claims varies enormously. Ormsby (2021) asked whether mechanistic support exists but did not measure how widely each food is claimed, nor compare research volume across foods; reviews of the adjacent clinical concept of cold hypersensitivity (Jin et al. 2025, 65 studies) consistently take traditional-medicine interventions, not lay food beliefs, as their subject. We therefore ask a descriptive question: across the foods that Japanese lay sources classify as warming or cooling, is the breadth of that lay coverage related to whether the specific thermal claim has been directly studied — and, if there is any apparent relationship, does it survive adjustment for how much the food is studied for any reason at all?

Answering that question turns out to depend on a measurement problem that a keyword count cannot solve, and addressing it is the methodological contribution of this paper. Counting how often a food name co-occurs with thermal vocabulary in PubMed does not count studies of that food's thermal effect in people: the co-occurrence set is dominated by poultry and livestock heat-stress research, and it misses the nutrition trials that report the thermic effect of food. We therefore screened the entire co-occurrence set to the intended construct before analysing it, using two independent language models with author adjudication — a design with recent published precedent in evidence synthesis (Guo et al. 2024; Hilkenmeier et al. 2026).

---

## Methods

### Design

This is a descriptive, cross-sectional bibliometric study. It maps two independently constructed axes against each other for a fixed set of foods and reports their association; it does not estimate a causal effect of lay coverage on research or vice versa. Because the study was not registered on any protocol registry, we describe fixed-in-advance choices as *planned* rather than pre-specified.

### Axis A: lay-source coverage

Axis A quantifies how many independent Japanese lay-facing sources assign each food a warming or cooling direction, following the bibliographic-coding approach of García-Hernández et al. (2023). We use "coverage" rather than "belief" throughout: the measure counts sources that publish an attribution, and is a proxy for — not a measurement of — how widely the attribution is actually held.

The sampling frame was frozen in advance: 15 sources verified to be reachable over HTTP, to present a concrete per-food warm/cool list, and to permit fetching per robots.txt. Nine corporate- or association-operated sources form the **primary (Tier 1) frame**; six individual-expert blogs form a **Tier 2 sensitivity frame**, which the coding protocol reserves for testing whether conclusions are stable. Sources sharing a single operator were counted once. Two frame corrections were made during fetching and before any coding of results — one source lacking a concrete per-food list was excluded, and one source's URL was corrected to its per-food list page — with both decisions driven by page content rather than by any result.

Each source page was fetched once, on 2026-08-03 (one source re-fetched 2026-08-04 at its corrected URL), and stored locally; the per-source access dates are published in `data/sources.csv`. Every food mentioned was then coded for its direction (warming, cooling, or neutral), with the verbatim supporting quotation recorded on each row. Coding rules were documented before coding: sources using traditional five-nature or yin–yang vocabulary were mapped to warming (温性/熱性/陽性), cooling (涼性/寒性/陰性), or neutral (平性); serving temperature (e.g. "cold drinks") is not a food's nature and was not coded as one. For each food, Axis A records the number of independent sources assigning a direction (`n_sources`), the majority direction, and a consensus ratio.

**Who coded, and what the agreement statistic can support.** All coding was performed by large language models operating under the author's direction; there were no human raters. Each source was coded twice, independently: the first pass over six Tier-1 sources by Claude Opus 4.8 reading the stored text, the remaining nine sources by separate Claude Sonnet 4.6 agents, and the second pass throughout by further Claude Sonnet 4.6 agents that received only the protocol and the stored source text, with the first coder's output withheld. Codings were reconciled on the (source, food, condition) key. Cohen's κ was 1.000 over **481 co-coded items** across the two rounds, with no direction disagreements; the 190 coverage differences (a food one coder recorded and the other did not) were adjudicated individually against the source text, which dropped eleven records that carried no nature attribution in the source, added one the first coder had missed, and corrected three misread directions.

Because the second round's two coders are independent instances of the *same* model, that κ measures the stability of one model's reading rather than the convergence of two independent judgments. It is an upper-bound-leaning reliability estimate and is not comparable to a κ between human raters — a point we return to in the Limitations. The reproducibility evidence we rely on instead is deterministic: `verify_claims.py` checks that every retained row occurs verbatim in the stored source text, and every row carries its source, quotation, and access date, so the coding can be re-derived from the published frame rather than taken on trust.

Coding yielded 649 rows and 196 distinct foods. Of these, 157 are covered by at least one Tier-1 source; 11 are composite category labels ("nuts," "spices," "shellfish," "leafy greens" and similar) that cannot be turned into a single unambiguous search query and were excluded from Axis B, leaving **146 foods** in the primary analysis. A normative five-nature classification, against which lay attribution could be benchmarked, was planned but is deferred to future work because a citable primary source could not be secured within scope.

### Axis B: on-construct research attention

**Raw counts.** Axis B begins from the NCBI PubMed E-utilities (no API key; queries rate-limited under 3 requests/s). All PubMed, CiNii, and OpenAlex queries were executed on 2026-08-06 to 2026-08-07; because bibliometric counts grow over time, this snapshot fixes the reported values. For each food we counted hits at two nested layers: **L1**, the food term alone, as total research volume; and **L2**, the food term co-occurring with any of four thermal-effect terms — *thermogenesis*, *body temperature*, *peripheral circulation*, *thermoregulation*. The four-term vocabulary was frozen after a one-time validity check on real hits: adding human cold-sensitivity terms recovered no additional relevant studies for ginger, whereas adding plant "cold tolerance" terms injected agronomy noise. Japan-specific foods with weak English coverage were given minimal English synonyms (for example, natto → "fermented soybean"); the inclusion criterion was held constant across foods so that counts are comparable. Queries are built deterministically from each food's key, and the raw count response for every query is published, so each reported count is pinned to its retrieval snapshot.

**Why the raw count is not the measure.** L2 counts keyword co-occurrence, not studies of the construct. Inspection showed both failure directions: `chicken` returned 278 hits dominated by avian thermoregulation and poultry heat-stress research, while ginger's thermic-effect and energy-expenditure trials — the studies most relevant to the warming claim — were largely missed by the four seed terms. An analysis built on L2 would therefore report the research attention paid to a keyword pattern, not to the belief.

**Screening.** We retrieved the title, abstract, journal, and publication types for every L2 hit and screened all **2,887 records across 107 foods** to a single construct: *a study of the thermal effect, on a human, of ingesting the food or its principal dietary constituent*. The include/exclude definition is documented in `data/screening_protocol.md` and fixed before coding. Include requires all of: human subjects in vivo; oral ingestion of the food, a food form of it, or its principal dietary constituent; a thermal-related physiological outcome (core, peripheral, skin, tympanic or axillary temperature; thermogenesis or thermic effect of food; energy expenditure reported in a thermogenic context; peripheral circulation; thermoregulation or cold tolerance; subjective thermal sensation); and attribution of the outcome to the food as the exposure of interest. Exclusions are coded by reason (`animal`, `livestock-heat`, `invitro`, `agri`, `name-only`, `no-thermal`, `mechanism-only`). Isolated constituents given at dietary doses (caffeine for coffee, capsaicin for chili pepper) are included and sub-labelled; a different species in the same family is excluded, so that *Aframomum* and *Kaempferia* studies do not inflate "ginger." No quality grading was performed — this is construct-validity screening, not risk-of-bias assessment. The 68 queried foods with zero L2 hits have L2′ = 0 by construction and required no screening; foods queried but not screened would be recorded as missing rather than zero, and there were none.

**Screening reliability.** Every record was labelled independently by two large language models drawn from **different model families**, so that the pair does not share one model's blind spots: Claude Sonnet 4.6 with Claude Opus 4.7 for the five golden-set foods, and Claude Sonnet 5 with Claude Opus 5 for the remaining 102 foods. Model versions differ across batches because screening ran over several working sessions; within each batch the two coders are contemporaneous and cross-family. Each agent received the protocol and its assigned records only — the other coder's labels, the golden set, and the reconciliation code were withheld. Cohen's κ was **0.811 on all 2,887 co-coded records** (observed agreement 0.984), with 45 divergences; the author adjudicated 56 records against title and abstract — every divergence, plus every record either coder flagged as not stating the subject species or as having no abstract, since agreement reached on information a record does not contain is not evidence about that information. Before full screening, the author hand-labelled a 169-record golden set (29 include, 140 exclude) spanning the foods where the include boundary actually lives; against it, coder 1 achieved precision 0.867 / recall 0.897 / F1 0.881 and coder 2 precision 0.813 / recall 0.897 / F1 0.853. Gold labels for records whose abstract does not state the subject species were set from PubMed Humans/Animals MeSH headings or full text, never by inference; this check corrected one gold label, and the correction was surfaced by a coder divergence rather than by the author's own review.

**Auxiliary databases.** OpenAlex (keyword-based) and the CiNii Research API (Japanese-language literature) were queried as auxiliary columns. OpenAlex `search=` is a full-text match and returns counts an order of magnitude larger than PubMed `[tiab]`, so the two are reported separately and never summed. The CiNii query retrieves the Japanese food name alone — an L1-equivalent total, **not** a thermal-context count; it therefore bounds how much Japanese-language literature exists on each food but does not establish that a food's thermal claim is unstudied in Japanese. The primary axis is the screened PubMed count.

### Analysis

The analysis plan was fixed before any estimate was computed and is recorded in the project PLAN. The **primary model** is a logistic regression of whether a food has any on-construct study (L2′ > 0) on lay-source coverage (`n_sources`), adjusted for log(L1 + 1); the unadjusted fit is reported beside it. A binary outcome is what the data can support — L2′ is sparse, with most foods at zero and most non-zero foods at one or two studies — and "which foods have no direct research" is the paper's question. **Reported alongside** are Spearman rank correlations of coverage against L2′, against raw L2, and against L1, so that the effect of screening and the role of literature volume are both legible. The **sensitivity model** is a negative binomial regression of L2′ with log(L1 + 1) as an offset, fitted after a Poisson over-dispersion check (Green 2021; the model class has bibliometric precedent in Millones-Gómez et al. 2023). Branch conditions were fixed in advance: if the negative binomial failed to converge it would be reported as such rather than replaced by a zero-inflated model, which this many zeros over this few foods cannot identify; and a null primary result would be reported as no detected association rather than treated as a failed study.

Two analyses are reported that were **not** in the fixed plan and are labelled as such wherever they appear: the rank correlation of coverage against the L2′/L1 ratio, and the refit of the primary model under the Tier 1+2 frame. Both were computed after the primary estimates and neither is used to support a conclusion.

The zero-research rate is reported at every level of lay-source coverage rather than at selected thresholds, so that no cut-point is chosen after seeing the data. Warming and cooling foods are compared on the zero-research contrast (Fisher exact) and on L2′ (Mann–Whitney U) within the core set. All tests are two-sided at α = 0.05; only the primary logistic model is confirmatory, and the remaining comparisons are descriptive and reported without correction for multiplicity. Ninety-five-percent confidence intervals use the Fisher z-transformation with the Bonett–Wright variance for rank correlations, profile bounds for regression coefficients, Woolf's logit method for the odds ratio, and Wilson score intervals for the proportions in Figure 1. Analyses used Python 3.14.3 with pandas 3.0.1, scipy 1.17.1, numpy 2.4.2, statsmodels 0.14.6, and matplotlib 3.10.8; the pipeline is covered by 100 unit tests (all passing), and every statistic reported here is recomputed from the pipeline output by `src/verify_stats.py`. Figure labels are English-only to avoid CJK-glyph problems in the PDF build (weasyprint 68.1).

---

## Results

### Sample and the effect of screening

Axis A coding covered 196 distinct foods across 15 sources. Under the primary Tier-1 frame, 146 queryable foods carry at least one source attribution: 51 reach three or more sources (the *core* set), 28 have two, and 67 have one (Table 1). Among the 51 core foods, 31 are lay-classified warming, 19 cooling, and one contested.

Screening changed the measure substantially. Across the 146 foods in the primary frame, 2,718 raw L2 hits reduced to **102 on-construct studies** — a 96.2% reduction (Table 2). Two-thirds of the exclusions are animal research: 1,530 records were excluded as `animal` and a further 376 as `livestock-heat`, together 68.5% of all exclusions. The next largest class, `name-only` (549 records, 19.7%), covers studies where the food term matched but nothing about ingestion and body temperature was at issue. Only 106 records across the full 175-food query universe survived as on-construct studies, of which 86 are primary reports and 20 are reviews or meta-analyses of human thermal-ingestion evidence.

The screening behaved as intended on the foods that motivated it. **Chicken fell from 278 raw hits to zero**: no study in that set examined a human eating chicken and measured a thermal outcome. Lamb (107 → 0) and soybean (68 → 0) behaved the same way. Ginger moved in the opposite direction, recovering the thermic-effect and energy-expenditure trials the seed vocabulary had missed (35 raw → 7 on-construct, including Mansour et al. 2012). Milk fell from 586 to 6 (Table 5).

### Lay-source coverage does not predict whether a food has been studied

Of the 146 foods, **118 (80.8%) have no on-construct study at all**, and among the 51 core foods the rate is 37/51 (72.5%).

In the planned primary model, lay-source coverage did not predict whether a food had any on-construct study: **OR 1.015 per additional source (95% CI 0.824–1.251, p = 0.888)**. Literature volume did: **OR 1.728 per unit of log(L1 + 1) (95% CI 1.321–2.260, p < 0.001)**; model pseudo-R² = 0.176 (Table 3). Unadjusted, the coverage estimate is larger and does not reach significance (OR 1.185, 95% CI 0.987–1.423, p = 0.070).

The rank correlations show why adjustment matters. Coverage correlates positively with the screened count (ρ = +0.211, 95% CI +0.048 to +0.362, p = 0.011) — but it also correlates, more strongly, with the food's total literature (ρ = +0.465, 95% CI +0.320 to +0.589, p < 0.001). Widely covered foods are, on the whole, foods with large general literatures; once that is accounted for, the coverage association is not distinguishable from zero. Figure 1 shows this directly: the observed proportion studied rises modestly with coverage (panel a) and rises monotonically with literature volume (panel b), and when the primary model holds literature volume fixed the coverage curves are flat at every volume level while remaining widely separated from one another (panel c).

The correlation with raw, unscreened L2 was substantially higher (ρ = +0.381, p < 0.001) than with the screened count, indicating that roughly half of the apparent coverage–attention association in the unscreened data was carried by records that do not measure the construct.

The zero-research rate does not fall as coverage widens. It is 80.8% across all 146 foods, 72.5% at three or more sources, 68.4% at four or more, 75.0% at five or more, and 81.8% at seven or more (Table 3); the confidence intervals in Figure 1a overlap throughout. The sensitivity model agreed with the primary one: Poisson deviance/df was 2.296, confirming over-dispersion, and the negative binomial with log(L1 + 1) as offset converged with a coverage IRR of 1.213 (95% CI 0.968–1.519, p = 0.093).

Refitting the primary model under the wider Tier 1+2 frame (175 foods, an unplanned check) gave the same answer: 144/175 (82.3%) with no on-construct study, coverage OR 1.006 (95% CI 0.882–1.148, p = 0.926).

### Widely covered foods with no direct study

Thirty-seven of the 51 core foods have no on-construct study (Table 4). They include the foods most consistently presented as warming or cooling: carrot, cucumber, pumpkin, and tomato at eight of nine Tier-1 sources; miso, burdock, eggplant, mango, and apple at seven. Their total literatures differ by two orders of magnitude — burdock has 323 PubMed records and tomato 38,050 — yet neither extreme has produced a study of the thermal claim.

Chicken is the sharpest case. Six Tier-1 sources present it as warming; PubMed holds 94,310 records on it and 278 in the thermal keyword context; and not one of those 278 examines a human eating chicken and measures a thermal outcome. Abundant literature, a widely published claim, and no test of that claim coexist in the same food.

### Warming versus cooling foods

Warming and cooling foods did not differ. Among core foods the zero-research rate was 22/31 (71.0%) for warming and 14/19 (73.7%) for cooling (Fisher exact OR 0.873, 95% CI 0.242–3.147, p = 1.000), and the screened counts did not differ (Mann–Whitney U = 290.5, p = 0.93; median zero in both groups). We make no claim of a warm/cool asymmetry.

### Flagship foods

Three foods illustrate that "attention present" does not resolve the question (Table 5). **Green tea** (cooling, four sources) has the most on-construct evidence in the set — 17 studies from 62 raw hits — yet that is 0.11% of its 15,476-record literature. **Coffee** (cooling, four sources) has 7 on-construct studies from 23,286 records, and the best-powered relevant synthesis reports that caffeine *raises* core temperature under heat exposure (Peel et al. 2025), opposite to the lay attribution. **Ginger** (warming, eight sources) has 7, and those studies disagree with each other: positive in Mansour et al. (2012), null in Fagundes et al. (2021). Even where the claimed context has been examined, it has been examined thinly, and in one case in the direction opposite to the belief.

---

## Discussion

Across 146 foods that Japanese lay-facing sources classify as warming or cooling, how widely a food's attribution circulates was unrelated to whether that attribution has been directly examined. What predicted examination was how much the food is studied for any reason: each unit increase in log total literature raised the odds of having an on-construct study by about three-quarters, while an additional lay source changed them by an estimated 1.5% with a confidence interval spanning both directions. The apparent positive association visible in the unadjusted data is, on this evidence, an artefact of the same foods being both widely written about and widely researched.

This is a more specific claim than the one we set out to test, and it came from taking the measurement problem seriously. An earlier version of this analysis used the raw keyword co-occurrence count and reported a near-zero correlation between coverage and attention. That correlation was not interpretable, because the count it was computed on included 1,902 animal studies and excluded the human thermic-effect trials that bear most directly on the claims. After screening, the correlation is positive rather than null — and then disappears under adjustment for literature volume, for a reason the raw analysis could not have identified. Construct validity was not a caveat on the result here; it determined what the result was.

The finding refines rather than contradicts the prior reviews. Ormsby (2021), Namiranian et al. (2021), and Zhou & Xu (2021) each establish that the field holds partial, mechanistically suggestive evidence, so "no evidence" is the wrong description; our contribution is orthogonal — we show that whatever evidence exists is distributed by general research salience rather than by which claims circulate, and is absent entirely for four-fifths of the foods that circulate at all. Zhou & Xu's observation that food-level research is scarce relative to Chinese-medicine research is echoed quantitatively here: 2,887 records that mention a food alongside thermal vocabulary yield 106 studies of a human eating that food. García-Hernández et al. (2023) showed that a hot–cold belief system can be bibliometrically mapped and found domain-specific knowledge gaps in Mexico; our two-axis design extends that from documenting that a system exists to testing, food by food, what governs whether its claims get examined. Nagata et al. (2017) found that Japan's four warm/cool classification lists disagree when applied to cohort data; that internal disunity and the pattern reported here are complementary symptoms of a field elaborated culturally faster than it has been consolidated empirically.

The practical reading is diagnostic rather than causal. Because research attention tracks a food's overall research salience, the foods most in need of direct study are systematically the ones least likely to receive it: burdock, lotus root, hojicha, and daikon are widely presented as warming or cooling and carry small general literatures, so nothing in the current allocation of research effort will bring their claims into contact with evidence. Table 4 names 37 such foods with logged, reproducible counts, and they are the concrete targets a direct-verification programme would take up.

An important interpretive caution applies to caffeine. The evidence that caffeine raises core temperature comes from heat-exposure performance settings (sport, military, and industrial contexts) rather than from studies of everyday subjective warm/cool sensation, and physiological core-temperature change is a distinct measure from felt thermal comfort. We therefore treat the coffee reversal as a well-powered example of belief-incongruent physiological evidence in a specific context, not as a refutation of the subjective experience the belief describes.

Finally, the screening pipeline is itself a transferable result. Two language models from different families, blinded to each other and to the reference labels, agreed on 98.4% of 2,887 records (κ = 0.811) — against a published human benchmark of κ = 0.46 on a comparable screening task (Guo et al. 2024) — and their 45 divergences were where the real difficulty was concentrated, including one case where the divergence exposed an error in the author's own reference labels. This is consistent with the multi-model full-agreement design of Hilkenmeier et al. (2026), and it suggests that for bibliometric work where a keyword query is a poor proxy for a construct, screening the full hit set is now tractable at a scale that would previously have ruled it out.

---

## Limitations

**First — lay-source coverage is a source count, not a measure of conviction.** Axis A counts how many independent sources publish an attribution; it does not weight by readership, and appearing in many sources is not the same as being widely believed. The frame is 15 Japanese lay-facing web sources frozen in advance and dominated by corporate and association wellness media. A different frame — print encyclopedias of *yakuzen*, or reader surveys — could shift individual foods' values. Widening the frame to include the six individual-expert blogs did not change the conclusion (OR 1.006, p = 0.926).

**Second — the coders were language models, and one reliability statistic overstates what that supports.** All Axis A coding was performed by large language models under the author's direction. In the second round both coders were independent instances of the same model, so the reported κ = 1.000 reflects the stability of one model's reading rather than agreement between two independent judgments, and it should not be read as comparable to a human inter-rater κ. The Axis B screening is stronger in this respect — its two coders come from different model families, and its κ = 0.811 is a genuine cross-model estimate — but it is still an agreement between models rather than between trained human screeners. What does not depend on model agreement is the verbatim grounding check on every Axis A row and the publication of every screening judgment with its PMID, which allow the coding to be audited directly.

**Third — the screened count is a floor, not a census.** L2′ counts studies that a four-term PubMed query surfaced *and* that survived screening. A study of a food's thermal effect phrased entirely in other vocabulary would never enter the candidate set, so L2′ under-counts by an unknown margin; the ginger recovery shows the seed terms miss real studies, and the targeted cross-check for that food family remains outstanding. Zero therefore means "no study was found by this query and screen," not "no such study exists."

**Fourth — database coverage is incomplete and the Japanese-language check is weaker than it should be.** PubMed does not index J-STAGE/CiNii, KMbase/OASIS, or CNKI, so the counts under-represent Japanese, Korean traditional-medicine, and Chinese literatures. Our CiNii query returns total counts for the Japanese food name, not thermal-context counts, so it bounds the size of the Japanese literature on each food but cannot confirm that a food's thermal claim is unstudied in Japanese. A thermal-context search of Japanese-language databases is the most direct extension of this work.

**Fifth — search terms are not equally apt for every food.** Some synonyms conflate distinctions the belief makes (green tea and black tea share *Camellia sinensis*), and the unit of the query does not always match the unit of the claim (lay sources speak of chicken breast; the query returns work on the whole species). Screening removes the resulting false positives but cannot recover a study the query never retrieved, so residual differences in query aptness remain a source of between-food measurement error.

**Sixth — cross-sectional snapshot.** Both axes were measured once, in August 2026. Lay sources are edited and PubMed counts grow, so specific values will drift, although the structural pattern is unlikely to reverse on the timescale of source updates.

**Seventh — descriptive, ecological, and unregistered.** The design identifies an association pattern across foods, not a mechanism or a cause, and food-level associations should not be read as statements about individuals. The analysis plan was fixed before estimation but was not registered on a public protocol registry, and two reported analyses were computed outside it and are labelled where they appear.

---

## References

1\. Ormsby SM. Hot and Cold Theory: Evidence in Nutrition. *Adv Exp Med Biol*. 2021;1343:87-107. doi:10.1007/978-3-030-80983-6_6. PMID: 35015278.

2\. Namiranian P, Naghizadeh A, Adel-Mehraban MS, Karimi M. Hot and Cold Theory: Evidence in Physiology. *Adv Exp Med Biol*. 2021;1343:119-133. doi:10.1007/978-3-030-80983-6_8. PMID: 35015280.

3\. Zhou Y, Xu B. New insights into molecular mechanisms of "Cold or Hot" nature of food: When East meets West. *Food Res Int*. 2021;144:110361. doi:10.1016/j.foodres.2021.110361. PMID: 34053554.

4\. Mansour MS, Ni YM, Roberts AL, Kelleman M, Roychoudhury A, St-Onge MP. Ginger consumption enhances the thermic effect of food and promotes feelings of satiety without affecting metabolic and hormonal parameters in overweight men: a pilot study. *Metabolism*. 2012;61(10):1347-1352. doi:10.1016/j.metabol.2012.03.016. PMID: 22538118.

5\. Fagundes GBP, Rodrigues AMDS, Martins LB, Monteze NM, Correia MITD, Teixeira AL, Ferreira AVM. Acute effects of dry extract of ginger on energy expenditure in eutrophic women: A randomized clinical trial. *Clin Nutr ESPEN*. 2021;41:168-174. doi:10.1016/j.clnesp.2020.10.001. PMID: 33487261.

6\. Peel JS, McNarry MA, Heffernan SM, Nevola VR, Kilduff LP, Waldron M. The effect of dietary supplements on core temperature and sweating responses in hot environmental conditions: a meta-analysis and meta-regression. *Am J Physiol Regul Integr Comp Physiol*. 2025;328(4):R515-R555. doi:10.1152/ajpregu.00186.2024. PMID: 39884667.

7\. García-Hernández KY, Vargas-Guadarrama LA, Vibrans H. Academic history, domains and distribution of the hot-cold system in Mexico. *J Ethnobiol Ethnomed*. 2023;19(1):50. doi:10.1186/s13002-023-00624-1. PMID: 37919763.

8\. Nagata C, Wada K, Tamura T, Konishi K, Goto Y. Hot-cold foods in diet and all-cause mortality in a Japanese community: the Takayama study. *Ann Epidemiol*. 2017;27(3):194-199.e2. doi:10.1016/j.annepidem.2017.01.005. PMID: 28215585.

9\. Jin MH, Park SH, Choi SJ. A Comparative Review of Clinical Studies on Cold Hypersensitivity in Korea and Japan. *J Intern Korean Med*. 2025;46(4):844-865. doi:10.22246/jikm.2025.46.4.844. (Article in Korean; not indexed in PubMed.)

10\. Guo E, Gupta M, Deng J, Park YJ, Paget M, Naugler C. Automated Paper Screening for Clinical Reviews Using Large Language Models: Data Analysis Study. *J Med Internet Res*. 2024;26:e48996. doi:10.2196/48996. PMID: 38214966.

11\. Hilkenmeier F, Stoltenberg M, Stierle C. Using full agreement across multiple large language models for title-and-abstract screening in systematic reviews: a proof-of-concept. *Syst Rev*. 2026;15(1):191. doi:10.1186/s13643-026-03228-4. PMID: 42286747.

12\. Green JA. Too many zeros and/or highly skewed? A tutorial on modelling health behaviour as count data with Poisson and negative binomial regression. *Health Psychol Behav Med*. 2021;9(1):436-455. doi:10.1080/21642850.2021.1920416. PMID: 34104569.

13\. Millones-Gómez PA, Minchón-Medina CA, Rodríguez-Salazar DY, Delgado-Caramutti JGA, Valencia-Arias A. Factors associated with scientific production citations in dentistry: Zero-inflated negative binomial regression and hurdle modelling. *F1000Res*. 2023;12:1321. doi:10.12688/f1000research.141422.1. PMID: 38973941.

---

## Ethical considerations

This study used exclusively publicly available information: aggregate bibliographic counts and public bibliographic records from public literature databases (PubMed, CiNii, OpenAlex) and publicly published lay-media web pages. No individual-level, health, or personally identifying data were accessed, and no human subjects were recruited or contacted. Because the analysis is restricted to already-public bibliographic data and public web content, it does not meet the standard threshold for human-subjects research under either domestic (Japanese Ethical Guidelines for Medical and Biological Research Involving Human Subjects, 2021 revision, for research using publicly available information) or international (e.g., 45 CFR §46.102 for non-human-subjects data) frameworks; accordingly, no institutional review board approval or waiver was sought or required. The study was conducted in accordance with the principles of the Declaration of Helsinki where applicable to research using aggregate, publicly available data.

## Acknowledgments

Large language models were used as instruments in this study, not only as writing aids, and their roles are separated here accordingly.

**As coding instruments.** Axis A attributions were coded twice independently by Claude Opus 4.8 and Claude Sonnet 4.6 (Anthropic). Axis B abstract screening was performed twice independently by cross-family model pairs — Claude Sonnet 4.6 with Claude Opus 4.7, and Claude Sonnet 5 with Claude Opus 5 — under the protocol in `data/screening_protocol.md`. Every divergence, every record flagged for missing information, and every coverage difference was adjudicated by the author against the primary record. Model versions differ across batches because the work spanned several sessions; the batch-level assignment is tabulated in the protocol files.

**As development and writing aids.** Claude Opus 4.8 and Claude Opus 5 (Anthropic) assisted with code drafting, debugging, literature-search support, and manuscript editing.

All data extraction, statistical outputs, and numerical results were independently checked by the author by re-executing the analysis code (Python 3.14.3; unit tests n = 100, all passing) and by recomputing every reported statistic directly from the pipeline output before writing. The author is solely responsible for the accuracy of the numerical results, the choice of specifications, the interpretation, and the conclusions. All references were verified against PubMed, CrossRef, and publisher records; DOIs and PMIDs were confirmed against primary source pages, and one cited work (Jin et al. 2025) is not indexed in PubMed and is cited by DOI.

## Author Contributions (Contributor Roles Taxonomy, CRediT)

Mizuki Shirai: Conceptualization, Methodology, Investigation, Data Curation, Formal Analysis, Software, Writing — Original Draft, Writing — Review & Editing, Visualization, Project Administration.

## Conflict of Interest

The author declares no conflicts of interest per International Committee of Medical Journal Editors (ICMJE) guidelines.

## Funding

This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

## Data Availability

All input data used in this study are publicly available. Axis B counts derive from the NCBI PubMed E-utilities (https://www.ncbi.nlm.nih.gov/books/NBK25501/), the CiNii Research API (https://support.nii.ac.jp/en/cinii/api/api_outline), and OpenAlex (https://openalex.org/). Query strings are generated deterministically by the published query builder (`src/food_query_terms.py`, `src/evidence_mapping.py`) from each food's key, so every query in the study can be regenerated exactly; the 875 raw count responses that those queries returned are published under `data/query_log/`, pinning each reported count to its retrieval snapshot. The one class of raw response **not** redistributed is the PubMed efetch dumps of titles and abstracts, which are third-party content; they are regenerable with `src/fetch_l2_records.py`, and every PMID they contain appears in the published screening ledger.

Axis A source pages are the 15 publicly published lay-media URLs listed in `data/sources.csv` with their access dates; the raw HTML is not redistributed, and each coded row in `data/claims.csv` carries the verbatim supporting quotation, so every attribution can be located in the live source. The full screening ledger — one row per (food, PMID) with both coders' labels, whether the author adjudicated it, the final label, and the reason code — is published as `data/screening.csv`, the hand-labelled reference set as `data/screening_golden.csv`, and the two coding protocols as `data/coding_protocol.md` and `data/screening_protocol.md`.

Analysis code (Python 3.14.3, pandas 3.0.1, scipy 1.17.1, numpy 2.4.2, statsmodels 0.14.6, matplotlib 3.10.8, weasyprint 68.1) — including the source-fetching and text-extraction scripts, the claim-coding and Axis A aggregation modules, the Axis B query builders and PubMed/CiNii/OpenAlex collectors, the record-fetching and screening modules, the query logs, the figure pipeline, and the statistical verification script (`src/verify_stats.py`) that recomputes every number reported here — is publicly available at https://github.com/rehabilitation-collaboration/warming-cooling-foods (MIT License). All numerical results reported in this manuscript are reproducible from the analysis code at repository commit ⟨COMMIT⟩, recorded as the immutable reproducibility anchor at first posting.

---

## Figure Legends

**Figure 1. What predicts whether a food has been studied for a thermal effect (n = 146).** The outcome throughout is the share of foods with at least one on-construct study (L2′ ≥ 1), on a common y axis. **(a)** Observed share by lay-source coverage, binned; group sizes are printed on the axis. **(b)** Observed share by tertile of the food's total PubMed literature (L1). **(c)** The planned primary model: fitted probability across lay-source coverage with literature volume held at its 25th, 50th, and 75th percentiles, with 95% confidence bands. Panels (a) and (b) are marginal and cannot separate the two predictors, because widely covered foods also tend to carry large literatures; panel (c) does separate them — the curves are flat across coverage and widely spaced by volume. Error bars in (a) and (b) are Wilson score intervals.

**Figure 2. Lay-source coverage against on-construct research attention, per food (n = 146).** x = number of independent Tier-1 sources assigning a warming or cooling direction; y = log10(on-construct studies + 1), so foods with no study sit on the baseline rather than being dropped by the log scale. Lay direction is encoded by both colour and marker shape (warming = vermillion circle, cooling = blue triangle, contested/neutral = grey square/diamond), so identity never rests on colour alone; the Okabe–Ito palette is colour-blind safe. Foods with no on-construct study are drawn hollow, and **marker area encodes how many foods share a position** — 118 of 146 foods sit on the baseline, which a plain scatter would render as a handful of points. The shaded region marks the core set (≥ 3 sources) with at most one study. Individual foods are named in Table 4 and in `plots/attention_gap_data.csv` rather than labelled in place, because leader lines from the baseline would cross studied foods higher up.

---

## Tables

### Table 1. Sample composition

| Set | Definition | n foods | Warming | Cooling | Contested/neutral |
|---|---|---:|---:|---:|---:|
| All coded | ≥ 1 source, any tier | 196 | — | — | — |
| Tier-1 covered | ≥ 1 Tier-1 source | 157 | — | — | — |
| **Analysed (primary frame)** | **queryable, ≥ 1 Tier-1 source** | **146** | **77** | **61** | **8** |
| — core | ≥ 3 Tier-1 sources | 51 | 31 | 19 | 1 |
| — two-source | 2 Tier-1 sources | 28 | — | — | — |
| — single-source | 1 Tier-1 source | 67 | — | — | — |

*Coding covered 196 distinct foods across 15 sources (Tier 1: 9 corporate/association; Tier 2: 6 individual-expert blogs), 649 rows, two-coder Cohen's κ = 1.000 on 481 co-coded items. Of the 157 foods with Tier-1 coverage, 11 are composite category labels ("nuts," "spices," "shellfish," "leafy greens," "citrus," "red meat and fish," "chinese tea," "yellow-green vegetables," "small fish," "fatty meat," "animal fat") that cannot be turned into a single unambiguous query and were excluded from Axis B. The 29 queried foods with no Tier-1 source lie outside the primary frame and enter only the Tier 1+2 sensitivity refit.*

### Table 2. Effect of construct screening on the research measure

| Quantity | Value |
|---|---:|
| L2 records screened (all queried foods) | 2,887 |
| Foods with ≥ 1 L2 hit / queried with none | 107 / 68 |
| Two-coder Cohen's κ (co-coded n = 2,887) | 0.811 |
| Observed agreement | 98.4% |
| Coder divergences | 45 |
| Records adjudicated by the author | 56 |
| **Records surviving as on-construct (L2′)** | **106** |
| — primary reports / reviews | 86 / 20 |
| Raw L2 → L2′ within the primary frame | 2,718 → 102 (−96.2%) |

**Exclusion reasons (n = 2,781):**

| Reason | n | Share |
|---|---:|---:|
| `animal` (non-human subjects) | 1,530 | 55.0% |
| `name-only` (food named, no thermal-ingestion question) | 549 | 19.7% |
| `livestock-heat` (farm-animal heat stress) | 376 | 13.5% |
| `invitro` | 106 | 3.8% |
| `no-thermal` (human ingestion, no thermal outcome) | 92 | 3.3% |
| `species-mismatch` (different species in the same family) | 53 | 1.9% |
| other (`not-ingestion`, `agri`, `mechanism-only`, `uncertain-species`) | 75 | 2.7% |

*Golden-set validation (169 hand-labelled records: 29 include, 140 exclude): coder 1 precision 0.867 / recall 0.897 / F1 0.881; coder 2 precision 0.813 / recall 0.897 / F1 0.853.*

### Table 3. Primary and supporting statistics (primary frame, n = 146)

| Analysis | Estimate | 95% CI | p |
|---|---|---|---|
| **Logistic, adjusted — lay-source coverage** | **OR 1.015** | **0.824 to 1.251** | **0.888** |
| **Logistic, adjusted — log(L1 + 1)** | **OR 1.728** | **1.321 to 2.260** | **< 0.001** |
| Logistic, unadjusted — coverage | OR 1.185 | 0.987 to 1.423 | 0.070 |
| Spearman ρ — coverage vs L2′ | +0.211 | +0.048 to +0.362 | 0.011 |
| Spearman ρ — coverage vs raw L2 | +0.381 | +0.227 to +0.516 | < 0.001 |
| Spearman ρ — coverage vs L1 | +0.465 | +0.320 to +0.589 | < 0.001 |
| Negative binomial (offset log(L1+1)) — coverage | IRR 1.213 | 0.968 to 1.519 | 0.093 |
| Fisher exact — warming vs cooling zero rate (core) | OR 0.873 | 0.242 to 3.147 | 1.000 |
| Mann–Whitney U — warming vs cooling L2′ (core) | U = 290.5 | — | 0.930 |

**Zero-research rate at each level of lay-source coverage:**

| Coverage ≥ | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Foods | 146 | 79 | 51 | 38 | 24 | 19 | 11 | 6 |
| No on-construct study | 118 | 58 | 37 | 26 | 18 | 15 | 9 | 4 |
| % | 80.8 | 73.4 | 72.5 | 68.4 | 75.0 | 78.9 | 81.8 | 66.7 |

*Primary model pseudo-R² = 0.176; 28 of 146 foods have ≥ 1 on-construct study. Poisson deviance/df = 2.296 confirmed over-dispersion before the negative binomial was fitted. The unplanned Tier 1+2 refit (n = 175) gave coverage OR 1.006 (0.882–1.148), p = 0.926, with 144/175 (82.3%) having no on-construct study. The unplanned coverage-vs-(L2′/L1) rank correlation was ρ = +0.187 (+0.024 to +0.340), p = 0.024. Only the adjusted logistic model is confirmatory; the rest are descriptive and uncorrected for multiplicity.*

### Table 4. The 37 core foods with no on-construct study, by lay-source coverage

| Food | Lay direction | Sources | Total literature (L1) | Raw L2 | On-construct (L2′) |
|---|---|---:|---:|---:|---:|
| carrot | warming | 8 | 5,702 | 0 | 0 |
| cucumber | cooling | 8 | 12,174 | 4 | 0 |
| pumpkin | warming | 8 | 2,631 | 2 | 0 |
| tomato | cooling | 8 | 38,050 | 6 | 0 |
| miso | warming | 7 | 1,158 | 4 | 0 |
| burdock | warming | 7 | 323 | 0 | 0 |
| eggplant | cooling | 7 | 2,072 | 0 | 0 |
| mango | cooling | 7 | 3,627 | 5 | 0 |
| apple | warming | 7 | 23,770 | 17 | 0 |
| pineapple | cooling | 6 | 2,494 | 2 | 0 |
| melon | cooling | 6 | 3,898 | 5 | 0 |
| grape | warming | 6 | 17,722 | 14 | 0 |
| green onion | warming | 6 | 401 | 0 | 0 |
| watermelon | cooling | 6 | 3,146 | 4 | 0 |
| chicken | warming | 6 | 94,310 | 278 | 0 |
| natto | warming | 5 | 1,685 | 1 | 0 |
| tofu | cooling | 5 | 1,188 | 2 | 0 |
| lotus root | warming | 5 | 270 | 0 | 0 |
| tuna | warming | 4 | 3,715 | 28 | 0 |
| lettuce | cooling | 4 | 8,839 | 3 | 0 |
| kimchi | warming | 4 | 1,180 | 2 | 0 |
| cherry | warming | 4 | 7,209 | 1 | 0 |
| onion | warming | 4 | 7,727 | 2 | 0 |
| brown rice | warming | 4 | 2,040 | 0 | 0 |
| daikon | contested | 4 | 245 | 0 | 0 |
| white rice | cooling | 4 | 1,514 | 1 | 0 |
| hojicha | warming | 3 | 29 | 0 | 0 |
| sweet potato | warming | 3 | 3,941 | 1 | 0 |
| chinese cabbage | cooling | 3 | 2,115 | 2 | 0 |
| sake | warming | 3 | 5,244 | 7 | 0 |
| soy sauce | warming | 3 | 1,264 | 0 | 0 |
| spinach | cooling | 3 | 9,863 | 3 | 0 |
| vinegar | cooling | 3 | 3,419 | 5 | 0 |
| prune | warming | 3 | 1,957 | 1 | 0 |
| buckwheat | warming | 3 | 2,799 | 1 | 0 |
| cocoa | warming | 3 | 4,859 | 16 | 0 |
| kiwi | cooling | 3 | 1,195 | 2 | 0 |

*"Raw L2" is the unscreened keyword co-occurrence count. Every one of these 37 foods has at least three independent Tier-1 sources assigning it a thermal direction and no study, in the screened set, of a human ingesting it with a thermal outcome measured.*

### Table 5. Flagship foods: total volume, keyword hits, and on-construct studies

| Food | Lay direction | Sources | L1 total | Raw L2 | L2′ | L2′/L1 | What the direct evidence shows |
|---|---|---:|---:|---:|---:|---:|---|
| chicken | warming | 6 | 94,310 | 278 | 0 | 0% | No study of a human eating chicken with a thermal outcome; the 278 hits are avian and poultry-production research |
| green tea | cooling | 4 | 15,476 | 62 | 17 | 0.11% | The best-attended claim in the set, still a tenth of a percent of the food's literature |
| coffee | cooling | 4 | 23,286 | 24 | 7 | 0.03% | Caffeine *raises* core temperature under heat exposure (Peel et al. 2025, k = 30, g = 0.44) — opposite to the lay attribution |
| ginger | warming | 8 | 5,730 | 35 | 7 | 0.12% | Thermic effect positive in Mansour et al. (2012, n = 10), null in Fagundes et al. (2021, n = 20) |
| chili pepper | warming | 6 | 1,943 | 30 | 12 | 0.62% | Capsaicin studies at dietary doses; the highest on-construct share in the set |
| milk | cooling | 3 | 171,272 | 586 | 6 | 0.004% | 461 of the 586 keyword hits are animal or livestock-heat research |

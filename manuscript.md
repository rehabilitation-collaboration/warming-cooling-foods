# Widely Circulated, Rarely Examined: A Screened Bibliometric Map of Warming and Cooling Food Claims in Japan

**Running title:** What predicts research attention to warm/cool food claims in Japan

## Authors

Mizuki Shirai, MHS^1^

^1^ Specified Nonprofit Corporation Rehabilitation Collaboration, Suita, Osaka, Japan

<p style="text-align: left;"><strong>Corresponding author:</strong> Mizuki Shirai, MHS, Specified Nonprofit Corporation Rehabilitation Collaboration, Suita, Osaka, Japan. Email: rehabilitation.collaboration@gmail.com. ORCID: 0009-0005-3615-0670.</p>

---

## Abstract

**Background:** Japanese *onkatsu* ("warming care") rests on a widely shared belief that particular foods warm or cool the body. Prior reviews find the scientific support heterogeneous rather than absent, but none has asked, food by food, whether the most widely circulated claims are the ones examined.

**Methods:** This is a descriptive, cross-sectional bibliometric study. Axis A counts, per food, how many of 15 Japanese lay-facing sources — frozen in advance, its nine corporate/association members forming the primary frame — assign it a warming or cooling direction. Axis B counts PubMed hits for each food co-occurring with four thermal-effect terms, then screens every hit, since the raw count measures keyword co-occurrence, not the construct. Paired large language models of adjacent capability tiers from one vendor, versions differing across batches, independently labelled all 2,887 records, with the author adjudicating (Cohen's κ = 0.811).

**Results:** Screening cut 96% of the raw signal: 2,718 hits across 146 foods became 102 on-construct studies, and 118 foods (80.8%) had none. In the planned primary model, adjusted for the food's total PubMed volume (L1), volume predicted having been studied (odds ratio [OR] 1.728 per unit of log(L1 + 1), 95% confidence interval [CI] 1.321–2.260, p < 0.001); coverage did not (OR 1.015, 95% CI 0.824–1.251, p = 0.888), though it compounds to 0.21–6.00-fold over one-to-nine sources. The unadjusted rank correlation was positive (ρ = +0.211, p = 0.011), though the method-matched unadjusted logistic was already non-significant (OR 1.185, p = 0.070). Chicken, warming in six sources, returned 278 raw hits and none.

**Conclusions:** Whether a warming/cooling claim has been directly examined tracks how much the food is studied for any reason, not how widely it circulates, though the data cannot exclude a coverage effect. For four-fifths of these foods, the search retrieved no such study.

**Keywords:** attention gap; bibliometrics; folk nutrition; warming and cooling foods; thermoregulation; abstract screening; Japan

---

## Introduction

The idea that individual foods "warm" or "cool" the body is a durable feature of everyday health culture in Japan, where it underpins the popular practice of *onkatsu* (温活, "warming care") and lay reasoning about *hiesho* (冷え症, habitual cold sensitivity). Corporate wellness media, food manufacturers, and individual practitioners routinely publish lists that sort ginger, carrot, and burdock as "warming" and cucumber, tomato, and coffee as "cooling," and these attributions circulate widely enough to shape ordinary purchasing and seasonal eating advice. That the belief is culturally established, rather than niche, is visible both in the volume of lay-facing sources that maintain such lists and in the fact that Japanese epidemiology has taken the classification seriously: Nagata et al. (2017), analyzing the Takayama cohort (n = 28,356), applied four independent warm/cool food-classification lists to real dietary data. The premise of the belief is therefore neither obscure nor recent.

Crucially, the scientific literature on warm/cool food theory is not empty, and this study does not claim that it is. Ormsby (2021), in a scoping review of the nutritional evidence, characterized the support as "heterogeneous and of mixed quality" while identifying partial mechanistic correlates — heating foods associated with higher caloric density, sympathetic activation, and vasodilation, and cooling foods with higher water and fiber content and anti-inflammatory processes. Namiranian et al. (2021), a companion review in the same volume, surveyed the physiological basis of hot/cold theory across Persian medicine, traditional Chinese medicine, and Ayurveda. Zhou & Xu (2021) integrated candidate molecular mechanisms (for example, differential nuclear factor kappa B [NF-κB] and mitogen-activated protein kinase [MAPK] signaling) linking the cold/hot nature of foods to biological effects — while explicitly noting that research applying these mechanisms to foods is scarce relative to research on Chinese medicines. Any framing of the field as an "evidential desert" is thus untenable; the appropriate description is fragmentary, unintegrated, and unevenly attended.

At the level of individual foods, the available evidence is not only fragmentary but sometimes contradictory or opposite to belief. Ginger, the archetypal "warming" food, showed a significantly enhanced thermic effect of food in one small randomized crossover pilot (Mansour et al. 2012, n = 10 overweight men), yet a larger, double-blind crossover trial in a different population reported no such increase (Fagundes et al. 2021, n = 20 normal-weight women). Coffee, popularly classified as "cooling" (or "yin") in Japan, is dominated by caffeine, whose best-powered synthesis under thermal stress — a meta-analysis pooling n = 30 caffeine effects — found that caffeine significantly *raises* peak core temperature (Hedges' g = 0.44; Peel et al. 2025). The physiological direction most relevant to coffee's principal active compound therefore runs opposite to the folk attribution, even after allowing for the distinct measurement context (heat-exposure performance settings rather than everyday thermal sensation).

Methodologically, the practice of mapping a hot–cold belief system bibliometrically has direct precedent. García-Hernández et al. (2023) assembled and classified 101 academic publications spanning roughly a century to characterize Mexico's hot–cold system by research approach, depth, and conceptual domain. Nagata et al. (2017) demonstrated, within Japan, that the four extant warm/cool classification lists disagree with one another when applied to cohort data — an internal inconsistency that is itself a symptom of the field's uneven development. These works establish that belief systems of this kind can be quantified and that the classification schemes underlying them are neither unified nor exhaustively validated.

What remains unquantified is the *asymmetry* between the two facts above: that certain foods are very widely presented as warming or cooling, and that the direct scientific attention paid to those specific claims varies enormously. Ormsby (2021) asked whether mechanistic support exists but did not measure how widely each food is claimed, nor compare research volume across foods; reviews of the adjacent clinical concept of cold hypersensitivity (Jin et al. 2025, 65 studies) consistently take traditional-medicine interventions, not lay food beliefs, as their subject. We therefore ask a descriptive question: across the foods that Japanese lay sources classify as warming or cooling, is the breadth of that lay coverage related to whether the specific thermal claim has been directly studied — and, if there is any apparent relationship, does it survive adjustment for how much the food is studied for any reason at all?

Answering that question turns out to depend on a measurement problem that a keyword count cannot solve, and addressing it is the methodological contribution of this paper. Counting how often a food name co-occurs with thermal vocabulary in PubMed does not count studies of that food's thermal effect in people: the co-occurrence set is dominated by poultry and livestock heat-stress research, and it misses the nutrition trials that report the thermic effect of food. We therefore screened the entire co-occurrence set to the intended construct before analysing it, using two independent language models with author adjudication — a design with recent published precedent in evidence synthesis (Guo et al. 2024; Hilkenmeier et al. 2026).

---

## Methods

### Design

This is a descriptive, cross-sectional bibliometric study. It maps two independently constructed axes against each other for a fixed set of foods and reports their association; it does not estimate a causal effect of lay coverage on research or vice versa. Because the study was not registered on any protocol registry, we describe fixed-in-advance choices as *planned* rather than pre-specified.

### Axis A: lay-source coverage

Axis A quantifies how many independent Japanese lay-facing sources assign each food a warming or cooling direction, following the bibliographic-coding approach of García-Hernández et al. (2023). We use "coverage" rather than "belief" throughout: the measure counts sources that publish an attribution, and is a proxy for — not a measurement of — how widely the attribution is actually held.

**How the frame was assembled.** Candidate sources were located by Japanese-language web search in two passes. The first swept general queries for the belief itself — among them 「体を温める食べ物 冷やす食べ物 一覧 漢方」 ("list of foods that warm or cool the body, kampo"), 「温活 食材リスト 温める 冷やす 分類」 ("onkatsu ingredient list, warming/cooling classification"), 「五性 温 熱 涼 寒 食材 一覧」 ("five-nature ingredient list"), and 「冷え性 食べ物 温める 冷やす 一覧」 ("hiesho food list, warming and cooling"). The second ran domain-restricted queries over the sectors that publish such lists: kampo and pharmaceutical manufacturers, health-food companies, drugstore chains, food and beverage makers, medicinal-food (*yakuzen*) associations, and the web editions of women's and lifestyle magazines. Two independent existence scans then verified every candidate by fetching the page — publishing about warming care in general was not sufficient; the page had to assign individual foods a direction — and by retrieving its robots.txt. Independence was judged on operator and on content, so aggregator pages republishing another site's list were dropped. The frame is therefore a purposive sample of what was reachable on the Japanese-language web in August 2026, assembled before any Axis B count existed; it is not a probability sample of Japanese lay media, and it is not weighted by readership.

The sampling frame was frozen in advance: 15 sources verified to be reachable over HTTP, to present a concrete per-food warm/cool list, and to permit fetching per robots.txt. Nine corporate- or association-operated sources form the **primary (Tier 1) frame**; six individual-expert blogs form a **Tier 2 sensitivity frame**, which the coding protocol reserves for testing whether conclusions are stable. Sources sharing a single operator were counted once. Two frame corrections were made during fetching and before any coding of results — one source lacking a concrete per-food list was excluded, and one source's URL was corrected to its per-food list page — with both decisions driven by page content rather than by any result.

Each source page was fetched once, on 2026-08-03 (one source re-fetched 2026-08-04 at its corrected URL), and stored locally; the per-source access dates are published in `data/sources.csv`. Every food mentioned was then coded for its direction (warming, cooling, or neutral), with the verbatim supporting quotation recorded on each row. Coding rules were documented before coding: sources using traditional five-nature or yin–yang vocabulary were mapped to warming (温性/熱性/陽性), cooling (涼性/寒性/陰性), or neutral (平性); serving temperature (e.g. "cold drinks") is not a food's nature and was not coded as one. For each food, Axis A records the number of independent sources assigning a direction (`n_sources`) and the majority direction; a consensus ratio is also computed and published with the data, but no analysis here uses it.

**Who coded, and what the agreement statistic can support.** All coding was performed by large language models operating under the author's direction; there were no human raters. Each source was coded twice, independently: the first pass over six Tier-1 sources by Claude Opus 4.8 reading the stored text, the remaining nine sources by separate Claude Sonnet 4.6 agents, and the second pass throughout by further Claude Sonnet 4.6 agents that received only the protocol and the stored source text, with the first coder's output withheld. Codings were reconciled on the (source, food, condition) key. Cohen's κ was 1.000 across the two rounds, but on one specific quantity: **the direction assigned to the 481 items both coders extracted**. It is not a reliability estimate for extraction, and extraction is where this task's disagreement actually lived. The coders returned different numbers of records — in round 2, 236 and 377, agreeing on 214 — so the extraction overlap in that round is a Jaccard index of 0.54, not anything near unity. The 190 coverage differences across the two rounds — five in round 1 and 185 in round 2, a coverage difference being a food one coder recorded and the other did not — were accordingly adjudicated one at a time against the source text. That reading dropped eleven records that carried no nature attribution in the source, added one the first coder had missed, and corrected three misread directions; the remainder were adjudicated and accepted as coded. These are the counts of the reconciliation as executed on 2026-08-04; two food keys were later merged and split (a synonym pair, and a dried-versus-fresh distinction three sources had assigned inconsistently), so re-running the same reconciliation against the frozen dataset returns 218 co-coded items and 177 coverage differences in round 2, with direction agreement unchanged at κ = 1.000.

That κ pools two differently constituted rounds, and neither supports an independence claim. In round 2 (214 of the 481 co-coded items) both coders were separate instances of the same model, so their agreement measures the stability of one model's reading. In round 1 (the other 267 items) the two coders were different capability tiers of the same vendor's line — the same arrangement used for the Axis B screening — whose errors should be expected to correlate. Perfect agreement across that tier boundary is itself evidence of shared behaviour rather than of independent convergence. The κ is therefore an upper-bound-leaning consistency estimate, not comparable to a κ between human raters; we return to this in the Limitations. The reproducibility evidence we rely on instead is deterministic: `verify_claims.py` checks that every retained row occurs verbatim in the stored source text, and every row carries its source and quotation, so the coding can be re-derived from the published frame rather than taken on trust.

Coding yielded 649 rows and 196 distinct foods. Of these, 157 are covered by at least one Tier-1 source; 11 are composite category labels ("nuts," "spices," "shellfish," "leafy greens" and similar) that cannot be turned into a single unambiguous search query and were excluded from Axis B, leaving **146 foods** in the primary analysis. A normative five-nature classification, against which lay attribution could be benchmarked, was planned but is deferred to future work because a citable primary source could not be secured within scope.

### Axis B: on-construct research attention

**Raw counts.** Axis B begins from the National Center for Biotechnology Information (NCBI) PubMed E-utilities (no API key; queries rate-limited under 3 requests/s). All PubMed, CiNii, and OpenAlex queries were executed on 2026-08-06 to 2026-08-07; because bibliometric counts grow over time, this snapshot fixes the reported values. For each food we counted hits at two nested layers: **L1**, the food term alone, as total research volume; and **L2**, the food term co-occurring with any of four thermal-effect terms — *thermogenesis*, *body temperature*, *peripheral circulation*, *thermoregulation*. The four-term vocabulary was frozen after a one-time validity check on real hits: adding human cold-sensitivity terms recovered no additional relevant studies for ginger, whereas adding plant "cold tolerance" terms injected agronomy noise. Japan-specific foods with weak English coverage were given minimal English synonyms (for example, natto → "fermented soybean"); the inclusion criterion was held constant across foods so that counts are comparable. Queries are built deterministically from each food's key, and the raw count response for every query is published, so each reported count is pinned to its retrieval snapshot.

**Why the raw count is not the measure.** L2 counts keyword co-occurrence, not studies of the construct, and it fails in both directions. It over-counts: `chicken` returned 278 hits dominated by avian thermoregulation and poultry heat-stress research. It also under-counts, because the four seed terms do not cover how nutrition trials report the effect — Fagundes et al. (2021), a randomized crossover trial of ginger on energy expenditure, is not in the L2 set for ginger at all. An analysis built on L2 would therefore report the research attention paid to a keyword pattern, not to the belief. Screening addresses only the first failure: it is a filter, so L2′ is a subset of L2 and can remove false positives but never recover a study the query did not retrieve. The under-counting is carried into the Limitations as a floor on the measure.

**Screening.** We retrieved the title, abstract, journal, and publication types for every L2 hit and screened all **2,887 records across 107 foods** to a single construct: *a study of the thermal effect, on a human, of ingesting the food or its principal dietary constituent*. The include/exclude definition is documented in `data/screening_protocol.md` and fixed before coding. Include requires all of: human subjects in vivo; oral ingestion of the food, a food form of it, or its principal dietary constituent; a thermal-related physiological outcome (core, peripheral, skin, tympanic or axillary temperature; thermogenesis or thermic effect of food; energy expenditure reported in a thermogenic context; peripheral circulation; thermoregulation or cold tolerance; subjective thermal sensation); and attribution of the outcome to the food as the exposure of interest. Exclusions are coded by reason (`animal`, `livestock-heat`, `invitro`, `agri`, `name-only`, `no-thermal`, `mechanism-only`, `not-ingestion`, `species-mismatch`, and the two information-shortfall flags `uncertain-species` and `no-abstract`, which route a record to the author regardless of whether the coders agreed). Isolated constituents given at dietary doses (caffeine for coffee, capsaicin for chili pepper) are included and sub-labelled; a different species in the same family is excluded, so that *Aframomum* and *Kaempferia* studies do not inflate "ginger." No quality grading was performed — this is construct-validity screening, not risk-of-bias assessment. The 68 queried foods with zero L2 hits have L2′ = 0 by construction and required no screening; foods queried but not screened would be recorded as missing rather than zero, and there were none.

**Screening reliability.** Every record was labelled independently by two large language models of **different capability tiers from one vendor's line**: Claude Sonnet 4.6 with Claude Opus 4.7 for the five golden-set foods, and Claude Sonnet 5 with Claude Opus 5 for the remaining 102 foods. Model versions differ across batches because screening ran over several working sessions; within each batch the two coders are contemporaneous. We state the pairing precisely because it bounds what the agreement statistic can mean: two models from one vendor and one release generation share pretraining data, tokenizer and alignment methodology, so their errors should be expected to correlate, and their agreement measures the **consistency** of that lineage rather than the convergence of independent judgments. This is a weaker design than the three-vendor arrangement of Hilkenmeier et al. (2026), and we do not claim its properties. Each agent received the protocol and its assigned records only — the other coder's labels, the golden set, and the reconciliation code were withheld. Cohen's κ was **0.811 on all 2,887 co-coded records** (observed agreement 0.984), with 45 divergences. Both coders returned every record, so Axis B has none of the coverage differences that Axis A had to adjudicate, and κ's denominator here is the entire record set rather than an agreed subset of it. The author adjudicated 56 records against title and abstract — every divergence, plus every record either coder flagged as not stating the subject species or as having no abstract, since agreement reached on information a record does not contain is not evidence about that information. Before full screening, the author hand-labelled a 169-record golden set (29 include, 140 exclude) spanning the foods where the include boundary actually lives; against it, coder 1 achieved precision 0.867 / recall 0.897 / F1 0.881 and coder 2 precision 0.813 / recall 0.897 / F1 0.853. Gold labels for records whose abstract does not state the subject species were set from PubMed Humans/Animals Medical Subject Headings (MeSH) or full text, never by inference; this check corrected one gold label, and the correction was surfaced by a coder divergence rather than by the author's own review.

**A third, adversarial pass over the foods that could flip.** Two coders who exclude the same record for the same wrong reason leave no trace in κ, and because the primary outcome is binary, one such record would change a food's result outright. We therefore re-screened the records that stood to flip: all **419 candidates belonging to the 28 core foods (≥ 3 Tier-1 sources) whose L2′ is zero** and whose query returned anything at all. A third agent (Claude Opus 5), blind to the existing labels, to the golden set and to the reconciliation code, was told the opposite of what the first two coders were told — that every record it was about to read had been excluded, and that its task was to find the ones where that was wrong. Its verdicts were `exclude-agreed`, `uncertain`, or `include-candidate`, with standing instructions to return `uncertain` whenever it hesitated and never to infer an unstated subject species. It returned **no include candidates and five uncertains**; the author read all five against title, abstract and MEDLINE indexing, and **none changed label**. Every verdict and every ruling is published in `data/screening_thirdpass.csv`. The nine remaining core-zero foods returned no L2 hits at all and so have nothing to re-screen; their zero is a question about the search vocabulary rather than about screening, which is where the Limitations place it.

No publication-year restriction was applied at any layer; the retrieved records span the whole of PubMed's coverage, the oldest included here dating from the 1950s.

**Auxiliary databases.** OpenAlex (keyword-based) and the CiNii Research API (Japanese-language literature) were queried as auxiliary columns. OpenAlex `search=` is a full-text match and returns counts an order of magnitude larger than PubMed `[tiab]`, so the two are reported separately and never summed. The CiNii query retrieves the Japanese food name alone — an L1-equivalent total, **not** a thermal-context count; it therefore bounds how much Japanese-language literature exists on each food but does not establish that a food's thermal claim is unstudied in Japanese. The primary axis is the screened PubMed count.

### Analysis

The analysis plan was fixed before any estimate was computed and is recorded in the project PLAN. The **primary model** is a logistic regression of whether a food has any on-construct study (L2′ > 0) on lay-source coverage (`n_sources`), adjusted for log(L1 + 1); the unadjusted fit is reported beside it. A binary outcome is what the data can support — L2′ is sparse, with most foods at zero and most non-zero foods at one or two studies — and "which foods have no direct research" is the paper's question. **Reported alongside** are Spearman rank correlations of coverage against L2′, against raw L2, and against L1, so that the effect of screening and the role of literature volume are both legible. The **sensitivity model** is a negative binomial regression of L2′ with log(L1 + 1) as an offset, fitted after a Poisson over-dispersion check (Green 2021; the model class has bibliometric precedent in Millones-Gómez et al. 2023). Branch conditions were fixed in advance: if the negative binomial failed to converge it would be reported as such rather than replaced by a zero-inflated model, which this many zeros over this few foods cannot identify; and a null primary result would be reported as no detected association rather than treated as a failed study.

Five analyses are reported that were **not** in the fixed plan and are labelled as such wherever they appear: the rank correlation of coverage against the L2′/L1 ratio; the refit of the primary model under the Tier 1+2 frame; and three refits under narrower readings of what counts as an on-construct study — one dropping studies of a food's principal dietary constituent, one dropping reviews and meta-analyses, and one dropping both. The last three were added in revision. Each of those inclusions is defensible for "has this claim been examined at all" and each is arguable, so asserting either would leave the primary count resting on an untested choice. All five were computed after the primary estimates and none is used to support a conclusion.

The zero-research rate is reported at every level of lay-source coverage rather than at selected thresholds, so that no cut-point is chosen after seeing the data. Warming and cooling foods are compared on the zero-research contrast (Fisher exact) and on L2′ (Mann–Whitney U) within the core set. All tests are two-sided at α = 0.05; only the primary logistic model is confirmatory, and the remaining comparisons are descriptive and reported without correction for multiplicity. Ninety-five-percent confidence intervals use the Fisher z-transformation with the Bonett–Wright variance for rank correlations, **Wald bounds** for regression coefficients, Woolf's logit method for the odds ratio, and Wilson score intervals for the proportions in Figure 1. In the negative binomial the dispersion parameter is estimated by profiling the likelihood over a grid and then held fixed, so its interval is conditional on that value and is correspondingly narrow.

The two predictors are associated (Spearman ρ = +0.465), but not to a degree that destabilises the fit: on the model's own design matrix their Pearson correlation is +0.396 and each predictor carries a variance inflation factor of 1.19. The rank correlation is what Table 3 reports, but a variance inflation factor is defined from the linear fit between the predictors, so it is computed there rather than by squaring ρ. log(L1 + 1) rather than raw L1 enters the model, which compresses a four-order-of-magnitude range (29 records for hojicha, 171,272 for milk) into a scale where no single food dominates. Beyond this we report no model diagnostics: with 28 events over two predictors the model is used to describe an association, not to predict, and calibration or discrimination statistics would over-interpret it.

Analyses used Python 3.14.3 with pandas 3.0.1, scipy 1.17.1, numpy 2.4.2, statsmodels 0.14.6, and matplotlib 3.10.8; the pipeline is covered by 111 unit tests (all passing). Every statistic in the Results and in Tables 3, 4 and 5, and the composition counts in Table 1, are recomputed from the pipeline output by `src/verify_stats.py`; Table 1's Axis A reliability figures come from `src/reconcile_coders.py`; the screening quantities in Table 2 — the κ, the agreement and adjudication counts, the golden-set scores and the exclusion-reason breakdown — are recomputed by `src/build_screening.py` from the published ledger, and the third-pass row by `src/build_thirdpass.py`. Figure labels are English-only to avoid CJK-glyph problems in the PDF build (weasyprint 68.1).

---

## Results

### Sample and the effect of screening

Axis A coding covered 196 distinct foods across 15 sources. Under the primary Tier-1 frame, 146 queryable foods carry at least one source attribution: 51 reach three or more sources (the *core* set), 28 have two, and 67 have one (Table 1). Among the 51 core foods, 31 are lay-classified warming, 19 cooling, and one contested.

Screening changed the measure substantially. Across the 146 foods in the primary frame, 2,718 raw L2 hits reduced to **102 on-construct studies** — a 96.2% reduction. Over the full 175-food query universe, on which the screening was carried out, 2,887 records reduced to 106 (Table 2), of which 86 are primary reports and 20 are reviews or meta-analyses of human thermal-ingestion evidence. Two-thirds of the 2,781 exclusions are animal research: 1,530 records excluded as `animal` and a further 376 as `livestock-heat`, together 68.5%. The next largest class, `name-only` (549 records, 19.7%), covers studies where the food term matched but nothing about ingestion and body temperature was at issue.

The screening behaved as intended on the foods that motivated it. **Chicken fell from 278 raw hits to zero**: no study in that set examined a human eating chicken and measured a thermal outcome. Lamb (107 → 0) and soybean (68 → 0) behaved the same way, and milk fell from 586 to 6 (Table 5). Ginger illustrates the other side of the problem: 35 raw hits reduced to 7, and those 7 include the thermic-effect and energy-expenditure trials (Mansour et al. 2012 among them) that the raw count had buried among 28 irrelevant records. Screening surfaced them; it did not retrieve them, and could not have — the query had already returned them.

The adversarial third pass over the 419 candidate records behind the 28 core-zero foods returned no include candidates and five uncertains, none of which survived the author's reading (Methods). No food changed outcome. The zeros in Table 4 are therefore not an artefact of two coders making the same mistake in the same direction, which is the one failure mode their agreement statistic cannot detect.

### Lay-source coverage does not predict whether a food has been studied

Of the 146 foods, **118 (80.8%) have no on-construct study**, and among the 51 core foods the rate is 37/51 (72.5%). Throughout what follows, "no on-construct study" is shorthand for none that this query retrieved and this screen retained. That is a floor on the truth rather than a census of it, for reasons the Limitations set out.

In the planned primary model, literature volume predicted whether a food had any on-construct study — **odds ratio (OR) 1.728 per unit of log(L1 + 1), 95% confidence interval (CI) 1.321–2.260, p < 0.001** — and lay-source coverage did not: **OR 1.015 per additional source, 95% CI 0.824–1.251, p = 0.888**; model pseudo-R² = 0.176 (Table 3). Unadjusted, the coverage estimate is larger and does not reach significance (OR 1.185, 95% CI 0.987–1.423, p = 0.070).

The coverage estimate is a non-finding rather than a demonstrated null. Compounded across the observed range of one to nine sources, its interval spans an odds ratio from 0.21 to 6.00 — that is, the data are compatible with widely covered foods being either substantially less or substantially more likely to have been studied. What can be said is that no association was detected, and that the same model with the same 28 events detected a clear one for literature volume.

The rank correlations show why adjustment matters. Coverage correlates positively with the screened count (ρ = +0.211, 95% CI +0.048 to +0.362, p = 0.011) — but it also correlates, more strongly, with the food's total literature (ρ = +0.465, 95% CI +0.320 to +0.589, p < 0.001). Widely covered foods are, on the whole, foods with large general literatures; once that is accounted for, the coverage association is not distinguishable from zero. Figure 1 shows this directly: the observed proportion studied rises modestly with coverage (panel a) and rises monotonically with literature volume (panel b), and when the primary model holds literature volume fixed the coverage curves are flat at every volume level while remaining widely separated from one another (panel c).

The correlation with raw, unscreened L2 was substantially higher (ρ = +0.381, p < 0.001) than with the screened count, indicating that roughly half of the apparent coverage–attention association in the unscreened data was carried by records that do not measure the construct.

The zero-research rate does not fall as coverage widens. It is 80.8% across all 146 foods, 72.5% at three or more sources, 68.4% at four or more, 75.0% at five or more, 81.8% at seven or more, and 66.7% at eight or more on six foods (Table 3); the confidence intervals in Figure 1a overlap throughout. The per-food picture behind these rates is in Figure 2, where the 118 zero-study foods sit on the baseline across the whole coverage range rather than clustering at its narrow end.

The sensitivity model reached the same verdict of non-significance but not the same estimate. Poisson deviance/df was 2.296, confirming over-dispersion; the negative binomial with log(L1 + 1) as offset converged (dispersion parameter α = 4.81) with a coverage incidence rate ratio (IRR) of 1.213 (95% CI 0.968–1.519, p = 0.093). That coefficient is an order of magnitude larger than the primary model's, and its interval nearly excludes unity, so the two models agree only in failing to reach significance. The offset also constrains the volume coefficient to exactly 1, a constraint the primary model's own estimate (0.547 on the log-odds scale) does not support — which is part of why the offset specification is reported as a sensitivity check rather than as the primary analysis.

Refitting the primary model under the wider Tier 1+2 frame (175 foods, an unplanned check) gave the same answer: 144/175 (82.3%) with no on-construct study, coverage OR 1.006 (95% CI 0.882–1.148, p = 0.926).

Narrowing what counts as an on-construct study did not change it either (both checks unplanned). Thirty-two of the 102 studies examine a food's principal dietary constituent rather than the food itself; dropping them leaves 70 studies across 25 foods, a zero rate of 82.9%, coverage OR 1.033 (95% CI 0.834–1.280, p = 0.764) and volume OR 1.707 (1.295–2.249, p < 0.001). Dropping instead the 20 reviews and meta-analyses leaves 82 studies across 27 foods (81.5% zero), coverage OR 1.035 (0.840–1.275, p = 0.745). Dropping both — the two classes overlap in six records — leaves 56 studies across 22 foods (84.9% zero), coverage OR 1.026 (0.821–1.281, p = 0.823) and volume OR 1.602 (1.220–2.102, p < 0.001). The narrowing is not spread evenly: it bites hardest on the foods that carry the most evidence, and green tea — tied for the largest screened count in the frame — retains nothing at all once constituent and review records are removed (Table 5). The estimates do not move.

### Widely covered foods with no retrieved study

Thirty-seven of the 51 core foods have no on-construct study (Table 4). They include the foods most consistently presented as warming or cooling: carrot, cucumber, pumpkin, and tomato at eight of nine Tier-1 sources; miso, burdock, eggplant, mango, and apple at seven. Their total literatures differ by two orders of magnitude — burdock has 323 PubMed records and tomato 38,050 — yet at neither extreme did the search retrieve a study of the thermal claim.

Chicken is the sharpest case. Six Tier-1 sources present it as warming; PubMed holds 94,310 records on it and 278 in the thermal keyword context; and not one of those 278 examines a human eating chicken and measures a thermal outcome. Abundant literature, a widely published claim, and no retrieved test of that claim coexist in the same food.

The gap is specifically a human one. Four of those 278 records put this very question to animals: the postprandial thermic effect of chicken in rats and its thyroid-hormone mediation (Wakamatsu et al. 2013), diet-induced thermogenesis across meat proteins in rats (Ezoe et al. 2016), diet-induced thermogenesis in broilers (Swennen et al. 2006), and — closest of all — a behavioural assay in which mice select their ambient temperature after eating different meats (Wakamatsu et al. 2025), which is the folk construct itself transposed to a rodent. All four are excluded here as animal research, correctly under the protocol, and each is identifiable by its exclusion reason in the published ledger. The claim has been put to animals; this search retrieved no test of it in the people who hold it.

### Warming versus cooling foods

Warming and cooling foods did not differ. Among core foods the zero-research rate was 22/31 (71.0%) for warming and 14/19 (73.7%) for cooling (Fisher exact OR 0.873, 95% CI 0.242–3.147, p = 1.000), and the screened counts did not differ (Mann–Whitney U = 290.5, p = 0.930; median zero in both groups). We make no claim of a warm/cool asymmetry.

### Flagship foods

A handful of foods illustrate that "attention present" does not resolve the question (Table 5). **Green tea** (cooling, four sources) and **white sugar** (cooling, six sources) are tied for the most on-construct evidence in the whole frame, with 17 studies each — 0.11% and 0.02% respectively of their literatures. **Coffee** (cooling, four sources) has 7 on-construct studies from 23,286 records, and the best-powered relevant synthesis reports that caffeine *raises* core temperature under heat exposure (Peel et al. 2025), opposite to the lay attribution. **Ginger** (warming, eight sources) also has 7, and those studies disagree: positive in Mansour et al. (2012), null in Fagundes et al. (2021) — the latter never entering our candidate set at all, since the seed vocabulary did not retrieve it. Even where the claimed context has been examined, it has been examined thinly, sometimes inconsistently, and in one case in the direction opposite to the belief.

---

## Discussion

Across 146 foods that Japanese lay-facing sources classify as warming or cooling, how widely a food's attribution circulates showed no detectable relationship with whether that attribution has been directly examined. What was associated with examination was how much the food is studied for any reason: a unit increase in log total literature corresponded to about three-quarters higher odds of having an on-construct study, while an additional lay source corresponded to an estimated 1.5% change with an interval spanning both directions. The positive association visible in the unadjusted data was substantially attenuated once general literature volume was held fixed, which is what one expects if the same foods tend to be both widely written about and widely researched — though, as the Results note, the adjusted interval is wide enough that a real coverage effect of either sign remains possible.

This is a more specific reading than the one we set out to test, and it came from taking the measurement problem seriously. An earlier version of this analysis used the raw keyword co-occurrence count and reported a near-zero correlation between coverage and attention. That correlation was not interpretable, because two-thirds of the records screened — 1,906 of 2,887 — are studies of animals rather than of people eating food. After screening, the correlation is positive rather than null, and then is no longer distinguishable from zero once literature volume is held fixed, for a reason the raw analysis could not have identified. Construct validity was not a caveat on the result here; it determined what the result was.

The same applies one level down, to decisions the screening protocol had to make inside the construct. Whether a caffeine trial counts as evidence about coffee, and whether a review counts as an examination, are construct judgments rather than statistical ones. We tested both rather than asserting either, and neither moved the estimate. What the test did expose is that the narrowing falls unevenly: green tea carries the largest screened count in the frame and retains nothing under the strictest reading, because all of its evidence is about catechins or is second-hand. The aggregate result is robust to these choices; an individual food's count is not, and Table 5 should be read with that in view.

The finding refines rather than contradicts the prior reviews. Ormsby (2021), Namiranian et al. (2021), and Zhou & Xu (2021) each establish that the field holds partial, mechanistically suggestive evidence, so "no evidence" is the wrong description; our contribution is orthogonal — we show that whatever evidence exists is distributed by general research salience rather than by which claims circulate, and that a standardized search and screen retrieved none at all for four-fifths of the foods that circulate. Zhou & Xu's observation that food-level research is scarce relative to Chinese-medicine research is echoed quantitatively here: 2,887 records that mention a food alongside thermal vocabulary yield 106 studies of a human eating that food. García-Hernández et al. (2023) showed that a hot–cold belief system can be bibliometrically mapped and found domain-specific knowledge gaps in Mexico; our two-axis design extends that from documenting that a system exists to asking, food by food, what its claims' examination is associated with. Nagata et al. (2017) found that Japan's four warm/cool classification lists disagree when applied to cohort data; that internal disunity and the pattern reported here are complementary symptoms of a field elaborated culturally faster than it has been consolidated empirically.

One line of work deserves separate notice, because it is the closest thing to a sustained programme on this construct and it sits entirely inside our exclusions. Wakamatsu and colleagues have pursued the postprandial thermal effect of meat in rodents for over a decade: the thermic effect of chicken and its thyroid-hormone mediation (Wakamatsu et al. 2013), diet-induced thermogenesis across meat proteins (Ezoe et al. 2016), and most recently an assay in which mice choose their ambient temperature after eating different meats and their fractions (Wakamatsu et al. 2025) — a behavioural read-out of precisely the felt warmth the lay claim describes. The question this paper puts to the Japanese lay literature has therefore been asked, carefully and repeatedly, of rodents. What has not followed is the human study, and that is the shape of the gap these two axes describe.

The practical reading is diagnostic rather than causal. Research attention co-varies with a food's overall research salience, so the foods whose claims are least examined tend also to be those with the smallest general literatures: burdock, lotus root, hojicha, and daikon are widely presented as warming or cooling and carry a few hundred records each. If that pattern holds, these claims are unlikely to meet evidence as a by-product of research on those foods for other reasons. Table 4 names 37 such foods with logged, reproducible counts, and they are the concrete targets a direct-verification programme would take up.

An important interpretive caution applies to caffeine. The evidence that caffeine raises core temperature comes from heat-exposure performance settings (sport, military, and industrial contexts) rather than from studies of everyday subjective warm/cool sensation, and physiological core-temperature change is a distinct measure from felt thermal comfort. We therefore treat the coffee reversal as a well-powered example of belief-incongruent physiological evidence in a specific context, not as a refutation of the subjective experience the belief describes.

Finally, the screening step is itself a transferable result — but a narrower one than a multi-model design would give. What we can claim is tractability: screening an entire 2,887-record hit set to a construct, twice over, with every judgment published, is now feasible at a scale that would previously have forced the sampling compromise this study was originally designed around. What we cannot claim is decorrelated error. Our two coders are adjacent capability tiers of one vendor's line, not the three-vendor arrangement of Hilkenmeier et al. (2026), so their 98.4% agreement (κ = 0.811) bounds the internal consistency of that lineage rather than establishing independent convergence; comparing it to the human inter-rater κ = 0.46 reported by Guo et al. (2024) would also be misleading, since κ depends on prevalence and the two tasks differ sharply there — Guo et al. themselves report a prevalence- and bias-adjusted κ of 0.96 for their own comparison. The more informative observation is that the 45 divergences were where the difficulty concentrated, and that one of them exposed an error in the author's own reference labels: disagreement between models was useful as a flag for hard records even though agreement between them cannot be read as independent confirmation.

---

## Limitations

**First — lay-source coverage is a source count, not a measure of conviction.** Axis A counts how many independent sources publish an attribution; it does not weight by readership, and appearing in many sources is not the same as being widely believed. The frame is 15 Japanese lay-facing web sources frozen in advance and dominated by corporate and association wellness media. A different frame — print encyclopedias of *yakuzen*, or reader surveys — could shift individual foods' values. Widening the frame to include the six individual-expert blogs did not change the conclusion (an unplanned check; OR 1.006, p = 0.926).

**Second — the coders were language models, and neither reliability statistic supports an independence claim.** All coding on both axes was performed by large language models under the author's direction; there were no human raters. On Axis A, κ = 1.000 covers one thing only — the direction assigned to items both coders extracted — and round 2 paired two instances of the same model while round 1 paired two capability tiers of one vendor's line, so it measures the consistency of that lineage on the easier half of the task. Extraction, meaning which foods to record at all, is where the coders actually diverged: their overlap in round 2 was a Jaccard index of 0.54, and every difference was settled by the author against the source text rather than by any agreement statistic. Axis B is the same arrangement — Sonnet with Opus — so its κ = 0.811 is a within-vendor consistency estimate too. Models sharing pretraining data and alignment methodology should be expected to share failure modes, and perfect agreement across a tier boundary (Axis A round 1) is evidence of that rather than against it. Neither figure is comparable to a κ between trained human screeners, and κ is in any case prevalence-dependent, which our 4% include rate makes acute. What does not depend on model agreement is the verbatim grounding check on every Axis A row, the golden-set precision and recall against hand labels, and the publication of every screening judgment with its PMID, all of which can be audited directly. The failure mode that no agreement statistic can detect — both coders excluding the same record for the same wrong reason — was tested head-on where it would matter most, by a third pass instructed to overturn rather than to concur across all 419 candidate records of the core-zero foods; it overturned nothing. That bounds the concern without eliminating it, since the third agent is drawn from the same vendor's line as the first two.

**Third — the screened count is a floor, not a census.** L2′ counts studies that the four-term PubMed query retrieved *and* that survived screening. Screening is a filter, so it can only remove; a study phrased entirely in other vocabulary never enters the candidate set and no amount of screening recovers it. That this happens is demonstrable rather than hypothetical: Fagundes et al. (2021), a randomized crossover trial of ginger on energy expenditure and one of the two trials we discuss as ginger's direct evidence, is absent from the ginger candidate set entirely. L2′ therefore under-counts by an unknown margin, and the targeted cross-query that would bound that margin remains outstanding. Zero means "no study was retrieved by this query and retained by this screen," not "no such study exists."

**Fourth — database coverage is incomplete and the Japanese-language check is weaker than it should be.** PubMed does not index J-STAGE/CiNii, KMbase/OASIS, or CNKI, so the counts under-represent Japanese, Korean traditional-medicine, and Chinese literatures. Our CiNii query returns total counts for the Japanese food name, not thermal-context counts, so it bounds the size of the Japanese literature on each food but cannot confirm that a food's thermal claim is unstudied in Japanese. A thermal-context search of Japanese-language databases is the most direct extension of this work.

**Fifth — search terms are not equally apt for every food.** Some synonyms conflate distinctions the belief makes (green tea and black tea share *Camellia sinensis*), and the unit of the query does not always match the unit of the claim (lay sources speak of chicken breast; the query returns work on the whole species). Screening removes the resulting false positives but cannot recover a study the query never retrieved, so residual differences in query aptness remain a source of between-food measurement error.

**Sixth — cross-sectional snapshot.** Both axes were measured once, in August 2026. Lay sources are edited and PubMed counts grow, so specific values will drift, although the structural pattern is unlikely to reverse on the timescale of source updates.

**Seventh — descriptive, ecological, unregistered, and imprecise.** The design identifies an association pattern across foods, not a mechanism or a cause, and food-level associations should not be read as statements about individuals. The analysis plan was fixed before estimation but was not registered on a public protocol registry, and five reported analyses were computed outside it and are labelled where they appear. Precision is the binding constraint on the central result: 28 of 146 foods have any on-construct study, and the coverage interval compounds across the observed one-to-nine-source range to an odds ratio between 0.21 and 6.00. The absence of a detected coverage effect is therefore a non-finding, not evidence that no effect exists, and a frame with more sources or a database with more on-construct studies could resolve it either way.

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

14\. Wakamatsu J, Takabayashi N, Ezoe M, Hasegawa T, Fujimura T, Takahata Y, Morimatsu F, Nishimura T. Postprandial thermic effect of chicken involves thyroid hormones and hepatic energy metabolism in rats. *J Nutr Sci Vitaminol (Tokyo)*. 2013;59(6):516-525. doi:10.3177/jnsv.59.516. PMID: 24477248.

15\. Ezoe M, Wakamatsu J, Takahata Y, Hasegawa T, Morimatsu F, Nishimura T. Diet-induced thermogenesis and expression levels of thyroid hormone target genes and their products in rats differ between meat proteins. *J Nutr Sci Vitaminol (Tokyo)*. 2016;62(2):93-100. doi:10.3177/jnsv.62.93. PMID: 27264093.

16\. Swennen Q, Janssens GP, Collin A, Le Bihan-Duval E, Verbeke K, Decuypere E, Buyse J. Diet-induced thermogenesis and glucose oxidation in broiler chickens: influence of genotype and diet composition. *Poult Sci*. 2006;85(4):731-742. doi:10.1093/ps/85.4.731. PMID: 16615357.

17\. Wakamatsu JI, Tan Y, Kato S, Abe H, Kawahara M, Hayakawa T, Kumura H. Evaluation of postprandial thermal feeling in mice using a behavioral thermoregulation analysis: Differences in meat species and their fractions. *J Therm Biol*. 2025;129:104101. doi:10.1016/j.jtherbio.2025.104101. PMID: 40179544.

---

## Ethical considerations

This study used exclusively publicly available information: aggregate bibliographic counts and public bibliographic records from public literature databases (PubMed, CiNii, OpenAlex) and publicly published lay-media web pages. No individual-level, health, or personally identifying data were accessed, and no human subjects were recruited or contacted. Because the analysis is restricted to already-public bibliographic data and public web content, it does not meet the standard threshold for human-subjects research under either domestic (Japanese Ethical Guidelines for Medical and Biological Research Involving Human Subjects, 2021 revision, for research using publicly available information) or international (e.g., 45 CFR §46.102 for non-human-subjects data) frameworks; accordingly, no institutional review board approval or waiver was sought or required. The study was conducted in accordance with the principles of the Declaration of Helsinki where applicable to research using aggregate, publicly available data.

## Acknowledgments

Large language models were used as instruments in this study, not only as writing aids, and their roles are separated here accordingly.

**As coding instruments.** Axis A attributions were coded twice independently by Claude Opus 4.8 and Claude Sonnet 4.6 (Anthropic). Axis B abstract screening was performed twice independently by paired models of adjacent capability tiers — Claude Sonnet 4.6 with Claude Opus 4.7, and Claude Sonnet 5 with Claude Opus 5 — under the protocol in `data/screening_protocol.md`. The adversarial third pass over the core-zero foods was performed by Claude Opus 5. All models are from a single vendor; the Methods and Limitations state what that does and does not license. Every divergence, every record flagged for missing information, and every coverage difference was adjudicated by the author against the primary record. Model versions differ across batches because the work spanned several sessions; the batch-level assignment is tabulated in the protocol files.

**As development and writing aids.** Claude Opus 4.8 and Claude Opus 5 (Anthropic) assisted with code drafting, debugging, literature-search support, and manuscript editing.

All data extraction, statistical outputs, and numerical results were independently checked by the author by re-executing the analysis code (Python 3.14.3; unit tests n = 111, all passing) and by recomputing every reported statistic directly from the pipeline output before writing. The author is solely responsible for the accuracy of the numerical results, the choice of specifications, the interpretation, and the conclusions. All references were verified against PubMed, CrossRef, and publisher records; DOIs and PMIDs were confirmed against primary source pages, and one cited work (Jin et al. 2025) is not indexed in PubMed and is cited by DOI.

## Author Contributions (Contributor Roles Taxonomy, CRediT)

Mizuki Shirai: Conceptualization, Methodology, Investigation, Data Curation, Formal Analysis, Software, Writing — Original Draft, Writing — Review & Editing, Visualization, Project Administration.

## Conflict of Interest

The author declares no conflicts of interest per International Committee of Medical Journal Editors (ICMJE) guidelines.

## Funding

This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

## Data Availability

All input data used in this study are publicly available. Axis B counts derive from the NCBI PubMed E-utilities (https://www.ncbi.nlm.nih.gov/books/NBK25501/), the CiNii Research API (https://support.nii.ac.jp/en/cinii/api/api_outline), and OpenAlex (https://openalex.org/). Query strings are generated deterministically by the published query builder (`src/food_query_terms.py`, `src/evidence_mapping.py`) from each food's key, so every query in the study can be regenerated exactly; the 875 raw count responses that those queries returned are published under `data/query_log/`, pinning each reported count to its retrieval snapshot. The one class of raw response **not** redistributed is the PubMed efetch dumps of titles and abstracts, which are third-party content; they are regenerable with `src/fetch_l2_records.py`, and every PMID they contain appears in the published screening ledger.

Axis A source pages are the 15 publicly published lay-media URLs listed in `data/sources.csv` with their access dates; the raw HTML is not redistributed, and each coded row in `data/claims.csv` carries the verbatim supporting quotation, so every attribution can be located in the live source. The full screening ledger — one row per (food, PMID) with both coders' labels, whether the author adjudicated it, the final label, and the reason code — is published as `data/screening.csv`, the hand-labelled reference set as `data/screening_golden.csv`, and the two coding protocols as `data/coding_protocol.md` and `data/screening_protocol.md`. The adversarial third pass is published as `data/screening_thirdpass.csv`, one row per re-screened record carrying its verdict, its reason, and the author's ruling where one was required.

Analysis code (Python 3.14.3, pandas 3.0.1, scipy 1.17.1, numpy 2.4.2, statsmodels 0.14.6, matplotlib 3.10.8, weasyprint 68.1) — including the source-fetching and text-extraction scripts, the claim-coding and Axis A aggregation modules, the Axis B query builders and PubMed/CiNii/OpenAlex collectors, the record-fetching and screening modules, the query logs, the figure pipeline, and the four verification scripts that between them recompute every number reported here (`src/verify_stats.py` for the analysis statistics, `src/reconcile_coders.py` for the Axis A agreement figures, `src/build_screening.py` for the screening reliability and exclusion counts, and `src/build_thirdpass.py` for the third-pass ledger) — is publicly available at https://github.com/rehabilitation-collaboration/warming-cooling-foods (MIT License). All numerical results reported in this manuscript are reproducible from the analysis code at repository commit `83394075d4ab93e60393a9aa8595a78dfe0b2a77`, recorded as the immutable reproducibility anchor at first posting.

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

*Coding covered 196 distinct foods across 15 sources (Tier 1: 9 corporate/association; Tier 2: 6 individual-expert blogs), 649 rows, two-coder Cohen's κ = 1.000 for direction on the 481 co-coded items — extraction overlap was lower (Jaccard 0.54 in round 2) and every coverage difference was adjudicated by the author against the source text (Methods). Of the 157 foods with Tier-1 coverage, 11 are composite category labels ("nuts," "spices," "shellfish," "leafy greens," "citrus," "red meat and fish," "chinese tea," "yellow-green vegetables," "small fish," "fatty meat," "animal fat") that cannot be turned into a single unambiguous query and were excluded from Axis B. The 29 queried foods with no Tier-1 source lie outside the primary frame and enter only the Tier 1+2 sensitivity refit.*

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
| Third-pass re-screen of core-zero foods: records / flagged / overturned | 419 / 5 / 0 |

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

*L2 is the raw count of PubMed records in which a food term co-occurs with one of the four thermal-effect terms; L2′ is the subset that screening retained as on-construct. Golden-set validation (169 hand-labelled records: 29 include, 140 exclude): coder 1 precision 0.867 / recall 0.897 / F1 0.881; coder 2 precision 0.813 / recall 0.897 / F1 0.853.*

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
| Logistic, adjusted — coverage, whole-food studies only | OR 1.033 | 0.834 to 1.280 | 0.764 |
| Logistic, adjusted — coverage, primary reports only | OR 1.035 | 0.840 to 1.275 | 0.745 |
| Logistic, adjusted — coverage, both narrowings applied | OR 1.026 | 0.821 to 1.281 | 0.823 |
| Fisher exact — warming vs cooling zero rate (core) | OR 0.873 | 0.242 to 3.147 | 1.000 |
| Mann–Whitney U — warming vs cooling L2′ (core) | U = 290.5 | — | 0.930 |

**Zero-research rate at each level of lay-source coverage:**

| Coverage ≥ | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Foods | 146 | 79 | 51 | 38 | 24 | 19 | 11 | 6 | 1 |
| No on-construct study | 118 | 58 | 37 | 26 | 18 | 15 | 9 | 4 | 0 |
| % | 80.8 | 73.4 | 72.5 | 68.4 | 75.0 | 78.9 | 81.8 | 66.7 | 0.0 |

*Primary model pseudo-R² = 0.176; 28 of 146 foods have ≥ 1 on-construct study. Regression intervals are Wald. Poisson deviance/df = 2.296 confirmed over-dispersion before the negative binomial was fitted; its dispersion parameter (α = 4.81) was estimated by grid-profiling the likelihood and then held fixed, so the IRR interval is conditional on that value. The single food at coverage ≥ 9 (banana, one on-construct study) makes that column uninformative on its own; it is shown because the analysis plan commits to reporting every level rather than selected thresholds. Five analyses were computed outside the fixed plan and are labelled as such wherever they appear. The Tier 1+2 refit (n = 175) gave coverage OR 1.006 (0.882–1.148), p = 0.926, with 144/175 (82.3%) having no on-construct study; the coverage-vs-(L2′/L1) rank correlation was ρ = +0.187 (+0.024 to +0.340), p = 0.024; and the three narrowed-definition refits are the rows above, which drop the 32 studies of a principal dietary constituent, the 20 reviews and meta-analyses, or both (the classes overlap in six records), leaving 25, 27 and 22 foods respectively with any study (zero rates 82.9%, 81.5% and 84.9%). Volume stayed significant under every narrowing (OR 1.707, 1.654 and 1.602; all p < 0.001). Only the adjusted logistic model is confirmatory; the rest are descriptive and uncorrected for multiplicity.*

### Table 4. The 37 core foods for which the search retrieved no on-construct study, by lay-source coverage

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

*"Raw L2" is the unscreened keyword co-occurrence count. Every one of these 37 foods has at least three independent Tier-1 sources assigning it a thermal direction, and none of the records this query retrieved and this screen retained studies a human ingesting it with a thermal outcome measured. A zero is a floor on the evidence, not a census of it: a study phrased entirely outside the four-term search vocabulary never entered the candidate set (Limitations, third point).*

### Table 5. Flagship foods: total volume, keyword hits, and on-construct studies

| Food | Lay direction | Sources | L1 total | Raw L2 | L2′ | Whole-food primary | L2′/L1 | What the direct evidence shows |
|---|---|---:|---:|---:|---:|---:|---:|---|
| chicken | warming | 6 | 94,310 | 278 | 0 | 0 | 0% | No study of a human eating chicken with a thermal outcome; the 278 hits are avian and poultry-production research |
| green tea | cooling | 4 | 15,476 | 62 | 17 | 0 | 0.11% | Tied with white sugar for the largest screened count, but every one of the 17 is a constituent study (13), a review (8), or both — nothing survives the narrowest reading |
| white sugar | cooling | 6 | 85,454 | 195 | 17 | 16 | 0.02% | The other food at 17 studies, the more widely covered of the two, and the one that survives narrowing almost intact |
| coffee | cooling | 4 | 23,286 | 24 | 7 | 3 | 0.03% | Caffeine *raises* core temperature under heat exposure (Peel et al. 2025, n = 30, g = 0.44) — opposite to the lay attribution, and 3 of the 7 test caffeine rather than coffee |
| ginger | warming | 8 | 5,730 | 35 | 7 | 5 | 0.12% | Thermic effect positive in Mansour et al. (2012, n = 10), null in Fagundes et al. (2021, n = 20) |
| chili pepper | warming | 6 | 1,943 | 30 | 12 | 5 | 0.62% | Half the 12 are capsaicin at dietary doses; the highest on-construct share among the foods in this table, though not in the frame (mugicha reaches 2.70% on one study out of 37 records) |
| milk | cooling | 3 | 171,272 | 586 | 6 | 2 | 0.004% | 461 of the 586 keyword hits are animal or livestock-heat research; 4 of the 6 survivors test a milk constituent |

*"Whole-food primary" is an unplanned quantity, added in revision: the count remaining when records sub-labelled as testing a principal dietary constituent and records sub-labelled as reviews or meta-analyses are both removed — the narrowest reading reported in the Results. The two classes overlap, so the column is not L2′ minus their sum. L2′/L1 is computed on L2′ as reported.*

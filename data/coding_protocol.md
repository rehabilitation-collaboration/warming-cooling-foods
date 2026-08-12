# Axis A Coding Protocol — Lay Belief Breadth (consensus coverage)

Agreed 2026-08-03. This document fixes how each food's warm/cool attribution is
coded from the frame sources, so that Axis A ("breadth of belief") is
reproducible and defensible against a "subjective" critique. It mirrors the
bibliographic-coding approach of García-Hernández et al. (2023).

## 1. Sampling frame (fixed in advance)

The frame is the set of Japanese lay-facing sources in `sources.csv` that were
verified (2026-08-03, two independent existence scans) to (a) be reachable over
HTTP, (b) present a concrete list assigning individual foods to warming/cooling,
and (c) permit fetching per robots.txt.

- **Tier 1 (primary frame): 9 corporate/association-operated sources.** Sources
  sharing one operator count as one (e.g. Kracie).
- **Tier 2 (sensitivity only): 6 individual-expert blogs.**

Axis A metrics are computed on Tier 1. Tier 2 is added only to test whether
conclusions are stable (sensitivity analysis). The frame is frozen before
coding; no source is added or dropped after seeing the results.

**Frame corrections applied 2026-08-03 (before any coding of results).** Two
entries were verified during fetching to not meet inclusion criterion (b) — a
concrete per-food warm/cool list — at their registered URL:

- **`tsumugu` (紡ぐしあわせ薬膳協会, Tier 1) — excluded.** The registered URL was
  the association's landing page. A search of the same operator's domain
  (`yakuzen.or.jp`) found only seasonal wellness columns naming a few 寒涼性
  foods, not a comprehensive per-food warm/cool list comparable to the other
  Tier-1 sources. It fails criterion (b) and is excluded rather than substituted,
  keeping the frame homogeneous. **Tier 1: 10 → 9.**
- **`hiesyo_com` (冷え症.com, Tier 2) — URL corrected.** The registered URL was a
  blog index. A concrete macrobiotic yin-yang food list on the same domain was
  located and the `url` field corrected. This is a URL correction (same source,
  same operator), not a substitution, so frame identity is preserved.

No source was added, and the correction/exclusion was decided from page content
during fetching — not from any Axis A result.

**robots.txt `unknown` handling** (`sources.csv` `robots_ok=unknown`): a 404 on
`/robots.txt` means no robots file exists → fetching is permitted (treat as
`yes`). If `/robots.txt` is unreachable for other reasons, check the target page
responds 2xx with `curl -I` before fetching and record the outcome in the
source's `notes`. This applies to `kracie` (robots 404 → allowed) and
`karada_onkatsu` (robots not retrievable → verify page reachability first).
Kracie stays in the Tier-1 frame (it is a coffee=cool source and drops out only
if the page itself becomes unreachable).

## 2. Unit of coding

One row per (food, source) pair where that source assigns the food a direction.
A source that does not mention a food produces no row for it (absence ≠ neutral).

**`claims.csv` schema** (columns): `food_en`, `food_ja`, `source_id`,
`direction` (warm/cool/neutral), `quote` (verbatim label + short location),
`condition` (optional, blank unless the source splits by state — e.g. `raw` vs
`cooked` ginger). A food split by condition gets one row per condition. The
`condition` column may be omitted from the file entirely when unused;
`load_claims()` tolerates its absence.

## 3. Direction rules

Map each source's own vocabulary onto the binary lay direction:

| Source vocabulary | Coded direction |
|---|---|
| 温める / 体を温める / 温性 / 熱性 / 陽性 / 陽 | `warm` |
| 冷やす / 体を冷やす / 涼性 / 寒性 / 陰性 / 陰 | `cool` |
| 平 / どちらでもない / 中庸 | `neutral` |
| 温活向き / 温活食材 / 温活におすすめ / 温活をサポート / 温活に適している / 温活に役立つ / 温活と相性のよい | `warm` |
| 温活で控えたい / 温活中は避けたい / 温活で控えた方がよい / 温活の妨げになる | `cool` |

- **温活 on its own is the name of an activity, not a direction.** It carries one
  **when the sentence places a food, or a food class, on one side of it** — the
  food is what is recommended for 温活, suits it, helps it, or is to be limited
  during it. `温活向き` and `温活食材` say the food serves warming, `温活で控えたい`
  says it works against it. `温活レシピ` and `温活に関する商品` place no food on
  either side and state no direction.

  **The rows above are worked examples of that test, not a closed list.** The
  fifteen frame sources write 温活 with 228 distinct continuations, and the same
  wording appears on both sides of the test: 温活に効く食べ物 is an attribution in
  「にんにくは温活に効く食べ物です」and an article title in
  「温活に効く食べ物の見分け方」. No list of strings separates those; the
  grammatical question does, and it is the one §9.5 already asks of dishes —
  what is the sentence predicating this of? 温活 modifying a noun that is not a
  food (レシピ, 商品, 術, ガイド, 習慣, a section's own メニュー heading) never
  places a food anywhere, whatever the wording.

  ★ **2026-08-11**: this replaced "only in the constructions above". The closed
  list was over-specified: two coders reading the same batch split 5 includes
  against 11 on whether 温活に適している, 温活と相性のよい食材 and 温活に役立つ
  食べ物 counted, and that split moves include/exclude, κ and n_sources. The
  enumeration behind the change is `data/ledger_work/onkatsu_constructions.json`
  (regenerate by scanning `data/sources_raw/*.txt` for 温活).

  The 温活 rows were added on 2026-08-11 to match
  coding already in `claims.csv` rather than to extend §3: `basefood`'s
  飲み物の選び方: 温活向き ほうじ茶 / ココア are coded `warm` and its
  温活で控えた方がよい=緑茶 `cool`, and `karada_onkatsu`'s
  温活食材の中で最も代表的なのがしょうがです is coded `warm` — three of these
  carry no other direction vocabulary at all, so a ledger that did not read 温活
  as direction could not regenerate them (§9.7).

- Record the source's **verbatim label** and a short quote/location in
  `claims.csv` (`quote` column) for traceability.
- If a source lists a food under both warm and cool (e.g. raw vs cooked ginger),
  code the row as stated by the source and note the condition in `quote`; do not
  silently pick one. Cooked/raw splits are kept as separate rows with a
  `condition` note.
- Do **not** infer a direction the source does not state. No coding from the
  coder's own knowledge.
- **Two-column tables — read the column header, not adjacent prose.** Several
  sources present a "warming | cooling" two-column table. Code each food by the
  column it sits under, not by nearby sentences. Kracie's extracted text, for
  example, lists coffee under the "体を冷やすもの" (cooling) column of its
  drinks row; a separate "冷たい飲み物" (cold drinks) item just below refers to
  serving temperature, not the food's nature — do not conflate the two. Coffee
  is coded `cool` for Kracie on the column header.

## 4. Food naming

- Each `claims.csv` row carries `food_en` and `food_ja`. **`food_en` is the
  canonical key** used for aggregation; `food_ja` is for traceability. When
  `food_en` is blank, the Japanese label is normalized via a synonym table
  (e.g. しょうが/生姜/ジンジャー → ginger). The key derivation and synonym
  table live in `claim_mapping.py` and are unit-tested.

## 5. Axis A metrics (computed, not hand-entered)

For each food, over Tier 1 sources:
- `n_warm`, `n_cool`, `n_neutral` = distinct sources coding that direction.
- `n_sources` = distinct sources mentioning the food (breadth of belief).
- `direction` = majority of warm vs cool (ties → `contested`).
- `consensus` = max(n_warm, n_cool) / (n_warm + n_cool); undefined if
  n_warm + n_cool == 0.

## 6. Coffee branch (PLAN decision)

"Coffee = cools" is adopted as the flagship example only if ≥3 Tier-1 sources
code coffee as `cool`. Otherwise the representative example is replaced. (Kracie
Kampoful Life already codes coffee as cooling; final count decided from data.)

## 7. Provenance

Every coded row records `source_id`, `accessed` date, and `quote`. Raw HTML is
saved under `data/sources_raw/` (git-ignored, not redistributed); `sources.csv`
carries the public provenance.

## 8. Inter-coder reliability (reproducibility)

### Who the coders are

Both coders are large language models running under the author's direction, not
human raters. Recorded here because an agreement statistic means nothing without
knowing what produced it:

| Pass | Sources | Coder 1 | Coder 2 |
|---|---|---|---|
| Round 1 | 6 Tier-1 (yomeishu, esse, macaroni, oitr, kawashimaya, basefood) | `claude-opus-4-8`, reading the stored source text in the author's working session | `claude-sonnet-4-6`, separate agents |
| Round 2 | 9 (prezo, jsfca, kracie + 6 Tier-2) | `claude-sonnet-4-6`, separate agents | `claude-sonnet-4-6`, separate agents |

Each coder-2 agent received only the protocol and the stored source text, with
coder 1's output withheld, and wrote its coding straight to its own file. The
author fixed the protocol, adjudicated every disagreement and coverage
difference, and verified the result against the source text.

Adjudication proposals for the round-2 coverage differences were themselves
produced by `claude-sonnet-4-6` agents and reviewed by the author against the
stored text; that review overturned three of them (the `jsfca` トマト/スイカ/きゅうり
rows, §3).

**This bounds what the kappa below can mean.** In round 2 both coders are
independent instances of the *same* model, so their agreement measures the
stability of one model's reading, not the convergence of two independent
judgments. It is an upper-bound-leaning reliability estimate and is not
comparable to a kappa between human raters. The load-bearing reproducibility
evidence for Axis A is not the kappa but `verify_claims.py`: every retained row
is checked to occur verbatim in the stored source text, and every row carries
its source, quotation and access date, so a reader can re-derive the coding
from the published frame.

### Procedure

Each source is coded **independently by two coders** into the same schema. The
two codings are reconciled on the (source, food, condition) key by
`src/reconcile_coders.py`, which reports agreements, direction disagreements,
and coverage differences (a food one coder found and the other missed), and
computes Cohen's kappa on the co-coded items.

- **Agreement** rows are accepted as-is.
- **Disagreements and coverage differences** are adjudicated by the author
  against the source text and resolved per §3 (no direction is coded that the
  source does not state; substitute-recommendation context is not a nature
  attribution).
- The **reconciled** `claims.csv` is the frozen dataset; the reported kappa is
  the reproducibility evidence for Methods.

This two-coder pass complements `verify_claims.py`: grounding only checks that a
food label exists in its source, whereas reconciliation catches direction
errors, missed foods, and inclusion-rule slips that grounding cannot.

**First round (Tier-1 sources yomeishu/esse/macaroni/oitr/kawashimaya/basefood,
2026-08-04):** Cohen's kappa = 1.000 on 267 co-coded items (0 direction
disagreements). Five coverage differences were adjudicated: `yomeishu` celery
(coded cool — coder 1 had missed it, present verbatim in the cooling 野菜 line)
was added; `basefood` てんさい糖/はちみつ/玄米/そば (previously coded warm) were
dropped because the source only recommends them as substitutes for white
sugar/refined flour, without assigning a warming nature (§3). Final Tier-1
first-round dataset: 268 rows, all grounded, both coders in full agreement.

**Second round (remaining 9 sources prezo/jsfca/kracie and Tier-2
attaka_navi/onkatsu_note/karada_onkatsu/hiesyo_com/macrobiotic_rashinban/gveggie,
2026-08-04):** Coder 1 (236 records) and coder 2 (377 records) coded the nine
sources into the shared schema, both as independent `claude-sonnet-4-6` agents
blinded to each other's output (see "Who the coders are" above). Reconciliation on the
(source, food, condition) key gave Cohen's kappa = 1.000 on the 214 co-coded
items (0 direction disagreements); grounding passed for every record of both
coders. The 185 coverage differences (22 coder-1-only, 163 coder-2-only —
coder 2 coded more exhaustively) were each adjudicated against the source text
per §3. Seven were dropped: substitute-recommendation context without a nature
attribution (`attaka_navi` 黒糖; `karada_onkatsu` はちみつ/玄米), prepared
beverages rather than a food's nature (`kracie` 白湯/生姜湯), and forms not
present verbatim as coded (`hiesyo_com` アジ/サケ, present only as アジの開き/塩サケ).
Three `jsfca` records (トマト/スイカ/きゅうり) that coder 2 had read as warm from
an adjacent 陽性 sentence were corrected to cool, matching the source clause
「…を摂り、体をクールダウンさせましょう」. After removing eight within-source
duplicate records created when coder-1 and coder-2 codings collapsed to the same
(food, direction, season) key, the second round added 381 rows. Combined frozen
dataset: 649 rows across 15 sources, all grounded, both coders in full agreement
on direction (kappa = 1.000).

**Extraction agreement, stated separately (added 2026-08-08).** The kappa above
covers the *direction* assigned to items both coders extracted. It is not a
reliability estimate for extraction itself, and extraction is where the coders
actually diverged: in round 2, coder 1 returned 236 records and coder 2 returned
377, agreeing on 214, which is a Jaccard index of 0.54. Every coverage difference
was resolved by the author against the source text rather than by any agreement
statistic, so the reproducibility evidence for Axis A is the verbatim grounding
check (`verify_claims.py`), not the kappa.

**Two food keys corrected after this reconciliation ran (added 2026-08-08).**
The reconciliation counts recorded above are the values as executed on
2026-08-04. Two food-key operations were applied afterwards, during RB-5
pre-processing, both documented as D29 in the project handoff:

- `azuki bean` was merged into `adzuki bean` (the same food under two keys; the
  synonym was already registered in `food_query_terms.SYNONYMS`).
- 干し柿 was split out of `persimmon` into `dried persimmon`, because two sources
  had filed it under `persimmon` while a third kept it separate, which had put
  the same source on both the warm and the cool side of one key.

Re-running the same reconciliation against the frozen `claims.csv` therefore
returns **218 co-coded items and 177 coverage differences in round 2** (rather
than 214 and 185), with direction agreement unchanged at **kappa = 1.000**. The
manuscript reports both figures and says why they differ; a reader reproducing
the reconciliation from the published data will obtain the 218/177 pair.

## 9. Candidate ledger — recording what was read and not coded

Added 2026-08-09. Sections 1–8 fix how a kept attribution is coded. They do not
record what was read and dropped, and that asymmetry is what this section
closes.

### 9.1 Why the ledger exists

Axis B keeps both sides of its judgment: `screening.csv` carries 298 includes
*and* 12,435 exclusions, each with a reason code, so a reader can check the
exclusions rather than take them on trust. Axis A kept only the 649 kept rows.
`verify_claims.py` shows that each of those rows is real — every `food_ja`
occurs verbatim in its cited source — but no artefact shows that nothing was
missed, and the two are different claims.

The gap is not hypothetical. Re-reading kawashimaya's table found that its third
category, 冷たい食べ物 (アイスクリーム / かき氷 / サラダ / そうめん / 冷やし中華),
produced no rows at all, while the two categories beside it — 夏野菜 (6 items)
and 南国の果物 (5 items) — were coded completely. Under §9.4 those five are
`serving-temperature` exclusions, so the coders' outcome was very likely
correct; the point is that nothing in the published data distinguished "judged
and excluded" from "not seen". The ledger records the judgment either way.

### 9.2 Enumerating candidates

Candidates are enumerated by `src/extract_candidates.py` from the structure the
sources use to present foods — delimiter-separated lists, `category：item` lines,
one-item-per-line blocks under a thermal heading, and running text. The
enumeration uses **no food dictionary**. Searching the sources with the
vocabulary already in `claims.csv` would be self-referential: a food that no
source had ever been credited with could not be found that way, which is exactly
the failure the ledger exists to detect.

A candidate is a **span, not a resolved food name**. Japanese running text
offers no reliable token boundary for foods written in kana — じゃがいも ends in
the particle も, たけのこ contains の — so the extractor emits overlapping
granularities (the clause-level span and the particle-level token) and leaves
naming to the coder, which is what §3 already asks of one. A coarse span is
still judgeable; a food that never became a span is not.

**Recall is measured, not assumed** (`src/verify_candidate_recall.py`). The
reference set is the 649 rows already coded: each is a known-correct answer,
because §7's grounding check confirms its label occurs verbatim in its source.
Every one of the 649 is surfaced by the enumeration (covered-recall 1.0000;
1.0000 on Tier 1 alone), 89.5% of them as an exact token. The first
implementation reached only 0.9106, and the four blind spots that measurement
exposed — a thermal vocabulary carrying 体を温 but not 体を冷, a heading test
that rejected 体を温める肉・魚 over its interpunct, a heading consumed rather
than read so that ビールや炭酸系カクテルは体を冷やしやすい yielded nothing, and
inline emphasis splitting a sentence across lines — are each kept as a
regression test.

This is a necessary condition, not a sufficient one: recall against the coded
rows cannot speak for foods no coder ever recorded. A second check that does not
depend on `claims.csv` is therefore reported alongside it — of the 3,852
body-text lines across the frame, **every line containing thermal vocabulary
produces at least one candidate** (0 uncovered). Since §3 forbids coding a
direction the source does not state, a line that attributes a direction must
carry that vocabulary, so no attributing line goes unexamined.

### 9.3 Decision

Each candidate gets `include` or `exclude` with a reason code. `include` means
the span carries an attribution to be coded under §2–§4; the coder also returns
the `food_ja`, `food_en` and `direction` for it, so the ledger's include rows
regenerate `claims.csv` (§9.7).

### 9.4 Exclusion reason codes

Every code below is grounded in a rule or an adjudication this protocol already
records. None is introduced for this ledger alone.

| Code | Meaning | Basis |
|---|---|---|
| `serving-temperature` | The source is describing how cold or hot the item is served, not the nature attributed to the food (アイスクリーム, 冷やし中華, 白湯). | §3, final bullet: Kracie's 冷たい飲み物 "refers to serving temperature, not the food's nature — do not conflate the two"; §8 round 2 dropped kracie 白湯/生姜湯 as prepared beverages rather than a food's nature. |
| `no-direction` | A food is named but the source assigns it no direction — nutrient illustrations, recipe notes, substitute recommendations. | §3: "Do not infer a direction the source does not state." §8 round 1 dropped basefood てんさい糖/はちみつ/玄米/そば, and round 2 attaka_navi 黒糖 and karada_onkatsu はちみつ/玄米, on exactly this ground. |
| `not-verbatim` | The span is not a form the source actually presents (a coder's paraphrase or generalisation). | §8 round 2 dropped hiesyo_com アジ/サケ, present only as アジの開き/塩サケ; §7 requires the verbatim label. |
| `not-food` | The span names something that is not a food: a colour, a shape, a nutrient, a cooking method, a body state. Sources use these to explain how to *tell* warm from cool (「色は赤、黒、黄色…が温活食材」). | §2: the unit of coding is a (food, source) pair. |
| `navigation` | The page's apparatus rather than its own attributions — related-article links, tags, rankings, author blurbs, site chrome, and the reference lists a section cites. | §1: the frame is each source's per-food warm/cool list, not the page around it. A work the source cites is another author's claim, not this source's attribution, even where the citation's title names a food (`ショウガ摂取がヒト体表温に及ぼす影響`). |
| `fragment` | An extraction artefact: a partial word or clause that is not a token the source presents as an item. Includes the residue of the `wrapped` path, where two lines are joined and the join is not a form the source presents (`かき氷サラダ`, `きゅうりトマト`). | Follows from §9.2 — overlapping granularities are emitted deliberately, so their residue is dropped here, on the record, rather than by a silent filter. |
| `duplicate` | The same (food, source, direction) is already carried by another span **on the same line group** — the granularities §9.2 emits from one line, where the clause-level span and the particle-level token name the same food. **Not** a repeat in another section: see below. | §9.2 emits overlapping granularities from one line on purpose, so one of them has to be the row and the others have to be dropped on the record. §8 round 2 removed eight within-source duplicates, but on the finished `claims.csv`, not on a coder's partial view. |

**A repeat in another section is an `include`, not a `duplicate`.** A source that
names 生姜 in its table and again in a recipe made the attribution twice, and the
ledger records what was read (§9.1). Collapsing the two is a property of
`claims.csv`, where §2's one row per (food, source) pair applies, and it happens
mechanically when the ledger is projected there (§9.7) — not in a coder's head.

The distinction is not cosmetic. Candidates are batched (§9.6), and a coder sees
one batch. Scoping `duplicate` to the whole source asks a coder to drop a span
because *another batch's coder will keep* the same food — a judgment it has no
way to make. Measured on the kawashimaya canary: all 13 of one coder's
source-wide duplicates pointed at spans in a batch it had never seen, so had the
other coder excluded those too, the food would have left the ledger with both
coders believing the other had it.

**Applying them in order.** Two codes can both be literally true of one span
(`かき氷サラダ` is a form the source does not present *and* an extraction
artefact; `これらの香味野菜やスパイスは` carries no direction *and* repeats a
food already coded). Coding the first code that fits, in the order below,
settles which one is recorded. The order is not a new judgment — it follows from
the definitions above and from what each code's basis already covers:

1. **`navigation`** — is the span in a region the frame excludes? §1 makes the
   frame each source's own per-food warm/cool attributions, so a region falls
   outside it when the text there is not this source speaking about a food:
   the page's apparatus and chrome, another author's claim, or a pointer to
   text located elsewhere. The instances met so far are a related-article link,
   a tag, a ranking, an author blurb, a 参考： citation block, an in-page table
   of contents, a footnote or fine-print block, a qualification or
   certification list, a product card, a disclaimer, a signature or date line,
   and the site's own promotional block. **That list is worked examples of the
   test above, not the test itself** — a region answering the test is
   `navigation` whether or not it is named here. This was measured: coding the
   corpus against the six-item list this rule first carried produced six
   further kinds of apparatus that the list did not name, so a closed list is
   not available for this code. §1 puts such regions outside the frame
   regardless of what they contain, so the question comes before any question
   about the span's shape, and everything the extractor emits from one is
   `navigation`, whole line or fragment of one.

   **A span emitted from more than one line.** §9.2 emits each candidate once,
   carrying every line it occurs on, so one span can sit in an excluded region
   on one line and in the body on another. Rule 1 fires only where **every**
   occurrence is in an excluded region; otherwise the span falls through to
   rules 2-7 and is judged on its body occurrence. §1 excludes regions, not
   strings: a food this source attributes in its body does not leave the ledger
   because the same word also appears in its tag cloud. Four independent coder
   derivations across jsfca, yomeishu and kracie reached this rule from the
   text above before it was written down; the alternative they had to choose
   between — letting the first emitted line decide — makes the code a property
   of extraction order rather than of the frame.
2. **`fragment`** — is the span a form the **source does not present as an
   item**? This is the table's wording above, and it is the whole test. A span
   is an item where the source itself sets it off — a list entry, a table cell,
   a heading, or a food名 standing on its own in a sentence. It is *not* an item
   when the extractor has cut into or across the source's own units.

   **The test is about the cut, not about what the cut produced.** A string the
   extractor lifted out of running prose is residue whatever it happens to name
   — a noun, a conjunction (`しかし`, `一方`), a pronoun (`これら`), an adjectival
   stem (`一時的`, `大切`), a numeral (`1つ`), or a single character (`熱`, `逆`,
   `冬`). None of these is a unit the source offered, so all of them are
   `fragment`. Without this sentence such spans match none of the shapes below,
   fall through to rule 4, and the published ledger asserts that しかし is not a
   food — literally true, and plainly not what that code is for. The shapes
   below are worked examples of the test; they are not a closed list of what
   fails it.

   - a partial word or a cut mid-phrase: `し中華`, `育つ果物`, `変える働き`
   - a `wrapped` splice joining two lines: `かき氷サラダ`, `きゅうりトマト`
   - a clause or sentence, with or without direction vocabulary:
     `カリウムの持つ利尿作用により`, `体の芯から温まります`
   - **a food name carried along with its modifiers or its topic particle**:
     `水分を多く含む夏野菜は`, `りんごやぶどうなど寒い地域で育つ果物は`,
     `サポートしてくれる食材`, `これらの香味野菜やスパイスは`. The source presents
      夏野菜 and 果物; it does not present these longer strings as items. §9.2
     emits both granularities on purpose, and the shorter one — enumerated from
     the same line group — is the row.
   - **a span naming two or more foods jointly**: `豚肉や根菜類`, `味噌や生姜など`.
     A ledger row carries one `food_ja` (§9.7), and each of the foods is
     enumerated separately from the same line group.

   **The cut can also join two units the source did present.** A wrapping table
   row, the `wrapped` path, or a list marker can glue a span together out of
   material that was set off: a row label and its first cell
   (`野菜 ...... きゅうり`), a marker and its entry (`└小豆`), an entry and a
   trailing 等 (`きゅうり等`), or a food and the clause predicated of it
   (`納豆は温める`). The source did set the food off here; what the extractor did
   was carry a neighbour along with it. Such a span is not `fragment`. It is the
   row for the food it names, with §9.7's single `food_ja` naming the food and
   the `quote` keeping the span as the source wrote it.

   This limb and the joint-naming bullet above look alike, and what separates
   them is whether the food survives anywhere else: `豚肉や根菜類` is dropped
   because the source enumerates 豚肉 and 根菜類 separately from the same line
   group, while `野菜 ...... きゅうり` is kept because a glued row is the only form
   in which that source presents きゅうり at all — on yomeishu, six foods exist
   in no other form. **A coder cannot settle that question.** §9.6 splits a
   source into batches, so whether another batch enumerates the food cleanly is
   not visible from inside one; coders record what they see and flag the span,
   and the ledger settles it in adjudication, where the whole source is. Which
   coder rescues and which applies the bullet literally was measured across the
   corpus and is not a property of the coder — it tracks how badly the source's
   own enumeration was broken.

   Nothing further can be judged about a span the source never offered as a
   unit, so this is asked before the questions about what it names.
3. **`not-verbatim`** — is it a form a *coder* produced (a paraphrase or
   generalisation)? Its basis is §8's hiesyo_com ruling, where a coder wrote アジ
   for アジの開き. In this ledger the candidate string comes from the extractor,
   so this code is for the rare case where a coder restates rather than judges.
4. **`not-food`** — the span is one the source presents (rule 2 did not fire);
   is what it names not a food? Three kinds reach this rule: things that are
   plainly not food (`ビタミンB群` a nutrient, `寒さ` a condition, `南国` a place),
   a section's own title (§9.5), and **generic terms that are food-shaped but
   name no particular food** — 食材, 食べ物, 料理, レシピ, メニュー, 一品, 飲み物.
   §2 makes the unit of coding a (food, source) pair, and a generic term
   identifies no food to pair with the source; coding one would mint a food
   named "ingredient".

   **A product or brand name is `not-food` on the same ground.** Four of the
   fifteen sources are company sites, and a brand names a product rather than a
   food in §2's sense — coding `ベースフード` would mint a food called "BASE
   FOOD". The hand coding this ledger replaces carried no brand row in any of
   the 151 rows those four sites contributed, so this records an existing
   practice rather than a new judgment.

   **The generic-term limb reaches the bare term only.** 飲み物 names no food;
   `冷たい飲み物` names no food either, but what the source is saying about it is
   how it is served, and that is rule 6's question and the case §3 closes on.
   A generic term carrying a serving-temperature modifier is therefore not
   disposed of here — see rule 6.
5. **`no-direction`** — is the food named without the source assigning it a
   direction? This precedes `duplicate` because `duplicate` is defined on
   (food, source, **direction**), and a span carrying no direction cannot meet
   that condition. It does **not** cover a span whose point is the temperature
   the item is served at: the source has said something there, just not about
   the food's nature, and rule 6 is where that is recorded. Reading this rule as
   covering it is what made rule 6 unreachable from its own paradigm case.
6. **`serving-temperature`** — is what the source describes the temperature the
   item is served at rather than the nature attributed to it? §3's closing
   bullet and §8's round-2 kracie ruling make `冷たい飲み物` and 白湯/生姜湯 this
   code's paradigm cases, so the order has to reach them, and two earlier rules
   would otherwise take them first: rule 4 because 飲み物 is a generic term (see
   rule 4, which excludes the modified form), and rule 5 because the source has
   attributed no nature. **Rule 5 does not fire on a span whose temperature
   modifier is the source's point** — the source has said something about the
   item, just not about its nature, and that is precisely the distinction §3
   draws in telling the coder not to conflate the two. Rules 1-3 still come
   first: a temperature phrase the extractor cut out of a sentence is
   `fragment`, because nothing can be judged about a form the source never
   offered as a unit.
7. **`duplicate`** — is this (food, source, direction) already recorded from
   another span **on the same line group**? Rules 2 and 4 remove most of what
   would once have been a duplicate, so this code is rare; it is kept because
   the granularities of one line can still both be items the source presents.

A span that survives all seven is an `include`.

**When the two coders record different codes.** §9.6 puts two coders on every
candidate, and they can agree on the decision while differing on which code
names it. They do so often: measured on the completed corpus before this sweep,
1,964 of the 17,830 agreed exclusions (11.0%) carried two different codes
(`python3 -m src.rd4_delta` prints the current figure). That disagreement is the
situation this order was written for — both codes are literally true of the span
— so the order settles those rows as well: **the code recorded is the first one,
in the order above, that either coder reached.**

Neither coder is preferred over the other. Preferring one would make the
published `reason` column a property of which coder was assigned the batch
rather than of the span, and the corpus shows why that is not a safe shortcut:
which coder reads a rule literally and which rescues an attribution is not
stable within a coder, varying by source and even by batch. The order settles
1,952 of the 1,964 rows, moving the recorded code away from c1 on 726 of them
and away from c2 on 1,226 — it favours neither, which is what a uniform ruling
means. The remaining 12 are author rulings, filed where the order was itself
the thing in doubt: rule 6's paradigm cases, which every earlier rule could
also claim, and two brand names covered by rule 4.
`python3 -m src.rd4_delta` prints all of these figures, and they move whenever
a ruling is filed, so read them there rather than from this paragraph.

This settles only which name an exclusion carries. It moves no candidate between
`include` and `exclude`, so κ (§9.6, computed on the decision) and every Axis A
count are unchanged by it. Where the order is itself the thing in doubt — as it
was for rule 6 above — the row goes to author adjudication instead of to
whichever code happens to sort first.

**Why this order was changed.** Three rounds of the kawashimaya canary measured
it. Round 1 had no order at all and the two coders agreed on *why* only 46.2% of
their agreed exclusions were excluded. An order keyed on "is this a complete
noun phrase" took that to 74.7%, then to 89.0% once the category and dish rules
were settled — but it left a criterion that competed with the table's own
wording, and every one of the 38 remaining splits was a span where one coder
asked "did the source present this" and the other asked "is this a well-formed
noun phrase". Rule 2 now asks only the first question. Round 3 also showed
`navigation` unreachable behind a shape test, since a citation block reaches the
extractor as splices; hence rule 1.

### 9.5 Category and umbrella labels are included, not excluded

Sources attribute directions to classes as well as to foods — 葉物野菜, 香辛料,
ナッツ類, 海藻, 赤身魚. **These are `include`.** The source did make the
attribution, and dropping it from the ledger would misdescribe the source.

Whether such a label can carry an Axis B measurement is a separate question,
already settled elsewhere and deliberately not duplicated here: 21 composite
labels are marked non-queryable in `food_query_terms.EXCLUDE` (project decision
D30) because no single-food query can represent them, which is why the analysis
frame is 175 foods rather than 196. Re-deciding that at the ledger stage would
create a second list of categories that could drift from the first. The ledger
instead attaches a `category` sub-label, so a reader can move between the two
without either being authoritative over the other.

**A section's own title is not a food class.** Every example above names a class
that exists outside this page — 葉物野菜 is a kind of vegetable whether or not a
source lists it. `体を冷やしやすい食べ物一覧` names *this page's list*, and
`体が温まる！おすすめ温活レシピ` names *this page's section*. Neither is a food,
so rule 4 applies and they are `not-food`. Including them would mint a food
literally called "list of foods that cool the body" and give it a direction.

**A prepared dish is an `include` when the source predicates a direction of the
dish itself**, with a `dish` sub-label. kawashimaya writes
「愛知の郷土料理として知られる味噌煮込みうどんは、濃厚な味噌ベースのスープが体を
芯から温めてくれます」 — the dish is the grammatical subject of the warming claim,
and 「体が温まる！おすすめ温活レシピ」 predicates it of the recipes as a group.
§3 forbids inferring a direction the source does not state; it does not license
discarding one the source does state. This is the same move as the category
rule above: record the attribution the source made, and leave whether the item
can carry an Axis B measurement to `food_query_terms.EXCLUDE` (D30).

The boundary is the grammatical subject, not the presence of a dish name. Where
the dish is a vehicle and the warming is predicated of what goes into it —
kawashimaya's 「おすすめの取り入れ方は朝の味噌汁です。温活食材である根菜類やねぎ
を入れて」 — the attribution is to 根菜類/ねぎ, and the dish name is
`no-direction`. §8's kracie ruling (白湯/生姜湯 dropped as prepared beverages
rather than a food's nature) is the same distinction: there the source described
how a drink is prepared, not what the drink does.

### 9.6 Two coders, kappa, adjudication

The ledger is coded by **two independent coders**, as Axis B's records are, using
the same two tiers of one model line (`claude-sonnet-5` and `claude-opus-5`) so
that both axes are judged by the same instrument. Each coder receives this
protocol and its assigned candidates only; the other coder's labels, the
existing `claims.csv` and the reconciliation code are withheld.

This pairing measures within-lineage consistency, not independence, and the
caveat recorded in `screening_protocol.md` §5 applies here unchanged.

One thing does change relative to §8. The kappa reported there is a *direction*
statistic computed on items both coders had already extracted; extraction itself
diverged badly (Jaccard 0.54), and the coverage differences were settled by the
author one at a time. Because both coders now judge the *same* enumerated
candidate set, extraction is no longer a source of divergence, and kappa is
computed over the include/exclude decision across all candidates. Divergences,
and any candidate either coder flags as uncertain, are adjudicated by the author
against the source text and recorded with the ruling, as in
`screening_protocol.md` §5.

### 9.7 Output

`data/claims_ledger.csv` — `source_id, line_no, candidate, paths, coder1,
coder2, adjudicated, final_label, reason, sublabels, food_ja, food_en,
direction, quote`. One row per (source_id, candidate). It is committed, so the
exclusions are auditable in the same way Axis B's are.

`claims.csv` is **generated from this ledger's include rows** rather than
maintained beside it, so there is one record of the coding rather than two that
can disagree. The migration is verified to be lossless against the frozen 649-row
file, and any difference is a Route D judgment that is itself in the ledger.

## 10. Human audit of the ledger (specified 2026-08-13)

Every judgment in §9 was made by a language model, and §8's agreement statistic
pairs two capability tiers of one vendor's line, so it bounds consistency within
that lineage rather than establishing accuracy. That is a general weakness; it
becomes a specific one here because the headline result is a *non-finding*. If
`n_sources` carries measurement error, the error attenuates the coverage
association towards zero, which is the direction the paper already reports. No
statistic computed from the coders can answer that. A human reading the sources
can, and this section fixes what that reading is before it happens.

The audit is specified, sampled and scored by `src/human_audit.py`; the seed is
**20260813** and is published, so the sample cannot have been chosen after seeing
which rows would look good.

### 10.1 Precision — is what we assert there?

A simple random sample of **60 of the 497 Tier-1 claim rows** is read back
against the live source page. Simple rather than stratified: the quantity being
estimated is a proportion over all published claims, and stratifying would make
the sample easier to defend on balance and harder to defend on selection.

Each row takes one verdict, and the five are fixed here rather than invented
while reading:

| verdict | meaning |
|---|---|
| `supported` | the source gives this food this direction |
| `wrong-direction` | the food is attributed, the direction is not the one recorded |
| `not-in-source` | the source does not attribute this food at all |
| `wrong-food` | the span was read as the wrong food |
| `unlocatable` | the page has changed since the freeze and the claim cannot be checked |

`unlocatable` leaves the denominator: a page edited after 2026-08-03 is a fact
about the web, not about the coding. The other four stay in it, including
`wrong-direction`, which is a coding error even though the food is real.

Sheets: `data/human_audit_sample.csv` (the 60 rows, with source URL and the
recorded quote) and `data/human_audit_results.csv` (one verdict and note per row).

### 10.2 Completeness — is what is there asserted?

**Two of the nine Tier-1 sources are read end to end**, listing every food the
source gives a direction *without consulting the ledger*, and the list is then
diffed against the ledger's rows for that source. This is the half that answers
the review's objection: a missed claim lowers that food's `n_sources`, compresses
the predictor's spread, and pulls the estimate towards null, whereas a spurious
claim mostly adds noise.

The two are **the longest source by extracted body text, plus one drawn at
random from the remaining eight** — `basefood` (10,615 characters) and
`macaroni` (4,417). The longest is where an omission is most likely, since it
offers the most text to miss something in; the random draw keeps the pair from
being only a worst case. Two random draws would be cleaner to describe but could
leave the densest source unaudited by luck; the two longest would measure only
the hard tail.

Matching is on `food_ja` as the reader writes it, because that is what the source
prints. A food the reader names that the ledger holds under a different Japanese
surface form counts as **missed** until the author rules otherwise — the
conservative direction for a completeness claim.

Sheet: `data/human_audit_source_reads.csv`.

### 10.3 What the result can and cannot support

Sixty rows bound precision to roughly ±10 percentage points, and two sources of
nine bound completeness for those two only. Neither is a census, and the audit is
reported as what it is: a human check on a machine-built ledger, at a size that
can detect a systematic failure rather than certify the absence of one. Whatever
it finds is reported, including if it finds nothing.

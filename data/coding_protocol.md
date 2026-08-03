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

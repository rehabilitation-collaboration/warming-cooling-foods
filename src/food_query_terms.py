"""Map canonical food keys (food_en) to literature-search query terms.

Axis B counts, per food, how many studies examine it in a body-temperature
context. To do that fairly we must query each food with terms an English (and
Japanese) bibliographic database would actually index it under — otherwise a
zero count could mean "poorly searched" rather than "genuinely unstudied", which
is the confound this study must not commit (see PLAN Phase 2 rationale).

Design:
- Default: a food is searched under its own English name (``food_en``). Most
  common produce (banana, carrot, tomato) needs nothing more.
- ``SYNONYMS``: only foods that an English database would MISS under the plain
  name get extra OR-terms here (mostly Japan-specific items). We add a synonym
  ONLY when we are confident it is the term actually used in the literature; we
  never invent a Latin binomial we are unsure of (that would be a hallucinated
  search term inflating the count).
- ``MESH``: high-confidence scientific names for a MeSH-augmented sensitivity
  analysis, restricted to foods whose binomial is unambiguous.
- ``EXCLUDE``: composite labels that cannot be turned into a single-food query
  (recorded with a reason rather than silently coerced).

No network here — this module only builds query strings, so it is fully
unit-testable. The actual API calls live in ``evidence_mapping.py``.
"""

from __future__ import annotations

import re

# --- Effect vocabulary (Axis B, Layer 2) ---------------------------------
# The "in the claimed context" filter. One term per outcome the screening
# protocol will accept, because the two have to be the same width.
#
# They were not, until 2026-08-08. The set was four terms (thermogenesis, body
# temperature, peripheral circulation, thermoregulation) chosen to keep the
# candidate pool clean, while `screening_protocol.md` §2 condition 3 accepts a
# much wider outcome set — tympanic and axillary temperature, thermic effect of
# food, energy expenditure in a thermogenic context, blood flow and
# microcirculation, cold tolerance, subjective thermal sensation. A query
# narrower than its own inclusion rule cannot measure absence: a study can only
# be excluded on a criterion it was never given the chance to meet. This is not
# hypothetical — Fagundes 2021 (PMID 33487261), a randomised crossover trial of
# ginger measuring TEF, indirect calorimetry and axillary temperature, is
# retrieved by "axillary temperature" and "energy expenditure" and by none of
# the original four (verified 2026-08-08).
#
# The earlier argument for staying at four was that "cold tolerance"-type terms
# inject crop-agronomy noise. That is real and measured — "cold tolerance" alone
# returns 156 tomato hits, essentially all plant chilling physiology — but it is
# an argument about precision, and this design screens every candidate record by
# hand-fixed criteria. Recall is what a query has to buy; precision is what the
# screen is for. Noise costs screening effort, a missed study costs the outcome.
#
# Grouped by the protocol condition each term serves.
EFFECT_TERMS: tuple[str, ...] = (
    # §2.3 — core / peripheral / skin / tympanic / axillary body temperature
    "body temperature",
    "core temperature",
    "skin temperature",
    "tympanic temperature",
    "axillary temperature",
    "rectal temperature",
    "oral temperature",
    # §2.3 — thermogenesis, diet-induced thermogenesis, thermic effect of food
    "thermogenesis",
    "thermic effect",
    "heat production",
    # §2.3 — resting/postprandial energy expenditure in a thermogenic context
    "energy expenditure",
    "metabolic rate",
    # §2.3 — peripheral circulation / blood flow / microcirculation
    "peripheral circulation",
    "blood flow",
    "microcirculation",
    # §2.3 — thermoregulation / cold tolerance / cold-induced responses
    "thermoregulation",
    "cold tolerance",
    "cold exposure",
    # §2.3 — subjective thermal sensation, cold sensitivity (冷え)
    "thermal sensation",
    "thermal comfort",
    "cold sensitivity",
    "cold hypersensitivity",
)

# --- Per-food synonym overrides ------------------------------------------
# food_en -> extra search terms OR-ed with the plain name. Only foods that a
# database would plausibly miss under the plain English word. Terms chosen to be
# the ones literature actually uses; when unsure we leave the food on its plain
# name (a low count then legitimately reflects sparse study, not a bad query).
SYNONYMS: dict[str, list[str]] = {
    "natto": ["fermented soybean", "fermented soybeans"],
    "miso": ["fermented soybean paste"],
    "tofu": ["bean curd"],
    "daikon": ["Japanese radish", "white radish"],
    "hojicha": ["roasted green tea"],
    "green onion": ["scallion", "spring onion", "Welsh onion"],
    "nira": ["garlic chive", "Chinese chive"],
    "sansho": ["Japanese pepper", "sansho pepper"],
    "umeboshi": ["pickled plum", "Japanese apricot"],
    "wakame": ["Undaria pinnatifida", "brown seaweed"],
    "hijiki": ["Sargassum fusiforme"],
    "kombu": ["kelp"],
    "nori": ["laver", "Porphyra"],
    "nukazuke": ["rice bran pickles"],
    "amazake": ["fermented rice drink"],
    "brown sugar": ["unrefined sugar"],
    "white sugar": ["sucrose", "refined sugar"],
    "white rice": ["polished rice"],
    "brown rice": ["whole grain rice"],
    "komatsuna": ["Japanese mustard spinach"],
    "chinese cabbage": ["napa cabbage"],
    "chili pepper": ["hot pepper", "red pepper"],
    "sweet potato": ["Ipomoea batatas"],
    "black tea": ["Camellia sinensis"],
    "green tea": ["Camellia sinensis"],
    # sensitivity-tier Japan-specific items
    "mugicha": ["barley tea"],
    "tsukemono": ["Japanese pickles"],
    "atsuage": ["deep-fried tofu", "fried bean curd"],
    "adzuki bean": ["azuki bean", "Vigna angularis"],
    "black soybean": ["black soybeans", "Glycine max"],
    "edamame": ["green soybean"],
    # Route D additions (RD-5). Every term below was checked against PubMed
    # before being written here, and candidates that returned nothing were
    # dropped rather than kept: `coarse green tea` (0), `Japanese mustard
    # green` (0) and `barley malt syrup` (0) are not terms the literature uses,
    # which is only visible by asking.
    "daikon leaves": ["radish leaves", "radish greens"],  # `daikon leaves` itself: 0
    "fennel": ["Foeniculum vulgare"],
    "mizuna": ["potherb mustard"],
    "papaya": ["Carica papaya"],
    "shichimi pepper": ["shichimi", "shichimi togarashi"],  # `shichimi pepper` itself: 0
    "star anise": ["Illicium verum"],
    "yogurt": ["yoghurt"],
}

# Deliberately left on the plain name, with the reason, because each candidate
# synonym would have measured something other than the food:
#
# - `bancha`: `Japanese green tea` (77) covers sencha and gyokuro too, so it
#   would count tea research generally against 番茶. Unlike hojicha, which maps
#   one-to-one onto `roasted green tea`, 番茶 has no English term of its own.
# - `ganmodoki`: returns 0, and so do `fried tofu fritter` and its neighbours.
#   `fried bean curd` (7) and `deep-fried tofu` (3) are already 厚揚げ's
#   synonyms — adopting them would give two different foods one measurement.
#   The zero stands as the measurement.
# - `mugwort tea`: returns 0. `mugwort` (806) is the plant, not the drink, and
#   the vocabulary's practice is to not fall back to an ingredient — 麦茶 is
#   `barley tea`, never `barley`.
# - `long pepper`: ヒハツ names both Piper longum and Piper retrofractum in
#   Japanese, so a binomial here would be a guess presented as precision.
# - `pheasant`: Japanese きじ is Phasianus versicolor, not the P. colchicus
#   (410) that the English literature mostly means.
# - `malt syrup` / `rice syrup`: `maltose syrup` (46) is a different product,
#   and `brown rice syrup` (7) is a subset of `rice syrup` (39), so neither
#   adds recall for the food actually claimed.

# --- MeSH / scientific-name augmentation (sensitivity only) ---------------
# High-confidence binomials only. Used to show the main finding is robust to a
# MeSH-augmented search for foods with an unambiguous scientific name.
MESH: dict[str, str] = {
    "ginger": "Zingiber officinale",
    "garlic": "Allium sativum",
    "onion": "Allium cepa",
    "cinnamon": "Cinnamomum",
    "chili pepper": "Capsicum",
    "buckwheat": "Fagopyrum esculentum",
}

# --- Composite labels that cannot be a single-food query ------------------
# Recorded with reason instead of silently coercing into a misleading query.
#
# Two things disqualify a label: it names a *class* whose members are already
# separate food keys here (querying both would count one study under two foods,
# and attach it to beliefs Axis A recorded separately), or it names a
# compositional/processing category rather than a food. The count of sub-keys
# below is how many members of that class exist in claims.csv.
EXCLUDE: dict[str, str] = {
    "red meat and fish": (
        "composite source label ('赤身の肉・魚'); not a single food — "
        "cannot map to one search term without distorting the count"
    ),
    "leafy greens": (
        "category label, not a specific food; would over-count under a broad query"
    ),
    "nuts": "category label (mixed tree nuts); no single unambiguous query term",
    "mixed nuts": (
        "the same label as `nuts` with the mixing stated ('ミックスナッツ'); an "
        "unspecified blend has no single query term either. Named blends are a "
        "different case and stay queryable — `curry powder` is a food key, and "
        "so is 七味 — because the blend itself has a name a query can use"
    ),
    "spices": "category label (mixed spices); no single unambiguous query term",
    # Surfaced when the Axis B universe was widened to n_sources = 1 (D28):
    # single-source labels were never queried before, so these were never
    # screened against the rule above.
    "seafood": "umbrella label ('魚介'); 15 of its members are separate food keys",
    "shellfish": "umbrella label ('貝類'); 5 of its members are separate food keys",
    "seaweed": "umbrella label ('海藻'); 7 of its members are separate food keys",
    "whole grains": "umbrella label ('全粒穀物'); 7 of its members are separate food keys",
    "yellow-green vegetables": (
        "umbrella label ('緑黄色野菜'); 5 of its members are separate food keys"
    ),
    "vegetable oil": "umbrella label ('植物油'); 3 of its members are separate food keys",
    "citrus": "umbrella label ('柑橘類'); orange and grapefruit are separate food keys",
    "chinese tea": "umbrella label ('中国茶'); oolong and pu-erh tea are separate food keys",
    "mushroom": "category label ('きのこ類', many species); no single unambiguous query term",
    "mixed grains": "category label ('雑穀', unspecified minor grains)",
    "mountain vegetables": "category label ('山菜', unspecified wild plants)",
    "small fish": "category label ('小魚', unspecified whole small fish)",
    "raw vegetables": "preparation-state category ('生野菜'), not a food",
    "animal fat": "compositional category ('動物性脂肪'), not a food",
    "fatty meat": "compositional category ('脂身'), not a food",
    "chemical seasonings": "category label ('化学調味料'), not a food",
    "food additives": "category label ('食品添加物'), not a food",
}


def is_queryable(food_en: str) -> bool:
    """False for composite/category labels that cannot be a single-food query."""
    return food_en not in EXCLUDE


def food_terms(food_en: str, *, with_mesh: bool = False) -> list[str]:
    """Return the OR-list of search terms for one food.

    Always includes the plain English name; adds curated synonyms, and (when
    ``with_mesh``) the scientific name for the MeSH sensitivity analysis. Raises
    for excluded composite labels so callers handle them explicitly.
    """
    if food_en in EXCLUDE:
        raise ValueError(f"{food_en!r} is excluded: {EXCLUDE[food_en]}")
    # A parenthetical is a coder's gloss, not part of the name: Route D's
    # ledger carries `ganmodoki (fried tofu fritter)`, and searching that
    # literally returns nothing for a food that may simply be unstudied —
    # exactly the confound this module exists to avoid. The key keeps the gloss
    # (it is what the ledger recorded); only the query drops it.
    terms = [re.sub(r"\s*\([^)]*\)", "", food_en).strip() or food_en]
    terms.extend(SYNONYMS.get(food_en, []))
    if with_mesh and food_en in MESH:
        terms.append(MESH[food_en])
    # De-duplicate while preserving order (a synonym could equal the name).
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _or_tiab(terms: list[str]) -> str:
    """Join terms as a PubMed [tiab] OR-group, quoting multiword phrases."""
    parts = [f'"{t}"[tiab]' if " " in t else f"{t}[tiab]" for t in terms]
    inner = " OR ".join(parts)
    return f"({inner})" if len(parts) > 1 else inner


def pubmed_query(food_en: str, layer: str = "L2", *, with_mesh: bool = False) -> str:
    """Build the PubMed query string for a food at the given layer.

    - L1: food terms only (total research volume on the food).
    - L2: food AND effect terms (studies in the claimed thermal context) — the
      Axis B main metric (scatter-plot y-axis).
    - L3: L2 AND an RCT publication-type filter (design-quality stratum).
    """
    food_group = _or_tiab(food_terms(food_en, with_mesh=with_mesh))
    if layer == "L1":
        return food_group
    effect_group = _or_tiab(list(EFFECT_TERMS))
    l2 = f"{food_group} AND {effect_group}"
    if layer == "L2":
        return l2
    if layer == "L3":
        return f'{l2} AND "randomized controlled trial"[pt]'
    raise ValueError(f"unknown layer {layer!r} (expected L1/L2/L3)")

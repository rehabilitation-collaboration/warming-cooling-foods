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

# --- Effect vocabulary (Axis B, Layer 2) ---------------------------------
# The "in the claimed context" filter, frozen after a one-off PubMed hit-count
# sanity check (PLAN Phase 2). These four PLAN-fixed terms are the whole set.
#
# We tested adding "cold sensitivity" / "cold intolerance" to capture the 冷え性
# framing of Japanese 温活 belief, but rejected them: on PubMed those terms pull
# in plant low-temperature-tolerance agronomy (e.g. tomato +10 hits, all "cold
# tolerance / chilling tolerance" crop-physiology papers — verified 2026-08-04),
# which is noise for a human-thermal-effect count. Meanwhile the human 冷え性
# terms they were meant to rescue ("cold hypersensitivity" / "cold extremities")
# returned 0 hits for ginger outside the four core terms — i.e. nothing real was
# being missed. Net: adding them only injects crop-agronomy noise. Kept at four.
EFFECT_TERMS: tuple[str, ...] = (
    "thermogenesis",
    "body temperature",
    "peripheral circulation",
    "thermoregulation",
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
}

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
EXCLUDE: dict[str, str] = {
    "red meat and fish": (
        "composite source label ('赤身の肉・魚'); not a single food — "
        "cannot map to one search term without distorting the count"
    ),
    "leafy greens": (
        "category label, not a specific food; would over-count under a broad query"
    ),
    "nuts": "category label (mixed tree nuts); no single unambiguous query term",
    "spices": "category label (mixed spices); no single unambiguous query term",
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
    terms = [food_en]
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

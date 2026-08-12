"""Constants and controlled vocabularies for the warming/cooling foods study.

Single source of truth for enumerations, thresholds, and file paths used across
the pipeline. No logic here — see claim_mapping.py for aggregation.
"""

from pathlib import Path

# --- Paths ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOURCES_CSV = DATA_DIR / "sources.csv"
CLAIMS_CSV = DATA_DIR / "claims.csv"
# The hand coding as it stood before Route D, frozen. `claims.csv` is now
# generated from `claims_ledger.csv` (§9.7), which makes it useless as the
# reference for two checks that have to stay independent of the ledger:
# `verify_candidate_recall` measures the extractor against a set it did not
# produce, and the Route D goal declaration counts "claiming coverage from a
# recall figure measured against your own output" as a failure of the route.
CLAIMS_FROZEN_CSV = DATA_DIR / "claims_frozen.csv"
WU_XING_CSV = DATA_DIR / "wu_xing_reference.csv"
SOURCES_RAW_DIR = DATA_DIR / "sources_raw"
# Axis B evidence mapping (evidence_mapping.py).
QUERY_LOG_DIR = DATA_DIR / "query_log"          # raw API JSON (audit trail; git-ignored)
PUBMED_COUNTS_CSV = DATA_DIR / "pubmed_counts.csv"  # per-food study counts (tracked data)
# Phase 3 figures (analysis.py).
PLOTS_DIR = PROJECT_ROOT / "plots"              # attention-gap scatter plots (tracked)

# --- Belief direction (Axis A coding) ------------------------------------
# Each source assigns a food to one of these directions. Sources using the
# five-nature (五性) or yin-yang vocabulary are folded into warm/cool per the
# mapping in FIVE_NATURE_TO_DIRECTION below; "neutral" (平) is recorded but
# excluded from the warm-vs-cool majority vote.
WARM = "warm"
COOL = "cool"
NEUTRAL = "neutral"
DIRECTIONS = (WARM, COOL, NEUTRAL)

# --- Five natures 五性 (normative classification axis) --------------------
# Reference: 薬膳食典食物性味表 第2版 (日本中医食養学会) / 西村ら 2012
# (日本栄養・食糧学会誌 65(4):155-160, J-STAGE, "SEIMIHYOU").
HOT = "hot"        # 熱
WARM_N = "warm"    # 温
NEUTRAL_N = "neutral"  # 平
COOL_N = "cool"    # 涼
COLD = "cold"      # 寒
FIVE_NATURES = (HOT, WARM_N, NEUTRAL_N, COOL_N, COLD)

# Collapse the five natures onto the binary warm/cool axis used by Axis A,
# so normative classification and lay attribution can be compared directly.
FIVE_NATURE_TO_DIRECTION = {
    HOT: WARM,
    WARM_N: WARM,
    NEUTRAL_N: NEUTRAL,
    COOL_N: COOL,
    COLD: COOL,
}

# Japanese labels seen in sources, mapped to the canonical five natures.
JA_NATURE_LABELS = {
    "熱": HOT,
    "温": WARM_N,
    "平": NEUTRAL_N,
    "涼": COOL_N,
    "寒": COLD,
    # Macrobiotic yin-yang vocabulary → warm/cool (recorded as lay direction,
    # not as a five-nature value).
    "陽性": WARM,
    "陽": WARM,
    "陰性": COOL,
    "陰": COOL,
}

# --- Source frame tiers --------------------------------------------------
TIER_ORG = 1        # 法人・団体運営 (primary frame)
TIER_INDIVIDUAL = 2  # 個人専門家ブログ (sensitivity analysis only)
TIERS = (TIER_ORG, TIER_INDIVIDUAL)

# --- Axis A metric thresholds --------------------------------------------
# A food is treated as having a defined lay direction when the warm-vs-cool
# split is not a tie. Consensus ratio = max(W, C) / (W + C).
COFFEE_REPRESENTATIVE_MIN_SOURCES = 3  # PLAN branch: ≥3 Tier-1 sources say "cool"

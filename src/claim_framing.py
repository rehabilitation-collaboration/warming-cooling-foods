"""Split Axis A by how a source frames the attribution (review round 3, item 3).

The objection this answers: Axis A maps three different vocabularies onto one
warm/cool variable — a stated bodily effect ("体を温める"), a five-natures or
yin-yang classification ("陽性"), and a bare warm/cool food-category label
("＜温食材＞") — while Axis B measures a physiological outcome after ingestion.
That "陰性食品" and "lowers body temperature after ingestion" name the same
construct is an identification this study never tested, so any claim that the
attribution *itself* has been examined rests on it holding.

The split has to be per quote, not per source. `oitr` writes
"体を温める食材(陽性)＞根菜・冬野菜: にんじん" — both vocabularies in one line —
so no source-level partition separates them.

Classes, assigned from the quote text (PHYSIO and TCM can co-occur):

    PHYSIO   states a bodily warming/cooling effect
    TCM      five-natures (温性/熱性/涼性/寒性/平性) or yin-yang (陰性/陽性)
    LABEL    a warm/cool food-category label carrying neither of the above
    CONTEXT  no thermal vocabulary in the quote at all; the direction was read
             off the surrounding text by the coders

The vocabularies below were read off all 394 Tier-1 quotes rather than guessed.
CONTEXT is a real class, not an error branch — two quotes genuinely carry no
thermal wording and were coded from the surrounding text — so an unmatched quote
cannot be made to fail loudly. It lands in CONTEXT instead, which is why
`framing_counts` reports that column: a CONTEXT count that grows is the signal
that the vocabulary list has fallen behind the data.
"""

from __future__ import annotations

import re

import pandas as pd

from .claim_mapping import aggregate_axis_a
from .definitions import TIER_ORG

# A stated bodily thermal effect. Mechanism words (発汗 / 血行 / 血流 / 血管を拡張)
# are deliberately absent: every quote carrying one already carries a term below,
# so adding them would widen the pattern without moving a single row.
PHYSIO_PATTERN = re.compile(
    r"体を温|体が温|体の熱|温める|温まる|温まり|温めて|温めも"
    r"|冷やす|冷やし|冷える|冷えを|クールダウン|温活"
)

# Five-natures and yin-yang. These are classificatory: they place the food in a
# theoretical category rather than assert a measured effect on the body.
TCM_PATTERN = re.compile(r"五性|温性|熱性|涼性|寒性|平性|陰陽|陰性|陽性")

# A warm/cool food-category label. Plain Japanese rather than five-natures
# theory, but still a category membership claim rather than a stated effect.
LABEL_PATTERN = re.compile(r"温食材|冷食材")

PHYSIO, TCM, LABEL, CONTEXT = "physio", "tcm", "label", "context"

# Framings the sensitivity analysis refits the primary model on. `nontcm` is the
# reviewer's contrast made concrete: everything that is *not* five-natures theory.
FRAMINGS = {
    PHYSIO: (PHYSIO,),
    "nontcm": (PHYSIO, LABEL),
    TCM: (TCM,),
}

# Fixed before any of these models was fitted. Two predictors at the usual ten
# events per predictor; below that the odds ratio is not worth reporting, so the
# frame gets described and left unfitted rather than fitted and hedged.
MIN_EVENTS_TO_FIT = 20


def classify_claims(claims: pd.DataFrame) -> pd.DataFrame:
    """Tag every claim row with its framing flags.

    Adds boolean ``is_physio`` / ``is_tcm`` / ``is_label`` / ``is_context``.
    ``is_physio`` and ``is_tcm`` can both be true; ``is_label`` is only set when
    neither is, and ``is_context`` only when none of the three is, so the four
    flags cover every row and the last three are mutually exclusive.
    """
    if "quote" not in claims.columns:
        raise ValueError("claims frame has no 'quote' column")

    out = claims.copy()
    quote = out["quote"].fillna("")
    out["is_physio"] = quote.str.contains(PHYSIO_PATTERN)
    out["is_tcm"] = quote.str.contains(TCM_PATTERN)
    out["is_label"] = quote.str.contains(LABEL_PATTERN) & ~out["is_physio"] & ~out["is_tcm"]
    out["is_context"] = ~(out["is_physio"] | out["is_tcm"] | out["is_label"])
    return out


def framing_counts(claims: pd.DataFrame) -> pd.DataFrame:
    """Per-source quote counts by framing — the table that shows why the split
    has to be per quote (a source can sit in more than one column)."""
    tagged = classify_claims(claims)
    rows = []
    for source_id, grp in tagged.groupby("source_id"):
        rows.append(
            {
                "source_id": source_id,
                "n_quotes": len(grp),
                "physio": int(grp["is_physio"].sum()),
                "tcm": int(grp["is_tcm"].sum()),
                "both": int((grp["is_physio"] & grp["is_tcm"]).sum()),
                "label": int(grp["is_label"].sum()),
                "context": int(grp["is_context"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("source_id").reset_index(drop=True)


def select_framing(claims: pd.DataFrame, framing: str) -> pd.DataFrame:
    """Keep the claim rows belonging to ``framing`` (a key of ``FRAMINGS``)."""
    if framing not in FRAMINGS:
        raise ValueError(f"unknown framing {framing!r}; expected one of {sorted(FRAMINGS)}")

    tagged = classify_claims(claims)
    keep = pd.Series(False, index=tagged.index)
    for cls in FRAMINGS[framing]:
        keep |= tagged[f"is_{cls}"]
    return tagged[keep].drop(
        columns=["is_physio", "is_tcm", "is_label", "is_context"]
    ).reset_index(drop=True)


def framed_model_frame(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    counts: pd.DataFrame,
    framing: str,
    *,
    max_tier: int = TIER_ORG,
) -> pd.DataFrame:
    """Rebuild the analysis frame with breadth counted only within ``framing``.

    ``counts`` is the per-food frame from ``analysis._read_counts``. A food that
    no source describes in this framing leaves the frame — that is the point of
    the split, not a pipeline fault, so unlike `prepare_scatter_data` it is not
    an error here. The dropped keys land on ``frame.attrs["outside_framing"]``
    so the caller reports the narrowing instead of absorbing it.
    """
    subset = select_framing(claims, framing)
    axis_a = aggregate_axis_a(subset, sources, max_tier=max_tier)

    if axis_a.empty:
        raise ValueError(f"framing {framing!r} left no claims under tier {max_tier}")

    slim = axis_a[["food_key", "direction", "n_sources"]]
    merged = counts.drop(columns=["scope"], errors="ignore").merge(
        slim, on="food_key", how="left"
    )
    outside = sorted(merged.loc[merged["direction"].isna(), "food_key"])
    merged = merged[merged["direction"].notna()].copy()
    merged["n_sources"] = merged["n_sources"].astype(int)
    merged = merged.reset_index(drop=True)
    merged.attrs["outside_framing"] = outside
    merged.attrs["framing"] = framing
    return merged

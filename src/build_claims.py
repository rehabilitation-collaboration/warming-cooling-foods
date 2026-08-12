"""Generate data/claims.csv from the adjudicated candidate ledger (RD-4, D46).

Until Route D this module carried the coding itself, as 781 lines of literal
tuples, and ``claims.csv`` was its output. That arrangement is what the review's
fourth point was about: the file recorded what was coded and nothing about what
was read and rejected, so a reader could not tell a miss from an exclusion the
protocol called for. ``claims_ledger.csv`` now carries both sides of every
judgment, and ``claims.csv`` is a projection of its include rows.

The hand coding is not deleted — it is frozen at ``data/claims_frozen.csv``,
which stays the reference for ``verify_candidate_recall`` and
``verify_independent_read``. Those two measure the extractor against a set it did
not produce; pointing them at a generated file would make them measure the
ledger against itself.

**The projection is not lossless, and it is not supposed to be.** §9.7's wording
predates the rollout; measured, the ledger loses nothing from the frozen file and
adds 220 (source, food) attributions, because the protocol reaches attributions
the original pass did not. ``src/rd4_delta.py`` classifies the addition.

Two things happen on the way across:

- **Collapse.** The ledger's key is (source_id, candidate) — one row per span —
  while §2's unit of coding is (food, source). Spans naming the same food in the
  same source with the same direction become one row. §9.4's note on ``duplicate``
  says this explicitly: collapsing "is a property of claims.csv … and it happens
  mechanically when the ledger is projected there".
- **``condition`` is carried over, not re-derived.** The ledger has no condition
  column (D69 measured that no (food, source) pair splits direction on one, so
  adding one would have re-run 110 codings to record an annotation). Most of the
  47 frozen annotations are seasonal and sit in a section heading two to five
  lines above the food, which no candidate span reaches. They are joined back
  from the frozen file on (source_id, food_ja), then on food_en.

Run: ``python3 -m src.build_claims``
"""

from __future__ import annotations

import pandas as pd

from .definitions import CLAIMS_CSV, CLAIMS_FROZEN_CSV, DATA_DIR
from .rd4_delta import _norm_en, kata

LEDGER_CSV = DATA_DIR / "claims_ledger.csv"
COLUMNS = ["food_en", "food_ja", "source_id", "direction", "quote", "condition",
           "sublabel"]


def load_includes(path=LEDGER_CSV) -> pd.DataFrame:
    led = pd.read_csv(path, dtype=str).fillna("")
    inc = led[led["final_label"] == "include"].copy()
    missing = inc[(inc.food_ja == "") | (inc.food_en == "") | (inc.direction == "")]
    if not missing.empty:
        raise ValueError(
            f"{len(missing)} include rows in {path.name} lack food_ja/food_en/"
            f"direction, which §9.3 requires on every include: "
            f"{list(zip(missing.source_id, missing.candidate))[:5]}"
        )
    return inc


def canonicalise_food_en(inc: pd.DataFrame, frozen_path=CLAIMS_FROZEN_CSV) -> pd.DataFrame:
    """Adopt the frozen file's `food_en` wherever the Japanese label matches.

    `food_en` is the aggregation key the whole Axis B side is built on —
    `food_query_terms` maps it to a PubMed query — and the frozen coding is where
    that vocabulary was fixed. The two ledger coders named foods independently
    and produced 94 rows naming a known food under a new English key (`burdock`
    -> `burdock root`, `nira` -> `garlic chives`, `daikon` -> `daikon radish`).
    Left alone those foods would not join to their own Axis B measurements and
    would read as new foods needing queries built.

    Matching is on the Japanese label, kana-folded, first within the source and
    then across the corpus, because the frozen vocabulary is deliberately
    consistent across sources. A label the frozen file never carried keeps the
    coder's `food_en`: this canonicalises, it does not invent.
    """
    frozen = pd.read_csv(frozen_path, dtype=str).fillna("")
    within = {(r.source_id, kata(r.food_ja)): r.food_en for r in frozen.itertuples()}
    across: dict[str, str] = {}
    for r in frozen.itertuples():
        across.setdefault(kata(r.food_ja), r.food_en)
    inc = inc.copy()
    inc["food_en"] = [
        within.get((r.source_id, kata(r.food_ja)))
        or across.get(kata(r.food_ja), r.food_en)
        for r in inc.itertuples()
    ]
    return inc


# A preparation of a measured food is that food, not a new one. This is the
# frozen coding's own practice, applied consistently: 加熱した生姜 is `ginger`
# with condition=heated, 塩サケ is `salmon`, アジの開き is `horse mackerel`,
# ポテトチップス is `potato`, 黒焼き梅干し is `umeboshi`.
#
# A preparation earns its own food_en only where the same source gives it the
# opposite direction from the parent, since folding it would then make the file
# contradict itself: attaka_navi calls 干し柿 warm and 柿 cool, prezo calls
# 切り干し大根 warm and 大根 cool, gveggie calls 高野豆腐 warm and 豆腐 cool — which
# is why those three are separate keys in the frozen vocabulary. Each fold below
# was checked against that test and carries the parent's direction in the source
# it appears in.
#
# Without this the foods leave the analysis frame silently: the frame is built
# from pubmed_counts.csv, so `boiled egg` simply never appears, which the Route D
# goal declaration counts as a failure (#5).
PREP_PARENT: dict[str, str] = {
    "boiled egg": "egg",                    # oitr/onkatsu_note warm; egg warm in oitr
    "canned mackerel": "mackerel",          # oitr warm; mackerel warm in oitr
    "coarse sea salt": "salt",              # a grind of salt, as 塩 is the only salt key
    "dried ginger": "ginger",
    "ginger (heated/dried)": "ginger",
    "ginger (raw)": "ginger",
    "ginger powder (dried ginger)": "ginger",
    "ginger powder (dried)": "ginger",
    "raw ginger": "ginger",
}


def fold_preparations(inc: pd.DataFrame) -> pd.DataFrame:
    """Rewrite a preparation's ``food_en`` to the food it is a preparation of.

    Runs after :func:`canonicalise_food_en` (which settles spelling) and before
    :func:`collapse` (which is what actually merges the rows, on §2's unit). The
    Japanese label is left alone, so the preparation stays visible in `food_ja`
    exactly as 塩サケ does in the frozen file.
    """
    inc = inc.copy()
    inc["food_en"] = inc["food_en"].map(lambda f: PREP_PARENT.get(f, f))
    return inc


def collapse(inc: pd.DataFrame) -> pd.DataFrame:
    """Ledger rows -> one row per (source, food, direction).

    The representative span is the one with the shortest ``food_ja``, which is
    §9.4 rule 2's own tie-break ("the shorter one is the row") applied at the
    point where the granularities the enumeration emits on purpose have to become
    a single claim.
    """
    inc = inc.copy()
    inc["_k"] = inc["food_en"].map(_norm_en)
    inc["_len"] = inc["food_ja"].str.len()
    # §9.5's sub-label, carried through so Axis B can tell a food from a class.
    # D30 holds category and dish labels out of the analysis frame because no
    # single-food query represents them, and D48 decided not to restate that
    # list on the ledger side — which left the fact recorded in the ledger and
    # invisible to the code that builds the queries. Measured: 89 category and
    # dish labels were queried against PubMed before this column existed.
    # Kept verbatim, because the colon carries the meaning and stripping it
    # inverts it: bare `category` marks a label that *is* a class (根菜類), while
    # `category:寒冷地の果物・ナッツ` marks an ordinary food recorded as a *member*
    # of one — りんご under oitr's cold-region heading. Splitting on ":" makes
    # apple, onion, tofu and 17 other foods look non-queryable.
    inc["sublabel"] = inc["sublabels"].astype(str).str.split(";").str[0].str.strip()
    inc = inc.sort_values(["source_id", "_k", "direction", "_len", "food_ja"])
    out = inc.drop_duplicates(["source_id", "_k", "direction"], keep="first")
    return out[["food_en", "food_ja", "source_id", "direction", "quote",
                "sublabel"]].copy()


def attach_condition(claims: pd.DataFrame, frozen_path=CLAIMS_FROZEN_CSV) -> pd.DataFrame:
    """Restore the frozen ``condition`` annotations (D69).

    Joined rather than re-derived, and on the record: a condition the frozen file
    does not carry is not invented here, so a row with no counterpart gets none.
    """
    frozen = pd.read_csv(frozen_path, dtype=str).fillna("")
    frozen = frozen[frozen["condition"] != ""]
    by_ja = {(r.source_id, r.food_ja): r.condition for r in frozen.itertuples()}
    by_en: dict[tuple[str, str], str] = {}
    for r in frozen.itertuples():
        by_en.setdefault((r.source_id, _norm_en(r.food_en)), r.condition)
    claims = claims.copy()
    claims["condition"] = [
        by_ja.get((r.source_id, r.food_ja))
        or by_en.get((r.source_id, _norm_en(r.food_en)), "")
        for r in claims.itertuples()
    ]
    return claims


def build() -> pd.DataFrame:
    df = attach_condition(collapse(fold_preparations(canonicalise_food_en(load_includes()))))
    return df[COLUMNS].sort_values(
        ["source_id", "food_en", "direction"]).reset_index(drop=True)


def main() -> None:
    df = build()
    df.to_csv(CLAIMS_CSV, index=False)
    frozen = pd.read_csv(CLAIMS_FROZEN_CSV, dtype=str).fillna("")
    print(f"wrote {len(df)} claims to {CLAIMS_CSV}")
    print(f"  frozen hand coding: {len(frozen)} rows")
    # More rows can carry a condition than the frozen file has rows with one:
    # the join is on (source, food), and the ledger can hold two rows for a food
    # the frozen file held once. Printed as a count, not as "N of M", because the
    # "of" read as a ceiling and 48 of 47 looked like a bug.
    print(f"  condition annotations attached: {int((df['condition'] != '').sum())}"
          f"  (frozen rows carrying one: {int((frozen['condition'] != '').sum())})")
    print(f"  distinct (source, food_en): "
          f"{df.groupby(['source_id', df.food_en.map(_norm_en)]).ngroups}")


if __name__ == "__main__":
    main()

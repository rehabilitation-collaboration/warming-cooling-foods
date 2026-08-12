"""RD-4 step (a): explain the delta between the frozen claims.csv and the ledger.

第28 forecast that the ledger would carry *fewer* attributions than claims.csv
and that n_sources would fall. Measured after the RD-3 adjudication, the delta
runs the other way and only the other way: nothing is lost and 220 (source, food)
attributions are added. So this is not a loss accounting — it is a classification
of what Route D added and what that costs downstream.

The question that decides RD-5's size is not "how many rows are new" but "how
many *queryable single foods* are new", because project decision D30 already
holds composite and umbrella labels out of the analysis frame: no single-food
query can represent 葉物野菜, so they are recorded and then excluded from the
175-food frame. A `category` or `dish` sub-label is the ledger's own marker for
exactly that class.

Run: ``python3 -m src.rd4_delta``
"""

from __future__ import annotations

import pandas as pd

from .definitions import DATA_DIR
from .food_query_terms import EXCLUDE

LEDGER = DATA_DIR / "claims_ledger.csv"
CLAIMS = DATA_DIR / "claims.csv"


def kata(s: str) -> str:
    """Hiragana -> katakana so じゃがいも and ジャガイモ compare equal."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s)).strip()


def _norm_en(s: str) -> str:
    """Loose English key: lowercase, singularised, parentheticals dropped.

    The two coders named foods independently, so one referent picked up several
    English names (`cold-region fruit` / `cold-region fruits` /
    `fruit grown in cold regions`). Counting distinct `food_en` without folding
    those overstates how many new foods there are, and RD-5's cost is quoted per
    food.
    """
    s = str(s).lower().split("(")[0].strip()
    for a, b in ((" and ", " "), ("-", " ")):
        s = s.replace(a, b)
    words = [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in s.split()]
    return " ".join(sorted(words))


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    led = pd.read_csv(LEDGER, dtype=str).fillna("")
    claims = pd.read_csv(CLAIMS, dtype=str).fillna("")
    return led[led["final_label"] == "include"], claims


def delta(inc: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    """New (source, food) rows, tagged with why they are or are not in the frame."""
    known = {(r.source_id, kata(r.food_ja)) for r in claims.itertuples()}
    rows = inc.drop_duplicates(["source_id", "food_ja"])
    new = rows[[(r.source_id, kata(r.food_ja)) not in known for r in rows.itertuples()]].copy()

    old_en = {_norm_en(f) for f in claims["food_en"]}
    head = new["sublabels"].str.split(";").str[0].str.split(":").str[0]

    def classify(r, sub: str) -> str:
        if sub in ("category", "dish"):
            # D30's ground: no single-food query represents these, so they are
            # recorded in the ledger and held out of the 175-food frame.
            return f"non-queryable ({sub})"
        if r.food_en in EXCLUDE:
            return "non-queryable (D30 EXCLUDE)"
        if _norm_en(r.food_en) in old_en:
            return "既存食品の別名 (RB-4)"
        return "新規の queryable 食品 → RD-5"

    new["sublabel_head"] = head
    new["class"] = [classify(r, s) for r, s in zip(new.itertuples(), head)]
    return new


def main() -> None:
    inc, claims = load()
    new = delta(inc, claims)

    n_led = inc.drop_duplicates(["source_id", "food_ja"]).shape[0]
    n_cl = claims.drop_duplicates(["source_id", "food_ja"]).shape[0]
    print(f"台帳 {n_led} (source, food) / claims {n_cl} / 新規 {len(new)}\n")

    print("新規行の内訳:")
    for cls, g in new.groupby("class"):
        print(f"  {cls:34s} 行 {len(g):4d}   distinct food {g.food_en.nunique():3d}")

    frame = new[new["class"].str.startswith("新規の queryable")]
    foods = sorted({_norm_en(f): f for f in frame["food_en"]}.values())
    print(f"\n★ RD-5 で Axis B (L1/L2) 取得が要る新規食品: {len(foods)}")
    for f in foods:
        ja = frame[frame.food_en == f].food_ja.iloc[0]
        srcs = sorted(frame[frame.food_en == f].source_id.unique())
        print(f"    {f:38s} {ja:<16s} n_sources={len(srcs)}")

    alias = new[new["class"] == "既存食品の別名 (RB-4)"]
    if len(alias):
        print(f"\n★ 既存食品の別名として畳むべき行: {len(alias)}"
              f"（RD-5 の前に正規化が要る・RB-4 と同じ作業）")
        for f in sorted(alias.food_en.unique())[:20]:
            print(f"    {f}")

    print(f"\n★ n_sources が増えるだけの既存食品: "
          f"{int((~new.food_en.isin(frame.food_en) & (new.sublabel_head == '')).sum())} 行")


if __name__ == "__main__":
    main()

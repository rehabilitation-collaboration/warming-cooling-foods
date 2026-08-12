"""RD-4 step (a): explain the delta between the frozen claims.csv and the ledger.

第28 forecast that the ledger would carry *fewer* attributions than claims.csv
and that n_sources would fall. Measured after the RD-3 adjudication, the delta
runs the other way and only the other way: nothing is lost and attributions are
added (the count is printed rather than quoted here, because it moved twice as
late rulings landed and a figure in prose does not). So this is not a loss accounting — it is a classification
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

from .definitions import CLAIMS_FROZEN_CSV, DATA_DIR
from .food_query_terms import EXCLUDE

LEDGER = DATA_DIR / "claims_ledger.csv"
# The frozen hand coding, never the generated claims.csv: `build_claims` now
# projects the ledger into claims.csv, so comparing the ledger against it would
# compare the ledger to itself and report a delta of almost nothing.
CLAIMS = CLAIMS_FROZEN_CSV


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


def coverage(inc: pd.DataFrame | None = None) -> pd.DataFrame:
    """Axis A foods with no Axis B measurement, split by whether that is expected.

    The Route D goal declaration counts "adding include foods and quietly
    dropping the ones whose Axis B is missing" as a failure of the route, and the
    drop really is quiet: the analysis frame is built from `pubmed_counts.csv`,
    so a food the ledger added simply never appears and nothing warns.

    A `category` or `dish` sub-label is the ledger's own record that no
    single-food query represents the label, which is D30's ground for holding the
    21 composite labels out of the 175-food frame. Those are expected to be
    missing. Anything else is work RD-5 owes.
    """
    from .build_claims import canonicalise_food_en, load_includes

    if inc is None:
        inc = load_includes()
    # On the canonical vocabulary, not the coders' — `burdock root` is `burdock`
    # once claims.csv is built, and counting it as unmeasured would invent work.
    inc = canonicalise_food_en(inc)
    counts = pd.read_csv(DATA_DIR / "pubmed_counts.csv", dtype=str)
    measured = set(counts["food_key"])
    sub = inc.groupby("food_en")["sublabels"].apply(
        lambda s: s.str.split(";").str[0].str.split(":").str[0].mode().iat[0]
        if len(s.mode()) else "")

    # A measured food under a preparation modifier is not a new food. The frozen
    # coding settled this shape: kracie's 加熱した生姜 is `ginger` with
    # condition=heated, not a food called "heated ginger". Six ginger variants
    # reach here (raw / dried / powder / heated-dried …); building a PubMed query
    # for each would be six queries for one food.
    measured_words = {w for f in measured for w in _norm_en(f).split()}

    rows = []
    for food in sorted(inc["food_en"].unique()):
        if food in measured or food in EXCLUDE:
            continue
        head = sub.get(food, "")
        words = set(_norm_en(food).split())
        prep = bool(words & measured_words) and food not in measured
        rows.append({
            "food_en": food,
            "sublabel": head,
            "expected": head in ("category", "dish"),
            "prep_variant_of_measured": prep,
        })
    return pd.DataFrame(rows)


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

    cov = coverage()
    owed = cov[~cov["expected"]]
    print(f"\n★ Axis B 未取得の Axis A 食品: {len(cov)}")
    print(f"    うち category/dish（D30 の理由で測れんのが正常）: {int(cov['expected'].sum())}")
    prep = owed[owed["prep_variant_of_measured"]]
    fresh = owed[~owed["prep_variant_of_measured"]]
    print(f"    既存食品の調理形態・別形（RD-5 は condition として扱うか判断）: {len(prep)}")
    for f in prep["food_en"]:
        print(f"       ~ {f}")
    print(f"    ★★ RD-5 が新規にクエリを建てる食品: {len(fresh)}")
    for f in fresh["food_en"]:
        print(f"       {f}")

    print(f"\n★ n_sources が増えるだけの既存食品: "
          f"{int((~new.food_en.isin(frame.food_en) & (new.sublabel_head == '')).sum())} 行")

    reason_sweep()


def reason_sweep() -> pd.DataFrame:
    """RD-4 (e)'s target rows: agreed exclusions whose reason codes differ.

    Printed from here because the figure had no command behind it and a
    cold-start reader recomputed it two rows off — the ambiguity was whether
    `only_c1`/`only_c2` rows and the `uncertain` flag count. They do not: the
    sweep is over rows both coders excluded, which is what a reason-only
    ruling can act on without touching include/exclude.
    """
    from .build_ledger import load_coder
    from .ledger import _needs_ruling, reconcile

    c1, c2 = load_coder("c1"), load_coder("c2")
    recon = reconcile(c1.to_dict("records"), c2.to_dict("records"))
    settled = recon[~recon.apply(_needs_ruling, axis=1)]
    exc = settled[settled["label_c1"] == "exclude"]
    mism = exc[exc["reason_c1"] != exc["reason_c2"]].copy()
    mism["pair"] = [" <-> ".join(sorted([a, b]))
                    for a, b in zip(mism.reason_c1, mism.reason_c2)]
    print(f"\n★ RD-4(e) の対象: 一致 exclude {len(exc):,} 行のうち reason 不一致 "
          f"{len(mism):,} 行 ({len(mism) / len(exc):.1%})")
    for pair, n in mism["pair"].value_counts().head(5).items():
        print(f"    {pair:34s} {n:5d}")

    # How the ledger settled them. The coders' raw codes still differ — the
    # sweep does not rewrite their files — so the count above is unchanged by
    # RD-4(e) and cannot show it is done. This is what shows it.
    led = pd.read_csv(LEDGER, dtype=str).fillna("")
    j = mism.merge(led[["source_id", "candidate", "reason", "adjudicated"]],
                   on=["source_id", "candidate"], how="left")
    ruled = j["adjudicated"].str.lower() == "true"
    ordered = ~ruled
    unsettled = int((~ruled & (j["reason"] != j["reason_c1"])
                     & (j["reason"] != j["reason_c2"])).sum())
    from .ledger import REASON_CODES
    rank = {c: i for i, c in enumerate(REASON_CODES)}
    off_order = int(sum(
        rank.get(r.reason, 99) != min(rank.get(r.reason_c1, 99), rank.get(r.reason_c2, 99))
        for r in j[ordered].itertuples()))
    print(f"    → 台帳での解決: §9.4 の順序 {int(ordered.sum()):,} 行 / "
          f"著者裁定 {int(ruled.sum())} 行 / 未解決 {unsettled} 行")
    print(f"      （順序を外れた行 {off_order} / c1 側に落ちた "
          f"{int((j.reason == j.reason_c1).sum()):,} ・ c2 側 "
          f"{int((j.reason == j.reason_c2).sum()):,}）")
    return mism


if __name__ == "__main__":
    main()

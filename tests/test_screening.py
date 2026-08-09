"""Behaviour tests for L2 abstract screening (RB-2).

Tests the screening statistics contract, not implementation details:
reconciliation status on the (food, pmid) key, Cohen's kappa on co-coded
records only (coverage differences excluded from the denominator), fail-loud
adjudication, L2' aggregation, golden precision/recall, and attaching L2' to
pubmed_counts. Fully offline (pure DataFrame functions, no network/LLM).
"""

import math

import pandas as pd
import pytest

from src import screening as sc


# --- reconcile ------------------------------------------------------------
def test_reconcile_classifies_status():
    c1 = [
        {"food_key": "ginger", "pmid": "1", "label": "include"},
        {"food_key": "ginger", "pmid": "2", "label": "exclude"},
        {"food_key": "chicken", "pmid": "3", "label": "exclude"},  # only c1
    ]
    c2 = [
        {"food_key": "ginger", "pmid": "1", "label": "include"},   # agree
        {"food_key": "ginger", "pmid": "2", "label": "include"},   # disagree
        {"food_key": "chicken", "pmid": "9", "label": "exclude"},  # only c2
    ]
    recon = sc.reconcile(c1, c2)
    status = {(r.food_key, r.pmid): r.status for r in recon.itertuples()}
    assert status[("ginger", "1")] == "agree"
    assert status[("ginger", "2")] == "disagree"
    assert status[("chicken", "3")] == "only_c1"
    assert status[("chicken", "9")] == "only_c2"


def test_reconcile_keys_on_food_and_pmid():
    # Same PMID, two foods: judged per food, so two distinct records.
    c1 = [
        {"food_key": "ginger", "pmid": "5", "label": "include"},
        {"food_key": "chili pepper", "pmid": "5", "label": "include"},
    ]
    c2 = [
        {"food_key": "ginger", "pmid": "5", "label": "include"},
        {"food_key": "chili pepper", "pmid": "5", "label": "exclude"},
    ]
    recon = sc.reconcile(c1, c2)
    assert len(recon) == 2
    st = {r.food_key: r.status for r in recon.itertuples()}
    assert st["ginger"] == "agree" and st["chili pepper"] == "disagree"


def test_norm_label_tolerates_variants():
    assert sc._norm_label("Include") == "include"
    assert sc._norm_label("EXC") == "exclude"
    assert sc._norm_label("1") == "include"
    assert sc._norm_label("maybe") == ""


# --- Cohen's kappa --------------------------------------------------------
def test_kappa_uses_cocoded_denominator_only():
    # 4 co-coded (3 agree, 1 disagree) + 2 coverage-only rows that must NOT
    # count toward the kappa denominator.
    c1 = [
        {"food_key": "f", "pmid": "1", "label": "include"},
        {"food_key": "f", "pmid": "2", "label": "include"},
        {"food_key": "f", "pmid": "3", "label": "exclude"},
        {"food_key": "f", "pmid": "4", "label": "exclude"},
        {"food_key": "f", "pmid": "5", "label": "include"},  # only c1
    ]
    c2 = [
        {"food_key": "f", "pmid": "1", "label": "include"},
        {"food_key": "f", "pmid": "2", "label": "include"},
        {"food_key": "f", "pmid": "3", "label": "exclude"},
        {"food_key": "f", "pmid": "4", "label": "include"},  # disagree
        {"food_key": "f", "pmid": "6", "label": "exclude"},  # only c2
    ]
    k = sc.cohen_kappa(sc.reconcile(c1, c2))
    assert k["n_both"] == 4          # NOT 6 — coverage rows excluded
    assert k["po"] == 0.75           # 3/4 agree


def test_kappa_perfect_agreement_is_one():
    c = [
        {"food_key": "f", "pmid": "1", "label": "include"},
        {"food_key": "f", "pmid": "2", "label": "exclude"},
    ]
    k = sc.cohen_kappa(sc.reconcile(c, c))
    assert k["n_both"] == 2
    assert k["kappa"] == 1.0


# --- adjudicate -----------------------------------------------------------
def test_adjudicate_agree_takes_shared_label():
    recon = sc.reconcile(
        [{"food_key": "f", "pmid": "1", "label": "include"}],
        [{"food_key": "f", "pmid": "1", "label": "include"}],
    )
    adj = sc.adjudicate(recon)
    assert adj.iloc[0]["final_label"] == "include"


def test_adjudicate_requires_ruling_for_divergence():
    recon = sc.reconcile(
        [{"food_key": "f", "pmid": "1", "label": "include"}],
        [{"food_key": "f", "pmid": "1", "label": "exclude"}],
    )
    with pytest.raises(ValueError):
        sc.adjudicate(recon)  # no ruling → fail loud
    adj = sc.adjudicate(recon, rulings={("f", "1"): "exclude"})
    assert adj.iloc[0]["final_label"] == "exclude"
    assert bool(adj.iloc[0]["adjudicated"]) is True


def test_adjudicate_ruling_may_carry_the_authors_reason():
    recon = sc.reconcile(
        [{"food_key": "f", "pmid": "1", "label": "include", "reason": "human"}],
        [{"food_key": "f", "pmid": "1", "label": "exclude", "reason": "animal"}],
    )
    adj = sc.adjudicate(recon, rulings={("f", "1"): ("exclude", "33 rabbits per full text")})
    assert adj.iloc[0]["final_label"] == "exclude"
    assert adj.iloc[0]["reason"] == "33 rabbits per full text"


def test_a_ruling_overrides_an_agreed_label():
    # The §2.3 sweep depends on this: coders who agree on a wrong include are
    # never routed to adjudication, and the coding pass ran before §2.3 was
    # written down, so agreed includes must be correctable from the ledger.
    agreed = [
        {"food_key": "f", "pmid": "1", "label": "include", "reason": "skin blood flow"},
        {"food_key": "f", "pmid": "2", "label": "include", "reason": "skin blood flow"},
    ]
    recon = sc.reconcile(agreed, agreed)
    assert set(recon["status"]) == {"agree"}
    adj = sc.adjudicate(recon, rulings={("f", "1"): ("exclude", "no-thermal: retinal bed")})
    got = {r.pmid: (r.final_label, r.reason, bool(r.adjudicated)) for r in adj.itertuples()}
    assert got["1"] == ("exclude", "no-thermal: retinal bed", True)
    # an agreed row with no ruling is left exactly as the coders left it
    assert got["2"] == ("include", "skin blood flow", False)


def test_overriding_an_agreed_label_still_validates_the_ruling():
    agreed = [{"food_key": "f", "pmid": "1", "label": "include"}]
    recon = sc.reconcile(agreed, agreed)
    with pytest.raises(ValueError):
        sc.adjudicate(recon, rulings={("f", "1"): "maybe"})


@pytest.mark.parametrize("flag", ["uncertain-species", "no-abstract"])
def test_information_gap_flags_need_a_ruling_even_when_coders_agree(flag):
    # Agreement reached on what a record does not say is not evidence about it
    # (protocol §2/§5) — those rows must reach the author.
    agreed = [
        {"food_key": "f", "pmid": "1", "label": "exclude", "reason": flag},
        {"food_key": "f", "pmid": "2", "label": "exclude", "reason": "animal"},
    ]
    recon = sc.reconcile(agreed, agreed)
    assert set(recon["status"]) == {"agree"}
    with pytest.raises(ValueError):
        sc.adjudicate(recon)
    adj = sc.adjudicate(recon, rulings={("f", "1"): ("include", "MeSH: Humans")})
    settled = {r.pmid: (r.final_label, bool(r.adjudicated)) for r in adj.itertuples()}
    assert settled["1"] == ("include", True)
    assert settled["2"] == ("exclude", False)  # plain agreement stays untouched


# --- published screening.csv schema (protocol §6) -------------------------
def test_to_screening_csv_matches_protocol_columns_and_merges_sublabels():
    recon = sc.reconcile(
        [{"food_key": "g", "pmid": "1", "label": "include", "reason": "human RCT",
          "sublabels": "constituent"}],
        [{"food_key": "g", "pmid": "1", "label": "include", "reason": "human",
          "sublabels": "review;constituent"}],
    )
    out = sc.to_screening_csv(sc.adjudicate(recon))
    assert list(out.columns) == [
        "pmid", "food_key", "coder1", "coder2",
        "adjudicated", "final_label", "reason", "sublabels",
    ]
    row = out.iloc[0]
    assert row["coder1"] == "include" and row["coder2"] == "include"
    assert row["final_label"] == "include"
    assert row["sublabels"] == "constituent;review"  # union, no duplicates


def test_to_screening_csv_leaves_sublabels_empty_when_coders_gave_none():
    recon = sc.reconcile(
        [{"food_key": "g", "pmid": "1", "label": "exclude", "reason": "animal"}],
        [{"food_key": "g", "pmid": "1", "label": "exclude", "reason": "animal"}],
    )
    out = sc.to_screening_csv(sc.adjudicate(recon))
    assert out.iloc[0]["sublabels"] == ""  # not the string "nan"


# --- L2' aggregation ------------------------------------------------------
def test_l2_screened_counts_includes_per_food():
    adj = pd.DataFrame(
        {
            "food_key": ["ginger", "ginger", "ginger", "chicken", "chicken"],
            "pmid": ["1", "2", "3", "4", "5"],
            "final_label": ["include", "include", "exclude", "exclude", "exclude"],
        }
    )
    l2s = sc.l2_screened(adj)
    assert l2s["ginger"] == 2
    assert "chicken" not in l2s.index  # all excluded → not in the include tally


def test_l2_screened_can_drop_a_sublabel_class():
    adj = pd.DataFrame(
        {
            "food_key": ["coffee", "coffee", "coffee", "green tea"],
            "pmid": ["1", "2", "3", "4"],
            "final_label": ["include"] * 4,
            "sublabels": ["constituent", "", "review;constituent", "review"],
        }
    )
    assert sc.l2_screened(adj)["coffee"] == 3
    # Whole-food reading: only the record with no constituent sub-label survives.
    assert sc.l2_screened(adj, exclude_sublabels=("constituent",))["coffee"] == 1
    # Primary-report reading: the ";"-joined record is dropped by its review token.
    assert sc.l2_screened(adj, exclude_sublabels=("review",))["coffee"] == 2
    # A food whose only study is dropped leaves the tally entirely.
    assert "green tea" not in sc.l2_screened(adj, exclude_sublabels=("review",)).index


def test_l2_screened_treats_a_missing_sublabel_as_no_sublabel():
    # Most included records carry no sub-label at all; those must never be
    # dropped by a narrower definition.
    adj = pd.DataFrame(
        {
            "food_key": ["ginger", "ginger"],
            "pmid": ["1", "2"],
            "final_label": ["include", "include"],
            "sublabels": [None, "constituent"],
        }
    )
    assert sc.l2_screened(adj, exclude_sublabels=("constituent",))["ginger"] == 1


def test_attach_l2_screened_zero_for_all_excluded():
    pc = pd.DataFrame(
        {
            "food_key": ["ginger", "chicken", "ginger"],
            "layer": ["L2", "L2", "L1"],
            "n_pubmed": [35, 278, 900],
        }
    )
    l2s = pd.Series({"ginger": 2}, name="L2_screened")
    out = sc.attach_l2_screened(pc, l2s)
    g = out[(out.food_key == "ginger") & (out.layer == "L2")].iloc[0]
    c = out[(out.food_key == "chicken") & (out.layer == "L2")].iloc[0]
    l1 = out[out.layer == "L1"].iloc[0]
    assert g["L2_screened"] == 2
    assert c["L2_screened"] == 0          # L2 food, no includes → 0 not NaN
    assert math.isnan(l1["L2_screened"])  # non-L2 row → NaN


def test_attach_l2_screened_leaves_unscreened_foods_missing():
    # Partial screening: an unscreened food must not read 0, which would assert
    # "no on-construct studies" about records nobody has looked at yet.
    pc = pd.DataFrame(
        {
            "food_key": ["ginger", "chicken", "carrot"],
            "layer": ["L2", "L2", "L2"],
            "n_pubmed": [35, 278, 12],
        }
    )
    l2s = pd.Series({"ginger": 2}, name="L2_screened")
    out = sc.attach_l2_screened(pc, l2s, screened_foods=["ginger", "chicken"])
    by_food = out.set_index("food_key")["L2_screened"]
    assert by_food["ginger"] == 2
    assert by_food["chicken"] == 0          # screened, nothing included
    assert math.isnan(by_food["carrot"])    # not screened yet → unknown


# --- golden precision/recall ---------------------------------------------
def test_golden_scores_precision_recall():
    golden = [
        {"food_key": "g", "pmid": "1", "gold_label": "include"},
        {"food_key": "g", "pmid": "2", "gold_label": "include"},
        {"food_key": "g", "pmid": "3", "gold_label": "exclude"},
        {"food_key": "g", "pmid": "4", "gold_label": "exclude"},
    ]
    coder = [
        {"food_key": "g", "pmid": "1", "label": "include"},  # tp
        {"food_key": "g", "pmid": "2", "label": "exclude"},  # fn
        {"food_key": "g", "pmid": "3", "label": "include"},  # fp
        {"food_key": "g", "pmid": "4", "label": "exclude"},  # tn
    ]
    s = sc.golden_scores(coder, golden)
    assert s["tp"] == 1 and s["fp"] == 1 and s["fn"] == 1 and s["tn"] == 1
    assert s["precision"] == 0.5
    assert s["recall"] == 0.5
    assert s["accuracy"] == 0.5


# --- author ruling ledger -------------------------------------------------
# The rulings moved out of a dict literal into data/screening_rulings.csv when
# the recall rebuild pushed their count from 56 to 266. What matters is that the
# file reads back in the shape adjudicate() expects, and that a duplicated key
# fails loudly: two rulings for one record means one was never applied, and which
# one won would depend on row order.
def _rulings_csv(tmp_path, rows):
    import pandas as pd
    path = tmp_path / "screening_rulings.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_load_rulings_reads_the_shape_adjudicate_expects(tmp_path, monkeypatch):
    from src import build_screening as bs
    monkeypatch.setattr(bs, "RULINGS_CSV", _rulings_csv(tmp_path, [
        {"food_key": "chili pepper", "pmid": "1", "final_label": "include",
         "rationale": "human RCT, capsaicin", "batch": "t"},
        {"food_key": "salt", "pmid": "2", "final_label": "exclude",
         "rationale": "name-only", "batch": "t"},
    ]))
    got = bs.load_rulings()
    assert got[("chili pepper", "1")] == ("include", "human RCT, capsaicin")
    assert got[("salt", "2")] == ("exclude", "name-only")


def test_load_rulings_rejects_a_duplicated_record_key(tmp_path, monkeypatch):
    from src import build_screening as bs
    monkeypatch.setattr(bs, "RULINGS_CSV", _rulings_csv(tmp_path, [
        {"food_key": "salt", "pmid": "2", "final_label": "exclude",
         "rationale": "name-only", "batch": "t"},
        {"food_key": "salt", "pmid": "2", "final_label": "include",
         "rationale": "changed my mind", "batch": "t"},
    ]))
    with pytest.raises(ValueError, match="duplicated"):
        bs.load_rulings()


def test_load_rulings_is_empty_when_the_ledger_does_not_exist(tmp_path, monkeypatch):
    from src import build_screening as bs
    monkeypatch.setattr(bs, "RULINGS_CSV", tmp_path / "absent.csv")
    assert bs.load_rulings() == {}

def test_exclusion_breakdown_classes_on_the_prefix_not_the_free_text():
    # The reason field is "class: free text" ("animal: mice"), and Table 2 counts
    # classes. Splitting on the wrong side silently reports one class per phrasing.
    import pandas as pd

    from src.build_screening import exclusion_breakdown

    ledger = pd.DataFrame(
        [
            {"final_label": "exclude", "reason": "animal"},
            {"final_label": "exclude", "reason": "animal: mice"},
            {"final_label": "exclude", "reason": "animal: rats "},
            {"final_label": "exclude", "reason": "agri"},
            {"final_label": "include", "reason": ""},
        ]
    )
    out = exclusion_breakdown(ledger).set_index("reason")
    assert int(out.loc["animal", "n"]) == 3
    assert int(out.loc["agri", "n"]) == 1
    # Includes must not enter the denominator.
    assert int(out["n"].sum()) == 4
    assert float(out.loc["animal", "pct"]) == 75.0

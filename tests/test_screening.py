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

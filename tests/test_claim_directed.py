"""Behaviour tests for the §8 claim-directed / incidental sub-label pass.

Tests the contract the sensitivity analysis rests on: the sub-label vocabulary is
closed (an "include" from a confused coder is not silently read as a label),
kappa is computed on co-coded rows only, adjudication is fail-loud, and the
attach that folds the sub-label into the screening ledger refuses every way the
two ledgers can drift apart. Fully offline.
"""

import math

import pandas as pd
import pytest

from src import claim_directed as cd


def _screening(rows):
    """A screening frame in the published column order."""
    return pd.DataFrame(
        [
            {
                "pmid": p, "food_key": f, "coder1": "include", "coder2": "include",
                "adjudicated": False, "final_label": lab, "reason": "", "sublabels": sub,
            }
            for p, f, lab, sub in rows
        ]
    )


# --- vocabulary -----------------------------------------------------------
def test_norm_accepts_only_the_two_canonical_tokens():
    assert cd._norm("Claim-Directed") == "claim-directed"
    assert cd._norm("claim_directed") == "claim-directed"
    assert cd._norm(" incidental ") == "incidental"
    # The screening vocabulary must not leak in: a coder answering the wrong
    # question is a missing label, not a judgment.
    assert cd._norm("include") == ""
    assert cd._norm("direct") == ""
    assert cd._norm(None) == ""


# --- reconcile / kappa ----------------------------------------------------
def test_reconcile_classifies_status_on_food_and_pmid():
    c1 = [
        {"food_key": "ginger", "pmid": "1", "sub_label": "claim-directed"},
        {"food_key": "ginger", "pmid": "2", "sub_label": "incidental"},
        {"food_key": "chicken", "pmid": "3", "sub_label": "incidental"},
    ]
    c2 = [
        {"food_key": "ginger", "pmid": "1", "sub_label": "claim-directed"},
        {"food_key": "ginger", "pmid": "2", "sub_label": "claim-directed"},
        {"food_key": "chicken", "pmid": "9", "sub_label": "incidental"},
    ]
    st = {(r.food_key, r.pmid): r.status for r in cd.reconcile(c1, c2).itertuples()}
    assert st[("ginger", "1")] == "agree"
    assert st[("ginger", "2")] == "disagree"
    assert st[("chicken", "3")] == "only_c1"
    assert st[("chicken", "9")] == "only_c2"


def test_same_pmid_under_two_foods_is_two_records():
    c1 = [
        {"food_key": "barley", "pmid": "5", "sub_label": "claim-directed"},
        {"food_key": "mugicha", "pmid": "5", "sub_label": "claim-directed"},
    ]
    c2 = [
        {"food_key": "barley", "pmid": "5", "sub_label": "claim-directed"},
        {"food_key": "mugicha", "pmid": "5", "sub_label": "incidental"},
    ]
    recon = cd.reconcile(c1, c2)
    assert len(recon) == 2
    st = {r.food_key: r.status for r in recon.itertuples()}
    assert st["barley"] == "agree" and st["mugicha"] == "disagree"


def test_kappa_counts_only_co_coded_rows():
    c1 = [{"food_key": "g", "pmid": str(i), "sub_label": "claim-directed"} for i in range(4)]
    c1 += [{"food_key": "g", "pmid": "9", "sub_label": "incidental"}]
    c2 = [{"food_key": "g", "pmid": str(i), "sub_label": "claim-directed"} for i in range(4)]
    c2 += [{"food_key": "g", "pmid": "77", "sub_label": "incidental"}]  # coverage gap
    k = cd.cohen_kappa(cd.reconcile(c1, c2))
    assert k["n_both"] == 4  # the two one-sided rows are coverage, not ratings
    assert k["po"] == 1.0


def test_kappa_is_nan_without_co_coded_rows():
    k = cd.cohen_kappa(cd.reconcile([{"food_key": "g", "pmid": "1", "sub_label": "incidental"}], []))
    assert k["n_both"] == 0 and math.isnan(k["kappa"])


# --- adjudication ---------------------------------------------------------
def test_agreement_resolves_without_a_ruling():
    recon = cd.reconcile(
        [{"food_key": "g", "pmid": "1", "sub_label": "incidental"}],
        [{"food_key": "g", "pmid": "1", "sub_label": "incidental"}],
    )
    out = cd.adjudicate(recon)
    assert out.iloc[0]["sub_label"] == "incidental"
    assert not out.iloc[0]["adjudicated"]


def test_divergence_without_a_ruling_raises():
    recon = cd.reconcile(
        [{"food_key": "g", "pmid": "1", "sub_label": "incidental"}],
        [{"food_key": "g", "pmid": "1", "sub_label": "claim-directed"}],
    )
    with pytest.raises(ValueError, match="needs an author ruling"):
        cd.adjudicate(recon)


def test_author_flag_routes_an_agreed_row_to_the_author():
    rows = [{"food_key": "g", "pmid": "1", "sub_label": "incidental",
             "reason": "no-abstract"}]
    recon = cd.reconcile(rows, [dict(rows[0])])
    with pytest.raises(ValueError, match="needs an author ruling"):
        cd.adjudicate(recon)
    out = cd.adjudicate(recon, {("g", "1"): ("claim-directed", "full text says so")})
    assert out.iloc[0]["sub_label"] == "claim-directed"
    assert out.iloc[0]["adjudicated"]
    assert out.iloc[0]["reason"] == "full text says so"


def test_a_ruling_overrides_an_agreed_row_and_is_flagged():
    recon = cd.reconcile(
        [{"food_key": "g", "pmid": "1", "sub_label": "claim-directed"}],
        [{"food_key": "g", "pmid": "1", "sub_label": "claim-directed"}],
    )
    out = cd.adjudicate(recon, {("g", "1"): ("incidental", "the question is weight loss")})
    assert out.iloc[0]["sub_label"] == "incidental"
    assert out.iloc[0]["adjudicated"]


def test_an_unreadable_ruling_raises_rather_than_defaulting():
    recon = cd.reconcile(
        [{"food_key": "g", "pmid": "1", "sub_label": "incidental"}],
        [{"food_key": "g", "pmid": "1", "sub_label": "claim-directed"}],
    )
    with pytest.raises(ValueError, match="invalid ruling"):
        cd.adjudicate(recon, {("g", "1"): "include"})


def test_ledger_csv_carries_both_coders_and_the_settled_label():
    recon = cd.reconcile(
        [{"food_key": "g", "pmid": "1", "sub_label": "incidental", "reason": "weight loss"}],
        [{"food_key": "g", "pmid": "1", "sub_label": "incidental", "reason": "obesity trial"}],
    )
    out = cd.to_ledger_csv(cd.adjudicate(recon))
    assert list(out.columns) == [
        "pmid", "food_key", "coder1", "coder2", "adjudicated", "sub_label", "reason",
    ]
    assert out.iloc[0]["coder1"] == "incidental" and out.iloc[0]["coder2"] == "incidental"


# --- attach ---------------------------------------------------------------
def test_attach_folds_the_sub_label_into_sublabels_without_touching_the_input():
    screening = _screening([
        ("1", "ginger", "include", "constituent"),
        ("2", "ginger", "include", ""),
        ("3", "ginger", "exclude", ""),
    ])
    ledger = pd.DataFrame([
        {"pmid": "1", "food_key": "ginger", "sub_label": "claim-directed"},
        {"pmid": "2", "food_key": "ginger", "sub_label": "incidental"},
    ])
    out = cd.attach(screening, ledger)
    assert out.iloc[0]["sublabels"] == "constituent;claim-directed"
    assert out.iloc[1]["sublabels"] == "incidental"
    assert out.iloc[2]["sublabels"] == ""  # excludes are untouched
    # The caller's frame is not mutated — the reported L2' is built from it.
    assert screening.iloc[0]["sublabels"] == "constituent"


def test_attach_is_a_no_op_before_the_pass_has_run():
    screening = _screening([("1", "ginger", "include", "")])
    assert cd.attach(screening, None) is screening


def test_attach_refuses_an_include_with_no_sub_label():
    screening = _screening([
        ("1", "ginger", "include", ""),
        ("2", "ginger", "include", ""),
    ])
    ledger = pd.DataFrame([{"pmid": "1", "food_key": "ginger", "sub_label": "incidental"}])
    with pytest.raises(ValueError, match="carry no .8 sub-label"):
        cd.attach(screening, ledger)


def test_attach_refuses_a_sub_label_whose_record_is_not_an_include():
    screening = _screening([("1", "ginger", "exclude", "")])
    ledger = pd.DataFrame([{"pmid": "1", "food_key": "ginger", "sub_label": "incidental"}])
    with pytest.raises(ValueError, match="not includes"):
        cd.attach(screening, ledger)


def test_attach_refuses_duplicate_and_unknown_labels():
    screening = _screening([("1", "ginger", "include", "")])
    dup = pd.DataFrame([
        {"pmid": "1", "food_key": "ginger", "sub_label": "incidental"},
        {"pmid": "1", "food_key": "ginger", "sub_label": "claim-directed"},
    ])
    with pytest.raises(ValueError, match="duplicated keys"):
        cd.attach(screening, dup)
    bad = pd.DataFrame([{"pmid": "1", "food_key": "ginger", "sub_label": "include"}])
    with pytest.raises(ValueError, match="unknown sub-labels"):
        cd.attach(screening, bad)


# --- figures recomputed from the published ledger -------------------------
def _published(rows):
    """The ledger as it is read back from disk: every column a string."""
    return pd.DataFrame(
        [{"pmid": p, "food_key": f, "coder1": a, "coder2": b,
          "adjudicated": adj, "sub_label": final, "reason": ""}
         for p, f, a, b, adj, final in rows],
        dtype=str,
    )


def test_ledger_agreement_recomputes_the_reported_figures():
    ledger = _published([
        ("1", "g", "claim-directed", "claim-directed", "False", "claim-directed"),
        ("2", "g", "incidental", "incidental", "False", "incidental"),
        ("3", "g", "claim-directed", "incidental", "True", "incidental"),
        ("4", "g", "incidental", "incidental", "True", "claim-directed"),
    ])
    a = cd.ledger_agreement(ledger)
    assert a["n"] == 4
    assert a["divergences"] == 1
    # The flag arrives as the string "True", not as a boolean — pandas 3 gives
    # string columns their own dtype, so a truthiness test on the raw column
    # counts every row.
    assert a["adjudicated"] == 2
    assert a["claim-directed"] == 2 and a["incidental"] == 2
    assert a["po"] == 0.75


def test_ledger_agreement_accepts_a_boolean_flag_too():
    ledger = _published([
        ("1", "g", "incidental", "incidental", "False", "incidental"),
        ("2", "g", "incidental", "claim-directed", "True", "incidental"),
    ])
    ledger["adjudicated"] = [False, True]
    assert cd.ledger_agreement(ledger)["adjudicated"] == 1


def test_attached_sub_label_drives_the_narrower_l2_prime():
    from src.screening import l2_screened

    screening = _screening([
        ("1", "ginger", "include", "constituent"),
        ("2", "ginger", "include", ""),
        ("3", "coffee", "include", ""),
    ])
    ledger = pd.DataFrame([
        {"pmid": "1", "food_key": "ginger", "sub_label": "claim-directed"},
        {"pmid": "2", "food_key": "ginger", "sub_label": "incidental"},
        {"pmid": "3", "food_key": "coffee", "sub_label": "incidental"},
    ])
    joined = cd.attach(screening, ledger)
    assert l2_screened(joined)["ginger"] == 2
    narrow = l2_screened(joined, exclude_sublabels=("incidental",))
    assert narrow["ginger"] == 1
    assert "coffee" not in narrow.index  # every coffee record is incidental
    # The §3 sub-label readings are unaffected by the new token.
    assert l2_screened(joined, exclude_sublabels=("constituent",))["ginger"] == 1

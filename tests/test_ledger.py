"""Behaviour tests for the Axis A candidate ledger (Route D, RD-3).

Tests the ledger's contract rather than its implementation: reconciliation on
the (source_id, candidate) key, Cohen's kappa over the include/exclude decision
on co-coded candidates only, fail-loud adjudication, and the published §9.7
schema.

Two guards get the most attention here because the Route D goal declaration
names them as failure conditions: an exclusion reason code with no basis in
``coding_protocol.md`` §9.4 must not reach the ledger, and a candidate that was
enumerated but never judged must not be able to pass as an exclusion.
"""

import math

import pandas as pd
import pytest

from src import ledger as lg


def _row(source_id="src", candidate="しょうが", label="include", **kw) -> dict:
    row = {"source_id": source_id, "candidate": candidate, "label": label}
    if label == "include":
        row.setdefault("food_ja", candidate)
        row.setdefault("food_en", "ginger")
        row.setdefault("direction", "warm")
        row.setdefault("quote", "しょうがは体を温める")
    else:
        row.setdefault("reason", "fragment")
    row.update(kw)
    return row


# --- reconcile ------------------------------------------------------------
class TestReconcile:
    def test_classifies_status(self):
        c1 = [
            _row(candidate="a"),
            _row(candidate="b", label="exclude"),
            _row(candidate="only1", label="exclude"),
        ]
        c2 = [
            _row(candidate="a"),                       # agree
            _row(candidate="b"),                       # disagree
            _row(candidate="only2", label="exclude"),  # only c2
        ]
        recon = lg.reconcile(c1, c2)
        status = {r.candidate: r.status for r in recon.itertuples()}
        assert status["a"] == "agree"
        assert status["b"] == "disagree"
        assert status["only1"] == "only_c1"
        assert status["only2"] == "only_c2"

    def test_keys_on_source_and_candidate(self):
        # The same span in two sources is judged separately: the unit of coding
        # is a (food, source) pair (§2), and a source may present it differently.
        c1 = [_row(source_id="a", candidate="なす"), _row(source_id="b", candidate="なす")]
        c2 = [
            _row(source_id="a", candidate="なす"),
            _row(source_id="b", candidate="なす", label="exclude"),
        ]
        recon = lg.reconcile(c1, c2)
        assert len(recon) == 2
        st = {r.source_id: r.status for r in recon.itertuples()}
        assert st["a"] == "agree" and st["b"] == "disagree"

    def test_norm_label_tolerates_variants(self):
        assert lg._norm_label("Include") == "include"
        assert lg._norm_label("EXC") == "exclude"
        assert lg._norm_label("maybe") == ""


# --- protocol-bound vocabularies -----------------------------------------
class TestValidateCodes:
    def test_rejects_a_reason_code_outside_section_9_4(self):
        # `category-label` is the code Route D deliberately did not create
        # (DEV-5): categories are included with a sub-label instead. A coder
        # reaching for it means the protocol needs revising, not the ledger
        # quietly absorbing a code nothing sanctions.
        c1 = [_row(label="exclude", reason="category-label")]
        with pytest.raises(ValueError, match="§9.4"):
            lg.reconcile(c1, c1)

    def test_accepts_every_code_the_protocol_defines(self):
        rows = [
            _row(candidate=f"c{i}", label="exclude", reason=code)
            for i, code in enumerate(lg.REASON_CODES)
        ]
        assert len(lg.reconcile(rows, rows)) == len(lg.REASON_CODES)

    def test_rejects_an_exclusion_with_no_reason_at_all(self):
        c1 = [_row(label="exclude", reason="")]
        with pytest.raises(ValueError, match="without a reason code"):
            lg.reconcile(c1, c1)

    def test_rejects_a_direction_outside_the_coding_vocabulary(self):
        c1 = [_row(direction="hot")]  # 五性 label, not an Axis A direction
        with pytest.raises(ValueError, match="direction"):
            lg.reconcile(c1, c1)

    def test_uncertain_is_allowed_as_a_reason_without_being_an_exclusion_code(self):
        # §9.6: a span the coder cannot judge from the source goes to the
        # author. It is a routing flag, not a §9.4 exclusion basis.
        c1 = [_row(label="exclude", reason=lg.UNCERTAIN)]
        assert len(lg.reconcile(c1, c1)) == 1


# --- kappa ----------------------------------------------------------------
class TestKappa:
    def test_counts_only_co_coded_candidates(self):
        c1 = [_row(candidate=f"c{i}") for i in range(4)] + [_row(candidate="only1")]
        c2 = [_row(candidate=f"c{i}") for i in range(4)]
        k = lg.cohen_kappa(lg.reconcile(c1, c2))
        assert k["n_both"] == 4  # the coverage difference is not a rating

    def test_perfect_agreement_on_a_mixed_set_is_one(self):
        rows = [_row(candidate="a")] + [_row(candidate="b", label="exclude")]
        k = lg.cohen_kappa(lg.reconcile(rows, rows))
        assert k["kappa"] == pytest.approx(1.0)

    def test_is_nan_when_nothing_was_co_coded(self):
        k = lg.cohen_kappa(lg.reconcile([_row()], []))
        assert math.isnan(k["kappa"]) and k["n_both"] == 0


# --- adjudication ---------------------------------------------------------
class TestAdjudicate:
    def test_agreement_stands_without_a_ruling(self):
        rows = [_row()]
        out = lg.adjudicate(lg.reconcile(rows, rows))
        assert out["final_label"].tolist() == ["include"]
        assert out["adjudicated"].tolist() == [False]

    def test_a_divergence_without_a_ruling_is_a_hard_error(self):
        c1 = [_row(candidate="なす")]
        c2 = [_row(candidate="なす", label="exclude")]
        with pytest.raises(ValueError, match="needs an author ruling"):
            lg.adjudicate(lg.reconcile(c1, c2))

    def test_a_ruling_settles_a_divergence_and_is_marked(self):
        c1 = [_row(candidate="なす")]
        c2 = [_row(candidate="なす", label="exclude")]
        out = lg.adjudicate(
            lg.reconcile(c1, c2), {("src", "なす"): ("exclude", "no-direction")}
        )
        assert out["final_label"].tolist() == ["exclude"]
        assert out["reason"].tolist() == ["no-direction"]
        assert out["adjudicated"].tolist() == [True]

    def test_a_ruling_overrides_an_agreed_row(self):
        # The D42 behaviour, kept identical across the axes: coders who agree on
        # a wrong judgment are never routed to adjudication, so an agreed row
        # has to be correctable without re-running the batch.
        rows = [_row()]
        out = lg.adjudicate(
            lg.reconcile(rows, rows), {("src", "しょうが"): ("exclude", "fragment")}
        )
        assert out["final_label"].tolist() == ["exclude"]
        assert out["adjudicated"].tolist() == [True]

    def test_an_uncertain_flag_goes_to_the_author_even_when_both_agree(self):
        rows = [_row(label="exclude", reason=lg.UNCERTAIN)]
        with pytest.raises(ValueError, match="needs an author ruling"):
            lg.adjudicate(lg.reconcile(rows, rows))

    def test_a_ruling_that_excludes_still_needs_a_protocol_code(self):
        c1 = [_row(candidate="なす")]
        c2 = [_row(candidate="なす", label="exclude")]
        with pytest.raises(ValueError, match="§9.4"):
            lg.adjudicate(
                lg.reconcile(c1, c2), {("src", "なす"): ("exclude", "looked wrong")}
            )

    def test_an_invalid_ruling_label_is_rejected(self):
        c1 = [_row(candidate="なす")]
        c2 = [_row(candidate="なす", label="exclude")]
        with pytest.raises(ValueError, match="invalid ruling"):
            lg.adjudicate(lg.reconcile(c1, c2), {("src", "なす"): "maybe"})


# --- published schema -----------------------------------------------------
def _enumeration(pairs) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source_id": s, "candidate": c, "line_no": n, "paths": "list"}
            for s, c, n in pairs
        ]
    )


class TestToLedgerCsv:
    def test_emits_the_section_9_7_columns(self):
        rows = [_row()]
        out = lg.to_ledger_csv(
            lg.adjudicate(lg.reconcile(rows, rows)),
            _enumeration([("src", "しょうが", 42)]),
        )
        assert list(out.columns) == [
            "source_id", "line_no", "candidate", "paths", "coder1", "coder2",
            "adjudicated", "final_label", "reason", "sublabels", "food_ja",
            "food_en", "direction", "quote",
        ]

    def test_takes_line_no_and_paths_from_the_enumeration(self):
        # Where a span was found is recorded independently of how it was judged.
        rows = [_row()]
        out = lg.to_ledger_csv(
            lg.adjudicate(lg.reconcile(rows, rows)),
            _enumeration([("src", "しょうが", 42)]),
        )
        assert out["line_no"].tolist() == [42]
        assert out["paths"].tolist() == ["list"]

    def test_a_judgment_on_something_never_enumerated_is_a_hard_error(self):
        rows = [_row(candidate="invented")]
        with pytest.raises(ValueError, match="not in the enumeration"):
            lg.to_ledger_csv(
                lg.adjudicate(lg.reconcile(rows, rows)),
                _enumeration([("src", "しょうが", 1)]),
            )

    def test_an_exclusion_carries_its_reason_and_no_coding_fields(self):
        rows = [_row(label="exclude", reason="navigation")]
        out = lg.to_ledger_csv(
            lg.adjudicate(lg.reconcile(rows, rows)),
            _enumeration([("src", "しょうが", 3)]),
        )
        assert out["reason"].tolist() == ["navigation"]
        assert out["food_ja"].tolist() == [""]
        assert out["direction"].tolist() == [""]

    def test_an_inclusion_carries_the_coded_food_and_direction(self):
        rows = [_row()]
        out = lg.to_ledger_csv(
            lg.adjudicate(lg.reconcile(rows, rows)),
            _enumeration([("src", "しょうが", 3)]),
        )
        assert out["food_en"].tolist() == ["ginger"]
        assert out["direction"].tolist() == ["warm"]
        assert out["reason"].tolist() == [""]

    def test_sublabels_are_unioned_across_coders(self):
        # §9.5: a category label is included and marked, not excluded.
        c1 = [_row(candidate="葉物野菜", sublabels="category")]
        c2 = [_row(candidate="葉物野菜", sublabels="category;umbrella")]
        out = lg.to_ledger_csv(
            lg.adjudicate(lg.reconcile(c1, c2)),
            _enumeration([("src", "葉物野菜", 9)]),
        )
        assert out["sublabels"].tolist() == ["category;umbrella"]


def test_exclusion_breakdown_reports_each_reason_with_its_share():
    rows = [
        _row(candidate="a", label="exclude", reason="fragment"),
        _row(candidate="b", label="exclude", reason="fragment"),
        _row(candidate="c", label="exclude", reason="navigation"),
    ]
    ledger = lg.to_ledger_csv(
        lg.adjudicate(lg.reconcile(rows, rows)),
        _enumeration([("src", "a", 1), ("src", "b", 2), ("src", "c", 3)]),
    )
    bd = lg.exclusion_breakdown(ledger)
    assert bd.iloc[0]["reason"] == "fragment"
    assert bd.iloc[0]["n"] == 2
    assert bd.iloc[0]["share"] == pytest.approx(2 / 3)

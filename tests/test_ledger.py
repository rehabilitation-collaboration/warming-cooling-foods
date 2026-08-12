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


class TestReasonOrder:
    """§9.4's application order settles which code an agreed exclusion carries.

    Before this, the ledger took the first coder's code whenever the two
    differed — 1,964 of 17,830 agreed exclusions on the finished corpus. Nothing
    in §9.4 sanctions preferring a coder, and which coder reads a rule literally
    varies by source, so the bias had no fixed direction to correct for.
    """

    def test_reason_codes_are_in_section_9_4_application_order(self):
        # The tuple is both the vocabulary and the order (§9.4). If a code is
        # added or moved, this is the test that says the protocol text and the
        # code have to be changed together.
        assert lg.REASON_CODES == (
            "navigation",
            "fragment",
            "not-verbatim",
            "not-food",
            "no-direction",
            "serving-temperature",
            "duplicate",
        )

    def test_the_earlier_code_in_the_order_is_recorded(self):
        # navigation (1st) beats not-food (4th): §1 puts a region outside the
        # frame regardless of what the span names.
        assert lg._first_code("not-food", "navigation") == "navigation"
        assert lg._first_code("navigation", "not-food") == "navigation"

    def test_it_does_not_prefer_the_first_coder(self):
        # The regression the rewrite fixes: with `reason_c1 or reason_c2` both
        # of these returned the c1 value, so the published code depended on who
        # was assigned the batch.
        assert lg._first_code("not-food", "fragment") == "fragment"
        assert lg._first_code("duplicate", "no-direction") == "no-direction"

    def test_one_code_or_two_identical_ones_are_unchanged(self):
        assert lg._first_code("fragment", "fragment") == "fragment"
        assert lg._first_code("", "not-food") == "not-food"
        assert lg._first_code("navigation", "") == "navigation"
        assert lg._first_code("", "") == ""

    def test_an_unrankable_flag_falls_back_rather_than_raising(self):
        # `uncertain` is not one of §9.4's codes; a row carrying it goes to the
        # author via _needs_ruling anyway, so this only supplies the value a
        # ruling may override.
        assert lg._first_code(lg.UNCERTAIN, "fragment") == "fragment"
        assert lg._first_code(lg.UNCERTAIN, lg.UNCERTAIN) == lg.UNCERTAIN

    def test_ordering_a_split_reason_moves_no_decision(self):
        # Both coders exclude; only the name differs. The decision, and so κ and
        # every Axis A count, must be untouched.
        c1 = [_row(candidate="しかし", label="exclude", reason="not-food")]
        c2 = [_row(candidate="しかし", label="exclude", reason="fragment")]
        out = lg.adjudicate(lg.reconcile(c1, c2))
        assert out["final_label"].tolist() == ["exclude"]
        assert out["reason"].tolist() == ["fragment"]
        assert not out["adjudicated"].any()

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


# --- guards added after review (2026-08-10) -------------------------------
class TestExhaustivenessBothWays:
    """The enumeration and the judgments have to match in both directions.

    The first version checked only one: it left-joined the judgments onto the
    enumeration, which structurally cannot surface an enumerated candidate that
    nobody judged — and that is the failure the ledger exists to prevent, since
    an unjudged candidate is indistinguishable from an excluded one once
    published.
    """

    def test_an_enumerated_candidate_with_no_judgment_is_a_hard_error(self):
        rows = [_row(candidate="しょうが")]
        with pytest.raises(ValueError, match="carry no judgment"):
            lg.to_ledger_csv(
                lg.adjudicate(lg.reconcile(rows, rows)),
                _enumeration([("src", "しょうが", 1), ("src", "ねぎ", 2)]),
            )

    def test_a_complete_pairing_passes(self):
        rows = [_row(candidate="しょうが"), _row(candidate="ねぎ")]
        out = lg.to_ledger_csv(
            lg.adjudicate(lg.reconcile(rows, rows)),
            _enumeration([("src", "しょうが", 1), ("src", "ねぎ", 2)]),
        )
        assert len(out) == 2


class TestSplitDirection:
    """Two coders can agree a span is an attribution and split on what it says.

    ``status`` compares include/exclude only, so this never showed up as a
    disagreement — the first version silently kept coder 1's direction.
    Direction is Axis A's construct; RD-1b found three real cases of this in
    macrobiotic_rashinban.
    """

    def _split(self):
        return (
            [_row(candidate="きゅうり", direction="warm")],
            [_row(candidate="きゅうり", direction="cool")],
        )

    def test_a_split_direction_on_an_agreed_include_goes_to_the_author(self):
        c1, c2 = self._split()
        with pytest.raises(ValueError, match="needs an author ruling"):
            lg.adjudicate(lg.reconcile(c1, c2))

    def test_a_dict_ruling_settles_the_direction(self):
        c1, c2 = self._split()
        out = lg.adjudicate(
            lg.reconcile(c1, c2),
            {("src", "きゅうり"): {"label": "include", "direction": "cool"}},
        )
        assert out["final_direction"].tolist() == ["cool"]
        assert out["adjudicated"].tolist() == [True]

    def test_the_settled_direction_reaches_the_published_ledger(self):
        c1, c2 = self._split()
        out = lg.to_ledger_csv(
            lg.adjudicate(
                lg.reconcile(c1, c2),
                {("src", "きゅうり"): {"label": "include", "direction": "cool"}},
            ),
            _enumeration([("src", "きゅうり", 41)]),
        )
        assert out["direction"].tolist() == ["cool"]

    def test_agreement_on_the_direction_needs_no_ruling(self):
        rows = [_row(candidate="きゅうり", direction="cool")]
        out = lg.adjudicate(lg.reconcile(rows, rows))
        assert out["adjudicated"].tolist() == [False]
        assert out["final_direction"].tolist() == ["cool"]


class TestIncludesCarryTheirCoding:
    """§9.3: an include regenerates claims.csv, so it must carry the coding.

    Reachable through the public API: a ruling may flip an agreed exclusion to
    include, and neither coder ever filled in food_ja/food_en/direction on a
    row they both excluded.
    """

    def test_a_ruling_flipping_an_exclusion_to_include_must_supply_the_coding(self):
        rows = [_row(candidate="ねぎ", label="exclude", reason="fragment")]
        with pytest.raises(ValueError, match="carries no"):
            lg.adjudicate(lg.reconcile(rows, rows), {("src", "ねぎ"): "include"})

    def test_a_dict_ruling_can_supply_it(self):
        rows = [_row(candidate="ねぎ", label="exclude", reason="fragment")]
        out = lg.adjudicate(
            lg.reconcile(rows, rows),
            {
                ("src", "ねぎ"): {
                    "label": "include", "food_ja": "ねぎ",
                    "food_en": "spring onion", "direction": "warm",
                }
            },
        )
        assert out["final_label"].tolist() == ["include"]
        assert out["final_food_en"].tolist() == ["spring onion"]

    def test_an_include_a_coder_left_without_a_direction_is_rejected(self):
        rows = [{"source_id": "src", "candidate": "ねぎ", "label": "include",
                 "food_ja": "ねぎ", "food_en": "spring onion"}]
        with pytest.raises(ValueError, match="carries no"):
            lg.adjudicate(lg.reconcile(rows, rows))

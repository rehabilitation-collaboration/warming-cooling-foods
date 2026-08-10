"""Behaviour tests for the Axis A coder input batches (Route D, RD-3).

The batches are what each coder agent actually reads, so the contract that
matters is: the whole source text travels with every batch (six candidates in
ten carry their thermal context only in the heading or a neighbouring line), a
line group is never split across batches, and the batches partition the
enumeration exactly. The last one is the reason this module fails loudly — a
candidate assigned to no batch never reaches a coder, and a ledger silently
short of rows reads exactly like one whose coders excluded them.
"""

import pandas as pd
import pytest

from src import dump_ledger_batches as dlb


def _candidates(spec: dict[int, int], source_id: str = "src") -> pd.DataFrame:
    """Enumeration fixture: ``{line_no: how many candidates on that line}``."""
    rows = [
        {
            "source_id": source_id,
            "line_no": line_no,
            "candidate": f"{source_id}-L{line_no}-{i}",
            "n_occurrences": 1,
            "paths": "list",
            "heading": "体を温める食材",
            "line": f"line {line_no}",
        }
        for line_no, n in spec.items()
        for i in range(n)
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "source_id", "line_no", "candidate", "n_occurrences",
            "paths", "heading", "line",
        ],
    )


# --- batch planning -------------------------------------------------------
class TestPlanBatches:
    def test_a_line_group_is_never_split(self):
        # One line carrying 300 candidates (the real maximum is 75) must land
        # whole: the overlapping granularities of a line are judged together,
        # or the duplicate/fragment codes of §9.4 cannot be applied.
        cands = _candidates({1: 10, 2: 300, 3: 10})
        batches = dlb.plan_batches(cands, target=100)
        homes = [i for i, lines in enumerate(batches) if 2 in lines]
        assert len(homes) == 1

    def test_splits_a_source_evenly_rather_than_leaving_a_short_tail(self):
        # 1,000 candidates at target 400 is three batches of ~333, not
        # 400/400/200 — every agent should carry a comparable load.
        cands = _candidates({ln: 10 for ln in range(1, 101)})
        sizes = [
            len(cands[cands["line_no"].isin(set(lines))])
            for lines in dlb.plan_batches(cands, target=400)
        ]
        assert len(sizes) == 3
        assert max(sizes) - min(sizes) <= 20

    def test_a_source_under_the_target_stays_one_batch(self):
        assert len(dlb.plan_batches(_candidates({1: 5, 2: 5}), target=400)) == 1

    def test_every_line_is_assigned_exactly_once(self):
        cands = _candidates({ln: 7 for ln in range(1, 60)})
        assigned = [ln for lines in dlb.plan_batches(cands, target=100) for ln in lines]
        assert sorted(assigned) == sorted(cands["line_no"].unique())

    def test_an_empty_source_plans_no_batches(self):
        assert dlb.plan_batches(_candidates({}), target=400) == []


# --- batch contents -------------------------------------------------------
class TestBuildBatch:
    def _patched(self, monkeypatch, text="全文\n本文"):
        monkeypatch.setattr(dlb, "source_text", lambda source_id: text)

    def test_carries_the_whole_source_text(self, monkeypatch):
        # A span shown alone cannot be judged: 59.7% of candidates carry thermal
        # vocabulary only in the enclosing heading, 1.6% only in a neighbouring
        # line. The text is what makes those judgeable.
        self._patched(monkeypatch, "体を温める食材\nしょうが")
        batch = dlb.build_batch(_candidates({1: 2}), "src", "src_b1", [1])
        assert batch["source_text"] == "体を温める食材\nしょうが"

    def test_takes_only_the_lines_it_was_assigned(self, monkeypatch):
        self._patched(monkeypatch)
        batch = dlb.build_batch(_candidates({1: 2, 2: 3}), "src", "src_b1", [2])
        assert {c["line_no"] for c in batch["candidates"]} == {2}
        assert len(batch["candidates"]) == 3

    def test_exposes_the_fields_a_coder_judges_on(self, monkeypatch):
        self._patched(monkeypatch)
        batch = dlb.build_batch(_candidates({1: 1}), "src", "src_b1", [1])
        assert set(batch["candidates"][0]) == {"line_no", "candidate", "paths"}
        assert isinstance(batch["candidates"][0]["line_no"], int)

    def test_withholds_the_heading_and_line_that_misled_both_canary_coders(
        self, monkeypatch
    ):
        # `heading` is the last thermal short line, not the nearest section
        # title, and `line` is where the emission started, so a `wrapped`
        # candidate reports a line that does not contain it. Both are kept in
        # the enumeration and withheld from the coder, whose context is
        # source_text.
        self._patched(monkeypatch)
        batch = dlb.build_batch(_candidates({1: 1}), "src", "src_b1", [1])
        assert "heading" not in batch["candidates"][0]
        assert "line" not in batch["candidates"][0]

    def test_batch_path_is_named_after_the_batch_id(self):
        assert dlb.batch_path("kawashimaya_b2").name == "candidates_kawashimaya_b2.json"


# --- the partition guard --------------------------------------------------
class TestVerifyPartition:
    def _batch(self, cands: pd.DataFrame, source_id="src", batch_id="src_b1") -> dict:
        return {
            "batch_id": batch_id,
            "source_id": source_id,
            "source_text": "",
            "candidates": cands.to_dict("records"),
        }

    def test_accepts_an_exact_partition(self):
        cands = _candidates({1: 2, 2: 2})
        halves = [
            self._batch(cands[cands["line_no"] == 1]),
            self._batch(cands[cands["line_no"] == 2], batch_id="src_b2"),
        ]
        dlb.verify_partition(cands, halves)  # does not raise

    def test_rejects_a_candidate_assigned_to_no_batch(self):
        cands = _candidates({1: 2, 2: 2})
        only_first = [self._batch(cands[cands["line_no"] == 1])]
        with pytest.raises(ValueError, match="assigned to no batch"):
            dlb.verify_partition(cands, only_first)

    def test_rejects_a_candidate_assigned_twice(self):
        cands = _candidates({1: 2})
        twice = [self._batch(cands), self._batch(cands, batch_id="src_b2")]
        with pytest.raises(ValueError, match="more than one batch"):
            dlb.verify_partition(cands, twice)

    def test_rejects_a_batch_holding_something_never_enumerated(self):
        cands = _candidates({1: 2})
        invented = self._batch(cands)
        invented["candidates"].append({"candidate": "invented", "line_no": 1})
        with pytest.raises(ValueError, match="not in the enumeration"):
            dlb.verify_partition(cands, [invented])

    def test_the_same_span_in_two_sources_is_two_candidates(self):
        # The unit of coding is a (food, source) pair, so an identical span in
        # two sources must not be mistaken for a duplicate assignment.
        a = _candidates({1: 1}, source_id="a")
        b = _candidates({1: 1}, source_id="b")
        a.loc[:, "candidate"] = "しょうが"
        b.loc[:, "candidate"] = "しょうが"
        both = pd.concat([a, b], ignore_index=True)
        dlb.verify_partition(
            both,
            [self._batch(a, "a", "a_b1"), self._batch(b, "b", "b_b1")],
        )  # does not raise


# --- edge cases the review asked to pin -----------------------------------
def test_a_source_with_exactly_the_target_stays_one_batch():
    cands = _candidates({ln: 4 for ln in range(1, 101)})  # exactly 400
    assert len(dlb.plan_batches(cands, target=400)) == 1


def test_main_rejects_a_source_that_has_no_candidates(tmp_path, monkeypatch):
    monkeypatch.setattr(dlb, "load_candidates", lambda: _candidates({1: 2}))
    monkeypatch.setattr(dlb, "WORK_DIR", tmp_path)
    with pytest.raises(ValueError, match="no candidates for source"):
        dlb.main(["absent"])


def test_main_writes_a_batch_per_plan_and_an_index(tmp_path, monkeypatch):
    monkeypatch.setattr(dlb, "load_candidates", lambda: _candidates({1: 250, 2: 250}))
    monkeypatch.setattr(dlb, "WORK_DIR", tmp_path)
    monkeypatch.setattr(dlb, "BATCH_INDEX_CSV", tmp_path / "batch_index.csv")
    monkeypatch.setattr(dlb, "batch_path", lambda bid: tmp_path / f"candidates_{bid}.json")
    monkeypatch.setattr(dlb, "source_text", lambda source_id: "本文")
    dlb.main(target=400)
    index = pd.read_csv(tmp_path / "batch_index.csv")
    assert index["n_candidates"].sum() == 500
    assert len(list(tmp_path.glob("candidates_*.json"))) == len(index)

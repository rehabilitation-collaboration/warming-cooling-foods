"""Behaviour tests for the per-food coder input batches (RB-2).

The batches are what each coder agent actually reads, so the contract that
matters is: one food's records only, the four fields a coder is allowed to see,
and a missing abstract carried as an empty string rather than the literal
"nan" (which a coder would read as content).
"""

import pandas as pd

from src import dump_screening_batches as dsb


RECORDS = pd.DataFrame(
    {
        "food_key": ["ginger", "ginger", "chili pepper"],
        "pmid": ["1", "2", "3"],
        "title": ["Ginger and TEF", "No abstract here", "Capsaicin trial"],
        "pubtypes": ["Journal Article", "Journal Article", "Randomized Controlled Trial"],
        "abstract": ["We gave ginger...", None, "Capsaicin was given..."],
    }
)


def test_build_batch_takes_one_food_and_the_coder_visible_fields():
    batch = dsb.build_batch(RECORDS, "ginger")
    assert batch["food_key"] == "ginger"
    assert [r["pmid"] for r in batch["records"]] == ["1", "2"]
    assert set(batch["records"][0]) == {"pmid", "title", "pubtypes", "abstract"}


def test_build_batch_renders_missing_abstract_as_empty_string():
    batch = dsb.build_batch(RECORDS, "ginger")
    assert batch["records"][1]["abstract"] == ""  # not "nan", not None


def test_batch_path_replaces_spaces_in_the_food_key():
    assert dsb.batch_path("chili pepper").name == "records_chili_pepper.json"


# --- incremental pass after a query widening ------------------------------
# Widening the effect vocabulary grows the record pool without changing the
# inclusion rule, so records already coded must be reused, never re-coded:
# reconcile() outer-joins on (food_key, pmid) and a duplicated key inflates the
# merge silently instead of failing.
def _screening_csv(tmp_path, pairs):
    path = tmp_path / "screening.csv"
    pd.DataFrame(
        [{"food_key": f, "pmid": p, "final_label": "exclude"} for f, p in pairs]
    ).to_csv(path, index=False)
    return path


def test_drop_judged_keeps_only_records_without_a_judgment(tmp_path, monkeypatch):
    monkeypatch.setattr(
        dsb, "SCREENING_CSV", _screening_csv(tmp_path, [("ginger", "1")])
    )
    left = dsb.drop_judged(RECORDS)
    assert list(zip(left["food_key"], left["pmid"])) == [
        ("ginger", "2"),
        ("chili pepper", "3"),
    ]


def test_drop_judged_matches_on_the_pair_not_the_food_or_pmid_alone(tmp_path, monkeypatch):
    # "ginger/3" is judged; "chili pepper/3" shares the pmid and must survive,
    # because the same record can be a candidate for more than one food.
    monkeypatch.setattr(
        dsb, "SCREENING_CSV", _screening_csv(tmp_path, [("ginger", "3")])
    )
    left = dsb.drop_judged(RECORDS)
    assert ("chili pepper", "3") in set(zip(left["food_key"], left["pmid"]))
    assert len(left) == 3


def test_drop_judged_is_a_noop_when_nothing_has_been_screened(tmp_path, monkeypatch):
    monkeypatch.setattr(dsb, "SCREENING_CSV", tmp_path / "absent.csv")
    assert len(dsb.drop_judged(RECORDS)) == len(RECORDS)

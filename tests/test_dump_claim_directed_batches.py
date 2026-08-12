"""Behaviour tests for the §8 coder input batches.

What matters here is what the coder sees and what it must not see: only the
included records, each with the §8-visible fields, a missing abstract rendered as
an empty string rather than "nan", and a judgment with no record text failing
loudly instead of shrinking the pass by one.
"""

import pandas as pd
import pytest

from src import dump_claim_directed_batches as dcb


def _write(tmp_path, monkeypatch, screening_rows, record_rows):
    s = tmp_path / "screening.csv"
    pd.DataFrame(screening_rows).to_csv(s, index=False)
    r = tmp_path / "l2_records.csv"
    pd.DataFrame(record_rows).to_csv(r, index=False)
    monkeypatch.setattr(dcb, "SCREENING_CSV", s)
    monkeypatch.setattr(dcb, "L2_RECORDS_CSV", r)


SCREENING = [
    {"pmid": "1", "food_key": "ginger", "final_label": "include", "sublabels": "constituent"},
    {"pmid": "2", "food_key": "ginger", "final_label": "exclude", "sublabels": ""},
    {"pmid": "3", "food_key": "chicken", "final_label": "include", "sublabels": ""},
]
RECORDS = [
    {"pmid": "1", "food_key": "ginger", "title": "Ginger and TEF",
     "pubtypes": "Journal Article", "abstract": "We gave ginger..."},
    {"pmid": "2", "food_key": "ginger", "title": "Excluded", "pubtypes": "", "abstract": "x"},
    {"pmid": "3", "food_key": "chicken", "title": "No abstract here",
     "pubtypes": "Journal Article", "abstract": None},
]


def test_only_included_records_are_dumped(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, SCREENING, RECORDS)
    out = dcb.included_records()
    assert list(zip(out["food_key"], out["pmid"])) == [("chicken", "3"), ("ginger", "1")]


def test_the_settled_sub_labels_travel_with_the_record(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, SCREENING, RECORDS)
    out = dcb.included_records().set_index("pmid")
    # §8's boundary rules name the §3 sub-labels, so the coder is given them.
    assert out.loc["1", "sublabels"] == "constituent"
    assert out.loc["3", "sublabels"] == ""


def test_a_missing_abstract_is_an_empty_string(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, SCREENING, RECORDS)
    out = dcb.included_records().set_index("pmid")
    assert out.loc["3", "abstract"] == ""  # not "nan", which a coder reads as text


def test_an_included_record_with_no_text_fails_loudly(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, SCREENING, RECORDS[1:])  # record 1 missing
    with pytest.raises(ValueError, match="no row in"):
        dcb.included_records()


def test_canary_covers_each_boundary_stratum_once(tmp_path, monkeypatch):
    rows = pd.DataFrame(
        [
            {"pmid": "1", "food_key": "a", "sublabels": "review", "abstract": "x"},
            {"pmid": "2", "food_key": "b", "sublabels": "constituent", "abstract": "x"},
            {"pmid": "3", "food_key": "c", "sublabels": "confounded", "abstract": "x"},
            {"pmid": "4", "food_key": "d", "sublabels": "", "abstract": ""},
            {"pmid": "5", "food_key": "e", "sublabels": "", "abstract": "x"},
            {"pmid": "5", "food_key": "f", "sublabels": "", "abstract": "x"},
        ]
    )
    picked = dcb.canary_sample(rows, per_stratum=1)
    # One per stratum, deduplicated: review, constituent, confounded,
    # no-abstract, multi-food, plain — the multi-food and plain strata overlap.
    assert set(picked["pmid"]) == {"1", "2", "3", "4", "5"}
    assert len(picked) == len(set(zip(picked["pmid"], picked["food_key"])))

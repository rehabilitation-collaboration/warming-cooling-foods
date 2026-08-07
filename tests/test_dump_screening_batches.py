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

"""Behaviour tests for Axis B evidence mapping.

Tests the count-collection contract, not implementation details: each API's
count is parsed from the right field, the OpenAlex query re-expresses L2 as a
boolean full-text search, the Japanese name for CiNii is chosen deterministically
from the coded data, composite labels are skipped, PubMed rate-limiting is
honoured, and the output rows carry the auxiliary counts on the right layer.
All network access is stubbed via ``_get_json`` — fully offline.
"""

import pandas as pd
import pytest

from src import evidence_mapping as em


# --- Count parsers read the correct field --------------------------------
def test_pubmed_count_reads_esearchresult_count(monkeypatch):
    monkeypatch.setattr(em, "_get_json", lambda url, params: {"esearchresult": {"count": "43"}})
    n, raw = em.pubmed_count("ginger[tiab]")
    assert n == 43
    assert raw["esearchresult"]["count"] == "43"


def test_openalex_count_reads_meta_count(monkeypatch):
    monkeypatch.setattr(em, "_get_json", lambda url, params: {"meta": {"count": 3172}})
    n, _ = em.openalex_count("ginger AND (thermogenesis)")
    assert n == 3172


def test_cinii_count_reads_opensearch_total(monkeypatch):
    monkeypatch.setattr(em, "_get_json", lambda url, params: {"opensearch:totalResults": 652})
    n, _ = em.cinii_count("生姜")
    assert n == 652


def test_cinii_passes_appid_only_when_set(monkeypatch):
    seen = {}
    def fake(url, params):
        seen.update(params)
        return {"opensearch:totalResults": 1}
    monkeypatch.setattr(em, "_get_json", fake)
    em.cinii_count("生姜")
    assert "appid" not in seen
    em.cinii_count("生姜", appid="XYZ")
    assert seen["appid"] == "XYZ"


# --- OpenAlex query re-expresses L2 as a boolean full-text search ---------
def test_openalex_query_has_no_pubmed_field_tags():
    q = em.openalex_query("ginger")
    assert "[tiab]" not in q and "[pt]" not in q


def test_openalex_query_joins_food_and_effects_with_and():
    q = em.openalex_query("banana")
    assert q.startswith("banana AND (")
    assert "thermogenesis" in q
    assert '"body temperature"' in q  # multiword phrase quoted


# --- Representative Japanese name is deterministic ------------------------
def test_representative_food_ja_picks_most_common():
    claims = pd.DataFrame(
        {
            "food_en": ["carrot", "carrot", "carrot"],
            "food_ja": ["にんじん", "にんじん", "人参"],
            "food_key": ["carrot", "carrot", "carrot"],
            "source_id": ["a", "b", "c"],
            "direction": ["warm", "warm", "warm"],
        }
    )
    assert em.representative_food_ja(claims)["carrot"] == "にんじん"


def test_representative_food_ja_breaks_ties_by_sorted_order():
    # Two names tied 1-1 → deterministic sorted pick, not insertion order.
    claims = pd.DataFrame(
        {
            "food_en": ["x", "x"],
            "food_ja": ["ナ", "ア"],
            "food_key": ["x", "x"],
            "source_id": ["a", "b"],
            "direction": ["cool", "cool"],
        }
    )
    assert em.representative_food_ja(claims)["x"] == "ア"


# --- Target selection: every coded food, scope split at 3 and 2 -----------
def _mini_frame():
    sources = pd.DataFrame(
        {"source_id": [f"s{i}" for i in range(4)], "tier": [1, 1, 1, 1]}
    )
    # core3 seen by 3 sources; sens2 by 2; one1 by 1.
    rows = []
    for sid in ("s0", "s1", "s2"):
        rows.append({"food_en": "core3", "food_ja": "コア", "source_id": sid, "direction": "warm"})
    for sid in ("s0", "s1"):
        rows.append({"food_en": "sens2", "food_ja": "セン", "source_id": sid, "direction": "cool"})
    rows.append({"food_en": "one1", "food_ja": "ワン", "source_id": "s0", "direction": "warm"})
    claims = pd.DataFrame(rows)
    return claims, sources


def test_target_foods_spans_every_coded_food():
    claims, sources = _mini_frame()
    tgt = em.target_foods(claims, sources)
    scopes = dict(zip(tgt["food_key"], tgt["scope"]))
    assert scopes == {"core3": "core", "sens2": "sensitivity", "one1": "single"}


def test_target_foods_min_sources_reproduces_the_core_sensitivity_cut():
    claims, sources = _mini_frame()
    tgt = em.target_foods(claims, sources, min_sources=em.SCOPE_MIN_SOURCES)
    scopes = dict(zip(tgt["food_key"], tgt["scope"]))
    assert scopes == {"core3": "core", "sens2": "sensitivity"}
    assert "one1" not in scopes


# --- Full collection over stubbed APIs ------------------------------------
class _StubAPIs:
    """Route _get_json to a canned count by endpoint, recording call order."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, params):
        self.calls.append(url)
        if "esearch" in url:
            return {"esearchresult": {"count": "5"}}
        if "openalex" in url:
            return {"meta": {"count": 500}}
        return {"opensearch:totalResults": 50}


def test_collect_counts_shapes_rows_and_places_aux_counts(monkeypatch, tmp_path):
    claims, sources = _mini_frame()
    monkeypatch.setattr(em, "_get_json", _StubAPIs())
    monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
    slept = []
    df, skipped, aux_missing = em.collect_counts(
        claims, sources, save_raw=True, reuse_cache=False, sleep=lambda s: slept.append(s)
    )
    # 3 foods × 3 layers.
    assert len(df) == 9
    assert skipped == []
    assert aux_missing == []
    l1 = df[df["layer"] == "L1"].iloc[0]
    l2 = df[df["layer"] == "L2"].iloc[0]
    l3 = df[df["layer"] == "L3"].iloc[0]
    # CiNii on L1, OpenAlex on L2, neither leaks onto other layers.
    assert l1["n_cinii"] == 50 and l1["n_openalex"] == ""
    assert l2["n_openalex"] == 500 and l2["n_cinii"] == ""
    assert l3["n_openalex"] == "" and l3["n_cinii"] == ""
    assert l1["n_pubmed"] == 5
    # PubMed rate-limit sleep called once per layer per food (3×3).
    assert len(slept) == 9
    assert all(s == em.PUBMED_DELAY for s in slept)


def test_collect_counts_skips_composite_labels(monkeypatch, tmp_path):
    sources = pd.DataFrame({"source_id": ["s0", "s1", "s2"], "tier": [1, 1, 1]})
    rows = [
        {"food_en": "nuts", "food_ja": "ナッツ", "source_id": s, "direction": "warm"}
        for s in ("s0", "s1", "s2")
    ]
    claims = pd.DataFrame(rows)
    monkeypatch.setattr(em, "_get_json", _StubAPIs())
    monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
    df, skipped, aux_missing = em.collect_counts(
        claims, sources, save_raw=False, sleep=lambda s: None
    )
    assert skipped == ["nuts"]
    assert df.empty


def test_collect_counts_saves_raw_json(monkeypatch, tmp_path):
    claims, sources = _mini_frame()
    monkeypatch.setattr(em, "_get_json", _StubAPIs())
    monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
    em.collect_counts(claims, sources, save_raw=True, reuse_cache=False, sleep=lambda s: None)
    # Each food: 3 PubMed + 1 OpenAlex + 1 CiNii = 5 files.
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 3 * 5


def test_openalex_failure_is_tolerated_pubmed_still_written(monkeypatch, tmp_path):
    # An OpenAlex 429 must not kill the run or discard the PubMed main axis.
    claims, sources = _mini_frame()

    def flaky(url, params):
        if "openalex" in url:
            raise em.requests.HTTPError("429 Too Many Requests")
        if "esearch" in url:
            return {"esearchresult": {"count": "7"}}
        return {"opensearch:totalResults": 70}

    monkeypatch.setattr(em, "_get_json", flaky)
    monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
    df, skipped, aux_missing = em.collect_counts(
        claims, sources, save_raw=True, reuse_cache=False, sleep=lambda s: None
    )
    assert len(df) == 9  # PubMed rows all present
    assert all(df[df["layer"] == "L1"]["n_pubmed"] == 7)
    # OpenAlex blank, CiNii still filled, every food flagged.
    assert (df[df["layer"] == "L2"]["n_openalex"] == "").all()
    assert (df[df["layer"] == "L1"]["n_cinii"] == 70).all()
    assert sorted(aux_missing) == ["openalex:core3", "openalex:one1", "openalex:sens2"]


def test_reuse_cache_reads_counts_without_calling_apis(monkeypatch, tmp_path):
    # Pre-seed query_log; a cached re-run must not hit the network at all.
    claims, sources = _mini_frame()
    monkeypatch.setattr(em, "QUERY_LOG_DIR", tmp_path)
    tmp_path.mkdir(exist_ok=True)
    for food in ("core3", "sens2", "one1"):
        for layer in ("L1", "L2", "L3"):
            em._save_raw("pubmed", food, layer, {"esearchresult": {"count": "9"}})
        em._save_raw("openalex", food, "L2", {"meta": {"count": 900}})
        em._save_raw("cinii", food, "L1", {"opensearch:totalResults": 90})

    def explode(url, params):
        raise AssertionError(f"network hit despite cache: {url}")

    monkeypatch.setattr(em, "_get_json", explode)
    df, skipped, aux_missing = em.collect_counts(
        claims, sources, save_raw=False, reuse_cache=True, sleep=lambda s: None
    )
    assert aux_missing == []
    assert (df[df["layer"] == "L1"]["n_pubmed"] == 9).all()
    assert (df[df["layer"] == "L2"]["n_openalex"] == 900).all()
    assert (df[df["layer"] == "L1"]["n_cinii"] == 90).all()

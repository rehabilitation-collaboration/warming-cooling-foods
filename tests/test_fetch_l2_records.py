"""Behaviour tests for L2 record retrieval (RB-1).

Tests the retrieval contract, not implementation details: esearch returns the
PMID list, efetch XML is parsed into title/abstract/journal/pubtypes (including
structured multi-segment abstracts), efetch calls are batched, composite labels
are skipped, and the cache-first path avoids the network. All network access is
stubbed via ``_get_json`` / ``_get_xml`` — fully offline.
"""

import json

import pandas as pd
import pytest

from src import fetch_l2_records as fr


# --- A small PubmedArticleSet XML fixture ---------------------------------
_XML = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>111</PMID>
      <Article>
        <Journal><Title>Poultry Science</Title></Journal>
        <ArticleTitle>Heat stress disrupts core body temperature in broilers.</ArticleTitle>
        <Abstract>
          <AbstractText>Broilers exposed to heat showed elevated core temperature.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>222</PMID>
      <Article>
        <Journal><Title>J Nutr</Title></Journal>
        <ArticleTitle>Ginger and diet-induced thermogenesis in adults.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Ginger is claimed to warm the body.</AbstractText>
          <AbstractText Label="RESULTS">Thermic effect of food increased.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
          <PublicationType>Journal Article</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedBookArticle>
    <BookDocument>
      <PMID>333</PMID>
      <Book><BookTitle>Fat Detection: Taste, Texture, and Post Ingestive Effects</BookTitle></Book>
      <ArticleTitle>Preference for High-Fat Food in Animals</ArticleTitle>
      <Abstract>
        <AbstractText>Animals prefer high-fat food.</AbstractText>
      </Abstract>
      <PublicationType>Review</PublicationType>
    </BookDocument>
  </PubmedBookArticle>
</PubmedArticleSet>"""


# --- esearch returns the PMID list ---------------------------------------
def test_esearch_pmids_reads_idlist(monkeypatch):
    monkeypatch.setattr(
        fr, "_get_json",
        lambda url, params: {"esearchresult": {"count": "2", "idlist": ["111", "222"]}},
    )
    pmids, raw = fr.esearch_pmids("chicken[tiab] AND (thermogenesis[tiab])")
    assert pmids == ["111", "222"]
    assert raw["esearchresult"]["count"] == "2"


def test_esearch_uses_large_retmax(monkeypatch):
    seen = {}
    def fake(url, params):
        seen.update(params)
        return {"esearchresult": {"idlist": []}}
    monkeypatch.setattr(fr, "_get_json", fake)
    fr.esearch_pmids("q")
    assert int(seen["retmax"]) >= 586  # must exceed the largest single-food L2 count


# --- efetch XML parsing ---------------------------------------------------
def test_parse_efetch_extracts_fields():
    recs = fr.parse_efetch(_XML)
    assert [r["pmid"] for r in recs] == ["111", "222", "333"]
    assert recs[0]["title"].startswith("Heat stress")
    assert recs[0]["journal"] == "Poultry Science"
    assert "Journal Article" in recs[0]["pubtypes"]


def test_parse_efetch_captures_book_article():
    # PubmedBookArticle records are real L2 hits and must be recorded, else the
    # per-food record count drifts below the esearch count (audit break).
    recs = fr.parse_efetch(_XML)
    book = next(r for r in recs if r["pmid"] == "333")
    assert book["title"] == "Preference for High-Fat Food in Animals"
    assert book["journal"].startswith("Fat Detection")
    assert "Animals prefer high-fat food." in book["abstract"]


def test_parse_efetch_joins_structured_abstract():
    recs = fr.parse_efetch(_XML)
    ab = recs[1]["abstract"]
    assert "BACKGROUND:" in ab and "RESULTS:" in ab
    assert "Thermic effect of food" in ab


def test_parse_efetch_captures_rct_pubtype():
    recs = fr.parse_efetch(_XML)
    assert "Randomized Controlled Trial" in recs[1]["pubtypes"]


# --- efetch batching ------------------------------------------------------
def test_efetch_batches_calls(monkeypatch):
    calls = []
    def fake_xml(url, params):
        calls.append(params["id"])
        return _XML
    monkeypatch.setattr(fr, "_get_xml", fake_xml)
    monkeypatch.setattr(fr, "EFETCH_BATCH", 2)
    fr.efetch_records(["1", "2", "3"], sleep=lambda s: None)
    assert len(calls) == 2  # 3 pmids / batch 2 => 2 calls
    assert calls[0] == "1,2" and calls[1] == "3"


# --- end-to-end collect over target foods (offline) -----------------------
def _tiny_inputs(monkeypatch):
    """Two target foods, one queryable + one composite (skipped)."""
    tgt = pd.DataFrame(
        {"food_key": ["chicken", "spices"], "n_sources": [4, 3], "scope": ["core", "core"]}
    )
    monkeypatch.setattr(fr, "target_foods", lambda c, s: tgt)


def test_collect_skips_composite_and_flattens_records(monkeypatch, tmp_path):
    _tiny_inputs(monkeypatch)
    monkeypatch.setattr(fr, "is_queryable", lambda f: f != "spices")
    monkeypatch.setattr(
        fr, "_get_json",
        lambda url, params: {"esearchresult": {"idlist": ["111", "222"]}},
    )
    monkeypatch.setattr(fr, "_get_xml", lambda url, params: _XML)
    # isolate cache dir so the test never touches the real query_log
    monkeypatch.setattr(fr, "QUERY_LOG_DIR", tmp_path)
    monkeypatch.setattr(fr, "_records_raw_path", lambda f: tmp_path / f"{f}.json")

    df, skipped = fr.collect_l2_records(
        pd.DataFrame(), pd.DataFrame(), save_raw=False, reuse_cache=False,
        sleep=lambda s: None,
    )
    assert skipped == ["spices"]
    assert set(df["food_key"]) == {"chicken"}
    assert list(df["pmid"]) == ["111", "222", "333"]
    assert df.iloc[0]["scope"] == "core"


_CACHED_REC = {"pmid": "999", "title": "cached", "abstract": "a", "journal": "j", "pubtypes": ""}


def _cache_setup(monkeypatch, tmp_path, payload):
    """Point the collector at one cache file holding ``payload``."""
    _tiny_inputs(monkeypatch)
    monkeypatch.setattr(fr, "is_queryable", lambda f: f != "spices")
    monkeypatch.setattr(fr, "QUERY_LOG_DIR", tmp_path)
    cache = tmp_path / "chicken.json"
    monkeypatch.setattr(fr, "_records_raw_path", lambda f: cache)
    cache.write_text(json.dumps(payload), encoding="utf-8")
    return cache


def test_collect_is_cache_first_when_the_query_matches(monkeypatch, tmp_path):
    _cache_setup(monkeypatch, tmp_path, {
        "_query": fr.pubmed_query("chicken", "L2"),
        "records": [_CACHED_REC],
    })

    def boom(*a, **k):
        raise AssertionError("network must not be hit when the cached query matches")
    monkeypatch.setattr(fr, "_get_json", boom)
    monkeypatch.setattr(fr, "_get_xml", boom)

    df, _ = fr.collect_l2_records(
        pd.DataFrame(), pd.DataFrame(), save_raw=False, reuse_cache=True,
        sleep=lambda s: None,
    )
    assert list(df["pmid"]) == ["999"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"_query": "chicken[tiab] AND thermogenesis[tiab]",
                      "records": [_CACHED_REC]}, id="different-query"),
        pytest.param([_CACHED_REC], id="legacy-untagged-list"),
    ],
)
def test_collect_refetches_when_the_cache_was_built_by_another_query(
    monkeypatch, tmp_path, payload
):
    """A stale record set must never be reused after the query widens.

    This is the failure mode that has no error to notice: the collector would
    finish cleanly and leave the record count exactly where it was, so the
    screening input would silently stay narrower than the query it claims.
    """
    _cache_setup(monkeypatch, tmp_path, payload)
    monkeypatch.setattr(
        fr, "_get_json", lambda url, params: {"esearchresult": {"idlist": ["111", "222"]}}
    )
    monkeypatch.setattr(fr, "_get_xml", lambda url, params: _XML)

    df, _ = fr.collect_l2_records(
        pd.DataFrame(), pd.DataFrame(), save_raw=False, reuse_cache=True,
        sleep=lambda s: None,
    )
    assert list(df["pmid"]) == ["111", "222", "333"]  # refetched, not the cached 999


def test_collect_writes_the_query_into_the_cache(monkeypatch, tmp_path):
    # Without this the next run cannot tell what the cache was built from.
    _tiny_inputs(monkeypatch)
    monkeypatch.setattr(fr, "is_queryable", lambda f: f != "spices")
    monkeypatch.setattr(fr, "QUERY_LOG_DIR", tmp_path)
    cache = tmp_path / "chicken.json"
    monkeypatch.setattr(fr, "_records_raw_path", lambda f: cache)
    monkeypatch.setattr(
        fr, "_get_json", lambda url, params: {"esearchresult": {"idlist": ["111"]}}
    )
    monkeypatch.setattr(fr, "_get_xml", lambda url, params: _XML)

    fr.collect_l2_records(
        pd.DataFrame(), pd.DataFrame(), save_raw=True, reuse_cache=False,
        sleep=lambda s: None,
    )
    written = json.loads(cache.read_text())
    assert written["_query"] == fr.pubmed_query("chicken", "L2")
    assert isinstance(written["records"], list)

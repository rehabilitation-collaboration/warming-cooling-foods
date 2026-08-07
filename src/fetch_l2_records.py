"""Fetch the individual PubMed records behind each food's Layer-2 count.

Axis B's L2 metric (food × thermal-effect terms) counts hits, but a count cannot
tell us *what* was counted. The GPT review (2026-08-07) showed the count is not
measuring the intended construct: ``chicken[tiab] AND body temperature`` is
dominated by poultry heat-stress and avian thermoregulation studies, not by
studies of a human eating chicken. To screen those false positives out
(``screening.py``, Phase RB-2) we first need the actual records — this module
retrieves them.

For every queryable food it runs the same L2 query used for the count
(``food_query_terms.pubmed_query(food, "L2")``), then:

1. ``esearch`` with a large ``retmax`` to get the full PMID list, and
2. ``efetch`` (``retmode=xml``) in batches to get title + abstract per PMID.

Raw responses are saved under ``data/query_log/`` for audit, and one flat table
is written to ``data/l2_records.csv`` (food_key, pmid, title, abstract,
journal, pubtypes). This module does **not** screen — it only assembles the
records that RB-2 will label include/exclude.

All network access goes through ``_get_json`` / ``_get_xml`` so tests can
monkeypatch them and run fully offline, mirroring ``evidence_mapping.py``.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from .claim_mapping import load_claims, load_sources
from .definitions import DATA_DIR, QUERY_LOG_DIR
from .evidence_mapping import (
    PUBMED_DELAY,
    REQUEST_TIMEOUT,
    USER_AGENT,
    _slug,
    is_queryable,
    target_foods,
)
from .food_query_terms import pubmed_query

# --- Endpoints -----------------------------------------------------------
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# esearch retmax: comfortably above the largest single-food L2 count (milk≈586).
ESEARCH_RETMAX = 5000
# efetch batch size: how many PMIDs per efetch call (NCBI is fine with a few
# hundred per POST-sized GET; keep modest to stay well within URL limits).
EFETCH_BATCH = 200

L2_RECORDS_CSV = DATA_DIR / "l2_records.csv"


def _get_json(url: str, params: dict) -> dict:
    """JSON network primitive (monkeypatched in tests)."""
    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def _get_xml(url: str, params: dict) -> bytes:
    """XML network primitive for efetch (monkeypatched in tests)."""
    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.content


# --- esearch: PMID list --------------------------------------------------
def esearch_pmids(query: str) -> tuple[list[str], dict]:
    """Return (pmid_list, raw_json) for an L2 query via esearch with idlist."""
    data = _get_json(
        PUBMED_ESEARCH,
        {"db": "pubmed", "term": query, "retmode": "json", "retmax": ESEARCH_RETMAX},
    )
    idlist = list(data["esearchresult"].get("idlist", []))
    return idlist, data


# --- efetch: title + abstract per PMID -----------------------------------
def _abstract_text(article: ET.Element) -> str:
    """Join all AbstractText segments (structured abstracts have several)."""
    parts: list[str] = []
    for ab in article.findall(".//Abstract/AbstractText"):
        label = ab.get("Label")
        text = "".join(ab.itertext()).strip()
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts)


def _parse_one(art: ET.Element) -> dict:
    """Extract pmid/title/abstract/journal/pubtypes from one article element.

    Handles both PubmedArticle (journal) and PubmedBookArticle (book chapter);
    for a book the container title falls back to BookTitle. Book chapters are
    kept — they are real L2 hits and must be recorded before RB-2 screens them.
    """
    pmid = art.findtext(".//PMID") or ""
    title_el = art.find(".//ArticleTitle")
    title = "".join(title_el.itertext()).strip() if title_el is not None else ""
    if not title:  # book articles sometimes only carry BookTitle
        title = art.findtext(".//BookTitle") or ""
    abstract = _abstract_text(art)
    journal = art.findtext(".//Journal/Title") or art.findtext(".//BookTitle") or ""
    pubtypes = ";".join(
        (pt.text or "").strip()
        for pt in art.findall(".//PublicationType")
        if (pt.text or "").strip()
    )
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "pubtypes": pubtypes,
    }


def parse_efetch(xml_bytes: bytes) -> list[dict]:
    """Parse an efetch PubmedArticleSet into per-record dicts.

    Pure function (no network): tests feed it a fixed XML blob. Captures both
    journal articles (PubmedArticle) and book chapters (PubmedBookArticle) so
    the record count matches the esearch hit count (audit trail).
    """
    root = ET.fromstring(xml_bytes)
    return [
        _parse_one(art)
        for art in root.findall(".//PubmedArticle")
        + root.findall(".//PubmedBookArticle")
    ]


def _batched(seq: list[str], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def efetch_records(pmids: list[str], *, sleep=time.sleep) -> list[dict]:
    """Fetch title+abstract for a list of PMIDs, batching efetch calls."""
    out: list[dict] = []
    for batch in _batched(pmids, EFETCH_BATCH):
        xml = _get_xml(
            PUBMED_EFETCH,
            {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"},
        )
        out.extend(parse_efetch(xml))
        sleep(PUBMED_DELAY)
    return out


# --- Raw-response caching (mirrors evidence_mapping's query_log pattern) ---
def _records_raw_path(food_key: str) -> Path:
    return QUERY_LOG_DIR / f"pubmed_{_slug(food_key)}_L2_records.json"


def collect_l2_records(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    *,
    save_raw: bool = True,
    reuse_cache: bool = True,
    sleep=time.sleep,
) -> tuple[pd.DataFrame, list[str]]:
    """Fetch L2 PMIDs + abstracts for every queryable target food.

    Returns (records_df, skipped). One row per (food, pmid). ``skipped`` =
    composite labels that have no single-food query. Cache-first: if a food's
    records JSON already exists it is read back instead of re-hitting NCBI, so
    re-runs are idempotent and stay within the rate limit.
    """
    if save_raw:
        QUERY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    tgt = target_foods(claims, sources)

    rows: list[dict] = []
    skipped: list[str] = []
    for _, t in tgt.iterrows():
        food = t["food_key"]
        if not is_queryable(food):
            skipped.append(food)
            continue

        cache = _records_raw_path(food)
        if reuse_cache and cache.exists():
            recs = pd.read_json(cache, orient="records").to_dict("records")
        else:
            query = pubmed_query(food, "L2")
            pmids, _ = esearch_pmids(query)
            sleep(PUBMED_DELAY)
            recs = efetch_records(pmids, sleep=sleep)
            if save_raw:
                pd.DataFrame(recs).to_json(
                    cache, orient="records", force_ascii=False, indent=2
                )

        for r in recs:
            rows.append(
                {
                    "food_key": food,
                    "scope": t["scope"],
                    "n_sources": int(t["n_sources"]),
                    "pmid": str(r.get("pmid", "")),
                    "title": r.get("title", ""),
                    "abstract": r.get("abstract", ""),
                    "journal": r.get("journal", ""),
                    "pubtypes": r.get("pubtypes", ""),
                }
            )

    return pd.DataFrame(rows), skipped


def main() -> None:
    claims, sources = load_claims(), load_sources()
    df, skipped = collect_l2_records(claims, sources)
    df.to_csv(L2_RECORDS_CSV, index=False)
    print(
        f"wrote {len(df)} L2 records for {df['food_key'].nunique()} foods "
        f"→ {L2_RECORDS_CSV}"
    )
    if skipped:
        print(f"skipped {len(skipped)} composite labels: {skipped}")


if __name__ == "__main__":
    main()

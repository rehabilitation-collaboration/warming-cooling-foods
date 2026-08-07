"""Axis B evidence mapping: how much each food is studied in a thermal context.

For every food that reached the Axis A belief threshold (n_sources ≥ 2), this
module queries three bibliographic APIs for study counts and writes them to
``pubmed_counts.csv`` (the scatter-plot y-axis data for Phase 3):

- **PubMed E-utilities** (main axis): exact ``[tiab]`` / ``[pt]`` field queries,
  built by ``food_query_terms.pubmed_query``. Three layers per food —
  L1 (food total), L2 (food × effect terms = the claimed-context count), and
  L3 (L2 restricted to RCTs). Counted via ``esearch?rettype=count``.
- **OpenAlex** (auxiliary): a *full-text* keyword co-occurrence count. Its
  ``search=`` matches title+abstract+**full text**, so the magnitude is not
  comparable to PubMed's ``[tiab]`` count (ginger: PubMed L2 ≈ 43 vs OpenAlex
  ≈ 3k). It is recorded in a separate column as a robustness check on relative
  attention, NOT summed with PubMed. OpenAlex has no RCT filter, so only an
  L2-equivalent count is taken. (Verified against docs + live API 2026-08-06.)
- **CiNii Research** (Japanese literature): a food-total count queried with the
  Japanese food name (``food_ja``), so it reflects L1-style volume in the
  Japanese corpus. The docs list ``appid`` as required; in practice the endpoint
  answered without one (2026-08-06), so we pass ``CINII_APPID`` when the env var
  is set and fall back to an unauthenticated request otherwise.

All raw API responses are saved under ``data/query_log/`` for audit
(García-Hernández 2023 style). Network calls go through the single ``_get_json``
primitive so tests can monkeypatch it and run fully offline.
"""

from __future__ import annotations

import json
import os
import time

import pandas as pd
import requests

from .claim_mapping import _add_food_key, aggregate_axis_a, load_claims, load_sources
from .definitions import PUBMED_COUNTS_CSV, QUERY_LOG_DIR
from .food_query_terms import EFFECT_TERMS, food_terms, is_queryable, pubmed_query

# --- Endpoints -----------------------------------------------------------
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
OPENALEX_WORKS = "https://api.openalex.org/works"
CINII_OPENSEARCH = "https://cir.nii.ac.jp/opensearch/all"

CONTACT_EMAIL = "rehabilitation.collaboration@gmail.com"
USER_AGENT = (
    "warming-cooling-foods-research/1.0 (bibliometric study; "
    f"contact: {CONTACT_EMAIL})"
)
REQUEST_TIMEOUT = 30  # seconds
PUBMED_DELAY = 0.34   # keep under NCBI's 3 req/s ceiling (no API key)

# n_sources thresholds. core = independent belief established (≥3);
# sensitivity = 2; single = 1. Foods seen by a single source were originally
# left unqueried, which restricted the belief-breadth range the correlation is
# computed over (peer review #7). They are now queried too, so the analysis can
# span every queryable food; ``scope`` keeps the tiers separable.
CORE_MIN_SOURCES = 3
SCOPE_MIN_SOURCES = 2
SINGLE_MIN_SOURCES = 1


def _get_json(url: str, params: dict) -> dict:
    """Single network primitive (monkeypatched in tests) returning parsed JSON."""
    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


# --- Count parsers (pure; also used to read counts back from cached JSON) --
def _parse_pubmed(data: dict) -> int:
    return int(data["esearchresult"]["count"])


def _parse_openalex(data: dict) -> int:
    return int(data["meta"]["count"])


def _parse_cinii(data: dict) -> int:
    return int(data["opensearch:totalResults"])


def pubmed_count(query: str) -> tuple[int, dict]:
    """Total PubMed hits for a query via esearch count mode."""
    data = _get_json(
        PUBMED_ESEARCH,
        {"db": "pubmed", "term": query, "retmode": "json", "rettype": "count"},
    )
    return _parse_pubmed(data), data


def openalex_count(query: str) -> tuple[int, dict]:
    """Total OpenAlex works matching a full-text keyword query (meta.count)."""
    data = _get_json(
        OPENALEX_WORKS,
        {"search": query, "per_page": 1, "select": "id", "mailto": CONTACT_EMAIL},
    )
    return _parse_openalex(data), data


def cinii_count(query: str, appid: str | None = None) -> tuple[int, dict]:
    """Total CiNii Research hits (opensearch:totalResults) for a Japanese term."""
    params = {"q": query, "count": 1, "format": "json"}
    if appid:
        params["appid"] = appid
    data = _get_json(CINII_OPENSEARCH, params)
    return _parse_cinii(data), data


# --- Query building ------------------------------------------------------
def _or_group(terms: list[str]) -> str:
    """Join terms as an OpenAlex OR-group, quoting multiword phrases."""
    parts = [f'"{t}"' if " " in t else t for t in terms]
    inner = " OR ".join(parts)
    return f"({inner})" if len(parts) > 1 else inner


def openalex_query(food_en: str, *, with_mesh: bool = False) -> str:
    """Build the OpenAlex ``search=`` string: food terms AND effect terms.

    PubMed field tags ([tiab]/[pt]) are not valid here, so we re-express the
    L2 concept as a boolean full-text search (OpenAlex has no RCT filter).
    """
    foods = _or_group(food_terms(food_en, with_mesh=with_mesh))
    effects = _or_group(list(EFFECT_TERMS))
    return f"{foods} AND {effects}"


def representative_food_ja(claims: pd.DataFrame) -> dict[str, str]:
    """Pick one Japanese name per food_key for CiNii queries.

    Many foods carry spelling variants across coders (e.g. にんじん/ニンジン/人参).
    We choose the term coders used most often, breaking ties by sorted order, so
    the CiNii query is deterministic and reproducible from the coded data.
    """
    df = _add_food_key(claims).copy()
    df["food_ja"] = df["food_ja"].fillna("").astype(str).str.strip()
    df = df[df["food_ja"] != ""]
    out: dict[str, str] = {}
    for key, grp in df.groupby("food_key"):
        counts = grp["food_ja"].value_counts()
        top = counts.max()
        out[key] = sorted(counts[counts == top].index)[0]
    return out


def _scope_of(n_sources: int) -> str:
    """Belief-breadth tier for a food: core (≥3) / sensitivity (2) / single (1)."""
    if n_sources >= CORE_MIN_SOURCES:
        return "core"
    if n_sources >= SCOPE_MIN_SOURCES:
        return "sensitivity"
    return "single"


def target_foods(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    *,
    min_sources: int = SINGLE_MIN_SOURCES,
) -> pd.DataFrame:
    """Foods to query for Axis B, tagged with their belief-breadth scope.

    Defaults to every food with at least one source, so Axis B spans the whole
    coded universe; pass ``min_sources=SCOPE_MIN_SOURCES`` to reproduce the
    original core+sensitivity selection.
    """
    a2 = aggregate_axis_a(claims, sources, max_tier=2)
    tgt = a2.loc[a2["n_sources"] >= min_sources, ["food_key", "n_sources"]].copy()
    tgt["scope"] = tgt["n_sources"].apply(_scope_of)
    return tgt.reset_index(drop=True)


def _slug(name: str) -> str:
    """Filesystem-safe token for a food key (for query_log filenames)."""
    return "".join(c if c.isalnum() else "_" for c in name)


def _raw_path(api: str, food_key: str, layer: str):
    return QUERY_LOG_DIR / f"{api}_{_slug(food_key)}_{layer}.json"


def _save_raw(api: str, food_key: str, layer: str, data: dict) -> None:
    _raw_path(api, food_key, layer).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _cached_count(api: str, food_key: str, layer: str, parse) -> int | None:
    """Read a count back from a saved query_log JSON, or None if absent/unreadable.

    Lets a re-run reuse already-fetched counts instead of re-hitting the APIs —
    both for idempotence and to avoid re-spending OpenAlex's small daily quota.
    """
    path = _raw_path(api, food_key, layer)
    if not path.exists():
        return None
    try:
        return parse(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, KeyError, OSError):
        return None


def collect_counts(
    claims: pd.DataFrame,
    sources: pd.DataFrame,
    *,
    appid: str | None = None,
    with_mesh: bool = False,
    save_raw: bool = True,
    reuse_cache: bool = True,
    sleep=time.sleep,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Query the three APIs for every target food; return (df, skipped, aux_missing).

    Emits one row per (food, PubMed layer). OpenAlex's keyword count sits on the
    L2 row (its closest analogue); CiNii's food-total sits on the L1 row.

    - **PubMed is the main axis and is required**: a PubMed error aborts the run
      (we do not want a silently incomplete y-axis).
    - **OpenAlex and CiNii are auxiliary**: their per-food failures (e.g. an
      OpenAlex 429 daily-quota exhaustion) are tolerated — the count is left
      blank and the food is recorded in ``aux_missing`` rather than killing the
      run and discarding the PubMed data already gathered.
    - When ``reuse_cache`` and a query_log JSON already exists, its count is read
      back instead of re-hitting the API (idempotent re-runs; conserves quota).

    ``skipped`` = composite labels; ``aux_missing`` = foods whose OpenAlex or
    CiNii count could not be obtained.
    """
    if save_raw:
        QUERY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ja_map = representative_food_ja(claims)
    tgt = target_foods(claims, sources)

    rows: list[dict] = []
    skipped: list[str] = []
    aux_missing: list[str] = []
    for _, t in tgt.iterrows():
        food, n_src, scope = t["food_key"], int(t["n_sources"]), t["scope"]
        if not is_queryable(food):
            skipped.append(food)
            continue

        # PubMed (required, main axis) — cache-first, then live.
        pubmed: dict[str, tuple[int, str]] = {}
        for layer in ("L1", "L2", "L3"):
            q = pubmed_query(food, layer, with_mesh=with_mesh)
            cached = _cached_count("pubmed", food, layer, _parse_pubmed) if reuse_cache else None
            if cached is not None:
                pubmed[layer] = (cached, q)
                continue
            n, raw = pubmed_count(q)
            if save_raw:
                _save_raw("pubmed", food, layer, raw)
            pubmed[layer] = (n, q)
            sleep(PUBMED_DELAY)

        # OpenAlex (auxiliary, L2-equivalent full-text) — tolerate failures.
        oa_q = openalex_query(food, with_mesh=with_mesh)
        oa_n: int | str = _cached_count("openalex", food, "L2", _parse_openalex) if reuse_cache else None
        if oa_n is None:
            try:
                oa_n, oa_raw = openalex_count(oa_q)
                if save_raw:
                    _save_raw("openalex", food, "L2", oa_raw)
            except (requests.RequestException, ValueError, KeyError):
                oa_n = ""
                aux_missing.append(f"openalex:{food}")

        # CiNii (auxiliary, Japanese food-total) — tolerate failures.
        food_ja = ja_map.get(food, "")
        ci_n: int | str = ""
        ci_q = food_ja
        if food_ja:
            ci_n = _cached_count("cinii", food, "L1", _parse_cinii) if reuse_cache else None
            if ci_n is None:
                try:
                    ci_n, ci_raw = cinii_count(ci_q, appid)
                    if save_raw:
                        _save_raw("cinii", food, "L1", ci_raw)
                except (requests.RequestException, ValueError, KeyError):
                    ci_n = ""
                    aux_missing.append(f"cinii:{food}")

        for layer in ("L1", "L2", "L3"):
            n, q = pubmed[layer]
            rows.append(
                {
                    "food_key": food,
                    "food_ja": food_ja,
                    "scope": scope,
                    "n_sources": n_src,
                    "layer": layer,
                    "n_pubmed": n,
                    "n_openalex": oa_n if layer == "L2" else "",
                    "n_cinii": ci_n if layer == "L1" else "",
                    "pubmed_query": q,
                    "openalex_query": oa_q if layer == "L2" else "",
                    "cinii_query": ci_q if layer == "L1" else "",
                }
            )

    return pd.DataFrame(rows), skipped, aux_missing


def main() -> None:
    claims, sources = load_claims(), load_sources()
    appid = os.environ.get("CINII_APPID")
    df, skipped, aux_missing = collect_counts(claims, sources, appid=appid)
    df.to_csv(PUBMED_COUNTS_CSV, index=False)
    print(f"wrote {len(df)} rows for {df['food_key'].nunique()} foods → {PUBMED_COUNTS_CSV}")
    if skipped:
        print(f"skipped {len(skipped)} composite labels: {skipped}")
    if aux_missing:
        print(f"auxiliary count missing for {len(aux_missing)}: {aux_missing}")


if __name__ == "__main__":
    main()

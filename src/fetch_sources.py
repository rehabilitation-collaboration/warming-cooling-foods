"""Fetch the fixed Axis A source frame over HTTP for hand-coding.

Reads ``data/sources.csv`` (the frozen frame), fetches each source page once,
saves the raw HTML under ``data/sources_raw/`` (git-ignored, not redistributed),
and records provenance (HTTP status, final URL, byte size, access date) into
``data/sources_raw/fetch_log.csv``.

Politeness: a descriptive research User-Agent, a per-request timeout, and a
delay between requests. robots.txt is honoured per the coding protocol:
``robots_ok=yes`` fetches directly; ``robots_ok=unknown`` first checks the
target page responds 2xx before fetching (Kracie: robots 404 → allowed;
karada_onkatsu: robots unreachable → verify page reachability first).

No parsing/coding here — coding is done by hand into ``claims.csv``.
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import date

import requests

from .definitions import SOURCES_CSV, SOURCES_RAW_DIR

# Descriptive UA so operators can identify the (single, one-shot) research fetch.
USER_AGENT = (
    "warming-cooling-foods-research/1.0 (bibliometric study; "
    "one-time fetch for hand-coding; contact: rehabilitation.collaboration@gmail.com)"
)
REQUEST_TIMEOUT = 30  # seconds
DELAY_BETWEEN_REQUESTS = 3.0  # seconds, be polite to small sites


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.8"})
    return s


def _reachable(session: requests.Session, url: str) -> bool:
    """For robots_ok=unknown: confirm the page responds 2xx before fetching."""
    try:
        r = session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if r.status_code >= 400:  # some servers reject HEAD; retry with GET
            r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, stream=True)
            r.close()
        return 200 <= r.status_code < 300
    except requests.RequestException:
        return False


def fetch_all() -> list[dict]:
    SOURCES_RAW_DIR.mkdir(parents=True, exist_ok=True)
    accessed = date.today().isoformat()
    session = _session()
    log: list[dict] = []

    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        sources = list(csv.DictReader(f))

    for i, src in enumerate(sources):
        sid, url, robots_ok = src["source_id"], src["url"], src["robots_ok"]
        entry = {
            "source_id": sid,
            "url": url,
            "robots_ok": robots_ok,
            "accessed": accessed,
            "status": "",
            "final_url": "",
            "bytes": 0,
            "note": "",
        }

        if robots_ok == "unknown" and not _reachable(session, url):
            entry["note"] = "skipped: page not reachable (robots unknown, reachability check failed)"
            log.append(entry)
            print(f"[{sid}] SKIP — not reachable")
            continue

        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            entry["status"] = str(r.status_code)
            entry["final_url"] = r.url
            content = r.content
            entry["bytes"] = len(content)
            if 200 <= r.status_code < 300 and content:
                out = SOURCES_RAW_DIR / f"{sid}.html"
                out.write_bytes(content)
                print(f"[{sid}] {r.status_code} — {len(content)} bytes → {out.name}")
            else:
                entry["note"] = f"not saved (status {r.status_code})"
                print(f"[{sid}] {r.status_code} — not saved")
        except requests.RequestException as exc:
            entry["status"] = "ERROR"
            entry["note"] = f"{type(exc).__name__}: {exc}"
            print(f"[{sid}] ERROR — {exc}")

        log.append(entry)
        if i < len(sources) - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    log_path = SOURCES_RAW_DIR / "fetch_log.csv"
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["source_id", "url", "robots_ok", "accessed", "status", "final_url", "bytes", "note"],
        )
        w.writeheader()
        w.writerows(log)
    print(f"\nWrote fetch log → {log_path}")
    return log


if __name__ == "__main__":
    result = fetch_all()
    ok = sum(1 for e in result if e["status"].startswith("2"))
    print(f"\n{ok}/{len(result)} fetched OK", file=sys.stderr)

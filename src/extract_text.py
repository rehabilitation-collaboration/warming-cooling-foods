"""Extract readable body text from the fetched raw HTML for hand-coding.

For each ``data/sources_raw/<sid>.html`` produced by ``fetch_sources.py``, strips
scripts/nav/boilerplate and writes ``data/sources_raw/<sid>.txt`` (also
git-ignored). The plain text is what the coder reads to fill ``claims.csv`` — it
is not parsed for directions programmatically (per the coding protocol, coding
is by hand to avoid context misattribution).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .definitions import SOURCES_RAW_DIR

DROP_TAGS = ["script", "style", "nav", "header", "footer", "noscript", "svg", "form"]


def extract_one(html: str) -> tuple[str, str]:
    """Return (title, body_text) from a raw HTML string."""
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    for tag in soup(DROP_TAGS):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    return title, "\n".join(lines)


def extract_all() -> None:
    for html_path in sorted(SOURCES_RAW_DIR.glob("*.html")):
        sid = html_path.stem
        html = html_path.read_text(encoding="utf-8", errors="replace")
        title, body = extract_one(html)
        out = SOURCES_RAW_DIR / f"{sid}.txt"
        out.write_text(f"# {sid}\n# TITLE: {title}\n\n{body}\n", encoding="utf-8")
        print(f"[{sid}] {len(body)} chars → {out.name}")


if __name__ == "__main__":
    extract_all()

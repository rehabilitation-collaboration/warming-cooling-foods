"""Walk every number in manuscript.md and ask the pipeline whether it still holds.

Why this exists. The manuscript's stale values have been enumerated by line
number three times, and each time the list missed values that sat outside it: the
unit-test count, the whole of Table 1, and a framing paragraph that no number
could fix. A line-number list records what was found last time, not what is
wrong, and writing one stops the search. So this walks every numeric token in the
manuscript instead. A number passes only by matching something the pipeline
printed or something a published ledger holds; everything else is listed.

What it does not do. It cannot tell a stale statistic from a citation's sample
size — `n = 10` in a reference to Mansour et al. is not ours to recompute. Rather
than guess, it reports unmatched tokens with their line and lets the author read
them, and it flags the ones that look like identifiers (years, PMIDs, versions)
as hints only. Nothing is dropped silently: the counts printed at the end add up
to every token found, which is the property that makes the report auditable.

Run it as `python3 -m src.verify_manuscript`. It writes nothing.
"""

from __future__ import annotations

import io
import re
from contextlib import redirect_stdout

import pandas as pd

from . import verify_stats
from .build_screening import RULINGS_CSV, exclusion_breakdown
from .claim_mapping import aggregate_axis_a, load_claims, load_sources
from .definitions import PROJECT_ROOT, PUBMED_COUNTS_CSV, TIER_ORG
from .screening import SCREENING_CSV, cohen_kappa

MANUSCRIPT = PROJECT_ROOT / "manuscript.md"

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Tokens that look like identifiers rather than measurements. These are still
# reported — the flag is a reading aid, not a filter.
YEAR = re.compile(r"^(19|20)\d{2}$")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
IDENTIFIER_CONTEXT = re.compile(
    r"PMID|doi:|https?://|ORCID|Claude|Python|pandas|scipy|numpy|statsmodels"
    r"|matplotlib|weasyprint|commit|CFR|45 CFR"
)


def _strip(token: str) -> str:
    return token.replace(",", "")


def _renderings(token: str) -> set[str]:
    """Every way the manuscript could legitimately print this pipeline value."""
    plain = _strip(token)
    out = {plain}
    try:
        value = float(plain)
    except ValueError:
        return out
    if value.is_integer():
        out.add(str(int(value)))
        out.add(f"{int(value):,}")
    for places in range(5):
        out.add(f"{value:.{places}f}")
    return out


def _tokens(text: str) -> list[str]:
    return NUMBER.findall(text)


COUNTS_COLUMNS = ("n_pubmed", "n_openalex", "n_cinii", "L2_screened", "n_sources")


def counts_reference(counts: pd.DataFrame) -> set[str]:
    """The per-food quantities Tables 4 and 5 print, as printable strings.

    Fails loudly on a renamed column. Skipping one would shrink the reference set
    and turn current values into "unmatched" — noise in the exact report whose
    worth depends on every unmatched token deserving a read.
    """
    missing = [column for column in COUNTS_COLUMNS if column not in counts.columns]
    if missing:
        raise ValueError(f"pubmed counts frame has no column(s) {missing}")
    values: set[str] = set()
    for column in COUNTS_COLUMNS:
        for value in counts[column].dropna().unique():
            values |= _renderings(str(value))
    return values


def pipeline_values() -> set[str]:
    """Everything the pipeline can currently vouch for, as printable strings.

    Three sources, and each is the published one for its quantities: the analysis
    statistics as `verify_stats` prints them, the per-food counts the tables are
    built from, and the screening ledger's own tallies. Axis A composition is
    recomputed here because `verify_stats` prints the frame size but not the
    coding totals that Table 1's first rows report — the gap that let those rows
    go stale unnoticed.
    """
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        verify_stats.main()
    values: set[str] = set()
    for token in _tokens(buffer.getvalue()):
        values |= _renderings(token)

    values |= counts_reference(pd.read_csv(PUBMED_COUNTS_CSV))

    claims, sources = load_claims(), load_sources()
    axis_a = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    for value in (len(claims), claims["food_en"].nunique(), len(axis_a)):
        values |= _renderings(str(value))
    for direction, n in axis_a["direction"].value_counts().items():
        values |= _renderings(str(n))

    ledger = pd.read_csv(SCREENING_CSV)
    recon = pd.DataFrame(
        {
            "label_c1": ledger["coder1"],
            "label_c2": ledger["coder2"],
            "status": (ledger["coder1"] == ledger["coder2"]).map(
                {True: "agree", False: "disagree"}
            ),
        }
    )
    kappa = cohen_kappa(recon)
    for value in (
        len(ledger),
        int(ledger["adjudicated"].sum()),
        int((recon["status"] == "disagree").sum()),
        len(pd.read_csv(RULINGS_CSV)),
        kappa["kappa"],
        kappa["po"],
        100 * kappa["po"],
        int((ledger["final_label"] == "include").sum()),
        int((ledger["final_label"] == "exclude").sum()),
    ):
        values |= _renderings(str(value))
    breakdown = exclusion_breakdown(ledger)
    for column in breakdown.columns:
        if pd.api.types.is_numeric_dtype(breakdown[column]):
            for value in breakdown[column]:
                values |= _renderings(str(value))
    return values


def audit(manuscript_text: str, values: set[str]) -> pd.DataFrame:
    """One row per numeric token the manuscript prints, matched or not."""
    rows = []
    section = ""
    for line_no, line in enumerate(manuscript_text.split("\n"), start=1):
        if line.startswith("#"):
            section = line.lstrip("# ").strip()
        # An access date is one identifier, not three numbers, so its month and
        # day are marked with it rather than surfacing as unexplained tokens.
        dates = [m.span() for m in DATE.finditer(line)]
        for match in NUMBER.finditer(line):
            plain = _strip(match.group())
            in_date = any(start <= match.start() < end for start, end in dates)
            rows.append(
                {
                    "line": line_no,
                    "section": section,
                    "token": match.group(),
                    "matched": plain in values,
                    "looks_like_id": in_date
                    or bool(YEAR.match(plain))
                    or bool(IDENTIFIER_CONTEXT.search(line)),
                    "context": line.strip()[:110],
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    report = audit(text, pipeline_values())
    unmatched = report[~report["matched"]]

    print("=" * 78)
    print(f"manuscript numeric tokens: {len(report)}   "
          f"matched by the pipeline: {int(report['matched'].sum())}   "
          f"unmatched: {len(unmatched)}")
    print("  (matched + unmatched exhausts the tokens found — nothing is skipped)")
    print("=" * 78)

    statistics = unmatched[~unmatched["looks_like_id"]]
    identifiers = unmatched[unmatched["looks_like_id"]]
    print(f"\n[Unmatched, and not identifier-shaped] {len(statistics)} tokens — read every one")
    for section, group in statistics.groupby("section", sort=False):
        print(f"\n  ## {section}")
        for line_no, rows in group.groupby("line", sort=True):
            print(f"    L{line_no:<4} {', '.join(rows['token'])}")
            print(f"          {rows['context'].iloc[0]}")

    print(f"\n[Unmatched, identifier-shaped] {len(identifiers)} tokens — years, PMIDs, "
          f"versions, cited sample sizes. Listed so the count adds up, not because "
          f"they are wrong.")
    for section, group in identifiers.groupby("section", sort=False):
        print(f"    ## {section}: {len(group)} tokens on lines "
              f"{sorted(set(group['line']))[:12]}")


if __name__ == "__main__":
    main()

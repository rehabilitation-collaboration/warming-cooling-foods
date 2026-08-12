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

from . import manuscript_tables, verify_stats
from .analysis import _read_counts, prepare_scatter_data
from .build_screening import RULINGS_CSV, exclusion_breakdown
from .claim_mapping import aggregate_axis_a, load_claims, load_sources
from .definitions import PROJECT_ROOT, PUBMED_COUNTS_CSV, TIER_ORG
from .gap_models import prepare_model_frame
from .screening import SCREENING_CSV, cohen_kappa

MANUSCRIPT = PROJECT_ROOT / "manuscript.md"

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Tokens that look like identifiers rather than measurements. These are still
# reported — the flag is a reading aid, not a filter.
YEAR = re.compile(r"^(19|20)\d{2}$")

# Spans whose digits name something rather than measure it. Matched as spans,
# not as a line-wide keyword test: the line-wide version let one word disarm a
# whole line. "The analysis plan commits to reporting" matched `commit` and
# demoted all 61 numbers in Table 3's footnote; "Claude Sonnet 4.6" did the
# same to the screening-reliability paragraph, which carries κ and the
# adjudication counts; and `Python 3.14.3` hid the unit-test count in two
# places. Every one of those lines held stale values.
IDENTIFIER_SPAN = re.compile(
    r"\d{4}-\d{2}-\d{2}"                                    # access date
    r"|PMID[:\s]*\d+"
    r"|doi:\S+|https?://\S+"
    r"|ORCID[^\d]{0,4}[\d-]+X?"
    r"|Claude [A-Za-z]+ [\d.]+"                             # coder model
    r"|(?:Python|pandas|scipy|numpy|statsmodels|matplotlib|weasyprint) [\d.]+"
    r"|45 CFR [\d.()a-z]+"
    r"|\b(?=[0-9a-f]{7,40}\b)[0-9a-f]*[a-f][0-9a-f]*\b"     # commit anchor
)

# Sections whose numbers belong to other people's papers — page ranges, volume
# numbers, the sample size of a cited trial. Nothing here is ours to recompute.
CITATION_SECTIONS = {"References"}


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


def pipeline_inputs() -> dict:
    """The frames both reports read, loaded once so they cannot disagree.

    The cell checks need the same claims, model frame and screening ledger the
    token walk builds its value set from. Loading them separately would let one
    report pass on a value the other calls stale.
    """
    claims, sources, counts = load_claims(), load_sources(), _read_counts()
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
    return {
        "claims": claims,
        "sources": sources,
        "counts": counts,
        "frame": prepare_model_frame(prepare_scatter_data(claims, sources, counts)),
        "ledger": ledger,
        "kappa": cohen_kappa(recon),
    }


def pipeline_values(inputs: dict) -> set[str]:
    """Everything the pipeline can currently vouch for, as printable strings.

    Three sources, and each is the published one for its quantities: the analysis
    statistics as `verify_stats` prints them, the per-food counts the tables are
    built from, and the screening ledger's own tallies. Axis A composition is
    recomputed here because `verify_stats` prints the frame size but not the
    coding totals that Table 1's first rows report — the gap that let those rows
    go stale unnoticed.

    Membership in this set is a weak test on its own: it says a number occurs
    somewhere in the pipeline, not that it belongs where the manuscript prints
    it. `manuscript_tables` supplies the positional test for every table cell.
    """
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        verify_stats.main()
    values: set[str] = set()
    for token in _tokens(buffer.getvalue()):
        values |= _renderings(token)

    values |= counts_reference(pd.read_csv(PUBMED_COUNTS_CSV))

    claims, sources = inputs["claims"], inputs["sources"]
    axis_a = aggregate_axis_a(claims, sources, max_tier=TIER_ORG)
    for value in (len(claims), claims["food_en"].nunique(), len(axis_a)):
        values |= _renderings(str(value))
    for direction, n in axis_a["direction"].value_counts().items():
        values |= _renderings(str(n))

    ledger, kappa = inputs["ledger"], inputs["kappa"]
    for value in (
        len(ledger),
        int(ledger["adjudicated"].sum()),
        int((ledger["coder1"] != ledger["coder2"]).sum()),
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
        spans = [m.span() for m in IDENTIFIER_SPAN.finditer(line)]
        for match in NUMBER.finditer(line):
            plain = _strip(match.group())
            in_identifier = any(s <= match.start() < e for s, e in spans)
            rows.append(
                {
                    "line": line_no,
                    "section": section,
                    "token": match.group(),
                    "matched": plain in values,
                    "looks_like_id": in_identifier
                    or bool(YEAR.match(plain))
                    or section in CITATION_SECTIONS,
                    "context": line.strip()[:110],
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    inputs = pipeline_inputs()
    report = audit(text, pipeline_values(inputs))
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

    manuscript_tables.report(text, inputs["claims"], inputs["sources"], inputs["frame"],
                             inputs["counts"], inputs["ledger"], inputs["kappa"])


if __name__ == "__main__":
    main()

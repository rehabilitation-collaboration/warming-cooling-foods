"""Check each table cell in the manuscript against the quantity it reports.

Why this sits beside ``verify_manuscript``'s token walk. That walk asks whether
a number occurs *anywhere* in the pipeline's output. For prose that is the right
question — a rate quoted mid-sentence has no fixed address. For a table cell it
is the wrong one, because the cell's address is exactly what makes it checkable.
``| carrot | warming | 8 |`` passed the walk because some other food has eight
sources; carrot has nine. Four of Table 1's six rows were stale under the same
reading, and so were the two smallest exclusion shares. A cell is compared here
to the quantity its own row and column name, so a value that is right for a
different food, or a different stratum, still fails.

Scope, stated rather than implied. Tables 1, 2, 4 and 5 are checked, plus the
exclusion-reason breakdown. Table 3's statistics and the three prose footnotes
are not: their values are refits and derived quantities that ``verify_stats``
prints in full, and every one of those rows already surfaces in the token walk
as unmatched. Rows this module does not know about are reported as unchecked
rather than passed over, so the gap is visible in the output.
"""

from __future__ import annotations

import re

import pandas as pd

from .build_screening import exclusion_breakdown
from .claim_mapping import CONTESTED, aggregate_axis_a
from .definitions import COOL, NEUTRAL, TIER_INDIVIDUAL, TIER_ORG, WARM
from .evidence_mapping import CORE_MIN_SOURCES
from .screening import INCLUDE, l2_screened

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

TABLE1 = "### Table 1. Sample composition"
TABLE2 = "### Table 2. Effect of construct screening on the research measure"
TABLE4 = ("### Table 4. The 24 core foods for which the search retrieved no "
          "on-construct study, by lay-source coverage")
TABLE5 = "### Table 5. Flagship foods: total volume, keyword hits, and on-construct studies"
# Table 2's second table has no `###` heading of its own, and the count in its
# caption is one of the values under test, so it is found by prefix.
EXCLUSIONS = "**Exclusion reasons"

# The foods Table 5 profiles, in the order it presents them. Fixed in the
# manuscript rather than computed, so the check is that each row's numbers are
# current — not that this is the set a rule would select.
FLAGSHIP = ("chicken", "green tea", "white sugar", "coffee", "ginger",
            "chili pepper", "milk")


def _cells(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def _plain(cell: str) -> str:
    """A cell with the markdown emphasis and the leading em dash removed.

    Backticks stay: they are what separates the `animal` exclusion row from the
    `livestock-heat` one, whose label also contains the word "animal".
    """
    return cell.replace("**", "").replace("—", "").strip()


def _numbers(cell: str) -> list[float]:
    return [float(token.replace(",", "")) for token in NUMBER.findall(cell)]


def _agrees(cell: str, expected: list[float]) -> bool:
    """Does the cell print ``expected``, at the precision the cell itself uses?

    Comparing at the printed precision is what lets 98.62% be written as 98.6
    while 0.8068 written as 0.806 still fails: the second is a rounding the
    manuscript could not have produced from the current value.
    """
    printed = _numbers(cell)
    if len(printed) != len(expected):
        return False
    places = [len(t.split(".")[1]) if "." in t else 0 for t in NUMBER.findall(cell)]
    return all(round(want, p) == round(got, p)
               for got, want, p in zip(printed, expected, places))


def table_body(text: str, heading: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """The header cells and the numbered body rows of one markdown table.

    Fails loudly when the heading is absent: a renamed table would otherwise
    silently check nothing, which is the failure mode this module exists to
    remove.
    """
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines)
                  if line.strip().startswith(heading)), None)
    if start is None:
        raise ValueError(f"manuscript has no table headed {heading!r}")

    header: list[str] | None = None
    body: list[tuple[int, list[str]]] = []
    for offset, line in enumerate(lines[start + 1:], start=start + 2):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if body:
                break
            continue
        cells = _cells(stripped)
        if set("".join(cells)) <= set("-: "):
            continue
        if header is None:
            header = [_plain(cell) for cell in cells]
            continue
        body.append((offset, cells))
    if header is None:
        raise ValueError(f"table {heading!r} has no header row")
    return header, body


def check_table(text: str, heading: str, expected: dict[str, dict[str, object]],
                *, exact: bool = False) -> list[dict]:
    """Compare every cell the manuscript prints against ``expected``.

    ``expected`` is keyed by the row label and then by column name. Prose labels
    are matched on a substring, since they carry counts and section references
    that move; food rows are matched with ``exact``, because ``onion`` is a
    substring of ``green onion`` and the two are different foods. A cell the
    manuscript leaves as an em dash is not reported — the manuscript is entitled
    to omit a quantity — but a row carrying numbers the module knows nothing
    about is, as ``unchecked``.
    """
    header, body = table_body(text, heading)
    findings: list[dict] = []
    matched_keys: set[str] = set()

    for line_no, cells in body:
        label = _plain(cells[0])
        if exact:
            keys = [label] if label in expected else []
        else:
            keys = [key for key in expected if key in label]
        if len(keys) > 1:
            raise ValueError(f"row {label!r} matches several expectations: {keys}")
        if not keys:
            if any(_numbers(cell) for cell in cells[1:]):
                findings.append({"line": line_no, "table": heading, "row": label,
                                 "column": "—", "printed": " | ".join(cells[1:])[:60],
                                 "expected": "unchecked — no expectation defined"})
            continue
        key = keys[0]
        matched_keys.add(key)
        for column, want in expected[key].items():
            if column not in header:
                raise ValueError(f"table {heading!r} has no column {column!r}")
            cell = cells[header.index(column)]
            if not _numbers(cell):
                continue
            wanted = list(want) if isinstance(want, (list, tuple)) else [float(want)]
            if not _agrees(cell, wanted):
                findings.append({
                    "line": line_no, "table": heading, "row": label, "column": column,
                    "printed": " / ".join(NUMBER.findall(cell)),
                    "expected": " / ".join(_format(value) for value in wanted),
                })

    for key in expected:
        if key not in matched_keys:
            findings.append({"line": 0, "table": heading, "row": key, "column": "—",
                             "printed": "row absent", "expected": "a row reporting it"})
    return findings


def _format(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.4g}"


def table1_expected(claims: pd.DataFrame, sources: pd.DataFrame,
                    frame: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Sample composition: coded foods, the Tier-1 subset, and the breadth strata."""
    expected: dict[str, dict[str, object]] = {
        "All coded": {"n foods": len(aggregate_axis_a(claims, sources,
                                                      max_tier=TIER_INDIVIDUAL))},
        "Tier-1 covered": {"n foods": len(aggregate_axis_a(claims, sources,
                                                           max_tier=TIER_ORG))},
    }
    strata = (
        ("Analysed", frame),
        ("core", frame[frame["n_sources"] >= CORE_MIN_SOURCES]),
        ("two-source", frame[frame["n_sources"] == 2]),
        ("single-source", frame[frame["n_sources"] == 1]),
    )
    for label, sub in strata:
        counts = sub["direction"].value_counts()
        expected[label] = {
            "n foods": len(sub),
            "Warming": int(counts.get(WARM, 0)),
            "Cooling": int(counts.get(COOL, 0)),
            # The column pools the two non-majority outcomes, as its name says.
            "Contested/neutral": (int(counts.get(CONTESTED, 0))
                                  + int(counts.get(NEUTRAL, 0))),
        }
    return expected


def table2_expected(ledger: pd.DataFrame, frame: pd.DataFrame, counts: pd.DataFrame,
                    kappa: dict) -> dict[str, dict[str, object]]:
    """Screening totals that follow from the published ledger alone.

    Deliberately partial. How the adjudications split across passes is recorded
    in the rulings file's batch labels, and the sweep and third-pass tallies are
    accounts of work done on a particular day rather than quantities a rerun
    recomputes. Those rows are left unchecked here and reported as such, rather
    than given an expectation that would look authoritative without being one.
    """
    include = ledger[ledger["final_label"] == INCLUDE]
    reviews = int(include["sublabels"].fillna("").astype(str)
                  .str.split(";").apply(lambda s: "review" in {x.strip() for x in s}).sum())
    return {
        "L2 records screened": {"Value": len(ledger)},
        "Foods with": {"Value": [int((counts["l2_raw"] > 0).sum()),
                                 int((counts["l2_raw"] == 0).sum())]},
        "Cohen's κ": {"Quantity": len(ledger), "Value": kappa["kappa"]},
        "Observed agreement": {"Value": 100 * kappa["po"]},
        "Coder divergences": {"Value": int((ledger["coder1"] != ledger["coder2"]).sum())},
        "Records adjudicated": {"Value": int(ledger["adjudicated"].sum())},
        "Records surviving": {"Value": len(include)},
        "primary reports / reviews": {"Value": [len(include) - reviews, reviews]},
        "Raw L2": {"Value": [
            int(frame["l2_raw"].sum()),
            int(frame["l2_screened"].sum()),
            100 * (1 - frame["l2_screened"].sum() / frame["l2_raw"].sum()),
        ]},
    }


def exclusions_expected(text: str, ledger: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Each exclusion row's count and share, summed over the reasons it names.

    The printed label drives the expectation rather than the other way round,
    because the manuscript folds the smallest reasons into one `other` row.
    Reading the codes out of the label keeps that row checked instead of
    reported as unknown, and keeps the check honest if the fold changes. Both of
    the smallest shares here were stale and passed the token walk.
    """
    breakdown = exclusion_breakdown(ledger).set_index("reason")
    total = int(breakdown["n"].sum())
    expected: dict[str, dict[str, object]] = {}
    for _, cells in table_body(text, EXCLUSIONS)[1]:
        named = [reason for reason in breakdown.index if f"`{reason}`" in cells[0]]
        if not named:
            continue
        counted = int(breakdown.loc[named, "n"].sum())
        expected[_plain(cells[0])] = {"n": counted, "Share": 100 * counted / total}
    return expected


def table4_expected(frame: pd.DataFrame) -> dict[str, dict[str, object]]:
    """The core-belief foods with no screened study, one expectation per food."""
    void = frame[(frame["n_sources"] >= CORE_MIN_SOURCES) & (frame["l2_screened"] == 0)]
    return {
        row["food_key"]: {
            "Sources": int(row["n_sources"]),
            "Total literature (L1)": int(row["l1"]),
            "Raw L2": int(row["l2_raw"]),
            "On-construct (L2′)": 0,
        }
        for _, row in void.iterrows()
    }


def table5_expected(frame: pd.DataFrame, ledger: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Flagship rows, including the narrowest reading the last column reports."""
    narrow = l2_screened(ledger, exclude_sublabels=("constituent", "review"))
    indexed = frame.set_index("food_key")
    expected: dict[str, dict[str, object]] = {}
    for food in FLAGSHIP:
        row = indexed.loc[food]
        expected[food] = {
            "Sources": int(row["n_sources"]),
            "L1 total": int(row["l1"]),
            "Raw L2": int(row["l2_raw"]),
            "L2′": int(row["l2_screened"]),
            "Whole-food primary": int(narrow.get(food, 0)),
            "L2′/L1": 100 * row["l2_screened"] / row["l1"],
        }
    return expected


def table4_ordering(text: str, frame: pd.DataFrame) -> list[str]:
    """Complaints about Table 4's row set and ordering, which its title asserts."""
    _, body = table_body(text, TABLE4)
    printed = [_plain(cells[0]) for _, cells in body]
    void = frame[(frame["n_sources"] >= CORE_MIN_SOURCES) & (frame["l2_screened"] == 0)]
    problems = []

    missing = sorted(set(void["food_key"]) - set(printed))
    extra = sorted(set(printed) - set(void["food_key"]))
    if missing:
        problems.append(f"core-zero foods absent from the table: {missing}")
    if extra:
        problems.append(f"rows that are no longer core-zero: {extra}")

    breadth = frame.set_index("food_key")["n_sources"]
    listed = [breadth[food] for food in printed if food in breadth.index]
    if listed != sorted(listed, reverse=True):
        problems.append("rows are not in descending order of lay-source coverage, "
                        "which the table's title claims")
    if len(printed) != len(void):
        problems.append(f"the title says {len(printed)} foods; the frame has {len(void)}")
    return problems


def report(text: str, claims: pd.DataFrame, sources: pd.DataFrame, frame: pd.DataFrame,
           counts: pd.DataFrame, ledger: pd.DataFrame, kappa: dict) -> None:
    """Print every cell-level disagreement, and the checks that found none."""
    checks = (
        (TABLE1, table1_expected(claims, sources, frame), False),
        (TABLE2, table2_expected(ledger, frame, counts, kappa), False),
        (EXCLUSIONS, exclusions_expected(text, ledger), False),
        (TABLE4, table4_expected(frame), True),
        (TABLE5, table5_expected(frame, ledger), True),
    )
    findings: list[dict] = []
    for heading, expected, exact in checks:
        findings.extend(check_table(text, heading, expected, exact=exact))

    print(f"\n[Anchored table cells] {len(findings)} disagreements — each cell "
          f"compared to the quantity its own row and column name")
    if not findings:
        print("  every checked cell matches")
    for finding in findings:
        where = f"L{finding['line']}" if finding["line"] else "  —"
        print(f"  {where:<6} {finding['row'][:26]:<26} {finding['column'][:22]:<22} "
              f"printed {finding['printed'][:26]:<26} expected {finding['expected']}")

    for problem in table4_ordering(text, frame):
        print(f"  Table 4 structure: {problem}")

    print("  not checked here (the token walk reports these): Table 3's statistics "
          "and every prose footnote")

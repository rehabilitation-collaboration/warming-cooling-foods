"""Check the manuscript's load-bearing sentences against the quantity each names.

Why this sits beside ``manuscript_tables``. That module gave table cells an
address — a cell is compared to the quantity its own row and column name — and
the token walk in ``verify_manuscript`` gives every other number the weaker test
of occurring somewhere in the pipeline's output. Prose fell in the gap. Five of
the six numeric errors an external review found in revision were prose, and all
five passed the walk because the number they printed was real somewhere else:
53 core foods was printed as 51, which is the zero rate 51.3%; 44 queried foods
with no hit as 37, which is white sugar's screened count; 50 events as 49 and
96 baseline foods as 97, both of which are counts in the *primary reports only*
refit. A value set cannot tell those apart. A sentence can, because the nouns
around the number say which quantity it is.

So each fact below pins one sentence to one expression over the pipeline. The
locator must match exactly once: a sentence that was reworded, split or deleted
fails loudly rather than quietly checking nothing, which is the failure mode a
list of line numbers has every time it has been written here.

Spelled numerals are checked here and nowhere else, and the reason is measured
rather than assumed. Adding ``one`` … ``twenty`` to the token walk would mark
essentially all of them matched, because every integer from 1 to 20 occurs
somewhere in the pipeline's output — the membership test is vacuous at that
magnitude. It would also bury the walk's real signal: the manuscript prints
roughly 450 spelled numerals, most of them not counting anything ("one of the
two axes", "the first pass"). They are therefore counted and reported as
unchecked unless a fact anchors them, so the gap is visible in the output
instead of being papered over with a matched flag that means nothing.

What is deliberately not checked is listed in ``OUT_OF_SCOPE`` with its reason,
and those sentences are still located, so the scope note cannot go stale while
the text moves under it.
"""

from __future__ import annotations

import functools
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .alt_l1 import load_alt_l1
from .build_screening import exclusion_breakdown
from .claim_directed import INCIDENTAL, attach, load_ledger
from .definitions import PROJECT_ROOT
from .evidence_mapping import CORE_MIN_SOURCES
from .gap_models import cloglog_exact_offset, presence_logit
from .human_audit import (
    READS_CSV as AUDIT_READS_CSV,
    RESULTS_CSV as AUDIT_RESULTS_CSV,
    score_completeness,
    score_precision,
    tier1_claims,
)
from .screening import l2_screened

COLLECTED = re.compile(r"(\d+) tests? collected")


@functools.lru_cache(maxsize=1)
def collected_tests() -> int | None:
    """How many unit tests the suite holds, or None if the collector cannot run.

    The one quantity checked here that does not come from a data frame. The
    manuscript states it twice and it has gone stale twice — once found by a
    reader who counted, once carried unnoticed across two revisions — because
    nothing recomputes a number about the code itself. Collection is used
    rather than a full run: it is under a second, and "all passing" is a claim
    a count cannot settle either way. A collector that will not run is reported
    as unchecked rather than guessed, since a reader of the published
    repository need not have the test runner installed.
    """
    try:
        finished = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=180,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    found = COLLECTED.search(finished.stdout)
    return int(found.group(1)) if found else None

# The range the coverage interval is compounded over: one source to nine, which
# is eight additional sources. Named because the exponent is the whole content
# of the compound-interval check.
COMPOUND_STEPS = 8

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_FRACTIONS = {"half": 0.5, "one-third": 1 / 3, "two-thirds": 2 / 3,
              "three-quarters": 0.75, "four-fifths": 0.8, "one-quarter": 0.25}

# Every spelled form the census counts. Ordinals are included because "a
# fourteenth analysis" is as much a count as "fourteen analyses".
_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
    "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
}

SPELLED = re.compile(
    r"\b(" + "|".join(
        sorted(set(_FRACTIONS) | set(_UNITS) | set(_TENS) | set(_ORDINALS),
               key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)

DIGITS = re.compile(r"\d[\d,]*(?:\.\d+)?")

_NUMERAL_WORD = "(?i:" + "|".join(
    sorted(set(_FRACTIONS) | set(_UNITS) | set(_TENS) | set(_ORDINALS),
           key=len, reverse=True)
) + ")"

# A capture group for a quantity however the sentence chooses to write it. Facts
# use this rather than a literal word, so that rewriting "nine" as "9" — or as
# the wrong word — is reported as the value disagreement it is, instead of
# breaking the locator and being reported as a sentence that moved.
QUANTITY = (r"(\d[\d,]*(?:\.\d+)?"
            rf"|{_NUMERAL_WORD}(?:[ -](?:hundred|thousand|and|{_NUMERAL_WORD}))*)")


def word_value(phrase: str) -> float | None:
    """The number a spelled phrase names, or None if it names none.

    Handles the compound forms the manuscript actually uses — "twenty-four",
    "one hundred and three" — rather than a general English numeral grammar,
    which nothing here would exercise.
    """
    key = phrase.strip().lower()
    if key in _FRACTIONS:
        return _FRACTIONS[key]
    total = current = 0.0
    seen = False
    for word in key.replace("-", " ").split():
        if word == "and":
            continue
        if word in _UNITS:
            current += _UNITS[word]
        elif word in _TENS:
            current += _TENS[word]
        elif word in _ORDINALS:
            current += _ORDINALS[word]
        elif word == "hundred":
            current = (current or 1) * 100
        elif word == "thousand":
            total += (current or 1) * 1000
            current = 0.0
        else:
            return None
        seen = True
    return total + current if seen else None


def token_value(token: str) -> float | None:
    """The number a printed token names, whether it is written in digits or words."""
    stripped = token.replace(",", "").strip()
    try:
        return float(stripped)
    except ValueError:
        return word_value(token)


@dataclass(frozen=True)
class Fact:
    """One sentence, the quantities it prints, and where they come from.

    ``expected`` returns one value per capture group, in order. A fact with no
    ``expected`` is one the pipeline cannot recompute; it is still located, so
    that the stated reason stays attached to text that exists.
    """

    key: str
    pattern: str
    expected: Callable[[dict], list[float]] | None = None
    why: str = ""
    tol: float | None = None


def as_printed(value: float, places: int = 3) -> float:
    """A quantity as the manuscript prints it, for the values derived from others.

    The paper computes its derived quantities from the figures it has printed,
    not from the full-precision ones behind them, and that is the right
    convention: it is what a reader can reproduce from the page. Compounding
    the coverage interval illustrates the difference — the printed 1.289 raised
    to the eighth is 7.62, the unrounded 1.28886 is 7.61, and only the first is
    checkable by anyone but us. Nothing is lost by checking at that convention,
    because the printed figures are themselves anchored to the fit below.
    """
    return round(value, places)


def _core(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["n_sources"] >= CORE_MIN_SOURCES]


def _reason_count(ledger: pd.DataFrame, *reasons: str) -> int:
    """Records excluded under the named reason codes, folded as the tables fold them.

    Uses the published breakdown rather than a second split of the reason
    column: the column carries free-text rationale after the code, and a
    parallel normalisation here would be a second definition able to drift from
    the one every other count uses.
    """
    breakdown = exclusion_breakdown(ledger).set_index("reason")
    return int(breakdown.loc[[r for r in reasons if r in breakdown.index], "n"].sum())


def _food(frame: pd.DataFrame, food: str, column: str) -> float:
    row = frame.loc[frame["food_key"] == food]
    if len(row) != 1:
        raise ValueError(f"frame holds {len(row)} rows for {food!r}")
    return float(row.iloc[0][column])


DECLARED_UNPLANNED = re.compile(
    r"(\w+) analyses are reported that were \*\*not\*\* in the fixed plan")


def _declared_unplanned(text: str) -> float | None:
    """How many unplanned analyses the Methods declares.

    The pipeline cannot compute this one: it counts choices the analysis plan
    did not fix, not anything in the data. So the Methods sentence is read as
    the source and every other statement of the count is checked against it.
    That is the failure that actually occurred — the count moved to seventeen
    when the complementary log-log pair was added, and the Limitations sentence
    kept the old word through a full review round. A wrong number here is still
    wrong everywhere; what this forecloses is the three places disagreeing.

    None when the declaration is absent, which the facts report as unchecked
    rather than as agreement. Losing it from the real manuscript is caught by
    ``unplanned_declaration``'s locator, so raising here would add no guarantee
    while breaking every caller that checks a fragment of the text.
    """
    match = DECLARED_UNPLANNED.search(text)
    return None if match is None else word_value(match.group(1))


def context(text: str, inputs: dict) -> dict:
    """Everything the facts below compute against, built once.

    ``text`` is taken so that a fact can key off the manuscript's own wording
    where the quantity depends on it; the values themselves all come from the
    pipeline.
    """
    frame, ledger = inputs["frame"], inputs["ledger"]
    fit = presence_logit(frame)
    unadjusted = presence_logit(frame, adjust_l1=False)

    cd_ledger = load_ledger()
    with_sublabels = attach(ledger, cd_ledger) if cd_ledger is not None else ledger
    claim_directed = l2_screened(with_sublabels, exclude_sublabels=(INCIDENTAL,))

    alt = load_alt_l1()
    # The §10 audit's own figures. Both counts are checked, the one the
    # procedure fixed in advance and the one adjudication leaves, because the
    # manuscript reports both and a check on only one would let the other drift.
    audit_rows = tier1_claims()
    precision = score_precision(pd.read_csv(AUDIT_RESULTS_CSV, dtype=str))
    completeness = score_completeness(
        pd.read_csv(AUDIT_READS_CSV, dtype=str).fillna(""), audit_rows)
    built = {
        "audit_rows": audit_rows,
        "audit_precision": precision,
        "audit_completeness": completeness,
        "frame": frame,
        "ledger": ledger,
        "counts": inputs["counts"],
        "fit": fit,
        "unadjusted": unadjusted,
        "coverage": fit["terms"]["n_sources"],
        "volume": fit["terms"]["log_l1"],
        "no_constituent": l2_screened(ledger, exclude_sublabels=("constituent",)),
        "no_review": l2_screened(ledger, exclude_sublabels=("review",)),
        "whole_food": l2_screened(ledger, exclude_sublabels=("constituent", "review")),
        "claim_directed": claim_directed,
        "alt_l1": None if alt is None else alt.set_index("food_key"),
        "cloglog_exact": cloglog_exact_offset(frame),
        "unplanned_declared": _declared_unplanned(text),
    }
    # The §8 refit is the one expensive quantity here and several facts read it,
    # so it is fitted once rather than once per capture group.
    built["claim_directed_fit"] = _refit(built, claim_directed)
    return built


def _screened_total(frame: pd.DataFrame) -> int:
    return int(frame["l2_screened"].sum())


def _narrowed(ctx: dict, series: pd.Series) -> tuple[int, int, float]:
    """Studies, foods carrying one, and the zero rate, within the primary frame."""
    frame = ctx["frame"]
    kept = frame["food_key"].map(series).fillna(0)
    return (int(kept.sum()), int((kept > 0).sum()),
            100 * float((kept == 0).mean()))


def _audit_recall(ctx: dict, key: str) -> list[float]:
    """The two sources' recall as numerator and denominator, in manuscript order.

    The longer source first, as the Methods introduces them. Fails loudly on a
    source the audit does not hold, rather than checking one pair twice.
    """
    scored = ctx["audit_completeness"]
    out: list[float] = []
    for source in ("basefood", "macaroni"):
        if source not in scored:
            raise ValueError(f"the audit holds no end-to-end read of {source!r}")
        stats = scored[source]
        denominator = (stats["read_by_human"] if key == "recall"
                       else stats["adjudicated_n"])
        out += [round(stats[key] * denominator), denominator]
    return out


def _refit(ctx: dict, series: pd.Series) -> dict:
    """The primary model refitted on a narrower reading of "an on-construct study".

    Mirrors what ``verify_stats`` does for its definition sensitivity: a
    narrower definition removes records, so a food's count can fall to zero,
    but no food enters or leaves the frame.
    """
    frame = ctx["frame"].copy()
    frame["l2_screened"] = frame["food_key"].map(series).fillna(0).astype(int)
    frame["has_study"] = (frame["l2_screened"] > 0).astype(int)
    return presence_logit(frame)


FACTS: tuple[Fact, ...] = (
    # ---- the primary estimates, and everything derived from them -------------
    Fact(
        "primary_estimates",
        r"\*\*odds ratio \(OR\) (\d+\.\d+) per unit of log\(L1 \+ 1\), 95% confidence "
        r"interval \(CI\) (\d+\.\d+)[–-](\d+\.\d+), p < 0\.001\*\* — and lay-source "
        r"coverage did not: \*\*OR (\d+\.\d+) per additional source, 95% CI "
        r"(\d+\.\d+)[–-](\d+\.\d+), p = (\d+\.\d+)\*\*; model pseudo-R² = (\d+\.\d+)",
        lambda c: [c["volume"]["or"], c["volume"]["or_lo"], c["volume"]["or_hi"],
                   c["coverage"]["or"], c["coverage"]["or_lo"], c["coverage"]["or_hi"],
                   c["coverage"]["p"], c["fit"]["pseudo_r2"]],
    ),
    Fact(
        "unadjusted_estimate",
        r"\(OR (\d+\.\d+), 95% CI (\d+\.\d+)[–-](\d+\.\d+), p = (\d+\.\d+); "
        r"pseudo-R² = (\d+\.\d+)\)",
        lambda c: [c["unadjusted"]["terms"]["n_sources"]["or"],
                   c["unadjusted"]["terms"]["n_sources"]["or_lo"],
                   c["unadjusted"]["terms"]["n_sources"]["or_hi"],
                   c["unadjusted"]["terms"]["n_sources"]["p"],
                   c["unadjusted"]["pseudo_r2"]],
    ),
    Fact(
        "compound_abstract",
        r"Compounded over one-to-nine sources the interval spans (\d+\.\d+)[–-](\d+\.\d+)-fold",
        lambda c: [as_printed(c["coverage"]["or_lo"]) ** COMPOUND_STEPS,
                   as_printed(c["coverage"]["or_hi"]) ** COMPOUND_STEPS],
    ),
    Fact(
        "compound_results",
        r"its interval spans an odds ratio from (\d+\.\d+) to (\d+\.\d+)",
        lambda c: [as_printed(c["coverage"]["or_lo"]) ** COMPOUND_STEPS,
                   as_printed(c["coverage"]["or_hi"]) ** COMPOUND_STEPS],
    ),
    Fact(
        "compound_limitations",
        r"compounds across the observed one-to-nine-source range to an odds ratio "
        r"between (\d+\.\d+) and (\d+\.\d+)",
        lambda c: [as_printed(c["coverage"]["or_lo"]) ** COMPOUND_STEPS,
                   as_printed(c["coverage"]["or_hi"]) ** COMPOUND_STEPS],
    ),
    Fact(
        "odds_change_discussion",
        r"an additional lay source corresponds to an estimated (\d+\.\d+)% change in the odds",
        lambda c: [100 * (c["coverage"]["or"] - 1)],
    ),
    Fact(
        "events_results",
        r"the same model with the same (\d+) events",
        lambda c: [c["fit"]["n_with_study"]],
    ),
    Fact(
        "events_methods",
        r"because (\d+) events over (\d+) foods is few enough that one food could carry",
        lambda c: [c["fit"]["n_with_study"], c["fit"]["n"]],
    ),
    Fact(
        "events_diagnostics",
        r"with (\d+) events over two predictors the model is used to describe",
        lambda c: [c["fit"]["n_with_study"]],
    ),
    Fact(
        "events_limitations",
        r"(\d+) of (\d+) foods have any on-construct study",
        lambda c: [c["fit"]["n_with_study"], c["fit"]["n"]],
    ),
    # ---- sample composition --------------------------------------------------
    Fact(
        "frame_strata",
        r"(\d+) queryable foods carry at least one source attribution: (\d+) reach "
        r"three or more sources \(the \*core\* set\), (\d+) have two, and (\d+) have one",
        lambda c: [len(c["frame"]), len(_core(c["frame"])),
                   int((c["frame"]["n_sources"] == 2).sum()),
                   int((c["frame"]["n_sources"] == 1).sum())],
    ),
    Fact(
        "core_directions",
        r"Among the (\d+) core foods, (\d+) are lay-classified warming, (\d+) cooling",
        lambda c: [len(_core(c["frame"])),
                   int((_core(c["frame"])["direction"] == "warm").sum()),
                   int((_core(c["frame"])["direction"] == "cool").sum())],
    ),
    Fact(
        "zero_rate_headline",
        r"Of the (\d+) foods, \*\*(\d+) \((\d+\.\d)%\) have no on-construct study\*\*, "
        r"and among the (\d+) core foods the rate is (\d+)/(\d+) \((\d+\.\d)%\)",
        lambda c: [
            len(c["frame"]),
            int((c["frame"]["l2_screened"] == 0).sum()),
            100 * float((c["frame"]["l2_screened"] == 0).mean()),
            len(_core(c["frame"])),
            int((_core(c["frame"])["l2_screened"] == 0).sum()),
            len(_core(c["frame"])),
            100 * float((_core(c["frame"])["l2_screened"] == 0).mean()),
        ],
    ),
    Fact(
        "baseline_foods_figure2",
        r"\*\*marker area encodes how many foods share a position\*\* — (\d+) of (\d+) "
        r"foods sit on the baseline",
        lambda c: [int((c["frame"]["l2_screened"] == 0).sum()), len(c["frame"])],
    ),
    Fact(
        "baseline_foods_results",
        r"where the (\d+) zero-study foods sit on the baseline",
        lambda c: [int((c["frame"]["l2_screened"] == 0).sum())],
    ),
    # ---- screening totals ----------------------------------------------------
    Fact(
        "screened_universe",
        r"screened all \*\*([\d,]+) records across the (\d+) of the (\d+) queried foods "
        r"that returned at least one hit\*\*",
        lambda c: [len(c["ledger"]),
                   int((c["counts"]["l2_raw"] > 0).sum()),
                   len(c["counts"])],
    ),
    Fact(
        # One of the five prose values an external review found stale: 44 was
        # printed as 37, which is white sugar's screened count, so the token
        # walk matched it.
        "queried_with_no_hit",
        r"The (\d+) queried foods with zero L2 hits have L2′ = 0 by construction",
        lambda c: [int((c["counts"]["l2_raw"] == 0).sum())],
    ),
    Fact(
        "screening_reduction",
        r"Across the (\d+) foods in the primary frame, ([\d,]+) raw L2 hits reduced to "
        r"\*\*(\d+) on-construct studies\*\* — a (\d+\.\d)% reduction",
        lambda c: [len(c["frame"]), int(c["frame"]["l2_raw"].sum()),
                   _screened_total(c["frame"]),
                   100 * (1 - _screened_total(c["frame"]) / c["frame"]["l2_raw"].sum())],
    ),
    Fact(
        "exclusion_prose",
        r"Well over half of the ([\d,]+) exclusions are animal research: ([\d,]+) records "
        r"excluded as `animal` and a further (\d+) as `livestock-heat`, together (\d+\.\d)%",
        lambda c: [
            int((c["ledger"]["final_label"] != "include").sum()),
            _reason_count(c["ledger"], "animal"),
            _reason_count(c["ledger"], "livestock-heat"),
            100 * _reason_count(c["ledger"], "animal", "livestock-heat")
            / int((c["ledger"]["final_label"] != "include").sum()),
        ],
    ),
    Fact(
        "animal_share_discussion",
        r"— ([\d,]+) of ([\d,]+) — are studies of animals rather than of people eating food",
        lambda c: [_reason_count(c["ledger"], "animal", "livestock-heat"),
                   len(c["ledger"])],
    ),
    # ---- per-food sentences, the class a value set cannot address -------------
    Fact(
        "chicken_screening",
        rf"\*\*Chicken fell from (\d+) raw hits to {QUANTITY}\*\*, a "
        r"(\d+\.\d)% reduction, with (\d+) of the (\d+) excluded as animal research",
        lambda c: [
            _food(c["frame"], "chicken", "l2_raw"),
            _food(c["frame"], "chicken", "l2_screened"),
            100 * (1 - _food(c["frame"], "chicken", "l2_screened")
                   / _food(c["frame"], "chicken", "l2_raw")),
            _reason_count(c["ledger"][c["ledger"]["food_key"] == "chicken"],
                          "animal", "livestock-heat"),
            _food(c["frame"], "chicken", "l2_raw"),
        ],
    ),
    Fact(
        "chicken_volume",
        rf"PubMed holds ([\d,]+) records on it and (\d+) in the thermal keyword "
        rf"context; {QUANTITY} of those "  r"(\d+) survive screening",
        lambda c: [_food(c["frame"], "chicken", "l1"),
                   _food(c["frame"], "chicken", "l2_raw"),
                   _food(c["frame"], "chicken", "l2_screened"),
                   _food(c["frame"], "chicken", "l2_raw")],
    ),
    Fact(
        "lamb",
        r"Lamb shows the pattern in its pure form \((\d+) → (\d+)\)",
        lambda c: [_food(c["frame"], "lamb", "l2_raw"),
                   _food(c["frame"], "lamb", "l2_screened")],
    ),
    Fact(
        "ginger_screening",
        r"Ginger illustrates the opposite failure: (\d+) raw hits reduced to (\d+)",
        lambda c: [_food(c["frame"], "ginger", "l2_raw"),
                   _food(c["frame"], "ginger", "l2_screened")],
    ),
    Fact(
        # "primary reports on ginger itself" is both narrowings at once, which is
        # what Table 5's food-form column reports and what the printed nine is.
        # Before this check the sentence named only the constituent rule, whose
        # value is eleven, while printing the number for both.
        "ginger_flagship",
        rf"\*\*Ginger\*\* \(warming, {QUANTITY} sources\) has "  r"(\d+)"
        rf", {QUANTITY} of them primary reports on ginger itself rather than on an "
        r"isolated constituent",
        lambda c: [_food(c["frame"], "ginger", "n_sources"),
                   _food(c["frame"], "ginger", "l2_screened"),
                   c["whole_food"].get("ginger", 0)],
    ),
    Fact(
        "core_zero_headline",
        rf"{QUANTITY} of the "  r"(\d+)"  r" core foods have no on-construct study",
        lambda c: [int((_core(c["frame"])["l2_screened"] == 0).sum()),
                   len(_core(c["frame"]))],
    ),
    Fact(
        "most_covered_zero_foods",
        rf"carrot at all {QUANTITY} Tier-1 sources, cucumber and pumpkin at "
        rf"{QUANTITY}; burdock, eggplant, mango, and miso at {QUANTITY}",
        lambda c: [_food(c["frame"], "carrot", "n_sources"),
                   _food(c["frame"], "cucumber", "n_sources"),
                   _food(c["frame"], "burdock", "n_sources")],
    ),
    Fact(
        "literature_extremes",
        r"hojicha has (\d+) PubMed records and cucumber ([\d,]+)",
        lambda c: [_food(c["frame"], "hojicha", "l1"),
                   _food(c["frame"], "cucumber", "l1")],
    ),
    Fact(
        "small_literature_trio",
        r"burdock, daikon, and hojicha are widely presented as warming or cooling and "
        r"carry a few hundred PubMed records or fewer \((\d+), (\d+) and (\d+) respectively\)",
        lambda c: [_food(c["frame"], "burdock", "l1"),
                   _food(c["frame"], "daikon", "l1"),
                   _food(c["frame"], "hojicha", "l1")],
    ),
    # ---- the narrowing refits ------------------------------------------------
    Fact(
        "constituent_narrowing",
        rf"{QUANTITY} of the "  r"(\d+)"  rf" studies examine a food's principal dietary "
        r"constituent rather than the food itself; dropping them leaves (\d+) studies "
        r"across (\d+) foods, a zero rate of (\d+\.\d)%",
        lambda c: [
            _screened_total(c["frame"]) - _narrowed(c, c["no_constituent"])[0],
            _screened_total(c["frame"]),
            *_narrowed(c, c["no_constituent"]),
        ],
    ),
    Fact(
        "review_narrowing",
        r"Dropping instead the (\d+) reviews and meta-analyses leaves (\d+) studies "
        r"across (\d+) foods \((\d+\.\d)% zero\)",
        lambda c: [
            _screened_total(c["frame"]) - _narrowed(c, c["no_review"])[0],
            *_narrowed(c, c["no_review"]),
        ],
    ),
    Fact(
        "both_narrowing",
        rf"Dropping both — the two classes overlap in {QUANTITY} records — leaves "
        r"(\d+) studies across (\d+) foods \((\d+\.\d)% zero\)",
        # Records dropped by both rules at once, by inclusion–exclusion over the
        # two narrowings: |A ∩ B| = |A| + |B| − |A ∪ B|.
        lambda c: [
            _screened_total(c["frame"])
            - _narrowed(c, c["no_constituent"])[0]
            - _narrowed(c, c["no_review"])[0]
            + _narrowed(c, c["whole_food"])[0],
            *_narrowed(c, c["whole_food"]),
        ],
    ),
    Fact(
        "narrowing_flagships",
        r"with green tea falling from (\d+) studies to (\d+) and coffee from (\d+) to (\d+)",
        lambda c: [_food(c["frame"], "green tea", "l2_screened"),
                   c["whole_food"].get("green tea", 0),
                   _food(c["frame"], "coffee", "l2_screened"),
                   c["whole_food"].get("coffee", 0)],
    ),
    Fact(
        "claim_directed_refit",
        r"Dropping the (\d+) of the (\d+) included records whose own framing was not the "
        r"food's thermal effect — the `incidental` sub-label of protocol §8 — leaves "
        r"(\d+), of which (\d+) fall in the primary frame, spread across (\d+) of its "
        r"(\d+) foods, for a zero rate of (\d+\.\d)%, coverage OR (\d+\.\d+) "
        r"\(95% CI (\d+\.\d+)[–-](\d+\.\d+), p = (\d+\.\d+)\) and volume OR (\d+\.\d+) "
        r"\((\d+\.\d+)[–-](\d+\.\d+), p < 0\.001\)",
        lambda c: [
            int((c["ledger"]["final_label"] == "include").sum())
            - int(c["claim_directed"].sum()),
            int((c["ledger"]["final_label"] == "include").sum()),
            int(c["claim_directed"].sum()),
            _narrowed(c, c["claim_directed"])[0],
            _narrowed(c, c["claim_directed"])[1],
            len(c["frame"]),
            _narrowed(c, c["claim_directed"])[2],
            c["claim_directed_fit"]["terms"]["n_sources"]["or"],
            c["claim_directed_fit"]["terms"]["n_sources"]["or_lo"],
            c["claim_directed_fit"]["terms"]["n_sources"]["or_hi"],
            c["claim_directed_fit"]["terms"]["n_sources"]["p"],
            c["claim_directed_fit"]["terms"]["log_l1"]["or"],
            c["claim_directed_fit"]["terms"]["log_l1"]["or_lo"],
            c["claim_directed_fit"]["terms"]["log_l1"]["or_hi"],
        ],
    ),
    Fact(
        "claim_directed_flagships",
        r"Salt shows the largest fall, from (\d+) studies to (\d+)",
        lambda c: [_food(c["frame"], "salt", "l2_screened"),
                   c["claim_directed"].get("salt", 0)],
    ),
    Fact(
        "claim_directed_ginger",
        r"with all (\d+) of its studies claim-directed",
        lambda c: [c["claim_directed"].get("ginger", 0)],
    ),
    Fact(
        "coverage_estimate_shift",
        r"the coverage estimate moves by (\d+\.\d+) and its interval still contains one",
        lambda c: [abs(as_printed(c["claim_directed_fit"]["terms"]["n_sources"]["or"])
                       - as_printed(c["coverage"]["or"]))],
    ),
    # ---- the alternative L1 definitions --------------------------------------
    Fact(
        "alt_l1_totals",
        r"cuts the frame's total from ([\d,]+) to ([\d,]+) — chicken from ([\d,]+) to "
        r"([\d,]+), salt from ([\d,]+) to ([\d,]+) — and restricting it to the MeSH "
        r"nutrition tree cuts it to ([\d,]+)",
        lambda c: [
            int(c["frame"]["l1"].sum()),
            int(c["alt_l1"].loc[c["frame"]["food_key"], "L1_humans"].sum()),
            _food(c["frame"], "chicken", "l1"),
            int(c["alt_l1"].loc["chicken", "L1_humans"]),
            _food(c["frame"], "salt", "l1"),
            int(c["alt_l1"].loc["salt", "L1_humans"]),
            int(c["alt_l1"].loc[c["frame"]["food_key"], "L1_nutrition"].sum()),
        ],
    ),
    # ---- the one quantity that is about the code, not the data ---------------
    Fact(
        "unit_tests_methods",
        r"the pipeline is covered by (\d+) unit tests \(all passing\)",
        lambda c: [collected_tests()],
    ),
    Fact(
        "unit_tests_acknowledgments",
        r"Python 3\.\d+\.\d+; unit tests n = (\d+), all passing",
        lambda c: [collected_tests()],
    ),
    # ---- the human audit of §10 ----------------------------------------------
    Fact(
        "audit_sample",
        r"a simple random sample of \*\*(\d+) of the (\d+) Tier-1 claim rows\*\*",
        lambda c: [c["audit_precision"]["n_sampled"], len(c["audit_rows"])],
    ),
    Fact(
        "audit_precision_result",
        rf"Of \*\*(\d+) claim rows drawn at random\*\*, \*\*(\d+) are supported\*\*",
        lambda c: [c["audit_precision"]["n_sampled"],
                   c["audit_precision"]["n_supported"]],
    ),
    Fact(
        "audit_recall_as_specified",
        r"recall is \*\*(\d+)/(\d+)\*\* for the longer source and \*\*(\d+)/(\d+)\*\* "
        r"for the other",
        lambda c: _audit_recall(c, "recall"),
    ),
    Fact(
        "audit_recall_adjudicated",
        rf"leaving \*\*(\d+)/(\d+)\*\* and \*\*(\d+)/(\d+)\*\*, and "
        rf"\*\*{QUANTITY} genuine gaps\*\*",
        lambda c: _audit_recall(c, "adjudicated_recall") + [
            sum(len(s["misses"]) for s in c["audit_completeness"].values())],
    ),
    # ---- quantities written as fractions -------------------------------------
    Fact(
        "two_thirds_abstract",
        rf"For {QUANTITY} of these foods, the search retrieved none",
        lambda c: [float((c["frame"]["l2_screened"] == 0).mean())],
        tol=0.05,
    ),
    Fact(
        "alt_l1_fractions",
        rf"which removes {QUANTITY} of chicken's literature and {QUANTITY} of salt's",
        lambda c: [
            1 - int(c["alt_l1"].loc["chicken", "L1_humans"])
            / _food(c["frame"], "chicken", "l1"),
            1 - int(c["alt_l1"].loc["salt", "L1_humans"])
            / _food(c["frame"], "salt", "l1"),
        ],
        tol=0.05,
    ),
    # ---- what L1 spans, and what the exactly-derived offset would cost -------
    Fact(
        "l1_range",
        rf"compresses a range running from {QUANTITY} foods holding no records at all "
        rf"to salt's {QUANTITY} \(hojicha has {QUANTITY}, milk {QUANTITY}\)",
        lambda c: [float((c["frame"]["l1"] == 0).sum()),
                   _food(c["frame"], "salt", "l1"),
                   _food(c["frame"], "hojicha", "l1"),
                   _food(c["frame"], "milk", "l1")],
    ),
    Fact(
        "cloglog_exact_methods",
        rf"so that all {QUANTITY} foods enter one model with a finite exposure: "
        rf"{QUANTITY} hold no records at all, and log L1 does not exist for them\. "
        rf"That substitution is an approximation to the exact form, so the exact form "
        rf"is fitted as well, on the {QUANTITY} foods where log L1 is defined",
        lambda c: [c["cloglog_exact"]["n"] + c["cloglog_exact"]["n_dropped"],
                   c["cloglog_exact"]["n_dropped"],
                   c["cloglog_exact"]["n"]],
    ),
    Fact(
        "cloglog_exact_results",
        rf"on the {QUANTITY} foods for which log L1 exists, leaves coverage at "
        rf"{QUANTITY} \({QUANTITY}[–-]{QUANTITY}, p = {QUANTITY}\) and rejects the "
        rf"offset by the same margin \({QUANTITY} on 1 degree of freedom, "
        rf"p = {QUANTITY}\)",
        lambda c: [c["cloglog_exact"]["n"],
                   c["cloglog_exact"]["offset"]["hr"],
                   c["cloglog_exact"]["offset"]["hr_lo"],
                   c["cloglog_exact"]["offset"]["hr_hi"],
                   c["cloglog_exact"]["offset"]["p"],
                   c["cloglog_exact"]["lr"]["stat"],
                   c["cloglog_exact"]["lr"]["p"]],
    ),
    Fact(
        "cloglog_exact_table3",
        rf"fitted on the {QUANTITY} foods for which it is defined, coverage {QUANTITY} "
        rf"\({QUANTITY}[–-]{QUANTITY}\), p = {QUANTITY} and the same test {QUANTITY} "
        rf"on 1 df, p = {QUANTITY}",
        lambda c: [c["cloglog_exact"]["n"],
                   c["cloglog_exact"]["offset"]["hr"],
                   c["cloglog_exact"]["offset"]["hr_lo"],
                   c["cloglog_exact"]["offset"]["hr_hi"],
                   c["cloglog_exact"]["offset"]["p"],
                   c["cloglog_exact"]["lr"]["stat"],
                   c["cloglog_exact"]["lr"]["p"]],
    ),
    # ---- the count of unplanned analyses, which the paper states three times --
    Fact(
        "unplanned_table3",
        rf"{QUANTITY} analyses were computed outside the fixed plan",
        lambda c: [c["unplanned_declared"]],
    ),
    Fact(
        "unplanned_limitations",
        rf"and {QUANTITY} reported analyses were computed outside it",
        lambda c: [c["unplanned_declared"]],
    ),
)

# Sentences whose numbers the pipeline cannot regenerate. Located but not
# checked, so that the reason stays attached to text that still exists.
OUT_OF_SCOPE: tuple[Fact, ...] = (
    Fact(
        "sweep_work_record",
        r"the author's sweep over all (\d+) agreed includes overturned (\d+)",
        why="an account of work done on one day, not a quantity a rerun recomputes "
            "— the same reason Table 2's sweep row is unchecked",
    ),
    Fact(
        "four_term_recall",
        r"the four-term query had returned \*\*(\d+) of them, a recall of (\d+\.\d)%\*\*",
        why="measured against the 292-study reference set as it stood when the "
            "comparison was run; the current ledger holds a different total, so "
            "recomputing it would answer a different question",
    ),
    Fact(
        "four_term_zero_rate",
        r"cut the core-zero set from (\d+) foods to (\d+) and the overall zero rate "
        r"from (\d+\.\d)% to (\d+\.\d)%",
        why="the before-values belong to the four-term query, which the pipeline no "
            "longer runs",
    ),
    Fact(
        "unplanned_declaration",
        rf"{QUANTITY} analyses are reported that were \*\*not\*\* in the fixed plan",
        why="a count of choices the analysis plan did not fix, which is not a "
            "quantity in the data; this sentence is the source, and the paper's two "
            "other statements of the count are checked against it",
    ),
)


def locate(text: str, fact: Fact) -> re.Match:
    """The one place ``fact`` speaks about, or a loud failure.

    Zero matches means the sentence moved and the check silently stopped
    checking; more than one means the locator is not specific enough to say
    which sentence carries the quantity. Both are defects in this module, and
    both are reported as such rather than skipped.
    """
    found = list(re.finditer(fact.pattern, text))
    if len(found) != 1:
        raise ValueError(
            f"fact {fact.key!r} locates {len(found)} sentences; a fact must locate "
            f"exactly one. Pattern: {fact.pattern[:70]}…"
        )
    return found[0]


def _agrees(printed: str, want: float, tol: float | None) -> bool:
    """Does the printed token name ``want``, at the precision it prints?"""
    got = token_value(printed)
    if got is None:
        return False
    if tol is not None:
        return abs(got - want) <= tol
    places = len(printed.split(".")[1]) if "." in printed else 0
    return round(got, places) == round(want, places)


def check_prose(text: str, inputs: dict, facts: tuple[Fact, ...] = FACTS) -> list[dict]:
    """Every prose quantity that disagrees with the pipeline."""
    ctx = context(text, inputs)
    findings: list[dict] = []
    for fact in facts:
        match = locate(text, fact)
        want = fact.expected(ctx)
        printed = list(match.groups())
        if len(printed) != len(want):
            raise ValueError(
                f"fact {fact.key!r} captures {len(printed)} values but expects "
                f"{len(want)}"
            )
        line = text[:match.start()].count("\n") + 1
        for position, (token, value) in enumerate(zip(printed, want), start=1):
            if value is None:
                # The expression could not be evaluated in this environment.
                # Saying so beats both crashing and passing silently.
                findings.append({"line": line, "fact": fact.key,
                                 "position": position, "printed": token,
                                 "expected": "unchecked — not computable here"})
                continue
            if not _agrees(token, float(value), fact.tol):
                findings.append({
                    "line": line, "fact": fact.key, "position": position,
                    "printed": token,
                    "expected": (f"{float(value):,.4g}" if not float(value).is_integer()
                                 else f"{float(value):,.0f}"),
                })
    return findings


def expected_numbers(text: str, inputs: dict) -> list[float]:
    """Every quantity these facts expect, so the token walk does not re-report them.

    Same reason as in ``manuscript_tables``: a number already checked against
    the sentence that names it should not also appear in the list of tokens
    nobody has vouched for.
    """
    ctx = context(text, inputs)
    out: list[float] = []
    for fact in FACTS:
        locate(text, fact)
        out.extend(float(value) for value in fact.expected(ctx) if value is not None)
    return out


def anchored_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges every fact's captures cover, including the unchecked ones."""
    spans: list[tuple[int, int]] = []
    for fact in FACTS + OUT_OF_SCOPE:
        match = locate(text, fact)
        spans.extend(match.span(group) for group in range(1, len(match.groups()) + 1))
    return spans


def spelled_census(text: str) -> dict:
    """How many spelled numerals the manuscript prints, and how many are anchored.

    Reported rather than folded into the token walk because the walk's test —
    does this number occur somewhere in the pipeline's output — is vacuous for
    them: every integer from 1 to 20 does. Marking them matched would be a
    claim this module cannot support, so the count of unchecked ones is printed
    instead.
    """
    spans = anchored_spans(text)
    inside = lambda start: any(lo <= start < hi for lo, hi in spans)  # noqa: E731

    anchored = 0
    unanchored: dict[str, int] = {}
    section = ""
    offset = 0
    for line in text.split("\n"):
        if line.startswith("#"):
            section = line.lstrip("# ").strip()
        for match in SPELLED.finditer(line):
            if inside(offset + match.start()):
                anchored += 1
            else:
                unanchored[section] = unanchored.get(section, 0) + 1
        offset += len(line) + 1
    return {"anchored": anchored, "unanchored": unanchored,
            "total": anchored + sum(unanchored.values())}


def report(text: str, inputs: dict) -> None:
    """Print every prose disagreement, what is out of scope, and the spelled census."""
    findings = check_prose(text, inputs)
    print(f"\n[Anchored prose] {len(findings)} disagreements — each sentence compared "
          f"to the quantity its own words name")
    if not findings:
        print(f"  every checked value in {len(FACTS)} anchored sentences matches")
    for finding in findings:
        print(f"  L{finding['line']:<5} {finding['fact'][:28]:<28} "
              f"value {finding['position']}: printed {finding['printed']:<12} "
              f"expected {finding['expected']}")

    print(f"  located but not checked ({len(OUT_OF_SCOPE)} sentences):")
    for fact in OUT_OF_SCOPE:
        line = text[:locate(text, fact).start()].count("\n") + 1
        print(f"    L{line:<5} {fact.key:<22} {fact.why}")

    census = spelled_census(text)
    print(f"\n[Spelled numerals] {census['total']} printed   "
          f"anchored above: {census['anchored']}   "
          f"unchecked: {census['total'] - census['anchored']}")
    print("  the token walk cannot vouch for these: every integer from 1 to 20 occurs "
          "somewhere in\n  the pipeline output, so set membership would pass all of "
          "them. Most count nothing\n  (\"one of the two axes\"); the load-bearing ones "
          "are anchored above.")
    for section, count in sorted(census["unanchored"].items(), key=lambda kv: -kv[1])[:8]:
        print(f"    {section[:52]:<52} {count}")

# Protocol §9 adversarial third pass — the prompt the third screener receives

This is the instruction given to every agent that re-reads a batch of *excluded*
records under `screening_protocol.md` §9. It is published for the same reason the
protocols and the other coder prompts are (`screening_coder_prompt.md`,
`ledger_coder_prompt.md`, `screening_claim_directed_coder_prompt.md`): the pass
cannot be reproduced without it. The 2026-08-09 core-zero pass was run under the
same instruction; this file writes it down.

Substitute `{FILES}` (the input → output mapping, one line per file). The pass
runs on `claude-opus-5`, a different tier from coder 1 and the same tier as
coder 2, so that a record's second reading is not by the weaker of the pair.

The batch files are git-ignored: they embed PubMed titles and abstracts, which
are third-party content. They regenerate from `data/l2_records.csv` and
`data/screening.csv` with `python3 -m src.dump_thirdpass_batches`.

---

You are the **third screener** on a bibliometric study of Japanese
warming/cooling food beliefs.

Working directory: `/Users/mizukishirai/claude/analysis/warming-cooling-foods`

## Read the standard first

Read `data/screening_protocol.md` **§2 and §3 in full**. §2 is the include/exclude
decision and §3 holds the boundary rules that decide the hard cases — the vascular
bed, the energy-expenditure carve-out, reviews, isolated constituents, absent
species, missing abstracts. They are the whole task. Do not work from a summary.

You may also read §9, which is the scope you are working under. Nothing in §9
changes a criterion: it decides *which* records get a second reading, not how
they are judged.

## What is already settled, and what you are looking for

Every record in your batch **has already been excluded** by two independent
coders and, in some cases, by an author's ruling on top of them.

Two coders who exclude the same record for the same wrong reason leave no trace
in any agreement statistic. Because a food's analysed outcome is binary — does it
have any qualifying study at all — one such record changes that food's result
outright. You are the check on that, and you are told what the first two coders
were not: **everything in front of you was excluded, and your task is to find the
ones where that was wrong.**

Do not try to be consistent with the existing labels. You cannot see them for a
reason. If §2 and §3 say a record qualifies, say so.

## Your verdict, per record

Exactly one of:

- **`exclude-agreed`** — you read it against §2 and §3 and the exclusion holds.
- **`include-candidate`** — §2's four conditions all hold on the text in front of
  you and no §3 boundary rule excludes it. This is a claim that the record was
  wrongly excluded.
- **`uncertain`** — you cannot settle it from the title, abstract and publication
  types you were given.

**Return `uncertain` whenever you hesitate.** It is not a weaker
`include-candidate`; it is the honest answer when the text does not decide, and
an author reads every one of them against the full record afterwards. Nothing is
lost by using it and something is lost by guessing.

**Never infer an unstated subject species.** If the abstract does not say the
subjects were human, it does not say it — do not reason from the setting, the
outcome, the journal or the food to a species the text omits. That is
`uncertain`, or an exclusion under §2's own clause on the matter, exactly as §2
and §3 write it.

## Every verdict carries a reason

One or two sentences, naming the §2 condition or the §3 rule that decides it, and
the words in the record that trigger it. "Not relevant" is not a reason. For an
`include-candidate`, state all four §2 conditions against the text, because that
verdict asks a human to overturn a settled judgment.

## Do not open these

They carry the labels you are checking, and reading them would make this pass a
copy of the pass it is supposed to test:

- `data/screening.csv`, `data/screening_golden.csv`, `data/screening_rulings.csv`
- `data/screening_thirdpass.csv`
- `src/screening.py`, `src/build_screening.py`, `src/build_thirdpass.py`
- anything under `data/screening_work/c1/`, `c2/`, `c3/`

Your inputs are the batch files named below and the protocol. Nothing else.

## Input and output

Each input file holds `{"food_key": ..., "records": [{pmid, title, pubtypes,
abstract}, ...]}`. Write one output file per input, as JSON:

```json
{
  "food_key": "<copy the food_key from the input file verbatim>",
  "verdicts": [
    {"pmid": "<as a string>", "verdict": "exclude-agreed", "reason": "..."}
  ]
}
```

Rules that matter:

- **Copy `food_key` from the input JSON.** Do not rebuild it from the filename —
  some food keys contain a space (`chili pepper`, `white rice`) that the filename
  writes as an underscore.
- **`pmid` is a string.** Keep it exactly as the input has it.
- **One verdict per input record, all of them, in the input's order.** If your
  batch has 200 records your output has 200 verdicts. Do not summarise, do not
  skip a run of similar records, and do not stop early — a short file reads as a
  completed pass and that is the one failure this check cannot absorb.
- If you need scratch space, name the file with the prefix `c3ext_scratch_` so it
  is never mistaken for an output.

Your files:

{FILES}

Reply with only: the number of records you judged per output file, and the counts
of each verdict. The files themselves are the deliverable.

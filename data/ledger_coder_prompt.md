# Axis A ledger — the prompt each coder agent receives

This is the instruction given to every coder agent that judges a batch of the
Axis A candidate ledger (`coding_protocol.md` §9). It is published for the same
reason the protocols are: the coding cannot be reproduced without it.

Substitute `{N}` (coder number, 1 or 2) and `{BATCH}` (batch id, e.g.
`kawashimaya_b2`). Coder 1 runs on `claude-sonnet-5`, coder 2 on
`claude-opus-5` — the same two tiers used for Axis B screening (project decision
D40), so both axes are judged by the same instrument.

The batch files themselves are git-ignored: they embed each source's full body
text, which is third-party content, and they regenerate from `data/sources_raw/`
with `python3 -m src.extract_candidates && python3 -m src.dump_ledger_batches`.

---

You are **Coder {N}** for the Axis A candidate ledger of a bibliometric study of Japanese warming/cooling food beliefs.

Working directory: `/Users/mizukishirai/claude/analysis/warming-cooling-foods`

## Read the standard first

Read `data/coding_protocol.md` **in full** before judging anything. It is the judgment standard. §9 governs this task specifically, but §1–§8 define how a kept attribution is coded and you need them. Do not skim.

★ **§9.4's "Applying them in order" is binding.** Walk the seven rules from 1 to 7 and take the **first** that fits. Rule 2 (`fragment`) asks one question only: **does the source present this span as an item?** — not whether it is well formed. A food name carried along with its modifiers or its topic particle (`水分を多く含む夏野菜は`) is not an item the source presents; 夏野菜 is, and it is enumerated separately.

## Your batch

`data/ledger_work/candidates_{BATCH}.json` contains:

- `source_text` — the full body text of the source. **This is your context.** A span cannot be judged alone: roughly six candidates in ten carry their thermal context only in the enclosing section or in a neighbouring line.
- `candidates` — spans enumerated from that text by a deliberately dictionary-free structural extractor, each with `line_no`, `lines` and `paths`.

Three things about those fields:

- ★ **`lines` lists *every* line the span was emitted from; `line_no` is only the first.** A candidate row stands for the span across the whole source — §2 makes the unit of coding a (food, source) pair — and about six candidates in ten occur more than once. **Read all of `lines` before deciding.** The first occurrence is often not where the source assigns a direction: it may be a table-of-contents entry, or a question the source then refutes, while the attribution sits forty lines further down.
- `line_no` is the 1-based line where the emission **started**. For a candidate whose `paths` includes `wrapped`, the span was recovered by joining that line with the **next** one, so the span may not appear in that line alone — read both.
- The candidates **overlap in granularity on purpose** (a clause-level span and a particle-level token from the same line) and **contain noise on purpose**. §9.2 explains why; noise is dropped in the ledger with a reason code, not filtered out silently.

★ **Your batch is one slice of the source, not the whole enumeration.** The source's candidates are partitioned across several batches by line group, and every other slice is being coded by someone else. A food you can see in `source_text` but cannot find among your candidates is almost always enumerated in a neighbouring batch — three coders in a row have reported such a food as an extraction gap, and all three times it was in the next batch along. Judge the candidates you were given; do not infer anything about the enumeration as a whole from what is missing here.

## The judgment

For **every candidate in the batch**, decide `include` or `exclude` per §9.3.

- `include` — the span carries an attribution to be coded under §2–§4. Also return `food_ja`, `food_en`, `direction` (exactly one of `warm` / `cool` / `neutral`), and `quote` (verbatim from `source_text`). Attach `sublabels` where §9.5 calls for one (`category`, `dish`).
- `exclude` — give **exactly one** reason code, chosen by walking §9.4's numbered order: `navigation`, `fragment`, `not-verbatim`, `not-food`, `no-direction`, `serving-temperature`, `duplicate`.
- If a span genuinely cannot be settled from the source, use `exclude` with reason `uncertain`; it routes to the author. Use it sparingly.

## If the protocol has no answer

If you hit a candidate where none of the codes fits, and calling it `uncertain` would be hiding a gap in the *protocol* rather than in the *source*, **say so explicitly in your final message** with the candidate and your reasoning. Do not paper over it.

## Output

Write `data/ledger_work/c{N}/{BATCH}.csv` **using Python** (pandas or the `csv` module) so quoting is correct — several quotes contain commas.

Columns, in this order:

```
source_id,candidate,label,reason,sublabels,food_ja,food_en,direction,quote
```

- One data row per candidate in the batch, plus the header. Verify the count.
- Keep the `candidate` string **byte-identical** to the JSON. Do not normalise, trim or merge.
- Do not drop rows, do not add rows.
- `source_id` is the batch's own source id on every row.
- Leave unused fields empty (an exclude has no `food_ja`/`direction`/`quote`; an include has no `reason`).

## Blind conditions

Do **not** read: `data/claims.csv`, `data/screening*.csv`, `data/independent_read/`, `src/ledger.py`, `src/build_claims.py`, `src/verify_*`, the other coder's directory, `data/ledger_work/round*/`, `data/ledger_work/superseded/`, or any other coder's output. Your judgment must come from the protocol and the source text alone.

Scratch files go in the session scratchpad and must be prefixed `c{N}_{BATCH}_`.

## Report back

Your final message: total includes / excludes, the count per reason code, and any protocol gaps you hit.

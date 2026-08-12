# Axis B screening — the prompt each coder agent receives

This is the instruction given to every coder agent that screens a batch of L2
records against `screening_protocol.md`. It is published for the same reason the
protocols are: the coding cannot be reproduced without it, and Axis A already
publishes its equivalent (`ledger_coder_prompt.md`).

Substitute `{N}` (coder number, 1 or 2), `{FILES}` (the input → output mapping,
written out one line per file) and `{SUFFIX}` (the batch's output suffix). Coder 1
runs on `claude-sonnet-5`, coder 2 on `claude-opus-5` (project decision D40), the
same two tiers that carry the existing judgments, so a widened record set is
judged by the same instrument as the set it extends.

**Scope of this file.** It records the prompt used for the batch named in §5 of
the protocol as the Route D universe extension (2026-08-12, 296 records over 9
foods). The earlier batches were composed per session rather than from a stored
file; their independence conditions, output schema and read-the-protocol-yourself
instruction were the same, but their exact wording was not kept, so this file is
scoped to the batch it names rather than presented as the wording of all of them.

The batch files themselves are git-ignored: they embed PubMed titles and
abstracts, which are third-party content, and they regenerate from
`data/l2_records.csv` with
`python3 -m src.dump_screening_batches --new-only --max=400`.

---

You are **Coder {N}**, screening PubMed records for a bibliometric study of
Japanese warming/cooling food beliefs.

Working directory: `/Users/mizukishirai/claude/analysis/warming-cooling-foods`

## Read the standard first

Read `data/screening_protocol.md` **in full** before judging anything. It is the
judgment standard, and §1–§3 are what you apply record by record. Do not skim it
and do not work from a summary of it: §2's four INCLUDE conditions and §3's
boundary rules are the whole task, and §2.3's notes on vascular beds, energy
expenditure and endothelial probes settle the single question that most
divergences turn on.

## Your batch

{FILES}

Each file is `{"food_key": "...", "records": [{"pmid", "title", "pubtypes",
"abstract"}]}`. You get titles and abstracts only — no counts, no other coder's
labels, no golden set.

- ★ **Use the `food_key` string from inside the JSON, verbatim.** Several food
  keys contain a space (`ice cream`, `long pepper`, `star anise`). The file name
  spells those with an underscore; the file name is not the key.
- A record's food is the food of its file, not whatever food the abstract talks
  about most. The question is always "does *this* record examine the thermal
  effect of ingesting *this* food".
- Some records have an empty `abstract`. §2 tells you what to do with those.

## The judgment

For **every record in the batch**, decide `include` or `exclude` per §2–§3.

- `include` — all four §2 conditions hold. Put a short description of the study
  in `reason` (subjects, exposure, thermal outcome), and attach any sub-labels
  §2–§3 call for (`review`, `constituent`, `supradose`, `confounded`), separated
  by `;` when more than one applies.
- `exclude` — give **exactly one** reason code from §2's list: `animal`,
  `livestock-heat`, `invitro`, `agri`, `name-only`, `no-thermal`,
  `mechanism-only`, `not-ingestion`, plus `species-mismatch` where §3 applies it.
  ★ `not-ingestion` is the code when the food reaches the subject by some route
  other than eating it — topical application, inhalation, infusion, a bath — or
  is present in the setting without being consumed. Do not fold those into
  `name-only`; the route is the thing that fails §2 condition 2.
- Where the abstract never states the subject species, use `exclude` with reason
  `uncertain-species`; where there is no abstract and the title cannot establish
  all four conditions, use `exclude` with reason `no-abstract`. Both route to the
  author regardless of what the other coder said (§5). **Do not infer the species
  from acupoint names, clinical phrasing or the journal's scope** — §2 records a
  case where exactly that inference was wrong.

You may add free text after a reason code with a colon (`species-mismatch:
Capsicum annuum, not Piper nigrum`); the code before the colon is what is
counted.

## If the protocol has no answer

If you hit a record where none of the codes fits, and forcing one would be hiding
a gap in the *protocol* rather than in the *record*, **say so explicitly in your
final message**, with the pmid and your reasoning. Do not paper over it. Two
coders reaching the same answer because the protocol left them the same safe
default is not agreement about the record.

## Output

Write the CSVs **using Python** (pandas or the `csv` module) so quoting is
correct. Output paths are listed above, one per input file.

Columns, in this order:

```
pmid,food_key,label,reason,sublabels
```

- One data row per record in the input file, plus the header. **Verify the count
  against the input before you finish.**
- Do not drop rows, do not add rows, do not reorder relative to the input.
- `sublabels` is normally empty for an exclude; `reason` carries the code on an
  exclude and the short study description on an include.
- Write each file as you finish it, appending in chunks of about 80 rows rather
  than emitting one large literal — a coder that tried to print a whole CSV in a
  single block hit the output token ceiling and lost the batch.

## Blind conditions

Do **not** read: `data/screening.csv`, `data/screening_golden.csv`,
`data/screening_rulings.csv`, `data/screening_thirdpass.csv`,
`src/screening.py`, `src/build_screening.py`, `src/build_golden.py`,
`data/screening_work/c1/`, `data/screening_work/c2/`, `data/screening_work/c3/`,
`data/screening_work/c3_batches/`, `data/screening_work/c3_prev_4term/`, or any
other coder's output. Your judgment must come from the protocol and the record
alone.

Scratch files go in the session scratchpad and must be prefixed `c{N}_{SUFFIX}_`.

## Report back

Your final message: per food, the include / exclude counts and the count per
reason code, plus any protocol gaps you hit.

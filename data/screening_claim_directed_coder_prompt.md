# Protocol §8 sub-labelling — the prompt each coder agent receives

This is the instruction given to every coder agent that sub-labels a batch of
included records `claim-directed` / `incidental` against `screening_protocol.md`
§8. It is published for the same reason the protocols and the two other coder
prompts are (`screening_coder_prompt.md`, `ledger_coder_prompt.md`): the coding
cannot be reproduced without it.

Substitute `{N}` (coder number, 1 or 2), `{FILES}` (the input → output mapping,
one line per file) and `{SUFFIX}` (the batch's output suffix). Coder 1 runs on
`claude-sonnet-5`, coder 2 on `claude-opus-5` (project decision D40), the same
two tiers that carry the include/exclude judgments this pass builds on.

The batch files are git-ignored: they embed PubMed titles and abstracts, which
are third-party content. They regenerate from `data/l2_records.csv` and
`data/screening.csv` with `python3 -m src.dump_claim_directed_batches`.

---

You are **Coder {N}**, sub-labelling PubMed records for a bibliometric study of
Japanese warming/cooling food beliefs.

Working directory: `/Users/mizukishirai/claude/analysis/warming-cooling-foods`

## Read the standard first

Read `data/screening_protocol.md` **§8 in full**, and read §2 and §3 for the
context §8 refers to. §8 is the judgment standard and its boundary rules are the
whole task. Do not work from a summary of it.

## What is already settled, and what you are deciding

Every record in your batch has **already been judged `include`** — it is a human
ingesting this food with a qualifying thermal outcome. That decision is not
yours to revisit and you cannot change it.

Your single question is §8's: **was the thermal effect of eating this food the
question the study set out to answer?**

- `claim-directed` — the study's own research question is whether ingesting this
  food (or a food form or principal dietary constituent of it) changes a thermal
  outcome. The thermal outcome is a primary or co-primary endpoint, and the food
  is the exposure the study is about.
- `incidental` — the record qualifies, but the study is asking something else
  (weight loss, endothelial or cardiovascular function, exercise performance,
  glycaemic control, a disease marker), and the thermal outcome is measured in
  service of that question or reported alongside it.

Read §8's framing paragraphs before you start, because three of them decide most
records:

- **Where the question is read from.** The study's own framing is its **title and
  the aim / objective sentences of its abstract**. Not the journal's scope, not
  what studies of that food usually ask, not the discussion's speculation. §8
  splits the judgment into two halves — the framing must name this food as what
  is given or varied, *and* name a thermal outcome as something measured — and a
  record is `incidental` when either half fails.
- **The test is the question, not the motivation.** Almost nothing here cites a
  Japanese warming/cooling belief. Requiring that citation would make everything
  `incidental` and would measure journal citation habits instead of what was
  studied. The question is whether the study set out to measure the food's
  thermal effect.
- **The test is not study quality.** A small single-arm trial asking the thermal
  question is `claim-directed`. A large, well-controlled trial that measures skin
  blood flow as one secondary outcome of a lipid study is `incidental`.

## Your batch

{FILES}

Each file is `{"batch": "...", "records": [{"pmid", "food_key", "title",
"pubtypes", "abstract", "sublabels"}]}`.

- ★ **Use the `food_key` string from inside the JSON, verbatim.** Several keys
  contain a space (`ice cream`, `green tea`, `chili pepper`).
- A record's food is the `food_key` on its row. The same pmid appears under more
  than one food in this batch, and the judgment is per food: the question is
  always "was *this food's* thermal effect what the study set out to measure".
- `sublabels` carries the §3 sub-labels already settled for the record
  (`review`, `constituent`, `supradose`, `confounded`). §8's boundary rules name
  them, so they are given to you rather than re-derived. They are not a hint
  about the answer.
- A few records have an empty `abstract`. §8 tells you what to do.

## The judgment

For **every record in the batch**, decide `claim-directed` or `incidental`.

- Put in `reason` the study's own stated question, in a few words, as you read it
  from the title and abstract — "acute DIT after a ginger drink", "12-week
  weight-loss RCT, REE among outcomes", "review of capsaicin and energy
  expenditure". This is what makes the judgment auditable, so make it name the
  question rather than describe the intervention.
- Where the abstract reports outcomes but never states what was being asked, use
  `incidental` with reason `unclear-question` — **and** say so, because that flag
  routes the record to the author regardless of what the other coder said (§8).
- Where the record has **no abstract at all**, give your best label from the
  title and put `no-abstract` in `reason` — **unconditionally, even when the
  title looks like it settles the question.** §8 is stricter than §2 here and
  says why. A title states the titled question; it cannot rule out that an
  unnamed endpoint shared primacy with it, and this is the clause most likely to
  manufacture agreement between two coders reading the same nine words. **Do not
  infer the study's question from the journal's scope or from what studies of
  that food usually ask.**

Both flags exist so that a guess is recorded as a gap rather than as a judgment.
Neither is a third value: the `sub_label` column always holds one of the two
labels, and the flag lives in `reason`.

## If the protocol has no answer

If you hit a record where neither label fits, and forcing one would be hiding a
gap in the *protocol* rather than in the *record*, **say so explicitly in your
final message**, with the pmid and your reasoning. Do not paper over it. Two
coders reaching the same answer because the protocol left them the same safe
default is not agreement about the record.

## Output

Write the CSVs **using Python** (pandas or the `csv` module) so quoting is
correct. Output paths are listed above, one per input file.

Columns, in this order:

```
pmid,food_key,sub_label,reason
```

- One data row per record in the input file, plus the header. **Verify the count
  against the input before you finish.**
- Do not drop rows, do not add rows, do not reorder relative to the input.
- Write each file as you finish it, appending in chunks of about 80 rows rather
  than emitting one large literal — a coder that tried to print a whole CSV in a
  single block once hit the output token ceiling and lost the batch.

## Blind conditions

Do **not** read: `data/screening.csv`, `data/screening_golden.csv`,
`data/screening_rulings.csv`, `data/screening_thirdpass.csv`,
`data/screening_claim_directed.csv`, `data/screening_claim_directed_rulings.csv`,
`src/screening.py`, `src/claim_directed.py`, `src/build_screening.py`,
`src/build_claim_directed.py`, `data/screening_work/cd1/`,
`data/screening_work/cd2/`, or any other coder's output. Your judgment must come
from §8 and the record alone.

Scratch files go in the session scratchpad and must be prefixed `cd{N}_{SUFFIX}_`.

## Report back

Your final message: the counts per label, the pmids you flagged
`unclear-question` or `no-abstract`, and any protocol gaps you hit.

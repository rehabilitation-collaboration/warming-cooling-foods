# The Attention Gap in Warming/Cooling Food Beliefs

A bibliometric study asking whether foods that are widely believed in Japan to
"warm" or "cool" the body have received correspondingly little (or skewed)
direct scientific scrutiny — an **attention gap** between breadth of lay belief
(Axis A) and volume/quality of research attention (Axis B).

This study does **not** claim there is "no evidence." Prior work (Ormsby 2021
scoping review; ginger and caffeine trials) shows the evidence is *fragmentary,
unintegrated, and unevenly attended*, not absent.

## Method (overview)

- **Axis A — belief breadth (consensus coverage):** for each food, count the
  distinct Japanese lay-facing sources that call it warming vs cooling, over a
  frozen frame of verified sources (`data/sources.csv`). Coding follows
  `data/coding_protocol.md` (hand-coded, García-Hernández 2023 style). Tier 1
  (corporate/association) is the primary frame; Tier 2 (individual experts) is a
  sensitivity check.
- **Axis B — research attention:** PubMed E-utilities (`[pt]` design filter) +
  OpenAlex + CiNii counts per food × effect term (planned).
- **Normative axis:** five-nature (五性) classification from the
  薬膳食典食物性味表 + Nishimura et al. 2012, compared against lay attribution.

## Layout

```
src/definitions.py     constants, controlled vocabularies, paths
src/claim_mapping.py   Axis A aggregation (consensus coverage)
data/sources.csv       frozen source frame (provenance)
data/coding_protocol.md  hand-coding rules for Axis A
tests/                 unit tests
```

## Run

```
pip install -r requirements.txt
python -m pytest tests/
```

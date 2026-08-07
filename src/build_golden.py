"""Build the RB-2 golden reference set from hand-read abstracts.

The author (an LLM in the main Claude session, disclosed in Methods) read the
title + abstract of every record below and assigned ``include``/``exclude`` per
``data/screening_protocol.md`` §2-§3. The judgments are recorded here as an
explicit {pmid: (label, reason)} map per food so they are auditable and
reproducible: this file *is* the provenance of the golden labels (no regex, no
automated classifier produced them). Running it writes
``data/screening_golden.csv`` with the record titles joined back in.

Golden design (protocol §4): the include boundary lives in ginger / coffee /
chili pepper, so those are labelled in full. chicken and salt are near-uniform
exclude classes, so each is a stratified 40: every human-signal record plus a
deterministic even-spaced fill of the remainder.

Boundary rules applied consistently across foods (documented in reasons):
- species-mismatch: for ginger, only Zingiber officinale (and its own
  gingerol/shogaol/zingerone) counts; grains of paradise (Aframomum melegueta)
  and black ginger (Kaempferia parviflora) are different Zingiberaceae species,
  so they are excluded from the *primary* (sensu stricto) count and recovered in
  a sensu-lato sensitivity variant.
- not-ingestion: footbaths, topical creams, IV saline/infusions are not oral
  ingestion → exclude (mirrors Axis A's serving-temperature rule).
- review-subject: a review/meta counts (include, review-subject reason) only
  when its stated objective is the thermal / thermogenic / energy-metabolism
  effect itself; a review whose objective is obesity / weight-loss / exercise
  performance (thermogenesis merely a listed mechanism) is name-only.
- name-only: the food/"salt" term is incidental — drug-salt dosage forms,
  "salt-inducible kinase", phase-change materials, urine colour, egg-white
  microbiology at "chicken body temperature", etc.
- species verification (protocol §4, added 2026-08-07): where the abstract does
  not state the subject species, the label is set from the PubMed
  Humans/Animals MeSH headings, or from the full text when the record carries
  no MeSH. This rule exists because ginger/29259648 was first labelled
  ``include`` on the inference that its acupoint names implied human subjects;
  the PMC full text states 33 rabbits (IACUC BUCM-3-2015032502-1002), so it is
  ``exclude`` (animal). Coder 2 had flagged it as animal — the divergence is
  what surfaced the error.
"""

from __future__ import annotations

import sys

import pandas as pd

from .screening import GOLDEN_CSV, L2_RECORDS_CSV

# --- hand labels: {pmid: (gold_label, gold_reason)} ------------------------

GINGER = {
    "42308737": ("exclude", "animal: broiler chickens, cloacal temp"),
    "42271377": ("exclude", "species-mismatch: grains of paradise (Aframomum), human but not Z.officinale"),
    "41007640": ("exclude", "animal: HFD mice"),
    "40577283": ("exclude", "invitro: adipocytes in vitro"),
    "40313435": ("exclude", "species-mismatch: Kaempferia parviflora (black ginger), human RCT"),
    "40092148": ("exclude", "name-only: broad cold-weather military nutrition review, ginger not the subject"),
    "39366495": ("exclude", "animal: rats, TCM network pharmacology"),
    "39259072": ("exclude", "no-thermal: ginger RCT in COVID-19, outcome viral clearance"),
    "39023772": ("exclude", "animal: HFD mice (black ginger)"),
    "36424723": ("exclude", "animal: obese mice, zingerone"),
    "36058007": ("include", "human RCT: dry ginger extract, resting energy expenditure in female adults (Z.officinale)"),
    "34814768": ("exclude", "not-ingestion: ginger footbath, not oral intake"),
    "34192599": ("exclude", "invitro/animal: BAT herb-pair network pharmacology, no human ingestion"),
    "33952741": ("exclude", "species-mismatch: grains of paradise (Aframomum) humans BAT"),
    "33789250": ("include", "review-subject: red pepper/ginger/turmeric on energy metabolism, human evidence"),
    "31586693": ("exclude", "animal: mice BAT/WAT browning"),
    "31505825": ("exclude", "name-only: broad functional-foods weight-management review"),
    "31369153": ("exclude", "animal: mice, GE promoted O2 consumption + intrascapular temp"),
    "30477855": ("exclude", "not-ingestion: ginger footbath, healthy subjects skin temp"),
    "30402121": ("include", "human: ginger beverage, palm skin temperature in cold-sensitive women (Z.officinale)"),
    "30168574": ("exclude", "name-only: broad anti-obesity spice mechanism review (cell/animal/human)"),
    "29259648": ("exclude", "animal: 33 rabbits, rectal/acupoint skin temp (species stated only in full text, not the abstract)"),
    "29193411": ("exclude", "name-only: ginger anti-obesity/weight systematic review, objective is weight not thermal"),
    "28154330": ("exclude", "name-only: Ephedra analgesic paper, ginger only a TCM comparator"),
    "27831646": ("exclude", "animal: rabbits, HSP model, ginger in decoction"),
    "25875447": ("include", "human: dried ginger root powder oral, thermoregulatory function/fat oxidation (Z.officinale)"),
    "23308394": ("exclude", "species-mismatch: grains of paradise (Aframomum) men, BAT/EE"),
    "23021155": ("include", "human RCT: ginger arm, postprandial diet-induced thermogenesis + EE (Z.officinale)"),
    "22538118": ("include", "human RCT: ginger powder, thermic effect of food in overweight men (Z.officinale)"),
    "21185236": ("exclude", "animal: rats, grains of paradise/6-paradol BAT"),
    "18295202": ("exclude", "animal: rats, [6]-gingerol hypothermia"),
    "17176640": ("exclude", "invitro/animal: HEK293 cells + rats, shogaol TRPV1"),
    "16580033": ("include", "review-subject: metabolic/thermogenic effects of spices, teas, caffeine (incl ginger)"),
    "1330955": ("exclude", "animal: perfused rat hindlimb"),
    "2070449": ("exclude", "animal: rats, goshuyu-to body temperature"),
}

COFFEE = {
    "42514427": ("exclude", "invitro: chlorogenic acid preclinical adipose review"),
    "39519525": ("exclude", "name-only: bibliometric study of caffeine-in-heat literature, not thermal-ingestion evidence"),
    "38694556": ("exclude", "name-only: coffee/tea/cocoa obesity-prevention review, objective is obesity"),
    "38140290": ("exclude", "name-only: coffee/caffeine on exercise & metabolism review, not thermal-ingestion"),
    "37764380": ("exclude", "name-only: natural products for obesity review"),
    "37596386": ("exclude", "invitro: CGA/caffeine nanoparticles PPAR pathway (retracted)"),
    "36990367": ("exclude", "animal: HFD mice, coffee BAT whitening"),
    "36603448": ("exclude", "name-only: spent coffee grounds as phase-change material, no ingestion"),
    "36517893": ("exclude", "animal: adipose browning model, caffeoylquinic acid"),
    "31505825": ("exclude", "name-only: broad functional-foods weight-management review"),
    "31235722": ("exclude", "animal/invitro: caffeine browning in vitro and in vivo (mice)"),
    "29723112": ("include", "human: green coffee, resting energy expenditure + body temperature in healthy women"),
    "26856274": ("include", "review-subject: natural stimulant/non-stimulant thermogenic agents (incl caffeine)"),
    "24448391": ("exclude", "invitro: HepG2 cells, N-methylpyridinium thermogenesis"),
    "18767348": ("exclude", "not-ingestion: cold-storage workers in coffee plant, occupational cold, no ingestion"),
    "9202101": ("exclude", "no-thermal: caffeine beverage, outcome is parasympathetic HRV, no thermal measure"),
    "9035968": ("exclude", "animal: newborn calves, Coffea arabica extract"),
    "8873167": ("exclude", "animal: rats, aspartame behavioural thermoregulation"),
    "7485480": ("include", "human: caffeinated vs decaf coffee, coffee-induced thermogenesis/EE in women"),
    "7486839": ("include", "human RCT: decaf ± caffeine, energy expenditure + skin/rectal temperature"),
    "7951473": ("include", "human: coffee-induced thermogenesis and skin temperature"),
    "2912011": ("exclude", "name-only: liquid-meal serving temperature effect (coffee as vehicle, not its nature)"),
    "3957721": ("include", "human: spiced food (incl caffeine) on metabolic rate / diet-induced thermogenesis"),
    "427705": ("exclude", "name-only: feedlot cattle, 'coffee-colored urine' incidental"),
}

CHILI = {
    "42186269": ("include", "review-meta-subject: culinary red pepper attenuating adaptive thermogenesis (human)"),
    "40092148": ("exclude", "name-only: broad cold-weather military nutrition review"),
    "39958175": ("exclude", "animal: HFD mice, Capsicum NET-2201"),
    "39289273": ("exclude", "mechanism: thermosensitive TRP channel review, not ingestion"),
    "38895664": ("exclude", "name-only: corrigendum, no data"),
    "38571755": ("include", "human RCT: red-chili capsaicinoids (Capsifen), energy balance/thermogenesis [constituent]"),
    "38531438": ("exclude", "invitro/animal: 3T3-L1 adipocytes + mouse, capsaicin"),
    "38379484": ("exclude", "not-ingestion: topical capsaicin cream, thermoregulation walking in cold"),
    "33789250": ("include", "review-subject: red pepper/ginger/turmeric on energy metabolism, human evidence"),
    "33063385": ("include", "meta-subject: capsaicinoids/capsinoids on thermogenesis in healthy adults"),
    "32199999": ("exclude", "name-only: energy-balance/food-reward review, not chili thermal-ingestion"),
    "31009639": ("exclude", "animal: mice, oral gavage capsaicin hypothermia"),
    "29568185": ("exclude", "animal: mice, thermogenic blend + whey"),
    "27899046": ("exclude", "name-only: 'chili as weight-loss food' review, objective is weight not thermal"),
    "26552144": ("exclude", "invitro/animal: DRG neurons + HEK293 cells + BAT, TRPV1 mechanism"),
    "26421678": ("exclude", "name-only: 'food ingredients as anti-obesity agents' review, objective is obesity"),
    "23844093": ("include", "human RCT: capsaicin, energy expenditure/fat oxidation in negative energy balance [constituent]"),
    "21093467": ("include", "human RCT: hedonic red-pepper doses on thermogenesis and appetite"),
    "20932337": ("exclude", "not-ingestion: TRPV1 agonists screened for therapeutic hypothermia, not chili intake"),
    "20925950": ("include", "human RCT: dihydrocapsiate (CH-19 Sweet), adaptive/diet-induced thermogenesis [constituent]"),
    "17341828": ("include", "human: CH-19 Sweet red pepper, body temperature + diet-induced thermogenesis"),
    "12959953": ("exclude", "animal: oral capsiate upregulates UCP (rodent tissue)"),
    "11767210": ("exclude", "animal: mice, CH-19 Sweet body temperature"),
    "11676017": ("include", "human: CH-19 Sweet, body temperature + oxygen consumption in 11 volunteers"),
    "11227803": ("include", "human: capsaicin curry, SNS activity + diet-induced thermogenesis in women"),
    "10211048": ("include", "human: red pepper with HF/HC meals, energy metabolism in Japanese women"),
    "9487017": ("exclude", "mechanism: vanilloid receptor review, pain/inflammation, not ingestion thermal"),
    "2747924": ("exclude", "animal: rats, resiniferatoxin (capsaicin analog) hypothermia"),
    "3957721": ("include", "human: spiced food on metabolic rate / diet-induced thermogenesis"),
    "5498502": ("exclude", "animal: rats/guinea-pigs, capsaicin thermoregulation impairment"),
}

# chicken: stratified 40 (14 human-signal + 26 deterministic fill). All exclude.
CHICKEN = {
    "41367205": ("exclude", "animal: domestic cats, energy expenditure"),
    "40387054": ("exclude", "name-only: theoretical protein/water model, chicken as example species"),
    "32582777": ("exclude", "animal: working dogs, pre-hydration in heat"),
    "32320452": ("exclude", "livestock-heat: broiler transport microclimate, production losses"),
    "30624709": ("exclude", "name-only: Salmonella egg-white microbiology at chicken body temp"),
    "27916641": ("exclude", "animal: UCP1 brown-adipocyte history (mammals/rodents)"),
    "27264093": ("exclude", "animal: rats fed purified meat proteins incl chicken, DIT"),
    "23909913": ("exclude", "animal: mice, vaccinia allergy model"),
    "23436537": ("exclude", "name-only: Salmonella egg-white survival at chicken body temp"),
    "23430386": ("exclude", "animal: chickens, avUCP energy expenditure"),
    "16615357": ("exclude", "livestock-heat: broiler chickens, diet-induced thermogenesis genotype"),
    "11171038": ("exclude", "animal: chicken skeletal-muscle UCP, avian thermogenesis"),
    "6085056": ("exclude", "invitro: Sindbis virus in chicken/other cells"),
    "19531576": ("exclude", "animal: chicken QTL for metabolic traits"),
    "10653500": ("exclude", "animal: chickens, sevoflurane anesthetic concentration"),
    "11989759": ("exclude", "livestock-heat: broiler PSE meat, body temp/glycolysis"),
    "14251943": ("exclude", "animal: chicken, cardiovascular changes with thermal polypnea"),
    "16156199": ("exclude", "livestock-heat: broiler thermoregulation vs humidity"),
    "17623916": ("exclude", "invitro: DT40 chicken cell culture conditions"),
    "18901892": ("exclude", "animal: chicken, body temperature vs blood pressure"),
    "21066167": ("exclude", "animal: chicken embryos, peripheral circulation cells"),
    "22937744": ("exclude", "animal: Japanese quail plumage/body temperature mutation"),
    "24123731": ("exclude", "animal: Salmonella in chickens, osmolarity/virulence"),
    "24973664": ("exclude", "animal: chicken hatchlings, preferred ambient temperature"),
    "26072164": ("exclude", "animal: chickens, FNDC5/irisin cold exposure"),
    "27587725": ("exclude", "livestock-heat: broiler embryo thermal manipulation"),
    "28943447": ("exclude", "name-only: Syzygium anti-allergic extract (chicken incidental)"),
    "31217129": ("exclude", "animal: subdermal photoplethysmography/thermometry device in animals"),
    "32331280": ("exclude", "livestock-heat: broiler post-hatch cold stress HSF3/Hsp70"),
    "33383690": ("exclude", "livestock-heat: heat-stress genetics in chickens review"),
    "34475725": ("exclude", "livestock-heat: broilers under heat stress, agarwood extract"),
    "35910562": ("exclude", "animal: birds, cutaneous TRPV4 warmth-defense"),
    "37276745": ("exclude", "animal: chicken thyroid hormone, endothermy development"),
    "39417774": ("exclude", "animal: laying hens, cold stress UCP/ANT"),
    "39877350": ("exclude", "livestock-heat: chicken intestinal heat damage, Physalis extract"),
    "41133095": ("exclude", "name-only: gut-microbiota fat-deposition review (chicken incidental)"),
    "42485672": ("exclude", "animal: chicken embryonic fibroblasts, thermal stress virus"),
    "6791150": ("exclude", "animal: chicken respiratory gas exchange"),
    "7435601": ("exclude", "animal: chicken temperature maintenance, dopamine/6-OHDA"),
    "9801153": ("exclude", "animal: avian testicular cells, heat-shock"),
}

# salt: stratified 40 (23 human-signal + 17 deterministic fill).
SALT = {
    "42036509": ("exclude", "not-ingestion: plantar hot salt PACKS (external), intraoperative hypothermia"),
    "41460707": ("exclude", "name-only: dextran sodium sulfate IBD model (chemical, not dietary salt)"),
    "40926793": ("exclude", "no-thermal: golfer heat-exhaustion case-control, salt not the ingested exposure"),
    "36896681": ("exclude", "no-thermal: eccrine sweat-gland density evolution, no salt ingestion"),
    "36451714": ("exclude", "no-thermal: skin sodium & blood-pressure review, outcome BP"),
    "35669471": ("exclude", "no-thermal: cold-pressor renal microcirculation, salt not ingested"),
    "35057434": ("include", "human RCT: increased salt intake decreases diet-induced thermogenesis in volunteers"),
    "31413064": ("exclude", "name-only: marathon AKI & thermoregulation, salt not the intervention"),
    "30030465": ("exclude", "name-only: 'salt-inducible kinase' (enzyme), BAT thermogenesis, not dietary salt"),
    "26317057": ("exclude", "animal/invitro: pig preadipocyte incubation temperature"),
    "25729305": ("include", "human: oral sodium supplementation, thermoregulation in endurance athletes [constituent]"),
    "25158789": ("exclude", "not-ingestion: hypertonic saline infusion (IV), not oral salt"),
    "24136220": ("exclude", "animal: rats, IL-1beta effort motivation (salt incidental)"),
    "23253191": ("include", "human RCT: sodium+water ingestion, cardiovascular function during heat [constituent]"),
    "21490606": ("include", "human: acute salt ingestion, core (rectal) temperature in healthy men"),
    "20303218": ("exclude", "name-only: obesity/hypothalamus hypothesis paper, no salt-ingestion thermal outcome"),
    "16055158": ("exclude", "name-only: calcium-potassium 'salt' of hydroxycitric acid (chemical form)"),
    "12108312": ("exclude", "name-only: quinine dosing in 'mg salt' (drug salt form)"),
    "10679499": ("exclude", "animal: rats, stress-response genetics"),
    "7643821": ("exclude", "name-only: ketoprofen lysine 'salt' suppositories (drug salt form)"),
    "8505832": ("exclude", "not-ingestion: IV sodic salt of dicarboxylic acid infusion, not dietary salt"),
    "3349990": ("exclude", "name-only: forced water intake & thermoregulation, water not salt"),
    "6862696": ("exclude", "name-only: lithium carbonate & circadian rhythm, no dietary salt"),
    "10529491": ("exclude", "name-only: autonomic thermoregulation review, no salt ingestion"),
    "11824399": ("exclude", "animal: spiny mouse non-shivering thermogenesis vs salinity"),
    "14736778": ("exclude", "invitro: ciprofloxacin/vancomycin precipitation in vitreous"),
    "17385431": ("exclude", "animal: hypothermic rats, EDTA disodium salt"),
    "19712477": ("exclude", "name-only: allometric metabolism/evolution review"),
    "2148191": ("exclude", "no-thermal: hypertension vascular-risk management review"),
    "23931727": ("exclude", "invitro: pNIPAM lipogel drug release material"),
    "25434233": ("exclude", "animal: rats resuscitation, EDTA disodium salt"),
    "28368063": ("exclude", "invitro: injectable microgel drug-release nanocomposite"),
    "3013361": ("exclude", "animal: rats, choline analog chloride salt behaviour"),
    "32320392": ("exclude", "invitro: PER2 protein thermal-stability (DLS/CD)"),
    "35739571": ("exclude", "animal: mice gastric-bypass microbiota, thermogenic adipose"),
    "380780": ("exclude", "animal: cat, prostacyclin sodium salt into cerebral ventricle"),
    "40286097": ("exclude", "name-only: polyurethane hydrated-salt phase-change materials"),
    "6137492": ("exclude", "invitro: cryopreserved human thyroid-cell bioassay"),
    "8141152": ("exclude", "animal: salt-sensitive spontaneously hypertensive rats"),
    "9852554": ("exclude", "name-only: sucralfate post-tonsillectomy analgesia"),
}

GOLDEN = {"ginger": GINGER, "coffee": COFFEE, "chili pepper": CHILI,
          "chicken": CHICKEN, "salt": SALT}


def build() -> pd.DataFrame:
    rec = pd.read_csv(L2_RECORDS_CSV, dtype={"pmid": str})
    rows = []
    problems = []
    for food, labels in GOLDEN.items():
        food_rec = rec[rec["food_key"] == food]
        have = set(food_rec["pmid"])
        for pmid, (label, reason) in labels.items():
            if pmid not in have:
                problems.append(f"{food} pmid {pmid} not in l2_records")
                continue
            title = food_rec.loc[food_rec["pmid"] == pmid, "title"].iloc[0]
            rows.append(
                {"food_key": food, "pmid": pmid, "gold_label": label,
                 "gold_reason": reason, "title": title}
            )
    if problems:
        print("[error] label keys not found in records:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        raise SystemExit(1)
    return pd.DataFrame(rows)


def main() -> None:
    df = build()
    df.to_csv(GOLDEN_CSV, index=False)
    print(f"wrote {GOLDEN_CSV} ({len(df)} records)")
    print("\nper-food include/exclude:")
    tab = df.pivot_table(index="food_key", columns="gold_label",
                         values="pmid", aggfunc="count", fill_value=0)
    print(tab)


if __name__ == "__main__":
    main()

# European data, expert rules and gold standards (checked 31 October 2026)

Purpose: find EU counterparts of the SEC + DQC setup, with a usable gold standard, and a possible third direction.
Files downloaded for inspection are not stored in the repository; URLs are listed so they can be fetched again.

## 1. ESEF annual reports (EU listed companies): closest EU counterpart of SEC + DQC

* Data: XBRL International's index filings.xbrl.org, JSON:API at `https://filings.xbrl.org/api/filings`.
  On 31 October 2026 the index reported 27,626 filings. Each record has links to the report package and an
  xBRL-JSON version, plus `error_count`, `warning_count` and `inconsistency_count`.
  In the first 5,000 records: 251 Dutch filings; 247 with errors, 4,124 with warnings, 2,344 with calculation
  inconsistencies.
* Meaning of the counts (filings.xbrl.org/docs/about): errors = not conforming to the XBRL specifications;
  warnings = mostly failed XBRL Formula Rules of the ESEF taxonomy. The ESEF Reporting Manual and country rules are
  not validated. The index is not complete (Germany and Ireland are named as hard to collect).
* Expert rules:
  * ESEF Data Quality Rules (DQR) of XBRL International, derived from the DQC IFRS rules; documentation at
    esef-dqr.xbrl.org. The rulesets (`dqc-esef-2020` to `2025`, V31) are in the DQC repository we already use, and
    run in Arelle with the same plugin.
  * Formula assertions in the ESEF taxonomy (these produce the warnings on filings.xbrl.org).
  * ESEF Reporting Manual rules (ESMA).
* Answer keys:
  * ESMA ESEF Conformance Suite: about 157 report packages in 60 tests, with at least one valid and one invalid case
    per rule and the expected error codes (ESMA press release; documentation December 2023; update January 2025).
    Covers the Reporting Manual and regulation, mostly technical/structural rules, not numeric data quality.
  * IFRS test rulesets exist in the DQC repository (`tests/input/dqc-ifrs-*-test-ruleset.zip`); whether there are
    test filings with expected messages for the ESEF DQR, like `secvalidationtests.json` for US rules, is still to
    be checked.
* Natural corrections: 634 entity-period combinations in the first 5,000 records have more than one filing. The
  about page says these are amended reports or language versions, and that the index does not record which. To be
  usable as corrections, amendments must be separated from language versions (for example same language, later
  date, changed facts).

## 2. EBA supervisory reporting (COREP/FINREP): large expert rule set, little public data

* Expert rules: EBA validation rules, Excel at
  `https://www.eba.europa.eu/risk-and-data-analysis/reporting/reporting-frameworks/validation-rules-packages`.
  * Workbook up to framework 3.5 (2026-09-14): one sheet per release back to v2.0; release 3.5 has 20,562 rules
    with type (identity 10,809, manual 6,821, sign 1,272, hierarchy 973, ...), severity (error 5,347, warning
    15,091), formula, and the columns "Deactivated on", "Reactivated on", "Deleted" and "Last Change".
  * Workbook 4.4 phase 1: 14,164 rows (8,658 rule codes) with a formal DPM-XL expression and a description
    (about 10,500 rows with text; part of the descriptions are plain language, part repeat the formula).
* Data: supervisory reports are confidential. Public: the EBA EU-wide transparency exercise (bank-level CSV data
  for about 119 banks, derived from COREP/FINREP, with a mapping to COREP/FINREP; continuation uncertain) and
  sample instance files per framework release. Only a subset of rules can be run on public data.
* Answer key for rule translation: the official DPM-XL expression of each rule; DPM database (table, row and column
  definitions) on the EBA DPM data dictionary page.

## 3. A gold standard for faulty expert rules (basis for a third direction)

* The EBA has published, since 2014, a "list of incorrect ITS validation rules": tests on real data from reporting
  institutions and questions in the Q&A tool showed that several rules were incorrect (EBA press releases 2014).
  Incorrect rules are deactivated; data must not be validated against them.
* In the 3.5 workbook, 1,694 of 20,562 rules carry a deactivation date ("primarily due to being identified as
  potentially incorrect", Explanation sheet), 684 a reactivation date and 1,911 are deleted. "Last Change" also
  marks "Correction: business semantics of the rule had been incorrect". Deactivation dates run from 2014 to 2025,
  which allows a split by date (for example rules deactivated after a model's release).
* Caveat: deactivation can also be caused by IT problems; labels are noisy and imbalanced (about 8% of all rules
  in release 3.5; with a temporal split at 2025-04-29, 97 of 5,537 manual rules, 1.75%).
* No study was found that tries to detect such faulty regulatory validation rules before they are deactivated.
* Tested in a half-day mini-pilot (`docs/eba_minipilot.md`): a local 8B LLM scored AUC 0.64 on a balanced sample,
  below formula length alone (0.71), and at chance within a table (0.53). No usable signal with formula text only.

## 4. Related EU and Dutch literature

* van der Loo and de Jonge, "Data Validation Infrastructure for R", Journal of Statistical Software 97(10), 2021,
  doi:10.18637/jss.v097.i10 (Statistics Netherlands; validation rules as first-class objects).
* Eurostat: VTL 2.0 as the ESS language for validation rules; 21 generic validation rule types (2018); open-source
  VTL interpreter (github.com/eurostat/VTL). No public gold standard of errors found.
* BIS Irving Fisher Committee: IFC Bulletin 57 (2021, workshop with Banca d'Italia, supported by the ECB) on machine
  learning for data quality and anomaly detection in central bank statistics; IFC Bulletin 67 (2026) on generative AI
  in central banking. To be read in full before citing specific claims.
* XBRL International blog series "ESEF errors and common pitfalls" (practitioner evidence on ESEF errors, such as
  wrong dates for opening balances and calculation inconsistencies). IRIS ESEF quality report 2023 (practitioner,
  1,426 companies): use only with care.

## 5. Literature around the third direction (search on 31 October 2026)

* Rule-base verification (expert systems): Preece and Shinghal, "Foundation and application of knowledge base
  verification", International Journal of Intelligent Systems 9(8), 1994; Preece, Shinghal and Batarekh, Knowledge
  Engineering Review 1992. Static detection of anomalies in rule bases (redundancy, ambivalence/conflict,
  circularity, deficiency). Anomalies are signals for a person, not proven errors. A natural non-AI baseline.
* Spreadsheet formula errors: ExceLint (Barowy, Berger, Zorn; OOPSLA 2018, arXiv 1901.11100) finds formulas that
  break the regular structure of neighbouring formulas; CUSTODES and formula smells (Hermans et al., TU Delft).
  EBA rules are formulas over table cells, so "deviates from its sibling rules" is a second baseline.
* LLMs auditing specifications: VeriSpec (arXiv 2610.01847, October 2026) uses an LLM as verifier to find
  inconsistencies in a natural-language specification (405 rules, 5 validated inconsistencies, no gold standard);
  LLM-based requirements quality assessment shows useful signals but many false alarms (arXiv 2609.03230);
  LLM autoformalisation plus an SMT solver for defect identification (VeriMed, preprint).
* Data quality: Martin et al. (PVLDB 2025) on why discovered constraints are mostly false; LeDQeR filters
  generated rules. Both concern generated rules, not expert rule sets.
* EBA rules: no academic study found. Practitioner sources note that checking the consistency of thousands of DPM
  rules is hard (UBPartner); open-source DPM-XL parser github.com/luukhopman/dpm-xl (not checked).
* Gap: no work found that evaluates AI or static methods for finding faulty rules in a large regulatory rule set
  against an official record of rules later found incorrect.

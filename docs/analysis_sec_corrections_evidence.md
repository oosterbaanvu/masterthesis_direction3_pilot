# How much evidence is behind the SEC correction candidates?

Inputs: the stratified review sample (`results/p1_corrections/review_sample.csv`, 64 rows, unchanged), an
AI-simulated review of that sample made with ChatGPT by the author (`ai_simulated_review_NOT_GOLD.csv`,
explicitly not ground truth), and the full correction table. Script: `scripts/p1_review_evidence.py`;
outputs `evidence_summary.json` and `evidence_risk_factors.csv`.

## 1. The AI simulation adds almost no item-level evidence

* 52 of 64 rows (81%) are labelled by a **type heuristic only**: within these rows the label is a fixed function
  of the correction type (sign flip, scale, zero change -> "error corrected"; retag, period move -> "representation
  only"; other value -> "legitimate restatement"). These labels carry no information beyond the type we computed.
* 10 rows (16%) use filing-level context (the explanatory note) but not the specific fact; 2 rows (3%) cite the
  specific field and the note. Both are scale changes.
* 62 of 64 evidence conclusions are "unclear"; confidence is very low for 52 rows.
* Human decisions filled: 0. **No correction type currently has verified item-level evidence.**

Consequence: these labels may guide which items to review first, but they cannot be used as evaluation labels,
and agreement between a detector and them would be circular for the 52 heuristic rows.

## 2. Structural risk factors per correction type (full data, 2023q1-2025q2)

| Type | Facts | Filings | Dimensional | On restatement axis | Scale change in share units | Amendment purpose = restatement | Targeted fix, no dimensions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| other value | 22,897 | 609 | 30% | 2% | - | 70% | 8.5% |
| retag | 2,234 | 326 | 40% | 1% | - | 45% | 8.4% |
| zero change | 537 | 150 | 37% | 21% | - | 70% | 5.6% |
| sign flip | 299 | 100 | 33% | 23% | - | 57% | 12.4% |
| scale | 202 | 40 | 57% | 32% | 42% | 53% | 0% |
| period move | 122 | 36 | 59% | 4% | - | 52% | 13.9% |

Reading the table:
* **Scale** looks like the cleanest error type, but 42% are share counts (consistent with retroactive stock-split
  adjustments, which are not errors), a third sit on the restatement axis, and none come from a targeted,
  non-dimensional correction.
* **Sign flips and zero changes** are often restatement presentations (about a fifth on the restatement axis).
* **Retags** are frequently element replacements between taxonomy versions or presentation changes.
* **Other value** changes are dominated by accounting restatements (70%).
* The subset that most resembles data-entry or tagging errors (targeted fix, no dimensions) is small: about
  1,950 changed amounts, 190 retags, 37 sign flips, 30 zero changes, 17 period moves and no scale changes.

## 3. What this means for SEC corrections as research data

* **Usable now:** as a source of realistic error *patterns* (which elements, which change types, which magnitude
  ratios) to calibrate injection, and as an exploratory "candidate" set reported with this uncertainty.
* **Not usable now:** as ground-truth labels. A detection of a candidate is a detection of a value that the filer
  later changed, not of a confirmed error.
* **What a usable gold subset needs:** item-level human verification (open both filings, locate the fact, read the
  note), ideally by two annotators with agreement reported, on a stratified sample from the targeted, non-dimensional
  subset. At an estimated 3-5 minutes per item, 200 items cost roughly 10-17 hours per annotator (estimate, not measured).
* Amendments miss corrections made in a later period without amendment (revision restatements), so even a verified
  set is a biased sample of real errors.

In the pilot, every result on amendment data is labelled "correction candidates" and kept separate from results
on official DQC tests and on injected errors.

## 4. Second AI review with document links (batch 1, 20 targeted non-dimensional candidates)

File: `results/p1_corrections/ai_document_review_batch1_NOT_HUMAN_GOLD.csv` (AI-assisted by the author with
ChatGPT; human decisions intentionally left blank). Each row cites the document page it relied on, so it can
be checked quickly by a person, but it is not human ground truth.

* Original fact stated as confirmed wrong: 6 of 20. All six are **accounting or classification corrections**
  documented in a restatement schedule (reclassified receivables, AOCI reallocated to non-controlling interest,
  warrants reclassified from equity to liabilities, non-controlling interest moved to permanent equity, a
  liability moved from non-current to current). None is a typing, sign or scale error.
* Retags (4): two keep the same value and only change the element (e.g. CostOfRevenueNet -> CostOfRevenue);
  one is a material current/non-current classification correction; one is unresolved.
* Sign flips (5) and period moves (2): none confirmed; several conflict with the stated purpose of the amendment
  (for example a 10-K/A filed to fix the auditor's signature), which suggests extraction or presentation
  differences rather than corrected errors.
* Status: 12 unclear, 6 legitimate restatement, 2 representation only.

Implications:
* Even in the "targeted fix" subset, the confirmed cases are restatement-type accounting errors. The purpose
  classifier labelled at least some restatement amendments as targeted fixes; this is a known limitation and the
  classifier is not re-tuned on this batch (it would then be evaluated on its own tuning data).
* Amendment candidates are therefore mainly a source of **accounting-classification errors**, which value-level
  data-quality rules are not designed to catch, plus tagging changes whose wrongness is often not provable.
  Data-entry errors (typo, sign, scale) are rare or unconfirmed in this source.
* For the thesis this argues for: E3 reported as exploratory; error-type calibration of injection taken only from
  patterns, not from labels; and, if natural errors stay in scope, a human-verified subset built from document links
  like these.

## 5. Student-verified labels for batch 1 (28 October 2026)

Files: `results/p1_corrections/ai_prefill_batch1_sheet_NOT_HUMAN_GOLD.xlsx` (a second AI pass that pre-filled the blind
review sheet) and `results/p1_corrections/student_verified_review_batch1.csv` (the same labels after the student checked
all 20 against the SEC documents and confirmed them). Script: `scripts/p1_student_verified_review.py`.

* Method: verification of AI pre-filled labels by the student, not a blind annotation and not an expert review. The
  student saw the AI verdicts while checking, so agreement with that pass is anchored.
* Original number wrong: 9 of 20 (7 legitimate restatements; 2 data-entry/tagging errors: item 15, wrong element
  FairValueOfDerivative instead of a change in fair value, and item 19, a quarter reported with a full-year period
  length). Not wrong: 3 (one 10-K/A that only fixed the auditor's signature, two retags with the same value).
  Unclear: 8.
* By correction type: zero changes 3 of 3 wrong; other value changes 3 of 6; sign flips 1 of 5; retags 1 of 4; period
  moves 1 of 2.
* Agreement with the first, independent AI review on "original wrong": 10 of 20. All 10 differences are between a
  decisive answer and "unknown"; there is no case where one pass says wrong and the other says not wrong.
* Implication: the conclusion of section 4 holds with one refinement. Most confirmed corrections are accounting
  restatements, but tagging errors of the kind data-quality rules target (wrong element, wrong period) do occur.
  Two AI passes over the same documents disagree on half the items, which supports an expert-annotated subset with
  two annotators in the thesis.

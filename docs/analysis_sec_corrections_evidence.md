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

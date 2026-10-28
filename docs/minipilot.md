# Mini-pilot (28 October 2026): three checks before choosing the thesis topic

Purpose: test, at low cost, the three points that could change the choice of topic. No new AI rule sets were
generated for checks 1 and 3; check 2 used nine new generations with one model. All numbers are small-sample
indications, not significance-tested results.

## 1. Leakage between development and test

Script: inline check on `results/p2_sample/sample.csv` (company = CIK).

* 240 filings from 223 companies. 8 companies have filings in both splits, all among the corrected originals.
* None of the 66 test control filings (used for E2, E4 and E5) shares a company with any development filing.
* The reference statistics behind the statistical checks exclude every filing in the experiment sample, but not other
  filings of the same companies. Earlier wording ("filings of other companies") was corrected to "filings outside the
  sample". The effect is probably small, because the statistics are per element over thousands of companies.

Conclusion: the main E2, E4 and E5 results are not inflated by company overlap.

## 2. Input test: does the official implementation fix failing translations?

Script: `scripts/p7_input_test.py`. Results: `results/minipilot/input_test_results.csv`.

Nine rules that scored 0 for both models in the pilot (condition A: rule documentation plus published element lists)
were regenerated once by Qwen2.5-Coder-7B (greedy) with, in addition, the committee's XULE source of the rule and the
definitions of the constants and functions it uses (condition B). The source context was limited to 12,000
characters; for DQC_0009, DQC_0116 and DQC_0207 the rule source itself was longer and was cut.

| Rule | Released | A: messages found | B: messages found | B: flags outside official messages | Status in B |
| --- | --- | --- | --- | --- | --- |
| DQC_0009 | before models | 0/15 | 0/15 | 0 | runs, flags nothing |
| DQC_0011 | before models | 0/38 | 0/38 | 0 | runs, flags nothing |
| DQC_0013 | before models | 0/31 | 16/31 | 25 | runs |
| DQC_0091 | before models | 0/7 | 7/7 | 3,293 | runs, flags almost every percent item |
| DQC_0116 | before models | 0/211 | 0/211 | 0 | runs, flags nothing |
| DQC_0204 | after models | 0/35 | 0/35 | 0 | error: constant not available as data |
| DQC_0207 | after models | 0/16 | 0/16 | 0 | error: type error in generated code |
| DQC_0228 | after models | 0/16 | 0/16 | 0 | error: constant not available as data |
| DQC_0241 | after models | 0/8 | 8/8 | 0 | runs, exact |

* With the official implementation, 3 of 9 rules went from zero to non-zero recall (31 of 377 messages in total).
  One is exact (DQC_0241, released after the model), one partial (DQC_0013), and one finds all messages but also
  3,293 others (DQC_0091), which makes it unusable and shows that recall on official tests alone is misleading.
* Six rules still fail. Three run but flag nothing because of logic or data-format mistakes (for example testing a
  missing dimension as `None` while the documented format is `''`, or matching element labels instead of names). Two
  crash on constants that the official code derives from taxonomy relationships, which the fact table does not hold.
  One crashes on a programming error.
* Interpretation: missing information in the rule documentation explains a minority of the failures. Most failures
  come from translating the logic onto the data, or from rules that need taxonomy information outside the fact table.
  One generation per rule with one model: an indication, not a result.

## 3. Per-rule qualification of the existing AI rule sets

Scripts: `scripts/p7_rule_qualification.py` (policies and budgets 1 and 5 fixed before the run) and
`scripts/p7_qualification_curve.py` (more budgets, added after seeing the first results; exploratory).
Results: `results/minipilot/qualification_*.csv`.

Candidates: the 24 sub-rules of the 13 generated discover and gap-closing rule sets (including repaired versions).
Data: the 66 test control filings and their calibrated injected variants, split by company into a selection half
(32 filings) and an evaluation half (34 filings, 237 injected errors). Policies only look at the selection half.
Existing controls: generic and statistical checks, plus official DQC where it ran. On the evaluation half they catch
42 of 237 injected errors and miss 195.

Policies:
* unfiltered: all sub-rules;
* generic filter (in the spirit of LeDQeR's filters, not a reimplementation): the rule set runs without error, the
  sub-rule fires, it fits the alert budget on clean filings and is not redundant with a kept sub-rule; it uses no
  existing controls and no injected errors;
* expert-aware qualification: the rule set runs without error, each kept sub-rule adds a catch on the selection half
  that the existing controls and earlier kept sub-rules miss, and the kept set fits the alert budget.

Results on the evaluation half (alerts = mean flagged facts per clean filing):

| Policy | Alert budget (selection) | Sub-rules kept | Extra errors caught beyond existing (of 195) | Alerts per clean filing |
| --- | --- | --- | --- | --- |
| unfiltered | none | 24 | 42 | 1,027 |
| generic filter | 1 | 4 | 0 | 0.35 |
| generic filter | 5 | 7 | 3 | 3.4 |
| expert-aware | 1 | 1 | 3 | 0.21 |
| expert-aware | 5 | 1 | 3 | 0.21 |
| generic filter (exploratory) | 25 / 50 / 100 | 9 / 11 / 12 | 8 / 12 / 16 | 7.1 / 31.5 / 41.1 |
| expert-aware (exploratory) | 10 / 50 / 100 | 2 / 3 / 3 | 8 / 16 / 29 | 3.5 / 26.7 / 49.5 |

* Useful sub-rules do hide inside rejected rule sets: 10 of 24 sub-rules catch at least one error beyond the existing
  controls on the selection half.
* Qualification makes AI rules quiet but leaves little value: at the pilot's gate of one alert per filing, one
  sub-rule survives and adds 3 of 195 missed errors (1.5%; the gate asks 20%). Value grows only with alerts: about
  15% of the gap at roughly 50 alerts per filing.
* For the same added catches, the expert-aware qualification needs fewer sub-rules and roughly half the alerts of the
  generic filter (8 extra at 3.5 versus 7.1 alerts; 29 extra at 49.5 versus 107 alerts).
* The kept sub-rules mainly catch sign flips, and at higher budgets some wrong elements and swapped periods. Changed
  amounts, one-digit changes, removed facts and x1000 errors beyond the existing controls are not caught at any budget.
* Caveat: very noisy sub-rules "catch" some errors only because they flag almost everything (a changed element or
  period creates a new fact key, which a flag-everything rule then flags). Qualification removes those rules.
* Caveats: 24 sub-rules from two small models; 34 evaluation filings; budgets beyond 1 and 5 were chosen after seeing
  the first results; no stability check across regenerations.

## What this means for the choice of topic

* The evaluation design holds up: no company leakage, and the checks give interpretable answers.
* The low E1 scores are not mainly an artefact of missing documentation. A larger study should still give the models
  the official implementation as a separate condition, and report precision next to recall.
* Qualification of individual AI rules is a real and measurable step: it separates noisy from useful rules and beats a
  generic filter on alerts. With these small models, the value that survives is small. Whether larger models produce
  more rules that survive is the open question for the thesis.

# EBA mini-pilot: can AI or simple static methods find expert validation rules that are later deactivated?

Date: 31 October 2026. Status: exploratory half-day test for a possible third direction. All numbers below come
from the files in `results/eba/`; scripts `scripts/p8_eba_*.py`.

## 1. Question

The EBA publishes validation rules for supervisory reporting (COREP, FINREP and others). Rules later found to be
incorrect get a deactivation date (Explanation sheet of the workbook: "primarily due to being identified as
potentially incorrect"). Question: if we look only at a rule as it was introduced, can a local open-source LLM, or a
simple static method, tell which rules will later be deactivated?

## 2. Data and labels

* Source: EBA validation rules workbooks (up to framework 3.5, published 2026-09-14, and 4.4 phase 1); URLs and
  sha256 in `results/eba/manifest.json`. All 18 release sheets were read (`results/eba/rules.csv.gz`).
* Population: manual (human-written) rules with a formula, not deactivated by the cutoff T = 2025-04-29 (release date
  of Qwen3-8B, so the model cannot have seen the later deactivations). 5,537 rules.
* Label: 1 if the rule was deactivated after T. 97 positives (base rate 1.75%).
* The positives are strongly clustered: 23 tables, and six deactivation dates (2025-06-10: 29 of the 60 sampled
  positives; 2025-09-15: 12; 2026-03-17: 12; others: 7). Many positives are families of near-identical rules (for
  example I 06.03, I 06.05 and I 06.07: "{c0010} = (sum of six columns) / 6", later corrected to the matching column).
  The effective sample size is therefore closer to the number of families than to 97.
* For 24 of the 60 sampled positives the formula changed between releases, which shows what was wrong (for example a
  wrong left-hand column, or a missing "/ 2" in C 08.01.b). For the other 36 the reason is not visible in the
  workbook.

## 3. Methods

All scores use only information available at T.

| Score | What it does |
| --- | --- |
| table history | share of the table's manual rules deactivated before T |
| formula features | logistic regression on deactivations before T (length, references, operators, severity, framework) |
| sibling rarity | how unusual the formula pattern is among rules of the same table (after ExceLint) |
| recency | later framework release = riskier (added after the first baseline run: post hoc) |
| length | number of characters of the formula (added after the LLM run: post hoc) |
| LLM auditor | Qwen3-8B (Q4, local CPU, temperature 0), sees the target rule, its tables and severity, and up to 8 other rules of the same table from the same or an earlier release; returns a score 0-10 and one sentence |
| random | random score |

LLM sample (fixed seed): 60 positives (at most 6 per table), 50 negatives from the same tables, 60 negatives from
other tables; 170 rules, about 30 seconds per rule. Prompts and answers are in `results/eba/llm_calls.jsonl`.

Evaluation: AUC (ties count as half), 95% confidence interval by bootstrapping over tables (not rules, because of the
families), AUC within table (only positive-negative pairs from the same table: "which rule in this table is
wrong?"), and expected precision in the top 20 and top 50 (`results/eba/evaluation.csv`).

## 4. Results

### 4.1 Full pool (5,537 rules, 97 positives, base rate 0.018)

| Score | AUC | 95% CI (tables) | AUC within table | Precision@50 |
| --- | --- | --- | --- | --- |
| table history | 0.38 | 0.24-0.58 | 0.50 | 0.00 |
| formula features | 0.41 | 0.23-0.71 | 0.63 | 0.00 |
| sibling rarity | 0.52 | 0.40-0.73 | 0.54 | 0.02 |
| recency (post hoc) | 0.84 | 0.73-0.90 | 0.57 | 0.14 |
| length (post hoc) | 0.81 | 0.69-0.89 | 0.65 | 0.00 |
| random | 0.47 | 0.41-0.55 | 0.43 | 0.02 |

The two methods that learn from the past (table history, formula features) point the wrong way: tables and formula
types that had deactivations before T do not have them after T. Recency and length separate well across the whole
pool, but both were chosen after looking at the data, and both mainly say "new framework, long formula". Within the
newest release alone no score does clearly better than random (AUC 0.42-0.69, all intervals include 0.5).

### 4.2 LLM sample (170 rules, 60 positives)

| Score | AUC | 95% CI (tables) | AUC within table | Precision@20 | Precision@50 |
| --- | --- | --- | --- | --- | --- |
| LLM auditor | 0.64 | 0.55-0.72 | 0.53 | 0.52 | 0.47 |
| length (post hoc) | 0.71 | 0.61-0.81 | 0.67 | 0.45 | 0.56 |
| recency (post hoc) | 0.70 | 0.64-0.77 | 0.63 | 0.50 | 0.46 |
| sibling rarity | 0.60 | 0.48-0.72 | 0.45 | 0.48 | 0.41 |
| formula features | 0.51 | 0.40-0.61 | 0.67 | 0.20 | 0.38 |
| table history | 0.44 | 0.35-0.53 | 0.50 | 0.30 | 0.30 |
| random | 0.43 | 0.36-0.51 | 0.49 | 0.25 | 0.30 |

Base rate in the sample is 0.35. Subsets:

* Same tables only (110 rules): LLM AUC 0.61 (0.52-0.70), length 0.65; within-table AUC of the LLM 0.53.
* Rules from the newest release only (38 rules, 7 tables): LLM AUC 0.53 (0.44-0.63); no score clearly above 0.5.

### 4.3 What the LLM does

* The scores are coarse: 82% of all answers are 7 or 8; positives average 7.4, negatives 6.6 (other tables) and 7.0
  (same table).
* The LLM score correlates with formula length (Spearman 0.27) and with release order (0.19). Length alone scores
  higher than the LLM.
* Within a table the LLM is at chance (0.53): it cannot say which of the rules on a table is the wrong one.
* Reasons are mostly generic: 70% contain "may", 36% "inconsistent". Of the 24 positives whose formula was later
  corrected, 13 got a score of 8 or higher, but only one reason points at the part that was later changed (v2858_m:
  column range c010-030, later c0010-0035). For the I 06.03 family the LLM gave 9 and 10 and mentioned the column
  set, but not the actual error (the left-hand column c0010).

## 5. Caveats

* Labels are noisy: deactivation can also have IT reasons, and a rule that was never deactivated is not proven
  correct.
* Few independent positives: 23 tables and six deactivation dates. Bootstrap over tables helps, but the intervals
  are still wide and the results can depend on a few families.
* Recency and length were added after looking at results; they are exploratory, not confirmatory.
* One small model, one prompt, no tuning. The model sees only cell codes (r0010, c0020), not what rows and columns
  mean. The DPM database (row and column labels, domains) was not used; this is the most obvious missing input.
* The sample is balanced (35% positives); in the real pool the base rate is 1.75%, so precision in practice would be
  much lower than the precision@k in the sample.

## 6. Conclusion for the thesis

* The data and the gold standard work: a temporal split with an official record of rules later deactivated is
  possible, free and reproducible.
* With the current setup there is no usable signal. The LLM does somewhat better than random on the mixed sample,
  but less well than formula length, and it is at chance for the practical question "which rule in this table is
  wrong". In the newest release nothing beats random.
* To make this a full direction, it would need at least row and column semantics from the DPM database, stronger or
  more models, and probably formal checks (for example comparing a rule with its family). That is a separate project
  with an uncertain outcome and few independent positives.
* Advice: keep the current direction (SEC + DQC) as the main thesis. This EBA test can be mentioned as an explored
  and rejected alternative, or as a short appendix showing that the EU gold standard exists but that a small local
  LLM does not find faulty expert rules from formula text alone.

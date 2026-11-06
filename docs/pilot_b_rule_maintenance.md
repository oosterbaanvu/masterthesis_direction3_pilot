# Pilot B: rule maintenance when a data standard changes (November 2026)

Question: when a reporting standard changes, the expert rules that check data must be updated. Is there enough real,
checkable material to study whether AI can do this (planned RQ1), is the cause of each change documented, and can a
local model update a rule? Scripts: `scripts/p10_rule_changes.py`, `scripts/p11_taxonomy_radar.py`,
`scripts/p12_rule_update_llm.py`; outputs in `results/pilot_b/`.

## 1. Corpus of real rule changes

DQC (XBRL US Data Quality Committee). The v31 repository keeps one version of every US rule per US GAAP taxonomy
year (2023 to 2026). Each assertion (sub-rule) was compared between consecutive years after removing comments and
four-digit years:

| Years | Unchanged | Logic changed | Bookkeeping only | Message only | Added | Removed |
| --- | --- | --- | --- | --- | --- | --- |
| 2023 to 2024 | 331 | 14 | 1 | 6 | 34 | 2 |
| 2024 to 2025 | 203 | 20 | 156 | 1 | 6 | 6 |
| 2025 to 2026 | 340 | 28 | 13 | 3 | 16 | 2 |

"Bookkeeping only" is almost entirely a 2025 clean-up across rules (variable `$rule_id` renamed to `$ruleId`,
`rule-focus` and `effectiveDate` lines). Without it, there are 62 substantive logic changes and 56 new assertions in
three years. An earlier estimate of "more than 130 logic changes" counted the bookkeeping clean-up and was too high.

EBA (European Banking Authority validation rules, workbook up to release 3.5). The EBA labels every rule in every
release with the kind of change ("Last Change"). Labelled changes: notation ("4 digits") 21,462, change 9,367,
reexpressed 1,864, severity 1,368, XBRL correction 757, table rename or split 518, plus combinations. Only 1,406
"change" rows (in 1,094 rules; 1,207 of the rows are rules of the EBA type "Manual") alter the formula itself; in the
other rows the change concerns other fields. After normalising three-digit to four-digit codes, 266 of the 1,406 are
notation only.

## 2. What causes the changes (manual sample)

DQC, 12 logic changes read by hand: about 7 to 9 follow from the taxonomy (renamed axes such as
`BalanceSheetLocationAxis` to `StatementOfFinancialPositionLocationBalanceAxis` in 2026, deprecated or removed
concepts, scope changes for the new employee benefit plan taxonomy), and 3 are fixes of the rule itself (a missing
exception, a missing component in a calculation, a bracket error).

EBA, 10 formula changes read by hand: 5 follow from template changes (new rows or columns, a renamed table), 3 are
corrections (arithmetic, a missing `abs()`), 2 are notation only.

## 3. Is the cause documented?

DQC: yes, machine-readably. The US GAAP taxonomy publishes per year a list of deprecated concepts with their
replacement where one exists (`us-gaap-depcon-def-YYYY.xml`, `us-gaap-depcon-pre-YYYY.xml`), and the element schema
shows which concepts disappear. Of the 62 substantive logic changes, 28 remove a concept that is deprecated or removed
in the new year (2024: 1 of 14; 2025: 7 of 20; 2026: 20 of 28). Example: the 2026 file states that
`StatementOfFinancialPositionLocationBalanceAxis` replaces `BalanceSheetLocationAxis`. Committees sometimes update a
rule only when a concept disappears from the taxonomy, years after it was deprecated.

EBA: the kind of change is documented per rule and release ("Last Change"). Template changes are documented in the
EBA data point model (DPM) per release; this was not downloaded in the pilot.

## 4. Radar baseline (no AI)

Before the new rule versions are known, flag every rule file that mentions a concept deprecated or removed in the
new taxonomy year, and compare with the rule files the committee actually changed:

| Years | Flagged | Flagged and changed | Changed | Precision | Recall |
| --- | --- | --- | --- | --- | --- |
| 2023 to 2024 | 12 | 4 | 14 | 0.33 | 0.29 |
| 2024 to 2025 | 15 | 9 | 26 | 0.60 | 0.35 |
| 2025 to 2026 | 15 | 10 | 17 | 0.67 | 0.59 |

Overall 42 flagged, 23 correct (precision 0.55), and 23 of 57 changed files found (recall 0.40). Element lists that
live in shared constant files are not attributed to individual rules yet, which lowers recall.

## 5. Updating rules: baselines and a local model

Cases: the 16 logic changes explained by the taxonomy files with old code of at most 3,000 characters (2024: 1,
2025: 4, 2026: 11). Input: the old assertion and change notes generated from the taxonomy files. Scoring on the
logic (comments, years, bookkeeping lines and message text removed) against the official new version.

| Method | Exact | Similarity |
| --- | --- | --- |
| No change (copy old rule) | 0 of 16 | 0.98 |
| Find and replace with the named replacement (no AI) | 10 of 16 | 0.99 |
| qwen2.5-coder-7b with change notes | LLM_EXACT | LLM_SIM |

LLM_NOTE

## 6. What this means for the thesis

LLM_IMPLICATIONS

Limitations: one model, one prompt, 16 cases; the manual samples are small (12 DQC, 10 EBA) and were read by one
person; the radar does not yet use constant files; EBA template changes were not linked to the DPM.

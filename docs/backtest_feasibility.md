# Backtest feasibility check (1 November 2026)

Purpose: before adding a historical backtest (planned RQ3) to the thesis, check whether we can replay SEC filings in
filing order, run the official DQC rules (Arelle + XULE) and pilot AI rules on each original filing, link every alert
to filing, rule, ruleset version and the date from which the rule was available, and compare alerts with the
student-verified corrections. Script: `scripts/p9_backtest_feasibility.py`; outputs in `results/backtest_feasibility/`.

## Setup

* Filings: 12 never-corrected filings that already had official DQC runs, plus the original filings of the 20
  student-verified corrections (17 unique filings, downloaded from EDGAR). Filed 10 February 2023 to 27 March 2025.
* Rules: official DQC rules (ruleset V31 for the US GAAP taxonomy year of the filing); AI rule set
  `qwen2.5-coder-7b/discover_greedy_repair1` from pilot 2, split into the sub-rule kept by expert-aware qualification in
  the mini-pilot (`AccountingRelationship`) and the other sub-rules (not kept).
* Two modes: historical stress test (all current rules on every filing) and time-bound (only DQC rules whose first
  release date, from the rule documentation, is on or before the filing date; the AI rules were created in October
  2026 and are not available for any filing in this period).

## Results

| Item | Result |
| --- | --- |
| Filings with official DQC results | 22 of 29 (12 reused, 10 new) |
| Not run | 5 filings use the 2022 US GAAP taxonomy, for which V31 has no ruleset; 2 downloads failed (HTTP error) |
| DQC run time | median 124 s per filing (4 CPUs) |
| AI rule set | ran on all 22 filings |
| Alerts linked to filing, filing date, rule, ruleset and availability date | 98.3%; two DQC rules (0126, 0128) have no parseable release date in their documentation |
| DQC flagged facts per filing (unique element and context) | 1.75 on never-corrected filings (pilot 2: 1.8); 9.1 on filings with verified corrections |
| AI flagged facts per never-corrected filing | kept sub-rule 0.67; other sub-rules 30.6 |
| DQC alert rows from rules released after the filing date | 404 of 886 (46%); 22 of the 32 DQC rules that fired were released after at least one of the filing dates |
| Verified corrections that could be checked | 13 of 20 (located in the XBRL instance) |
| Of these, flagged by any rule (DQC stress test, DQC time-bound, AI kept, AI not kept) | 0 of 13 |

The 13 checked corrections were labelled as 6 restatements, 2 data-entry errors, 1 representation-only change and 4
unclear.

## What this means for RQ3

1. The mechanics work: filing order, per-alert linkage and availability dates are feasible; about 2,000 filings would
   take roughly 70 CPU hours for the official rules, which is feasible on the university cluster.
2. The two backtest forms must be kept apart: almost half of today's DQC alerts on these filings come from rules that
   did not exist when the filing was made.
3. A true time-bound backtest needs older DQC releases (all releases are tagged on GitHub, v1 to v31). Whether older
   rulesets run with the current XULE processor is untested; otherwise time-bound mode can only filter current rule
   code by release date.
4. Real corrections are rarely flagged by any rule, consistent with pilot 2 (DQC flagged 1.6% of later-corrected
   numbers). Most verified corrections are restatements. RQ3 needs a larger verified set weighted towards data errors,
   and must rely on alert burden and a reviewed alert sample as well.

Limitations: small, non-random set of filings; time-bound mode uses current (V31) rule code; release dates come from
the first-release line in the rule documentation.

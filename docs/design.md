# Pilot design: stress-testing data-quality controls and AI-written rules

This document fixes the design of the direction-3 pilot before results are read. Changes after a
result is seen are logged at the bottom with the reason.

## Question

Can an AI system help a data team close gaps in its data-quality controls in a way that is reliable,
repeatable and auditable enough for a regulated institution? Concretely:

1. Which realistic errors slip through a given set of controls? (stress test)
2. Can a language model write deterministic validation rules that reproduce expert rules (translate)
   or that catch the errors the controls miss (discover, gap-closing)?
3. How does "AI as rule-writer" compare with "AI as judge" (the model labels facts directly), with
   statistical checks and with an expert rule set, at equal review effort?

## Working research question (not fixed)

*To what extent can LLM-generated validation rules provide reliable and reproducible error detection beyond
expert-defined data quality controls in financial XBRL filings?* The pilot still runs the broader comparison
(LLM judge, statistical checks, official DQC rules) so that the final scope can be chosen from evidence.

## Five evaluation dimensions, always reported separately

| | Dimension | Reference | Status of the reference |
| --- | --- | --- | --- |
| E1 | Reproducing official expert rules | DQC committee's expected messages on real filings | official, but a message is not proof of an error |
| E2 | Detecting controlled injected errors | injection log | exact, but only "value changed" |
| E3 | Detecting possible real errors | amendment correction candidates | unverified (see docs/analysis_sec_corrections_evidence.md) |
| E4 | Added detection beyond existing controls | E2/E3 minus what official DQC and statistics already flag | as E2/E3 |
| E5 | Stability, false alarms, human review needed | repeated runs; flags on never-amended filings; items per filing | flags on clean filings are alerts, not proven false positives |

## Domain discipline (no apples-to-oranges)

* One primary domain: SEC financial-statement XBRL filings. Replications (GLEIF, HMDA) are analysed
  separately with their own rule sets and units and are never pooled with SEC results.
* Unit of analysis in SEC: one reported fact (element + context). Every control - official DQC rules,
  generic rules, statistical checks, AI-written rules, AI judge - receives the same fact table parsed
  from the same instance document and returns flagged facts in the same format.
* Information available to each method is stated per comparison: rule documentation (translate),
  element metadata and filings (discover), stress-test feedback from development filings only (gap loop),
  historical statistics of other filers (statistical checks). Language models also bring pre-training
  knowledge; rules released after the model release date form a separate "unseen" stratum.
* A method that cannot handle an input is reported as not applicable, never scored as zero.

## References (what counts as correct)

| Reference | Meaning | Used for |
| --- | --- | --- |
| Official DQC test suite (expected logs on real filings) | what the expert rule reports | translate fidelity (recall of official messages) |
| Natural corrections (original vs amended filing) | values the filer later replaced | natural-error recall; calibration of injection |
| Injected errors (logged) | values we changed | stress-test coverage per error type |

Injected errors prove only that a value changed. Natural corrections are errors acknowledged by the filer,
but only those that were discovered; restatements (accounting errors) are separated from targeted
corrections by the stated purpose of the amendment.

## Error levels (stress-test operators)

L1 completeness (dropped fact), L2 sign, L3 scale x1000, L4/L6 changed amount (empirical ratios from
corrections) and one-digit error, L5 wrong element (confusion pairs observed in corrections), L7 period
swap. Placement: calibrated on the elements corrected in real amendments; uniform placement as sensitivity.

## Splits

* Control filings (never amended, 60 10-K + 60 10-Q): development half (stress feedback may be shown to
  the model) and test half (evaluation only), split by a fixed hash of the accession number.
* Corrected originals (60 10-K + 60 10-Q): evaluation only, never shown to a model.
* Official DQC cases: evaluation only.

## Models

Local, pinned GGUF builds run with llama.cpp on 4 CPU threads: Qwen2.5-Coder-7B-Instruct (released
2024-11), Qwen3-8B (2025-04, thinking disabled). One greedy run (temperature 0) and sampled runs
(temperature 0.7, seeds 1..k) per rule to measure stability. Every prompt and response is logged
with a hash (results/p3_rules/llm_calls.jsonl).

## Safety of generated code

Generated rules pass a static allow-list (no file, process or network access) and run in a child process
with CPU, memory and time limits. Nothing generated is executed outside this sandbox.

## Change log

* 2026-10-27: message-level recall excludes official messages that reference only document-level dei facts
  (they cannot be matched to the fact that triggered them); counts are reported separately.
* 2026-10-27: amendment purpose classifier revised twice after reading validation samples; the final version
  is reported with its accuracy on a held-out sample (23/30), not on the samples used to revise it.
* 2026-10-27: injection now changes every copy of a logical fact. In the first stress run, 21% of numeric facts
  were reported more than once; changing one copy created an inconsistent duplicate that the generic duplicate
  check caught (38-61% "detection"), while natural corrections almost never show this (0-3%). The first run is
  kept under results/p2_stress/attempts/run1_single_copy/ for transparency.
* 2026-10-27: the output limit for rule translation was raised from 1,200 to 2,048 tokens after DQC_0179 was cut off
  at the limit (unterminated code). Only that rule had reached the limit; it is regenerated. Greedy outputs that ended
  before the limit are unaffected by the change. The finish reason of every call is now logged.

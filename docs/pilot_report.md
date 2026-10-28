# Pilot report: AI-written data-quality rules versus expert controls on SEC XBRL filings

Status: pilot run completed on 28 October 2026 (one CPU machine, open-source local models only).
All numbers come from files in `results/`; every table names its filings and its reference.
This is exploratory evidence for choosing a thesis direction, not a confirmatory study.

## Samenvatting (NL)

- **Expertregels reproduceren (E1).** Twee kleine lokale modellen (Qwen2.5-Coder-7B, Qwen3-8B) vertaalden 18
  officiële DQC-regels naar code. Op regels van vóór de modellen vonden ze ongeveer 41% van de officiële meldingen;
  op regels die ná de modellen zijn uitgebracht 3% (Qwen2.5) en 13% (Qwen3). De meeste regels leverden 0% op;
  een paar regels 97-100%.
- **Stabiliteit (E5).** Dezelfde regel opnieuw laten schrijven gaf vaak een heel ander resultaat (bijv. 0% tot 100%
  voor dezelfde regel). Eén goede AI-regel zegt dus weinig zonder versiebeheer en herhaald testen.
- **Geïnjecteerde fouten (E2).** Bestaande generieke en statistische controles missen bijna alles behalve
  factor-1000-fouten. De officiële DQC-regels vangen 17-64% per fouttype (behalve ontbrekende feiten: 0%).
- **Aanvullende waarde (E4).** AI-regelsets die zelf regels bedenken voegden op 83 varianten 0 tot 6 extra
  vangsten toe boven DQC en statistiek, maar de sets die iets vingen gaven 450-1.000 alerts per correct verslag.
  Volgens de vooraf vastgelegde goedkeuringspoort zou geen enkele AI-regelset worden toegelaten.
- **Echte fouten (E3).** SEC-correcties zijn vooral boekhoudkundige herwerkingen; geen correctietype heeft
  geverifieerd bewijs per item. Resultaten hierop zijn verkennend.
- **AI als beoordelaar.** Qwen3-8B die zelf verdachte cijfers aanwijst, ving 2 van 42 geïnjecteerde fouten
  (maar zag door de promptlimiet slechts 19 ervan) en gaf ruim 6 alerts per correct verslag.
- **Artefact.** De `dqstress`-tool werkt end-to-end (registreren, stresstest, AI-voorstel, sandbox, poort,
  goedkeuring, rapport).

## 1. Question and scope

Working question (not fixed): *To what extent can LLM-generated validation rules provide reliable and reproducible
error detection beyond expert-defined data quality controls in financial XBRL filings?* Five dimensions are always
reported separately (see `docs/design.md`): E1 reproducing official expert rules, E2 controlled injected errors,
E3 possible real errors (unverified correction candidates), E4 added value beyond existing controls, E5 stability,
alerts and review effort.

## 2. Data and references

| Source | Content | Reference meaning |
| --- | --- | --- |
| SEC Financial Statement Data Sets 2023q1-2025q2 | 68,875 submissions, 1,294 amendment pairs | correction candidates (E3) and calibration patterns |
| EDGAR XBRL instances | 240 filings: 120 never amended (controls), 120 later corrected (originals) | input for every control |
| XBRL US DQC rules (commit `5f8cd32`) | 185 US rules, 472 official test cases on real filings | what the expert rule reports (E1); official execution as control (E2-E5) |

## 3. Methods in brief

- **Controls.** Generic schema checks; statistical checks learned from 2023-2024 filings of other companies (sign
  rarity, magnitude outlier, period jump); a naive "amounts are never negative" rule (to show false-alarm cost);
  official DQC (Arelle 2.47.3 + XULE 3.0.30055, rulesets 2023-2025); AI-written rules; an AI judge.
- **Injection.** Seven operators (sign flip, x1000, changed amount from empirical correction ratios, one digit,
  wrong element from observed confusion pairs, period swap, dropped fact), placed with weights from corrected
  elements; every copy of a duplicated fact is changed (first run, which changed one copy, is archived).
- **Models.** Qwen2.5-Coder-7B-Instruct (2024-11) and Qwen3-8B (2025-04), Q4_K_M, llama.cpp on 4 CPU threads, greedy
  plus two sampled runs (T=0.7) for stability. Every prompt and answer is logged with a hash.
- **Safety.** Generated code passes an allow-list and runs in a resource-limited child process.
- **Splits.** Stress feedback for the gap-closing loop comes from development filings only; AI rule sets are
  evaluated on test filings and corrected originals that no model saw.

## 4. Results

### E1 - Reproducing official expert rules (translation of DQC documentation into code)

Recall of official DQC messages on the committee's own test filings (greedy run; messages that point only at
document-level facts are excluded):

| Model | Stratum | Rules | Micro recall | Rules >= 80% | Rules 0% | Rules whose code runs on every case |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5-Coder-7B | released before the models | 10 | 0.41 | 1 | 6 | 8 |
| Qwen2.5-Coder-7B | released after the models | 6 | 0.03 | 0 | 5 | 5 |
| Qwen3-8B | released before the models | 10 | 0.42 | 3 | 6 | 8 |
| Qwen3-8B | released after the models | 6 | 0.13 | 1 | 4 | 5 |

Two rules had no locatable official message and are not in the table. Per-rule results:
`results/p3_rules/translate_model_comparison.csv`. The models disagree per rule (e.g. DQC_0014: 0.00 vs 0.97;
DQC_0179: 0.46 vs 0.01). A hand-written reference translation of DQC_0009 finds 15 of 16 messages, so the harness
itself does not cause the low recall.

Failure modes seen: code that crashes on the real schema (columns that do not exist), rules that run but flag nothing,
use of `eval` (blocked by the sandbox), output cut off at the token limit (fixed for one rule, logged), and rules whose
documentation refers to lists or presentation information that are not published with the rule (DQC_0228, DQC_0245;
the input inventory had classified DQC_0245 as facts-only).

### E5 - Stability across generations

Range of recall across three generations of the same rule (greedy + two samples), nine rules
(`results/p3_rules/translate_stability.csv`): Qwen3-8B 0.00-1.00 on DQC_0156 and DQC_0212, 0.05-0.99 on DQC_0109;
Qwen2.5-Coder 0.33-0.99 on DQC_0109; stable only on DQC_0156 (Qwen2.5) and DQC_0234. Regenerating a rule is
therefore not a reproducible operation; a generated rule has to be versioned and tested as code.

### E2 - Injected errors

Baseline controls on 66 test filings (strict detection, calibrated placement): the period-jump check catches about
80% of x1000 errors; everything else is caught in at most a few percent of cases, except the naive never-negative
rule (about two thirds of sign flips, at about 80 alerts per correct filing).
Official DQC on 12 test filings (83 variants), share caught: period swap 0.64, x1000 0.50, sign flip 0.25,
changed amount 0.17, one digit 0.17, wrong element 0.17, dropped fact 0.00.
Full table with every control on the same 12 filings: `results/summary/E2_catch_rate_dqc_filings.csv`.

### E4 - Added value beyond existing controls

On the same 83 variants, existing controls (official DQC + generic + statistical) catch 27. AI rule sets add:

| AI rule set (held-out filings) | Caught | Added beyond existing | Alerts per correct filing |
| --- | --- | --- | --- |
| Qwen3-8B gap-closing (sampled) | 13 | 6 | 458 |
| Qwen3-8B discover (sampled) | 6 | 4 | 1,021 |
| Qwen2.5-Coder discover (after one repair) | 2 | 1 | 36 |
| six other sets | 0 | 0 | 0-8 (most crash or are rejected) |
| AI judge Qwen3-8B (6 filings, 42 variants) | 2 | 1 | 6.2 (cap 10) |

Under the approval policy fixed in advance (`configs/approval_policy.json`: at most 1 alert per correct filing and at
least 20% of a gap caught) none of the nine AI rule sets would become a candidate.

### E3 - Correction candidates (unverified)

See `docs/analysis_sec_corrections_evidence.md`. Amendments are dominated by accounting restatements; the
document-linked AI review confirmed six accounting/classification corrections in 20 targeted items and no typing,
sign or scale error. On located candidate facts, official DQC flags 1.6% (129 facts, 9 filings), statistical checks
0.1-0.6%. AI sets that flag "many" candidates do so because they flag almost everything (92.6% at 1,021 alerts per
filing). Candidate recall is meaningless without the alert burden next to it.

### AI judge (Qwen3-8B reads a filing and lists up to 10 suspicious facts)

Qwen3-8B judged 6 of the 12 DQC test filings (clean version plus 7 injected variants each, 48 calls) and 6 corrected
originals, about 3.5 minutes per filing on 4 CPU threads. To fit the context and the CPU budget the judge sees at most
120 non-dimensional facts of the two latest periods, so only 19 of the 42 injected errors were visible to it.

| Measure | Result |
| --- | --- |
| Injected errors caught | 2 of 42 (2 of the 19 that were visible): one one-digit error, one x1000 error |
| Added beyond existing controls (same variants) | 1 |
| Flags per correct filing (cap 10) | 6.2 |
| Correction candidates flagged | 6.6% of 91 located candidate facts |

The judge raises six alerts on a correct filing while catching almost none of the injected errors; its flags also
differ in kind from rules (no reusable logic to review). Files: `results/p5_judge/`.

## 5. Negative results and limitations

- Small local models only (7-8B, 4-bit, CPU). Larger open-weight models may behave differently; the pilot cannot say.
- Compute forced subsets: official DQC on 12 test filings and 12 originals; the AI judge on 6 filings; stability on
  9 rules. Confidence intervals would be wide; no significance claims are made.
- One prompt per task, not tuned (to avoid tuning on the evaluation data); prompt design is a confounder.
- Rules are generated in Python on a fact table, not in XULE on the full DTS; some DQC rules need linkbase or
  constant lists that the model never saw, which lowers recall for reasons outside the model.
- Official test cases are mostly positive cases, so E1 measures recall only; precision of translations needs official
  DQC runs on clean filings (available only for the 12-filing subset).
- Injected errors are synthetic (one error per variant) even when calibrated; real errors may co-occur.
- Correction candidates are unverified, biased towards discovered and amended errors, and mostly accounting errors.
- The release-date split controls only part of the training-data contamination; the "after" stratum has 6 rules.
- DQC rulesets exist from taxonomy year 2023 onwards; 66 of 240 filings (2022 taxonomy) are outside the DQC comparison.
- The container restarted once during the run; all steps are resumable and no results were lost.

## 6. What this suggests for the thesis (options, not a decision)

1. **E1 as the core**: "Can LLMs reproduce a public expert DQ rule suite, and how stably?" The DQC suite with official
   tests and release dates is a strong, reusable benchmark; the pilot shows low and unstable results for small local
   models. Needs at least one larger open-weight model (e.g. on a university GPU cluster) to be convincing.
2. **E2/E4 as the core**: "What do AI-written rules add to an expert rule suite at an acceptable alert cost?" The pilot
   answer for small models is "very little"; a negative result with a clean design is still a contribution, but the
   novelty must be argued against JENGA/Homayouni (stress testing) and LeDQeR/AuDQ (rule writing).
3. **Governance and artefact as the core**: the instability and alert floods argue for gated adoption (sandbox,
   evidence, versioned approval). The artefact exists; the research question would be which evidence a reviewer needs.

See `docs/literature/novelty_matrix.md` for what is already done (do not claim) and what remains open.

## 7. Artefact

`dqstress` (src/dqstress/cli.py): register a source, run existing controls, stress-test them, let a local model
propose rules for the gaps, test a proposal in the sandbox and apply the approval gate, record a human decision, and
write an HTML report. Example: `docs/examples/dqstress_report_demo.html`.

## 8. Reproduction

See README. Every script states its inputs and outputs; long runs are resumable.

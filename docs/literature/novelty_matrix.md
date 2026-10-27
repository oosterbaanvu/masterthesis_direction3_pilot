# Novelty matrix: what the closest work already does

Purpose: avoid claiming novelty that exists. Each cell is what the cited source reports; "n/r" means not
reported in what was read (abstract and, where noted, full text). Read status is given per row. This matrix
complements [literature_review.md](literature_review.md) and must be re-checked before any thesis claim.

| Work | Read | AI role | Data | Reference for "correct" | Injected errors | Natural errors | Stability over runs | False alarms on clean data | Review effort / budget | Added value beyond existing controls | Audit / governance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AuDQ** (Biggiogera et al., arXiv 2610.26031, Oct 2026) | full text (HTML) | rule discovery by agents, human review (HITL) | Berka (Czech retail bank), H&M; public | human reviewers rate rules (good-rule rate); authors state no reference rule set exists for these datasets | no | no | 8 runs per mode for diversity; no stability analysis | n/r | reviewer agreement measured; no budget | not measured | versioned rules, governance links and replayable logs as vision |
| **LeDQeR** (Glock et al., arXiv 2609.06053, Sep 2026) | full text (HTML) | rule writer (Great Expectations) with generate-and-filter | Beers, Flights, Hospital, Tax (Raha), PCI (synthetic) | labelled dirty/clean data (F1, recall, redundancy) | benchmark errors (synthetic/injected) | no | n/r | redundancy filter on clean tuples | n/r | n/r | n/r |
| **Akella et al.** (arXiv 2509.10572, 2025, under review) | abstract | rule + code generation with RAG and guardrails | "benchmark datasets" (n/r) | n/r in abstract | n/r | n/r | n/r | n/r | n/r | n/r | rule cards |
| **Agentic retrieval DQ framework** (Fadlallah et al., arXiv 2606.13692, May 2026) | abstract | multi-agent rule generation from intended-use text | one dataset (n/r) | n/r | n/r | n/r | n/r | n/r | n/r | n/r | deterministic execution claimed |
| **ZeroED** (Ni et al., ICDE 2025) / **ForestED** (Wang et al., KDD 2026) | abstracts + literature agent | judge (hybrid: LLM criteria/trees + ML) | Raha-type benchmarks | labelled cells | benchmark errors | no | ForestED motivates instability; no stability study | precision on benchmark | n/r | n/r | explainable trees (ForestED) |
| **FinAuditing** (SIGIR 2026), **SEC-FinTables** (ACL Findings 2026) | via literature agent | judge on XBRL/financial tables | SEC filings | real DQC messages (FinAuditing); injected inconsistencies (SEC-FinTables) | SEC-FinTables yes | DQC messages as labels | n/r | n/r | n/r | n/r | n/r |
| **Homayouni et al.** (2017-2021), **JENGA** SchemaStresstest (EDBT 2021) | via literature agent | none (mutation analysis of data tests) | small or mock data; one TFDV schema | injected errors | yes | no | n/a | n/r | n/a | gaps fixed by hand (JENGA) | n/a |
| **SAVAGE** (PVLDB 2025) | via literature agent | error generation ("stress testing") | ML pipelines | model impact | yes, realistic | no | n/a | n/a | n/a | n/a | cites EU AI Act |
| **This pilot** | - | rule writer (translate, discover, gap-closing) and judge, side by side | SEC XBRL (public); GLEIF/HMDA planned | official DQC test suite (expert messages on real filings); injected errors; amendment correction candidates (unverified) | yes, calibrated on corrections | candidates only, not confirmed | sampled runs per rule | flags on never-amended filings | items to review per filing | measured beyond DQC and statistics | sandbox, approval gate, call log |

## What remains open after this check (candidate, not claimed)

1. **Evaluation against a public expert rule suite with official test cases.** AuDQ explicitly lacks a reference
   rule set; LeDQeR evaluates against labelled cells. Reproducing DQC rules and measuring recall of the
   committee's own messages on real filings, split by rule release date versus model release date, was not
   found. Risk: FinAuditing already harvests DQC messages (as labels for a judge, not as rules to reproduce).
2. **Added detection value beyond an expert rule suite.** None of the rows measures what AI rules or judges
   catch that the existing expert controls miss, at a given false-alarm and review cost.
3. **Stability and review effort as first-class outcomes.** Reported nowhere beyond AuDQ's reviewer agreement.
4. **Validity of injected errors against natural corrections in XBRL.** Not found; but the natural labels are
   unverified (see docs/analysis_sec_corrections_evidence.md), so this may only be possible on a verified subset.

Already done, do not claim: LLM-written DQ rules as such; human-in-the-loop approval; auditable deterministic
execution of generated rules; mutation-style stress testing of validation rules; LLM judges on SEC tables.

# masterthesis_direction3 — stress-testing data-quality controls with AI-written rules

MSc Artificial Intelligence thesis pilot (University of Groningen), direction 3: *when should AI be used
for data-quality control?* The pilot asks whether a language model can help a data team find and close
gaps in its validation rules, and whether the result is reliable, repeatable and auditable enough for a
regulated institution. Open data only; no client data.

**Status: pilot in progress.** Results and limitations are in [docs/pilot_report.md](docs/pilot_report.md)
(written when the runs finish). The design is fixed in [docs/design.md](docs/design.md); the literature map is in
[docs/literature/literature_review.md](docs/literature/literature_review.md).

## What is in here

| Part | Script | Output |
| --- | --- | --- |
| P1 natural corrections: original vs amended SEC filings | `scripts/p1_*.py` | `results/p1_corrections/` |
| P2 stress test: inject realistic errors, measure which controls catch them | `scripts/p2_*.py` | `results/p2_stress/` |
| P3 AI as rule-writer: translate official DQC rules; discover new rules | `scripts/p3_*.py` | `results/p3_rules/` |
| P4 gap-closing loop: stress feedback -> AI rule proposals -> held-out test | `scripts/p4_*.py` | `results/p4_gap/` |
| P5 AI as judge: the model labels facts directly | `scripts/p5_judge.py` | `results/p5_judge/` |

Library code is in `src/dqstress/` (SEC parsing, injection operators, baseline controls, sandbox for
generated code, prompts, evaluation). Unit tests: `data/env/bin/python -m pytest`.

## Data and rights

* SEC Financial Statement Data Sets and EDGAR XBRL instances: public U.S. government data, fetched with a
  declared User-Agent (set `SEC_USER_AGENT`) at no more than 2 requests per second. Not committed.
* XBRL US Data Quality Committee rules and test suite (github.com/DataQualityCommittee/dqc_us_rules):
  copyright AICPA, Calcbench, Toppan Merrill, Workiva and XBRL US; may be copied and used with the copyright
  notice. Read from a local checkout; not committed.
* Model weights (Qwen2.5-Coder-7B-Instruct, Qwen3-8B; Apache-2.0) are downloaded from Hugging Face at pinned
  revisions; checksums in `data/models/SHA256SUMS` (not committed).

## Reproduce

```bash
uv venv -p 3.12 data/env && VIRTUAL_ENV=data/env uv pip install -e ".[xbrl,llm,dev]"
export SEC_USER_AGENT="your-project contact@your-university.edu"
# acquisition and P1
PYTHONPATH=src data/env/bin/python scripts/p1_build_corrections.py
PYTHONPATH=src data/env/bin/python scripts/p1_amendment_notes.py
PYTHONPATH=src data/env/bin/python scripts/p1_analyse.py
# P2-P5: see the docstring at the top of each script for inputs and outputs
```

"""P4c: one automated repair attempt for generated rule sets that fail in the sandbox.

The rule set is run on three DEVELOPMENT filings; if it is rejected or raises an error, the same model
receives its original task, its code and the error message, and returns a corrected version
(<name>_repair1.py). This mirrors how an engineer would use the tool, and tests whether self-repair helps.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dqstress.llm.local import LocalModel, extract_code, log_call
from dqstress.rules import prompts
from dqstress.rules.sandbox import run_rule_batch
from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/p3_rules"
CONCEPTS = ROOT / "data/work/concepts.parquet"

REPAIR = """Your previous answer to the task above was this code:

```python
{code}
```

Running it on a real filing failed with: {error}

Return a corrected version of the complete code in one Python code block. Keep the same rules; only fix what is
needed. Use only the columns described in the input schema."""


def original_user_prompt(model: str, tag: str, run: str) -> str:
    for line in (RES / "llm_calls.jsonl").read_text().splitlines():
        record = json.loads(line)
        if record.get("experiment") == tag and record.get("model") == model and record.get("run") == run:
            return record["user"]
    raise LookupError(f"no logged prompt for {model} {tag} {run}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    dev = sample[(sample["group"] == "control") & (sample["adsh"].map(split_of) == "development")].head(3)
    probes = [ROOT / "data/sec_instances" / a / "facts.parquet" for a in dev["adsh"]]
    model = LocalModel(args.model, ROOT / "data/models")
    for path in args.files:
        code = path.read_text()
        results = run_rule_batch(code, probes, None, CONCEPTS)
        failures = [r for r in results.values() if r.status != "ok"]
        if not failures:
            print(path.name, "passes on development probes; no repair needed", flush=True)
            continue
        error = failures[0].detail or failures[0].status
        tag, run = path.stem.split("_", 1)
        user = original_user_prompt(args.model, tag, run) + "\n\n" + REPAIR.format(code=code, error=error)
        completion = model.complete(prompts.SYSTEM, user, temperature=0.0, max_tokens=2048)
        repaired = extract_code(completion.text) or ""
        target = path.with_name(f"{path.stem}_repair1.py")
        target.write_text(repaired)
        log_call(RES / "llm_calls.jsonl", {"experiment": f"{tag}_repair", "model": args.model, "run": run,
                                           "system": prompts.SYSTEM, "user": user, "response": completion.text,
                                           "error_shown": error, "prompt_tokens": completion.prompt_tokens,
                                           "completion_tokens": completion.completion_tokens,
                                           "finish_reason": completion.finish_reason,
                                           "seconds": round(completion.seconds, 1)})
        after = run_rule_batch(repaired, probes, None, CONCEPTS)
        print(path.name, "error:", error[:80], "-> after repair:",
              pd.Series([r.status for r in after.values()]).value_counts().to_dict(), flush=True)


if __name__ == "__main__":
    main()

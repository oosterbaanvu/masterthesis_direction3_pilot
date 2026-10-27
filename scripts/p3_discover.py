"""P3e: AI as rule-writer, discover mode (no rule documentation given).

The model sees the fact schema, metadata of the most common primary-statement elements and is asked
to propose its own validation rules. Optional --feedback FILE adds stress-test feedback (gap-closing
loop, P4): missed error types with examples from DEVELOPMENT filings only.
Generated rule sets are stored as code; their evaluation happens in the stress test (p2/p4 scripts).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from dqstress.llm.local import LocalModel, extract_code, log_call
from dqstress.rules import prompts
from dqstress.rules.sandbox import static_check

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/p3_rules"
TOP_ELEMENTS = 60


def common_elements() -> list[str]:
    reference = pd.read_parquet(ROOT / "data/work/reference_stats.parquet")
    usd = reference[reference["uom"] == "USD"].sort_values("filings", ascending=False)
    return usd["tag"].head(TOP_ELEMENTS).tolist()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--sampled", type=int, default=0)
    parser.add_argument("--feedback", type=Path)
    parser.add_argument("--tag", default="discover")
    args = parser.parse_args()
    concepts = pd.read_parquet(ROOT / "data/work/concepts.parquet")
    feedback = args.feedback.read_text() if args.feedback else ""
    user = prompts.discover_prompt(concepts, common_elements(), feedback)
    out_dir = RES / "generated" / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    model = LocalModel(args.model, ROOT / "data/models")
    runs = [("greedy", 0.0, 0)] + [(f"sample{s}", 0.7, s) for s in range(1, args.sampled + 1)]
    for run_name, temperature, seed in runs:
        target = out_dir / f"{args.tag}_{run_name}.py"
        if target.exists():
            continue
        completion = model.complete(prompts.SYSTEM, user, temperature=temperature, seed=seed, max_tokens=2000)
        code = extract_code(completion.text) or ""
        target.write_text(code)
        log_call(RES / "llm_calls.jsonl", {"experiment": args.tag, "model": args.model, "run": run_name,
                                           "temperature": temperature, "seed": seed, "system": prompts.SYSTEM,
                                           "user": user, "response": completion.text,
                                           "prompt_tokens": completion.prompt_tokens,
                                           "completion_tokens": completion.completion_tokens,
                                           "seconds": round(completion.seconds, 1)})
        print(args.tag, args.model, run_name, "static check:", static_check(code) or "ok",
              f"{completion.seconds:.0f}s", flush=True)


if __name__ == "__main__":
    main()

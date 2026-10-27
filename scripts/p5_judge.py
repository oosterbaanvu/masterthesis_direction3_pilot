"""P5: AI as judge. The model reads one filing's facts and lists the facts it considers erroneous.

Evaluated on (a) injected variants of TEST control filings and their clean versions, and (b) originals
that were later corrected. Output: results/p5_judge/judge_<model>.csv with flagged facts per filing.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from dqstress.llm.local import LocalModel, log_call
from dqstress.rules import prompts
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p5_judge"


def parse_rows(text: str) -> list[int]:
    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [int(x) for x in re.findall(r'"row"\s*:\s*(\d+)', text)]
    return [int(item["row"]) for item in items if isinstance(item, dict) and str(item.get("row", "")).isdigit()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--tasks", type=Path, required=True, help="CSV with columns task_id, path")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = pd.read_csv(args.tasks)
    out_path = OUT / f"judge_{args.model}.csv"
    done = set(pd.read_csv(out_path)["task_id"]) if out_path.exists() else set()
    model = LocalModel(args.model, ROOT / "data/models")
    for task in tasks.itertuples(index=False):
        if task.task_id in done:
            continue
        facts = parse_instance(Path(task.path)) if str(task.path).endswith(".xml") else pd.read_parquet(task.path)
        user, shown = prompts.judge_prompt(facts)
        completion = model.complete(prompts.JUDGE_SYSTEM, user, temperature=0.0, max_tokens=700)
        rows = [r for r in parse_rows(completion.text) if 0 <= r < len(shown)][:10]
        flagged = [{"qname": f"{shown.loc[r, 'prefix']}:{shown.loc[r, 'concept']}", "context_ref": shown.loc[r, "context_ref"]}
                   for r in rows]
        log_call(ROOT / "results/p3_rules/llm_calls.jsonl", {"experiment": "judge", "model": args.model,
                                                            "task": task.task_id, "system": prompts.JUDGE_SYSTEM,
                                                            "user": user, "response": completion.text,
                                                            "prompt_tokens": completion.prompt_tokens,
                                                            "completion_tokens": completion.completion_tokens,
                                                            "seconds": round(completion.seconds, 1)})
        pd.DataFrame([{"task_id": task.task_id, "shown_facts": len(shown), "flagged": json.dumps(flagged),
                       "seconds": round(completion.seconds, 1)}]).to_csv(out_path, mode="a", header=not out_path.exists(),
                                                                         index=False)
        print(task.task_id, len(flagged), f"{completion.seconds:.0f}s", flush=True)


if __name__ == "__main__":
    main()

"""P3d: AI as rule-writer, translate mode.

For each selected DQC rule and model, the model receives the rule documentation (and the element lists
published with it) and writes `check(facts, lists, concepts)`. Every generated rule is executed in the
sandbox on all official test filings of that rule and compared with the committee's reported messages.

Runs: one greedy run (temperature 0) per model and rule, plus sampled runs (temperature 0.7, seeds 1..k)
to measure how stable the generated rules are. Resumable: finished (model, rule, run) triples are skipped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dqstress.llm.local import LocalModel, extract_code, log_call
from dqstress.rules import prompts
from dqstress.rules.evaluate import message_recall
from dqstress.rules.sandbox import run_rule

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/p3_rules"
WORK = ROOT / "data/work"
DOCS = Path("/home/user/dataqualitycommittee/dqc_us_rules/docs")


def runs(sampled: int) -> list[tuple[str, float, int]]:
    return [("greedy", 0.0, 0)] + [(f"sample{s}", 0.7, s) for s in range(1, sampled + 1)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--sampled", type=int, default=0)
    parser.add_argument("--rules", nargs="*")
    args = parser.parse_args()

    selected = pd.read_csv(RES / "selected_rules.csv", dtype={"number": str})
    if args.rules:
        selected = selected[selected["rule"].isin(args.rules)]
    cases = pd.read_csv(RES / "official_cases.csv", dtype={"number": str})
    cases = cases[cases["facts_path"].notna()]
    expected = pd.read_csv(RES / "official_expected_refs.csv.gz")
    manifest = json.loads((WORK / "dqc_lists/manifest.json").read_text())
    code_dir = RES / "generated" / args.model
    code_dir.mkdir(parents=True, exist_ok=True)
    results_path = RES / f"translate_results_{args.model}.csv"
    done = pd.read_csv(results_path) if results_path.exists() else pd.DataFrame(columns=["rule", "run"])
    finished = set(zip(done["rule"], done["run"]))
    model = LocalModel(args.model, ROOT / "data/models")

    for rule in selected.itertuples(index=False):
        doc = next((DOCS / f"DQC_US_{rule.number}").glob("*.md")).read_text(errors="replace")
        list_paths = {name: Path(path) for name, path in manifest.get(rule.rule, {}).items()}
        lists = {name: pd.read_csv(path) for name, path in list_paths.items()}
        user = prompts.translate_prompt(doc, lists)
        for run_name, temperature, seed in runs(args.sampled):
            if (rule.rule, run_name) in finished:
                continue
            completion = model.complete(prompts.SYSTEM, user, temperature=temperature, seed=seed)
            code = extract_code(completion.text) or ""
            (code_dir / f"{rule.rule}_{run_name}.py").write_text(code)
            log_call(RES / "llm_calls.jsonl", {"experiment": "translate", "model": args.model, "rule": rule.rule,
                                               "run": run_name, "temperature": temperature, "seed": seed,
                                               "system": prompts.SYSTEM, "user": user, "response": completion.text,
                                               "prompt_tokens": completion.prompt_tokens,
                                               "completion_tokens": completion.completion_tokens,
                                               "seconds": round(completion.seconds, 1)})
            rows = []
            for case in cases[cases["rule"] == rule.rule].itertuples(index=False):
                result = run_rule(code, Path(case.facts_path), list_paths, WORK / "concepts.parquet")
                row = {"model": args.model, "rule": rule.rule, "run": run_name, "case_id": case.case_id,
                       "status": result.status, "detail": result.detail[:200]}
                row.update(message_recall(result.flagged, expected[expected["case_id"] == case.case_id]))
                rows.append(row)
            frame = pd.DataFrame(rows)
            frame["gen_seconds"] = round(completion.seconds, 1)
            frame.to_csv(results_path, mode="a", header=not results_path.exists(), index=False)
            print(rule.rule, run_name, frame["status"].value_counts().to_dict(),
                  f"recall {frame['messages_found'].sum()}/{frame['official_messages'].sum()}",
                  f"{completion.seconds:.0f}s", flush=True)


if __name__ == "__main__":
    main()

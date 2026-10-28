"""Mini-pilot, input test: does a failing translation improve when the model also gets the official implementation?

Condition A (pilot, already run): rule documentation + published element lists (scripts/p3_translate.py).
Condition B (this script): the same prompt plus the committee's XULE source of the rule and the definitions of the
constants and functions it references. Rules: those with zero recall for both models in condition A that have
locatable official messages. One greedy generation per rule, same model, same evaluation on the official test cases.
If recall rises in B, the documentation lacked information the rule needs; if not, the gap lies in the data the
Python rule receives (for example taxonomy navigation) or in the model.
Output: results/minipilot/input_test_results.csv and the generated code in results/minipilot/generated/.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from dqstress.llm.local import LocalModel, extract_code, log_call
from dqstress.rules import prompts
from dqstress.rules.evaluate import message_recall
from dqstress.rules.sandbox import run_rule

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/p3_rules"
OUT = ROOT / "results/minipilot"
WORK = ROOT / "data/work"
DQC = Path("/home/user/dataqualitycommittee/dqc_us_rules")
SOURCE = DQC / "dqc_us_rules/source"
RULES = ["DQC_0009", "DQC_0011", "DQC_0013", "DQC_0091", "DQC_0116",
         "DQC_0204", "DQC_0207", "DQC_0228", "DQC_0241"]
SOURCE_BUDGET = 12000
ITEM_BUDGET = 1500


def rule_source(rule: str) -> tuple[Path, str]:
    number = rule.split("_")[1]
    for year in ("2025", "2024", "2023"):
        path = SOURCE / "us" / year / f"DQC_{number}.xule"
        if path.exists():
            return path, path.read_text(errors="replace")
    raise FileNotFoundError(rule)


def definitions(folder: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Top-level constant and function definitions in the support files of one ruleset year."""
    constants, functions = {}, {}
    files = [p for p in folder.glob("*.xule") if not p.name.startswith("DQC_")] + list((SOURCE / "lib").glob("*.xule"))
    for path in files:
        blocks = re.split(r"\n(?=(?:constant|function|output|rule-name-prefix|/\*\*)\b)", path.read_text(errors="replace"))
        for block in blocks:
            if m := re.match(r"constant\s+\$(\w+)", block):
                constants.setdefault(m.group(1), block.strip())
            elif m := re.match(r"function\s+(\w+)\s*\(", block):
                functions.setdefault(m.group(1), block.strip())
    return constants, functions


def source_context(rule: str) -> str:
    path, code = rule_source(rule)
    constants, functions = definitions(path.parent)
    used_constants = [c for c in dict.fromkeys(re.findall(r"\$([A-Z][A-Z0-9_]+)", code)) if c in constants]
    used_functions = [f for f in dict.fromkeys(re.findall(r"\b([a-z_][a-z0-9_]*)\s*\(", code)) if f in functions]
    parts = [code.strip(), "\n# Definitions referenced above (from the ruleset support files)"]
    for name in used_constants:
        parts.append(constants[name][:ITEM_BUDGET] + (" ... [truncated]" if len(constants[name]) > ITEM_BUDGET else ""))
    for name in used_functions:
        parts.append(functions[name][:ITEM_BUDGET] + (" ... [truncated]" if len(functions[name]) > ITEM_BUDGET else ""))
    text = "\n\n".join(parts)
    return text[:SOURCE_BUDGET] + ("\n... [truncated]" if len(text) > SOURCE_BUDGET else "")


SECTION = """## Official implementation (XULE)

Below is the committee's own implementation of this rule in the XULE rule language, followed by the definitions of
the constants and functions it uses. XULE runs inside an XBRL processor on the full filing and its taxonomy; your
Python function only has the inputs described above. Port the logic as faithfully as these inputs allow. Where it
needs information that is not available (for example navigation of taxonomy relationships), implement the rest and
explain the gap in a short comment.

```
{source}
```

"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder-7b")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    code_dir = OUT / "generated" / args.model
    code_dir.mkdir(parents=True, exist_ok=True)
    results_path = OUT / "input_test_results.csv"
    done = pd.read_csv(results_path) if results_path.exists() else pd.DataFrame(columns=["model", "rule"])
    finished = set(zip(done["model"], done["rule"]))

    selected = pd.read_csv(RES / "selected_rules.csv", dtype={"number": str}).set_index("rule")
    cases = pd.read_csv(RES / "official_cases.csv", dtype={"number": str})
    cases = cases[cases["facts_path"].notna()]
    expected = pd.read_csv(RES / "official_expected_refs.csv.gz")
    manifest = json.loads((WORK / "dqc_lists/manifest.json").read_text())
    model = LocalModel(args.model, ROOT / "data/models", n_ctx=16384)

    for rule in RULES:
        if (args.model, rule) in finished:
            continue
        number = selected.loc[rule, "number"]
        doc = next((DQC / "docs" / f"DQC_US_{number}").glob("*.md")).read_text(errors="replace")
        list_paths = {name: Path(path) for name, path in manifest.get(rule, {}).items()}
        lists = {name: pd.read_csv(path) for name, path in list_paths.items()}
        context = source_context(rule)
        user = prompts.translate_prompt(doc, lists).replace("## Task", SECTION.format(source=context) + "## Task", 1)
        completion = model.complete(prompts.SYSTEM, user, temperature=0.0, seed=0, max_tokens=2048)
        code = extract_code(completion.text) or ""
        (code_dir / f"{rule}_greedy_source.py").write_text(code)
        log_call(RES / "llm_calls.jsonl", {"experiment": "translate_with_source", "model": args.model, "rule": rule,
                                           "run": "greedy_source", "temperature": 0.0, "seed": 0,
                                           "system": prompts.SYSTEM, "user": user, "response": completion.text,
                                           "prompt_tokens": completion.prompt_tokens,
                                           "completion_tokens": completion.completion_tokens,
                                           "finish_reason": completion.finish_reason,
                                           "seconds": round(completion.seconds, 1)})
        rows = []
        for case in cases[cases["rule"] == rule].itertuples(index=False):
            result = run_rule(code, Path(case.facts_path), list_paths, WORK / "concepts.parquet")
            row = {"model": args.model, "rule": rule, "condition": "doc_plus_source", "case_id": case.case_id,
                   "status": result.status, "detail": result.detail[:200]}
            row.update(message_recall(result.flagged, expected[expected["case_id"] == case.case_id]))
            rows.append(row)
        frame = pd.DataFrame(rows)
        frame["prompt_tokens"] = completion.prompt_tokens
        frame["gen_seconds"] = round(completion.seconds, 1)
        frame["finish_reason"] = completion.finish_reason
        previous = pd.read_csv(results_path) if results_path.exists() else pd.DataFrame()
        pd.concat([previous, frame], ignore_index=True).to_csv(results_path, index=False)
        print(rule, frame["status"].value_counts().to_dict(),
              f"recall {frame['messages_found'].sum()}/{frame['official_messages'].sum()}",
              f"prompt {completion.prompt_tokens} tok, {completion.seconds:.0f}s, {completion.finish_reason}", flush=True)


if __name__ == "__main__":
    main()

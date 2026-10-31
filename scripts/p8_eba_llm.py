"""EBA mini-pilot, step 3: can a local LLM tell which expert validation rules will later be deactivated?

Population: manual (human-written) EBA rules not deactivated by the cutoff T = 2025-04-29 (release of Qwen3-8B).
Positives: rules deactivated after T (so the model cannot have seen the deactivation). Sample, fixed by seed:
up to 6 positives per table (at most 60), and for each sampled positive one negative from the same table
(within-table question) and one negative from another table. The model sees the rule as introduced (its first
formula), its tables and severity, and up to 8 other manual rules of the same table that existed in the same or an
earlier release (never the rule that replaced it). It returns a score from 0 (certainly correct) to 10.
Output: results/eba/llm_sample.csv, results/eba/llm_scores.csv (resumable).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from p8_eba_rules import release_key  # noqa: E402

from dqstress.llm.local import LocalModel, log_call  # noqa: E402

OUT = ROOT / "results/eba"
T = pd.Timestamp("2025-04-29")
SEED = 7

SYSTEM = ("You are an experienced reviewer of EU supervisory reporting (EBA COREP and FINREP). You check validation "
          "rules for mistakes. Answer only with JSON.")

TASK = """Below is a validation rule from the EBA reporting framework, followed by other rules on the same table.
References look like {{table, row, column}}; r = row, c = column, s = sheet. Some rules in this framework were later
found to be incorrect, for example a wrong row or column reference, wrong arithmetic, a wrong comparison or sign, a
missing condition, or a check that does not hold for valid reports.

Target rule
- tables: {tables}
- severity: {severity}
- formula: {formula}
{narrative}
Other rules on the same table (for comparison):
{siblings}

How likely is it that the TARGET rule is incorrect? Return JSON {{"score": <integer 0-10, 0 = certainly correct,
10 = certainly incorrect>, "reason": "<one short sentence>"}}."""


def load_rules() -> pd.DataFrame:
    r = pd.read_csv(OUT / "rules.csv.gz", parse_dates=["deactivated_on", "reactivated_on"])
    r = r[(r["type"] == "manual") & r["formula_first"].notna()].copy()
    r["t1"] = r["tables"].fillna("").str.split(";").str[0]
    order = {s: i for i, s in enumerate(sorted(r["first_release"].unique(), key=release_key))}
    r["first_order"] = r["first_release"].map(order)
    pool = r[r["deactivated_on"].isna() | (r["deactivated_on"] > T)].copy()
    pool["label"] = (pool["deactivated_on"] > T).astype(int)
    return pool


def make_sample(pool: pd.DataFrame) -> pd.DataFrame:
    pos = pool[pool["label"] == 1].groupby("t1", group_keys=False).apply(
        lambda g: g.sample(min(len(g), 6), random_state=SEED)).head(60)
    neg = pool[pool["label"] == 0]
    rows = [pos.assign(group="positive")]
    same = []
    for t1, g in pos.groupby("t1"):
        cand = neg[neg["t1"] == t1]
        same.append(cand.sample(min(len(cand), len(g)), random_state=SEED))
    same = pd.concat(same)
    other = neg[~neg["t1"].isin(pos["t1"])].sample(len(pos), random_state=SEED)
    rows += [same.assign(group="negative_same_table"), other.assign(group="negative_other_table")]
    return pd.concat(rows).sample(frac=1, random_state=SEED).reset_index(drop=True)


def siblings(rule: pd.Series, pool_all: pd.DataFrame, k: int = 8) -> str:
    sib = pool_all[(pool_all["t1"] == rule["t1"]) & (pool_all["id"] != rule["id"])
                   & (pool_all["first_order"] <= rule["first_order"])
                   & (pool_all["replaces"].fillna("") != rule["id"])]
    sib = sib.sort_values("id").head(k)
    return "\n".join(f"- {f[:300]}" for f in sib["formula_first"]) or "- (none)"


def parse(text: str) -> tuple[float | None, str]:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        obj = json.loads(m.group(0)) if m else {}
        return float(obj.get("score")), str(obj.get("reason", ""))[:300]
    except (ValueError, TypeError, json.JSONDecodeError):
        n = re.search(r'"score"\s*:\s*(\d+)', text)
        return (float(n.group(1)) if n else None), ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3-8b")
    args = parser.parse_args()
    pool = load_rules()
    sample_path = OUT / "llm_sample.csv"
    if not sample_path.exists():
        make_sample(pool).to_csv(sample_path, index=False)
    sample = pd.read_csv(sample_path)
    print("sample:", sample["group"].value_counts().to_dict(), flush=True)
    all_manual = pd.read_csv(OUT / "rules.csv.gz")
    all_manual = all_manual[(all_manual["type"] == "manual") & all_manual["formula_first"].notna()].copy()
    all_manual["t1"] = all_manual["tables"].fillna("").str.split(";").str[0]
    order = {s: i for i, s in enumerate(sorted(all_manual["first_release"].unique(), key=release_key))}
    all_manual["first_order"] = all_manual["first_release"].map(order)

    scores_path = OUT / "llm_scores.csv"
    done = set(pd.read_csv(scores_path)["id"]) if scores_path.exists() else set()
    model = LocalModel(args.model, ROOT / "data/models")
    for rule in sample.itertuples(index=False):
        if rule.id in done:
            continue
        r = pd.Series(rule._asdict())
        narrative = f"- description: {r['narrative'][:300]}\n" if isinstance(r["narrative"], str) else ""
        user = TASK.format(tables=r["tables"], severity=r["severity"], formula=str(r["formula_first"])[:600],
                           narrative=narrative, siblings=siblings(r, all_manual))
        completion = model.complete(SYSTEM, user, temperature=0.0, seed=0, max_tokens=160)
        score, reason = parse(completion.text)
        log_call(OUT / "llm_calls.jsonl", {"experiment": "eba_rule_audit", "model": args.model, "rule": r["id"],
                                          "system": SYSTEM, "user": user, "response": completion.text,
                                          "seconds": round(completion.seconds, 1)})
        row = pd.DataFrame([{"id": r["id"], "group": r["group"], "label": r["label"], "t1": r["t1"],
                             "score": score, "reason": reason, "seconds": round(completion.seconds, 1)}])
        previous = pd.read_csv(scores_path) if scores_path.exists() else pd.DataFrame()
        pd.concat([previous, row], ignore_index=True).to_csv(scores_path, index=False)
        print(r["id"], r["group"], score, f"{completion.seconds:.0f}s", flush=True)


if __name__ == "__main__":
    main()

"""P3f: E1 (reproducing official expert rules) and E5 (stability) for translated DQC rules.

Per model and rule: share of official messages found (recall) in the greedy run and in each sampled run,
the spread across runs, how many runs execute, and the stratum (rule released before or after the models).
A message counts only if it can be located in the fact table (see rules/evaluate.py).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/p3_rules"


def main() -> None:
    selected = pd.read_csv(RES / "selected_rules.csv")[["rule", "title", "stratum", "release_date"]]
    frames = [pd.read_csv(p) for p in sorted(RES.glob("translate_results_*.csv"))]
    results = pd.concat(frames, ignore_index=True)
    per_run = (results.groupby(["model", "rule", "run"])
               .agg(cases=("case_id", "count"), executed=("status", lambda s: (s == "ok").mean()),
                    found=("messages_found", "sum"), messages=("official_messages", "sum"))
               .reset_index())
    per_run["recall"] = per_run["found"] / per_run["messages"].where(per_run["messages"] > 0)
    per_run = per_run.merge(selected, on="rule")
    per_run.to_csv(RES / "translate_per_run.csv", index=False)

    greedy = per_run[per_run["run"] == "greedy"]
    strata = (greedy.dropna(subset=["recall"]).groupby(["model", "stratum"])
              .agg(rules=("rule", "count"), micro_recall=("found", "sum"), messages=("messages", "sum"),
                   rules_recall_ge_80=("recall", lambda s: int((s >= 0.8).sum())),
                   rules_zero=("recall", lambda s: int((s == 0).sum())),
                   fully_executing=("executed", lambda s: int((s == 1).sum())))
              .reset_index())
    strata["micro_recall"] = (strata["micro_recall"] / strata["messages"]).round(3)
    strata.to_csv(RES / "translate_by_stratum.csv", index=False)

    sampled_rules = per_run[per_run["run"] != "greedy"]["rule"].unique()
    stability = (per_run[per_run["rule"].isin(sampled_rules)].dropna(subset=["recall"])
                 .groupby(["model", "rule"])["recall"]
                 .agg(runs="count", min="min", max="max", mean="mean").round(2).reset_index())
    stability["range"] = (stability["max"] - stability["min"]).round(2)
    stability.to_csv(RES / "translate_stability.csv", index=False)

    both = greedy.pivot_table(index="rule", columns="model", values="recall").round(2)
    both.to_csv(RES / "translate_model_comparison.csv")
    print(strata.to_string(index=False))
    print(stability.to_string(index=False))
    print(both.to_string())


if __name__ == "__main__":
    main()

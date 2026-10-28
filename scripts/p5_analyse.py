"""P5b: evaluate the AI judge on the same filings as the official DQC subset.

Injected: strict detection = the judge flags an injected fact; also flags on the clean version of the filing
(alerts that are not tied to an injected error). Natural: share of located correction candidates flagged.
The judge may flag at most 10 facts per filing, so its review cost is capped by design.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dqstress.inject.diff import injected_keys
from dqstress.sec.natural import gold_keys, load_gold

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/p5_judge"


def main() -> None:
    judged = pd.read_csv(RES / "judge_qwen3-8b.csv")
    judged[["adsh", "kind"]] = judged["task_id"].str.split("|", expand=True)
    flags = {row.task_id: {(f["qname"], f["context_ref"]) for f in json.loads(row.flagged)} for row in judged.itertuples()}
    gold = load_gold(ROOT / "results/p1_corrections/corrections_with_levels.csv.gz")
    rows, natural = [], []
    for row in judged.itertuples():
        if row.kind == "clean":
            rows.append({"adsh": row.adsh, "operator": "clean", "flags": len(flags[row.task_id])})
        elif row.kind == "original":
            facts = pd.read_parquet(ROOT / "data/sec_instances" / row.adsh / "facts.parquet")
            items = gold[gold["orig_adsh"] == row.adsh]
            for item, keys in zip(items.itertuples(index=False), gold_keys(facts, items)):
                natural.append({"adsh": row.adsh, "level": item.level, "located": bool(keys),
                                "judge": bool(keys & flags[row.task_id])})
        else:
            clean = pd.read_parquet(ROOT / "data/sec_instances" / row.adsh / "facts.parquet")
            variant = pd.read_parquet(ROOT / "data/stress_facts" / row.adsh / f"{row.kind}_calibrated.parquet")
            injected = injected_keys(clean, variant)
            clean_flags = flags.get(f"{row.adsh}|clean", set())
            rows.append({"adsh": row.adsh, "operator": row.kind, "flags": len(flags[row.task_id]),
                         "detected_strict": bool(flags[row.task_id] & injected),
                         "new_flags": len(flags[row.task_id] - clean_flags)})
    frame = pd.DataFrame(rows)
    frame.to_csv(RES / "judge_injected.csv", index=False)
    pd.DataFrame(natural).to_csv(RES / "judge_natural.csv", index=False)
    summary = frame[frame["operator"] != "clean"].assign(detected_strict=lambda d: d["detected_strict"].astype(float)).groupby("operator")["detected_strict"].mean().round(2)
    print(summary.to_string())
    print("flags per clean filing:", frame[frame["operator"] == "clean"]["flags"].mean())
    nat = pd.DataFrame(natural)
    if len(nat):
        located = nat[nat["located"]]
        print("natural candidates flagged:", round(located["judge"].mean(), 3), "of", len(located))


if __name__ == "__main__":
    main()

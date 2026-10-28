"""Mini-pilot, exploratory follow-up to p7_rule_qualification.py (added after seeing its results for budgets 1 and 5):
added catches beyond existing controls on the evaluation half for a range of alert budgets, and which error types
the kept sub-rules catch. Output: results/minipilot/qualification_curve.csv, qualification_kept_by_operator.csv.
"""
from __future__ import annotations

import pandas as pd

import p7_rule_qualification as q

BUDGETS = [0.5, 1, 2, 5, 10, 25, 50, 100, 250, 1000]


def main() -> None:
    tests, variants, existing = q.load_inputs()
    half = tests.set_index("adsh")["half"]
    table, catches = q.subrule_table(tests, variants, existing)
    sel, ev = table[table["half"] == "selection"], table[table["half"] == "evaluation"]
    rows, ops = [], []
    for policy in ["generic_filter", "expert_aware"]:
        for budget in BUDGETS:
            kept = q.select(policy, budget, sel, catches, existing, half)
            rows.append({"policy": policy, "budget": budget,
                         **q.evaluate(kept, ev, catches, existing, half, tests, variants)})
            caught = set().union(*[catches[r] for r in kept]) if kept else set()
            for adsh, op in caught:
                if half[adsh] == "evaluation" and not existing.get((adsh, op), False):
                    ops.append({"policy": policy, "budget": budget, "operator": op})
    pd.DataFrame(rows).to_csv(q.OUT / "qualification_curve.csv", index=False)
    by_op = pd.DataFrame(ops).groupby(["policy", "budget", "operator"]).size().rename("added").reset_index()
    by_op.to_csv(q.OUT / "qualification_kept_by_operator.csv", index=False)
    ev_vars = [(v.adsh, v.operator) for v in variants.itertuples() if half[v.adsh] == "evaluation"]
    gap = pd.Series([op for a, op in ev_vars if not existing.get((a, op), False)]).value_counts()
    print("missed by existing controls on the evaluation half, per error type:", gap.to_dict())
    print(pd.DataFrame(rows).to_string(index=False))
    print(by_op[by_op["policy"] == "expert_aware"].to_string(index=False))


if __name__ == "__main__":
    main()

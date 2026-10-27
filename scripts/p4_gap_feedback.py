"""P4a: write the stress-test feedback shown to the model in the gap-closing loop.

Only DEVELOPMENT control filings are used: per error operator, the share of injected errors that the
current controls missed, plus up to three concrete missed examples (element, old and new value).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p4_gap"
BASELINE = ["generic_schema", "stat_sign_rarity", "stat_magnitude", "stat_period_jump"]
DESCRIPTIONS = {
    "sign_flip": "a value reported with the wrong sign",
    "scale_x1000": "a value reported 1000 times too large",
    "changed_amount": "an amount changed to a different, plausible-looking amount",
    "one_digit": "one digit of an amount mistyped",
    "retag": "a correct value reported under a related but wrong element",
    "period_swap": "the current-period and prior-period values of an element swapped",
    "drop_fact": "a fact that should be reported is missing",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    detections = pd.read_csv(ROOT / "results/p2_stress/injected_detection.csv.gz", low_memory=False)
    detections = detections[(detections["applicable"] == True) & (detections["placement"] == "calibrated")]  # noqa: E712
    detections = detections[detections["adsh"].map(split_of) == "development"]
    caught = detections[detections["control"].isin(BASELINE)].groupby(["adsh", "operator"])["detected_strict"].any()
    caught = caught.reset_index()
    lines = ["\n## Stress-test feedback on development filings",
             "The current controls (schema checks, historical sign and magnitude checks, period-jump check) were tested"
             " by injecting one error into otherwise unchanged filings. Share of injected errors that were MISSED:"]
    examples = {}
    for operator, group in caught.groupby("operator"):
        missed = group[~group["detected_strict"]]
        lines.append(f"- {DESCRIPTIONS[operator]} ({operator}): missed {len(missed)}/{len(group)}")
        rows = detections[(detections["operator"] == operator) & detections["adsh"].isin(missed["adsh"])]
        sample = rows.drop_duplicates("adsh").head(3)["injected"].map(json.loads)
        examples[operator] = [c for changes in sample for c in changes][:3]
    lines.append("\nExamples of missed injected errors (element, context, value before -> after):")
    for operator, changes in examples.items():
        for change in changes:
            new = change.get("new_concept") or change["concept"]
            lines.append(f"- {operator}: {change['concept']} -> {new}, {change['old_value']} -> {change['new_value']}")
    lines.append("\nWrite rules that catch the missed error types while raising few alerts on correct filings.")
    text = "\n".join(lines)
    (OUT / "feedback_development.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()

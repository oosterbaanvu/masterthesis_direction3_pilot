"""P4b: evaluate generated rule sets (discover and gap-closing) as controls in the stress test.

Each generated rule set is run in the sandbox on every clean control filing, on every injected variant
and on every corrected original, exactly like the baseline controls. Results are written in the same
format as p2_stress_run.py (files with suffix _ai.csv.gz) so p2_analyse.py reports all controls together.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import pandas as pd

from dqstress.inject.diff import injected_keys
from dqstress.rules.sandbox import run_rule
from dqstress.sec.natural import gold_keys, load_gold
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p2_stress"
STORE = ROOT / "data/sec_instances"
VARIANTS = ROOT / "data/stress_variants"
CONCEPTS = ROOT / "data/work/concepts.parquet"


def flags_for(code: str, facts_path: Path) -> tuple[set, str]:
    result = run_rule(code, facts_path, None, CONCEPTS)
    return {(f["qname"], f["context_ref"]) for f in result.flagged}, result.status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rules", nargs="+", type=Path, help="generated rule files (name = control name)")
    args = parser.parse_args()
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    detections = pd.read_csv(OUT / "injected_detection.csv.gz", low_memory=False)
    variants = detections[detections["applicable"] == True].drop_duplicates(["adsh", "operator", "placement"])  # noqa: E712
    gold = load_gold(ROOT / "results/p1_corrections/corrections_with_levels.csv.gz")
    for rule_path in args.rules:
        code = rule_path.read_text()
        name = f"ai_{rule_path.parent.name}_{rule_path.stem}"
        rows, clean_rows, natural_rows = [], [], []
        clean_flags = {}
        for filing in sample[sample["group"] == "control"].itertuples(index=False):
            flags, status = flags_for(code, STORE / filing.adsh / "facts.parquet")
            clean_flags[filing.adsh] = flags
            clean_rows.append({"adsh": filing.adsh, "control": name, "flags": len(flags), "status": status})
        with tempfile.TemporaryDirectory() as tmp:
            for variant in variants.itertuples(index=False):
                target = VARIANTS / variant.adsh / f"{variant.operator}_{variant.placement}.xml"
                facts_path = Path(tmp) / "facts.parquet"
                variant_facts = parse_instance(target)
                variant_facts.to_parquet(facts_path)
                flags, status = flags_for(code, facts_path)
                injected = injected_keys(pd.read_parquet(STORE / variant.adsh / "facts.parquet"), variant_facts)
                new = flags - clean_flags.get(variant.adsh, set())
                rows.append({"adsh": variant.adsh, "form": variant.form, "operator": variant.operator,
                             "placement": variant.placement, "applicable": True, "control": name,
                             "new_flags": len(new), "detected_lenient": bool(new), "detected_strict": bool(new & injected),
                             "status": status})
        for filing in sample[sample["group"] == "corrected_original"].itertuples(index=False):
            facts_path = STORE / filing.adsh / "facts.parquet"
            flags, status = flags_for(code, facts_path)
            items = gold[gold["orig_adsh"] == filing.adsh]
            for item, keys in zip(items.itertuples(index=False), gold_keys(pd.read_parquet(facts_path), items)):
                natural_rows.append({"adsh": filing.adsh, "tag": item.tag, "correction_type": item.correction_type,
                                     "level": item.level, "purpose": item.purpose, "located": bool(keys),
                                     name: bool(keys & flags)})
        pd.DataFrame(natural_rows).to_csv(OUT / f"natural_detection_{name}_ai.csv.gz", index=False)
        pd.DataFrame(rows).to_csv(OUT / f"injected_detection_{name}_ai.csv.gz", index=False)
        pd.DataFrame(clean_rows).to_csv(OUT / f"clean_flags_{name}_ai.csv", index=False)
        print(name, pd.DataFrame(rows)["status"].value_counts().to_dict(),
              "strict detection", round(pd.DataFrame(rows)["detected_strict"].mean(), 3), flush=True)


if __name__ == "__main__":
    main()

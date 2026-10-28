"""P4b: evaluate generated rule sets (discover and gap-closing) as controls, on data the models never saw.

Injected errors: TEST-split control filings only (development filings were used for gap feedback), both
placements. Clean alerts: TEST-split control filings. Natural candidates: all corrected originals.
Each rule set runs in one sandboxed child process over all fact tables (fast and isolated).
Writes files with suffix _ai in results/p2_stress so p2_analyse.py reports them with the other controls.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from dqstress.inject.diff import injected_keys
from dqstress.rules.sandbox import run_rule_batch
from dqstress.sec.natural import gold_keys, load_gold
from dqstress.sec.xbrl_instance import parse_instance
from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p2_stress"
STORE = ROOT / "data/sec_instances"
VARIANTS = ROOT / "data/stress_variants"
FACTS = ROOT / "data/stress_facts"
CONCEPTS = ROOT / "data/work/concepts.parquet"


def variant_tables(variants: pd.DataFrame) -> dict[tuple, Path]:
    """Parse each variant once and cache its fact table."""
    tables = {}
    for v in variants.itertuples(index=False):
        target = FACTS / v.adsh / f"{v.operator}_{v.placement}.parquet"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            parse_instance(VARIANTS / v.adsh / f"{v.operator}_{v.placement}.xml").to_parquet(target)
        tables[(v.adsh, v.operator, v.placement)] = target
    return tables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rules", nargs="+", type=Path)
    args = parser.parse_args()
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    test_controls = sample[(sample["group"] == "control") & (sample["adsh"].map(split_of) == "test")]
    originals = sample[sample["group"] == "corrected_original"]
    detections = pd.read_csv(OUT / "injected_detection.csv.gz", low_memory=False)
    variants = detections[(detections["applicable"] == True)  # noqa: E712
                          & detections["adsh"].isin(test_controls["adsh"])].drop_duplicates(["adsh", "operator", "placement"])
    tables = variant_tables(variants)
    gold = load_gold(ROOT / "results/p1_corrections/corrections_with_levels.csv.gz")
    clean_paths = {a: STORE / a / "facts.parquet" for a in test_controls["adsh"]}
    original_paths = {a: STORE / a / "facts.parquet" for a in originals["adsh"]}

    for rule_path in args.rules:
        code = rule_path.read_text()
        name = f"ai_{rule_path.parent.name}_{rule_path.stem}"
        all_paths = list(clean_paths.values()) + list(tables.values()) + list(original_paths.values())
        results = run_rule_batch(code, all_paths, None, CONCEPTS)
        result_of = lambda path: results[str(Path(path).resolve())]  # noqa: E731
        flags_of = lambda path: {(f["qname"], f["context_ref"]) for f in result_of(path).flagged}  # noqa: E731

        clean_rows, rows, natural_rows = [], [], []
        clean_flags = {}
        for adsh, path in clean_paths.items():
            clean_flags[adsh] = flags_of(path)
            clean_rows.append({"adsh": adsh, "control": name, "flags": len(clean_flags[adsh]),
                               "status": result_of(path).status})
        for (adsh, operator, placement), path in tables.items():
            injected = injected_keys(pd.read_parquet(clean_paths[adsh]), pd.read_parquet(path))
            new = flags_of(path) - clean_flags[adsh]
            rows.append({"adsh": adsh, "operator": operator, "placement": placement, "applicable": True,
                         "control": name, "new_flags": len(new), "detected_lenient": bool(new),
                         "detected_strict": bool(new & injected), "status": result_of(path).status})
        for adsh, path in original_paths.items():
            items = gold[gold["orig_adsh"] == adsh]
            flags = flags_of(path)
            for item, keys in zip(items.itertuples(index=False), gold_keys(pd.read_parquet(path), items)):
                natural_rows.append({"adsh": adsh, "tag": item.tag, "correction_type": item.correction_type,
                                     "level": item.level, "purpose": item.purpose, "located": bool(keys),
                                     name: bool(keys & flags)})
        pd.DataFrame(rows).to_csv(OUT / f"injected_detection_{name}_ai.csv.gz", index=False)
        pd.DataFrame(clean_rows).to_csv(OUT / f"clean_flags_{name}_ai.csv", index=False)
        pd.DataFrame(natural_rows).to_csv(OUT / f"natural_detection_{name}_ai.csv.gz", index=False)
        frame = pd.DataFrame(rows)
        statuses = pd.Series([r.status for r in results.values()]).value_counts().to_dict()
        print(name, statuses, "strict", round(frame["detected_strict"].mean(), 3),
              "alerts/clean filing", round(pd.DataFrame(clean_rows)["flags"].mean(), 2), flush=True)


if __name__ == "__main__":
    main()

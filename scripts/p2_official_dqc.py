"""P2e: official DQC rules as a control in the stress test (subset, because one run takes ~2.5 min on 4 CPUs).

Subset (fixed): the first N TEST control filings and the first N corrected originals in sample order whose
US GAAP taxonomy year has a compiled DQC ruleset. For each control filing: the clean instance and the seven
calibrated variants. Output rows use the format of p2_stress_run.py, control name 'official_dqc'.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from dqstress.dqc import run_official
from dqstress.sec.natural import gold_keys, load_gold
from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p2_stress"
STORE = ROOT / "data/sec_instances"
VARIANTS = ROOT / "data/stress_variants"
WORK = ROOT / "data/dqc_runs"


def flag_set(frame: pd.DataFrame) -> set:
    return set(zip(frame["qname"], frame["context_ref"])) if len(frame) else set()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=12)
    args = parser.parse_args()
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    detections = pd.read_csv(OUT / "injected_detection.csv.gz", low_memory=False)
    variants = detections[(detections["applicable"] == True) & (detections["placement"] == "calibrated")]  # noqa: E712
    variants = variants.drop_duplicates(["adsh", "operator"])
    rows_path, clean_path, natural_path = (OUT / "injected_detection_official_dqc.csv.gz",
                                           OUT / "clean_flags_official_dqc.csv", OUT / "natural_detection_official_dqc.csv.gz")
    rows, clean_rows, natural_rows = [], [], []

    controls = sample[(sample["group"] == "control") & (sample["adsh"].map(split_of) == "test")]
    used = 0
    for filing in controls.itertuples(index=False):
        if used >= args.n:
            break
        instance = STORE / filing.adsh / filing.instance
        if run_official.ruleset_for(instance) is None:
            continue
        folder = WORK / filing.adsh
        folder.mkdir(parents=True, exist_ok=True)
        run_official.fetch_support_files(filing.cik, filing.adsh, folder)
        shutil.copy(instance, folder / filing.instance)
        status, clean = run_official.run(folder / filing.instance, folder / "clean.json")
        clean_rows.append({"adsh": filing.adsh, "control": "official_dqc", "flags": len(flag_set(clean)), "status": status})
        if status != "ok":
            continue
        used += 1
        for variant in variants[variants["adsh"] == filing.adsh].itertuples(index=False):
            target = folder / f"{variant.operator}.xml"
            shutil.copy(VARIANTS / filing.adsh / f"{variant.operator}_calibrated.xml", target)
            status, flags = run_official.run(target, folder / f"{variant.operator}.json")
            injected = {(c["new_concept"] or c["concept"], c["context_ref"]) for c in json.loads(variant.injected)}
            new = flag_set(flags) - flag_set(clean)
            rows.append({"adsh": filing.adsh, "form": filing.form, "operator": variant.operator, "placement": "calibrated",
                         "applicable": status == "ok", "control": "official_dqc", "new_flags": len(new),
                         "detected_lenient": bool(new), "detected_strict": bool(new & injected), "status": status})
            pd.DataFrame(rows).to_csv(rows_path, index=False)
        pd.DataFrame(clean_rows).to_csv(clean_path, index=False)
        print("control filing", used, filing.adsh, flush=True)

    gold = load_gold(ROOT / "results/p1_corrections/corrections_with_levels.csv.gz")
    used = 0
    for filing in sample[sample["group"] == "corrected_original"].itertuples(index=False):
        if used >= args.n:
            break
        instance = STORE / filing.adsh / filing.instance
        if run_official.ruleset_for(instance) is None:
            continue
        folder = WORK / filing.adsh
        folder.mkdir(parents=True, exist_ok=True)
        run_official.fetch_support_files(filing.cik, filing.adsh, folder)
        shutil.copy(instance, folder / filing.instance)
        status, flags = run_official.run(folder / filing.instance, folder / "original.json")
        if status != "ok":
            continue
        used += 1
        items = gold[gold["orig_adsh"] == filing.adsh]
        facts = pd.read_parquet(STORE / filing.adsh / "facts.parquet")
        for item, keys in zip(items.itertuples(index=False), gold_keys(facts, items)):
            natural_rows.append({"adsh": filing.adsh, "tag": item.tag, "correction_type": item.correction_type,
                                 "level": item.level, "purpose": item.purpose, "located": bool(keys),
                                 "official_dqc": bool(keys & flag_set(flags))})
        pd.DataFrame(natural_rows).to_csv(natural_path, index=False)
        print("corrected original", used, filing.adsh, flush=True)


if __name__ == "__main__":
    main()

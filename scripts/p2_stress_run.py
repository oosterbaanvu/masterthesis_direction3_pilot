"""P2c: stress test of baseline controls on SEC filings, plus natural-error recall.

Part A (injected): for every never-amended control filing, run each control on the clean filing and on
variants with one injected error per operator (calibrated placement from P1 corrections, and uniform
placement as sensitivity). A variant counts as detected by a control when the control raises a flag
that it did not raise on the clean filing (lenient), and when that new flag points at an injected fact
(strict).

Part B (natural): for every original filing that was later corrected, check which controls flag the
facts that the amendment changed (non-dimensional facts only, matched on element, period and unit).
"""
from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from dqstress.controls import generic, statistical
from dqstress.inject.xbrl_inject import OPERATORS, inject
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p2_stress"
STORE = ROOT / "data/sec_instances"
VARIANTS = ROOT / "data/stress_variants"
SEED = 20261029
CORRECTION_TYPES = {"sign_flip": ["sign_flip", "scale_and_sign"], "scale_x1000": ["scale"],
                    "changed_amount": ["other_value"], "one_digit": ["other_value"], "period_swap": ["period_move"],
                    "drop_fact": ["fact_added"], "retag": ["retag"]}


def calibration() -> tuple[dict, list[float], list[tuple[str, str, float]]]:
    corr = pd.read_csv(ROOT / "results/p1_corrections/corrections_with_levels.csv.gz", low_memory=False)
    dq = corr[corr["purpose"].isin(["targeted_fix", "xbrl_fix"])]
    weights = {}
    for operator, types in CORRECTION_TYPES.items():
        part = dq[dq["correction_type"].isin(types)]
        weights[operator] = (part.groupby("tag")["orig_adsh"].nunique() + 0.1).to_dict()
    amounts = dq[dq["correction_type"] == "other_value"]
    ratios = (amounts["amend_value"] / amounts["orig_value"]).replace([np.inf, -np.inf], np.nan).dropna()
    ratios = ratios[(np.abs(np.log10(ratios.abs())) > 5e-4) & (ratios > 0)]
    # Injection writes the value as originally (wrongly) filed, i.e. the inverse of the correction.
    amount_ratios = list((1 / ratios).astype(float))
    retags = dq[dq["correction_type"] == "retag"].groupby(["tag", "new_tag"])["orig_adsh"].nunique().reset_index()
    retag_pairs = [(wrong, right, float(n)) for wrong, right, n in retags.itertuples(index=False)]
    return weights, amount_ratios, retag_pairs


def run_controls(facts: pd.DataFrame, controls: dict) -> dict[str, set]:
    return {name: set(map(tuple, control(facts))) for name, control in controls.items()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    reference = pd.read_parquet(ROOT / "data/work/reference_stats.parquet")
    controls = generic.CONTROLS | statistical.controls(reference)
    weights, amount_ratios, retag_pairs = calibration()
    (OUT / "calibration_summary.json").write_text(json.dumps(
        {"operators": {k: len(v) for k, v in weights.items()}, "amount_ratios": len(amount_ratios),
         "amount_ratio_quantiles": pd.Series(amount_ratios).quantile([.1, .5, .9]).round(3).to_dict(),
         "retag_pairs": len(retag_pairs)}, indent=2))

    rows, clean_rows = [], []
    for filing in sample[sample["group"] == "control"].itertuples(index=False):
        instance = STORE / filing.adsh / filing.instance
        clean = run_controls(pd.read_parquet(STORE / filing.adsh / "facts.parquet"), controls)
        clean_rows += [{"adsh": filing.adsh, "control": c, "flags": len(f)} for c, f in clean.items()]
        for placement in ("calibrated", "uniform"):
            for operator in OPERATORS:
                rng = random.Random(f"{SEED}-{filing.adsh}-{operator}-{placement}")
                target = VARIANTS / filing.adsh / f"{operator}_{placement}.xml"
                injection = inject(instance, operator, 1, rng, target,
                                   concept_weights=weights[operator] if placement == "calibrated" else None,
                                   amount_ratios=amount_ratios, retag_pairs=retag_pairs)
                base = {"adsh": filing.adsh, "form": filing.form, "operator": operator, "placement": placement}
                if injection is None:
                    rows.append(base | {"applicable": False})
                    continue
                injected = {(c["new_concept"] or c["concept"], c["context_ref"]) for c in injection.changes}
                flags = run_controls(parse_instance(target), controls)
                for name in controls:
                    new = flags[name] - clean[name]
                    rows.append(base | {"applicable": True, "control": name, "new_flags": len(new),
                                        "detected_lenient": bool(new), "detected_strict": bool(new & injected),
                                        "injected": json.dumps(injection.changes)[:2000]})
    pd.DataFrame(rows).to_csv(OUT / "injected_detection.csv.gz", index=False)
    pd.DataFrame(clean_rows).to_csv(OUT / "clean_flags.csv", index=False)

    # Part B: natural corrections in originals.
    corr = pd.read_csv(ROOT / "results/p1_corrections/corrections_with_levels.csv.gz", low_memory=False)
    corr = corr[corr["segments"].isna() & corr["correction_type"].isin(
        ["sign_flip", "scale", "scale_and_sign", "other_value", "zero_change", "retag", "period_move"])]
    natural = []
    for filing in sample[sample["group"] == "corrected_original"].itertuples(index=False):
        facts = pd.read_parquet(STORE / filing.adsh / "facts.parquet")
        flags = run_controls(facts, controls)
        gold = corr[corr["orig_adsh"] == filing.adsh]
        plain = facts[facts["is_numeric"] & (facts["dimensions"] == "")].copy()
        plain["qtrs"] = [round(((date.fromisoformat(e[:10]) - date.fromisoformat(s[:10])).days) / 91) if s and e else 0
                         for s, e in zip(plain["start"], plain["end"])]
        plain["month_end"] = pd.to_datetime(plain["end"]).dt.to_period("M").dt.to_timestamp("M").dt.strftime("%Y%m%d")
        for item in gold.itertuples(index=False):
            ddate = str(int(item.ddate))
            match = plain[(plain["concept"] == item.tag) & (plain["qtrs"] == int(item.qtrs))
                          & (plain["unit"] == item.uom)
                          & (pd.to_datetime(plain["month_end"]).sub(pd.to_datetime(ddate)).abs().dt.days <= 31)]
            keys = set(zip(match["prefix"] + ":" + match["concept"], match["context_ref"]))
            row = {"adsh": filing.adsh, "tag": item.tag, "correction_type": item.correction_type,
                   "level": item.level, "purpose": item.purpose, "located": bool(keys)}
            for name, flagged in flags.items():
                row[name] = bool(keys & flagged)
            natural.append(row)
        for name, flagged in flags.items():
            natural.append({"adsh": filing.adsh, "tag": "__all_flags__", "correction_type": "__count__",
                            "control": name, "flags": len(flagged)})
    pd.DataFrame(natural).to_csv(OUT / "natural_detection.csv.gz", index=False)
    print("done", len(rows), "injected rows;", len(natural), "natural rows")


if __name__ == "__main__":
    main()

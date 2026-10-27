"""P2a: choose the SEC experiment sample and download the XBRL instances.

Sample (fixed seed): originals that were later corrected (stratified by base form and by
whether a numeric, element or period correction occurred) plus never-amended controls.
Instances are stored under data/sec_instances/ and parsed to parquet fact tables.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dqstress.sec import edgar
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "results/p1_corrections"
OUT = ROOT / "results/p2_sample"
STORE = ROOT / "data/sec_instances"
PER_STRATUM = 60
SEED = 20261028
NUMERIC = ["n_sign_flip", "n_scale", "n_scale_and_sign", "n_other_value", "n_zero_change"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = pd.read_csv(P1 / "amendment_pairs.csv", dtype=str)
    summary = pd.read_csv(P1 / "pair_summary.csv")
    for column in NUMERIC + ["n_retag", "n_period_move"]:
        if column not in summary:
            summary[column] = 0
    summary["has_correction"] = (summary[NUMERIC + ["n_retag", "n_period_move"]].sum(axis=1) > 0)
    corrected = summary[(summary["kind"] == "full_refiling") & summary["has_correction"]]
    corrected = corrected.merge(pairs, on=["orig_adsh", "amend_adsh", "base_form"])
    corrected = corrected.drop_duplicates("orig_adsh")
    picked = pd.concat([g.sample(n=min(len(g), PER_STRATUM), random_state=SEED)
                        for _, g in corrected.groupby("base_form")])
    sample = pd.DataFrame({"adsh": picked["orig_adsh"], "cik": picked["cik"], "form": picked["base_form"],
                           "instance": picked["orig_instance"], "group": "corrected_original",
                           "amend_adsh": picked["amend_adsh"]})
    controls = pd.read_csv(P1 / "control_filings.csv", dtype=str)
    controls = pd.concat([g.sample(n=min(len(g), PER_STRATUM), random_state=SEED)
                          for _, g in controls.groupby("form")])
    sample = pd.concat([sample, pd.DataFrame({"adsh": controls["adsh"], "cik": controls["cik"],
                                              "form": controls["form"], "instance": controls["instance"],
                                              "group": "control", "amend_adsh": None})])
    statuses = []
    for row in sample.itertuples(index=False):
        target = STORE / row.adsh / row.instance
        status = "ok"
        try:
            edgar.download(f"{edgar.filing_folder(row.cik, row.adsh)}/{row.instance}", target)
            facts = parse_instance(target)
            facts.to_parquet(STORE / row.adsh / "facts.parquet", index=False)
            status = f"ok:{len(facts)}"
        except Exception as error:
            status = f"error:{type(error).__name__}:{error}"[:200]
        statuses.append(status)
    sample["status"] = statuses
    sample.to_csv(OUT / "sample.csv", index=False)
    print(json.dumps(sample.groupby("group")["status"].apply(lambda s: s.str.startswith("ok").sum()).to_dict()))
    print(sample[~sample["status"].str.startswith("ok")].head())


if __name__ == "__main__":
    main()

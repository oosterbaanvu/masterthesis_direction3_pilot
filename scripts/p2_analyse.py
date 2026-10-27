"""P2d: coverage matrix (error type x control), alert burden and natural-error recall.

Optional extra result files (AI rules, official DQC) are appended when present, so the same tables
cover every control. Writes results/p2_stress/coverage_*.csv and natural_recall.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p2_stress"


def load(name: str) -> pd.DataFrame:
    frames = [pd.read_csv(path, low_memory=False) for path in sorted(OUT.glob(f"{name}*.csv.gz"))]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    injected = load("injected_detection")
    injected = injected[injected["applicable"] == True]  # noqa: E712
    injected["split"] = injected["adsh"].map(split_of)
    coverage = (injected.groupby(["split", "placement", "operator", "control"])
                .agg(variants=("adsh", "count"), strict=("detected_strict", "mean"), lenient=("detected_lenient", "mean"))
                .reset_index())
    coverage.to_csv(OUT / "coverage_long.csv", index=False)
    for split in ("development", "test"):
        part = coverage[(coverage["split"] == split) & (coverage["placement"] == "calibrated")]
        part.pivot(index="operator", columns="control", values="strict").round(2).to_csv(OUT / f"coverage_strict_{split}.csv")
    applicability = (load("injected_detection").drop_duplicates(["adsh", "operator", "placement"])
                     .groupby(["placement", "operator"])["applicable"].mean().round(2).reset_index())
    applicability.to_csv(OUT / "operator_applicability.csv", index=False)

    clean = pd.concat([pd.read_csv(p) for p in sorted(OUT.glob("clean_flags*.csv"))])
    burden = clean.groupby("control")["flags"].agg(["mean", "median", lambda s: (s > 0).mean()]).round(2)
    burden.columns = ["mean_flags_per_clean_filing", "median", "share_filings_with_flags"]
    burden.to_csv(OUT / "alert_burden_clean_filings.csv")

    natural = load("natural_detection")
    gold = natural[natural["correction_type"] != "__count__"]
    gold = gold[gold["located"] == True]  # noqa: E712
    control_cols = [c for c in gold.columns if c not in {"adsh", "tag", "correction_type", "level", "purpose",
                                                           "located", "control", "flags"}]
    # Each result file holds all gold facts for its own controls; average each control over its own rows.
    recall = gold.groupby(["purpose", "level"])[control_cols].agg(lambda s: s.dropna().astype(float).mean()).round(3)
    baseline_rows = gold[gold[control_cols[0]].notna()]
    recall.insert(0, "facts", baseline_rows.groupby(["purpose", "level"]).size())
    recall.to_csv(OUT / "natural_recall.csv")
    per_filing = gold.groupby("adsh")[control_cols].agg(lambda s: s.dropna().astype(bool).any()).mean().round(3)
    per_filing.to_csv(OUT / "natural_filing_recall.csv")
    print(coverage[(coverage["placement"] == "calibrated") & (coverage["split"] == "test")]
          .pivot(index="operator", columns="control", values="strict").round(2).to_string())
    print(burden.to_string())
    print(recall.to_string())


if __name__ == "__main__":
    main()

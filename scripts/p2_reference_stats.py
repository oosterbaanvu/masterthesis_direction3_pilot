"""P2b: historical reference statistics per element for the statistical controls.

From FSDS 2023q1-2024q4 10-K/10-Q filings (excluding every filing in the experiment sample):
for each us-gaap element without dimensions, in USD or shares, the number of filings, the share
of filings reporting it negative, and the median and MAD of log10 |value|.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QUARTERS = [f"{y}q{q}" for y in (2023, 2024) for q in (1, 2, 3, 4)]


def main() -> None:
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    excluded = set(sample["adsh"]) | set(sample["amend_adsh"].dropna())
    frames = []
    for quarter in QUARTERS:
        with zipfile.ZipFile(ROOT / f"data/sec_fsds/{quarter}.zip") as archive:
            sub = pd.read_csv(archive.open("sub.txt"), sep="\t", dtype=str, usecols=["adsh", "form"], keep_default_na=False)
            keep = set(sub.loc[sub["form"].isin(["10-K", "10-Q"]), "adsh"]) - excluded
            for chunk in pd.read_csv(archive.open("num.txt"), sep="\t", dtype=str, keep_default_na=False, quoting=3,
                                     usecols=["adsh", "tag", "version", "uom", "segments", "coreg", "value"],
                                     chunksize=2_000_000):
                chunk = chunk[chunk["adsh"].isin(keep) & (chunk["segments"] == "") & (chunk["coreg"] == "")
                              & chunk["uom"].isin(["USD", "shares"]) & chunk["version"].str.startswith("us-gaap")]
                chunk = chunk.assign(value=pd.to_numeric(chunk["value"], errors="coerce")).dropna(subset=["value"])
                frames.append(chunk[["adsh", "tag", "uom", "value"]])
        print(quarter, flush=True)
    num = pd.concat(frames, ignore_index=True)
    num["negative"] = num["value"] < 0
    nonzero = num[num["value"] != 0].assign(log=lambda d: np.log10(d["value"].abs()))
    sign = num.groupby(["tag", "uom"]).agg(filings=("adsh", "nunique")).reset_index()
    neg = num[num["negative"]].groupby(["tag", "uom"])["adsh"].nunique().rename("negative_filings").reset_index()
    mag = nonzero.groupby(["tag", "uom"])["log"].agg(log_median="median",
                                                     log_mad=lambda s: float(np.median(np.abs(s - s.median())))).reset_index()
    stats = sign.merge(neg, how="left").merge(mag, how="left").fillna({"negative_filings": 0})
    stats["share_negative"] = stats["negative_filings"] / stats["filings"]
    stats.to_parquet(ROOT / "data/work/reference_stats.parquet", index=False)
    print(len(stats), "element-unit pairs;", int((stats["filings"] >= 30).sum()), "with at least 30 filings")


if __name__ == "__main__":
    main()

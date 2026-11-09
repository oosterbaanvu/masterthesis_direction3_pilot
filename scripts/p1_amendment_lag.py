"""How long after the original filing does an SEC amendment arrive?

Input:  results/p1_corrections/amendment_pairs.csv (original and amended filing per pair, with acceptance times)
Output: results/p1_corrections/amendment_lag.json

Only originals accepted in 2023 are used for the shares, because the Financial Statement Data Sets in the pilot
end in 2025q2: every 2023 original has at least 18 months of follow-up. Amendments that arrive later than the end of
the data are not observed, so the shares are slightly optimistic (conditional on an amendment by mid-2025).
"""

import csv
import json
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "p1_corrections" / "amendment_pairs.csv"
OUT = ROOT / "results" / "p1_corrections" / "amendment_lag.json"
FMT = "%Y-%m-%d %H:%M:%S"


def lag_days(row: dict) -> int:
    return (datetime.strptime(row["amend_accepted"], FMT) - datetime.strptime(row["orig_accepted"], FMT)).days


def main() -> None:
    rows = list(csv.DictReader(SRC.open()))
    all_lags = [lag_days(r) for r in rows]
    lags_2023 = [lag_days(r) for r in rows if r["orig_accepted"].startswith("2023")]
    n = len(lags_2023)
    summary = {
        "pairs": len(all_lags),
        "median_days_all_pairs": statistics.median(all_lags),
        "originals_2023": n,
        "median_days_originals_2023": statistics.median(lags_2023),
        "share_within_days_originals_2023": {
            str(d): round(sum(x <= d for x in lags_2023) / n, 3) for d in (30, 90, 180, 365)
        },
        "max_days_originals_2023": max(lags_2023),
        "note": "Conditional on an amendment accepted by 2025q2; later amendments are not observed.",
    }
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

"""P1c: natural error profile of SEC amendments.

Joins amendment pairs, per-pair change counts and the stated purpose of each amendment, maps
correction types to the error levels used by the stress tester and writes summary tables.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dqstress.sec.amendment_reasons import primary_purpose

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "results/p1_corrections"

LEVELS = {
    "fact_added": "L1 completeness (fact missing in original)",
    "fact_removed": "L1 completeness (fact dropped in amendment)",
    "nil_change": "L1 completeness (nil value filled or emptied)",
    "sign_flip": "L2 sign",
    "scale_and_sign": "L2 sign",
    "scale": "L3 scale (power of ten)",
    "other_value": "L4/L6 changed amount",
    "zero_change": "L4/L6 changed amount (to or from zero)",
    "retag": "L5 wrong element",
    "period_move": "L7 wrong period",
    "precision": "representation only (rounding)",
}


def main() -> None:
    pairs = pd.read_csv(P1 / "amendment_pairs.csv", dtype=str)
    summary = pd.read_csv(P1 / "pair_summary.csv")
    notes = pd.read_csv(P1 / "amendment_notes.csv")
    notes["purpose"] = [primary_purpose(n if isinstance(n, str) else None) for n in notes["note_excerpt"]]
    corrections = pd.read_csv(P1 / "corrections.csv.gz", low_memory=False)
    corrections["level"] = corrections["correction_type"].map(LEVELS)
    corrections = corrections.merge(notes[["amend_adsh", "purpose"]], on="amend_adsh", how="left")
    corrections.to_csv(P1 / "corrections_with_levels.csv.gz", index=False)

    full = summary[summary["kind"] == "full_refiling"].merge(notes[["amend_adsh", "purpose"]], on="amend_adsh", how="left")
    numeric_cols = [c for c in ["n_sign_flip", "n_scale", "n_scale_and_sign", "n_other_value", "n_zero_change"] if c in full]
    full["numeric_changes"] = full[numeric_cols].sum(axis=1)
    by_purpose = full.groupby("purpose").agg(
        amendments=("amend_adsh", "count"),
        with_numeric_change=("numeric_changes", lambda s: int((s > 0).sum())),
        median_numeric_changes=("numeric_changes", "median"),
        with_retag=("n_retag", lambda s: int((s > 0).sum())),
        with_period_move=("n_period_move", lambda s: int((s > 0).sum())),
    ).reset_index()
    by_purpose.to_csv(P1 / "table_amendments_by_purpose.csv", index=False)

    level_counts = (corrections.groupby(["level", "purpose"]).agg(facts=("tag", "size"), filings=("orig_adsh", "nunique"))
                    .reset_index())
    level_counts.to_csv(P1 / "table_levels_by_purpose.csv", index=False)
    pivot = level_counts.pivot_table(index="level", columns="purpose", values="filings", fill_value=0)
    print(by_purpose.to_string(index=False))
    print(pivot.to_string())

    # Correction profile used to calibrate SEC injection: only amendments whose stated purpose is a
    # targeted correction (not restatements, not non-financial re-filings), primary-statement facts only.
    dq = corrections[corrections["purpose"].isin(["targeted_fix", "xbrl_fix"])
                     & corrections["correction_type"].isin(["sign_flip", "scale_and_sign", "scale", "other_value",
                                                            "zero_change", "retag", "period_move"])]
    profile = {
        "source": "SEC FSDS 2023q1-2025q2, amendments with purpose targeted_fix or xbrl_fix",
        "filings": int(dq["orig_adsh"].nunique()),
        "facts": int(len(dq)),
        "share_of_filings_by_type": (dq.groupby("correction_type")["orig_adsh"].nunique()
                                     / dq["orig_adsh"].nunique()).round(3).to_dict(),
        "facts_per_filing_median": float(dq.groupby("orig_adsh").size().median()),
        "top_tags": dq["tag"].value_counts().head(25).to_dict(),
        "share_current_vs_prior_period": None,
    }
    (P1 / "dq_correction_profile.json").write_text(json.dumps(profile, indent=2))
    print(json.dumps({k: v for k, v in profile.items() if k != "top_tags"}, indent=2))


if __name__ == "__main__":
    main()

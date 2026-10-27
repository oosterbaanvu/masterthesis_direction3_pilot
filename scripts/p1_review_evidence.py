"""P1d: how much evidence is there behind the SEC correction candidates?

Reads the AI-simulated review (results/p1_corrections/ai_simulated_review_NOT_GOLD.csv; NOT ground truth)
and the full correction table, and writes results/p1_corrections/evidence_summary.json with:
  - evidence scope per correction type in the AI simulation (item-level vs type heuristic)
  - whether the simulated label is a deterministic function of the correction type
  - structural risk factors per correction type in the full data (dimensional facts, restatement axis,
    share-unit scale changes that may be stock splits, restatement purpose)
The original review sample (review_sample.csv) is left untouched; no AI label is used as an error label.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "results/p1_corrections"
STRUCTURAL = ["sign_flip", "scale", "scale_and_sign", "other_value", "zero_change", "retag", "period_move"]


def main() -> None:
    review = pd.read_csv(P1 / "ai_simulated_review_NOT_GOLD.csv")
    original = pd.read_csv(P1 / "review_sample.csv")
    assert len(review) == len(original), "AI review must cover the original sample row for row"
    assert (review["orig_adsh"].values == original["orig_adsh"].values).all()
    heuristic = review[review["ai_evidence_scope"] == "type_heuristic_only"]
    per_type_labels = heuristic.groupby("correction_type")["ai_simulated_guess"].nunique()

    corrections = pd.read_csv(P1 / "corrections_with_levels.csv.gz", low_memory=False)
    structural = corrections[corrections["correction_type"].isin(STRUCTURAL)].copy()
    structural["dimensional"] = structural["segments"].notna()
    structural["restatement_axis"] = structural["segments"].fillna("").str.contains("Restatement|PreviouslyReported",
                                                                                    case=False)
    structural["share_unit_scale"] = structural["correction_type"].isin(["scale", "scale_and_sign"]) & (structural["uom"] == "shares")
    structural["restatement_purpose"] = structural["purpose"] == "restatement"
    structural["targeted_non_dimensional"] = structural["purpose"].isin(["targeted_fix", "xbrl_fix"]) & ~structural["dimensional"]
    risk = structural.groupby("correction_type")[["dimensional", "restatement_axis", "share_unit_scale",
                                                   "restatement_purpose", "targeted_non_dimensional"]].mean().round(3)
    risk.insert(0, "facts", structural.groupby("correction_type").size())
    risk.insert(1, "filings", structural.groupby("correction_type")["orig_adsh"].nunique())
    risk.to_csv(P1 / "evidence_risk_factors.csv")

    summary = {
        "ai_review_is_ground_truth": False,
        "rows": int(len(review)),
        "evidence_scope": review["ai_evidence_scope"].value_counts().to_dict(),
        "confidence": review["ai_guess_confidence"].value_counts().to_dict(),
        "evidence_conclusion": review["ai_evidence_conclusion"].value_counts().to_dict(),
        "heuristic_rows_with_one_label_per_type": bool((per_type_labels == 1).all()),
        "heuristic_label_per_type": heuristic.groupby("correction_type")["ai_simulated_guess"].first().to_dict(),
        "scope_by_type": pd.crosstab(review["correction_type"], review["ai_evidence_scope"]).to_dict(orient="index"),
        "human_decisions_filled": int(original["human_decision"].notna().sum()),
    }
    (P1 / "evidence_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(risk.to_string())


if __name__ == "__main__":
    main()

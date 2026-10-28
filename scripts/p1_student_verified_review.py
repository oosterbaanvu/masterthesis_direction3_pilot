"""Record the student-verified labels for review batch 1 and compare them with the first AI-assisted review.

Input: results/p1_corrections/ai_prefill_batch1_sheet_NOT_HUMAN_GOLD.xlsx (second AI pass, pre-filled).
The student checked all 20 pre-filled verdicts against the SEC documents and confirmed them in chat on
28 October 2026. These are AI-assisted labels verified by the student: not blind, not an expert annotation.
Outputs: results/p1_corrections/student_verified_review_batch1.csv and student_verified_review_summary.json
"""
import json
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results/p1_corrections"
SOURCE = "AI pre-fill (second AI pass) checked by the student against the SEC documents; not blind; not expert"


def main() -> None:
    ws = openpyxl.load_workbook(DIR / "ai_prefill_batch1_sheet_NOT_HUMAN_GOLD.xlsx")["Review"]
    rows = list(ws.iter_rows(min_row=2, max_row=21, values_only=True))
    verified = pd.DataFrame({
        "item": [r[0] for r in rows], "decision": [r[14] for r in rows],
        "original_wrong": [{"ja": "yes", "nee": "no"}.get(r[15], r[15]) for r in rows],
        "where_found": [r[16] for r in rows], "note": [r[17] for r in rows],
    })
    verified["label_source"] = SOURCE
    verified["verified_on"] = "2026-10-28"
    batch = pd.read_csv(DIR / "human_review_batch1.csv")[["item", "name", "correction_type", "tag", "new_tag"]]
    verified = batch.merge(verified, on="item")
    verified.to_csv(DIR / "student_verified_review_batch1.csv", index=False)

    first = pd.read_csv(DIR / "ai_document_review_batch1_NOT_HUMAN_GOLD.csv")[
        ["item", "ai_provisional_decision", "ai_original_fact_confirmed_wrong"]]
    both = verified.merge(first, on="item")
    summary = {
        "items": len(verified),
        "label_source": SOURCE,
        "decision_counts": verified["decision"].value_counts().to_dict(),
        "original_wrong_counts": verified["original_wrong"].value_counts().to_dict(),
        "original_wrong_by_correction_type": pd.crosstab(verified["correction_type"],
                                                          verified["original_wrong"]).to_dict(orient="index"),
        "agreement_with_first_ai_review_on_original_wrong":
            int((both["original_wrong"] == both["ai_original_fact_confirmed_wrong"]).sum()),
        "disagreements": both.loc[both["original_wrong"] != both["ai_original_fact_confirmed_wrong"],
                                  ["item", "original_wrong", "ai_original_fact_confirmed_wrong"]].to_dict(orient="records"),
    }
    (DIR / "student_verified_review_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

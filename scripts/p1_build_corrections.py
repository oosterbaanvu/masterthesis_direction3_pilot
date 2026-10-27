"""P1: build natural correction candidates from SEC FSDS amendments.

Outputs in results/p1_corrections/:
  amendment_pairs.csv       each 10-K/A and 10-Q/A paired with the filing it replaces
  pair_summary.csv          per pair: overlap, kind, counts per change type
  corrections.csv.gz        changed, retagged and period-moved facts in full re-filings
  control_filings.csv       never-amended 10-K/10-Q filings (fixed-seed sample) for later stages
  review_sample.csv         stratified sample for manual verification, decision column left blank
  summary.json              headline counts
Large fact tables are written to data/work/ (not committed).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dqstress.sec import fsds

ROOT = Path(__file__).resolve().parents[1]
ZIPS = sorted((ROOT / "data/sec_fsds").glob("20*q*.zip"))
OUT = ROOT / "results/p1_corrections"
WORK = ROOT / "data/work"
FULL_REFILING_OVERLAP = 0.5  # an amendment that re-reports at least half of the original's facts
CONTROLS_PER_FORM = 300
REVIEW_PER_STRATUM = 10
SEED = 20261027
NUMERIC_TYPES = ["sign_flip", "scale", "scale_and_sign", "other_value", "zero_change"]


def edgar_index_url(cik: str, adsh: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{adsh}-index.htm"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    sub = fsds.load_submissions(ZIPS)
    sub.to_parquet(WORK / "submissions.parquet", index=False)
    pairs = fsds.pair_amendments(sub)
    unmatched = fsds.unmatched_amendments(sub, pairs)
    pairs.to_csv(OUT / "amendment_pairs.csv", index=False)

    amended = set(pairs["orig_adsh"]) | set(pairs["amend_adsh"])
    candidates = sub[sub["form"].isin(fsds.BASE_FORMS) & (sub["prevrpt"] == "0") & ~sub["adsh"].isin(amended)]
    controls = pd.concat([group.sample(n=min(len(group), CONTROLS_PER_FORM), random_state=SEED)
                          for _, group in candidates.groupby("form")])
    controls.drop(columns=["accepted"]).to_csv(OUT / "control_filings.csv", index=False)

    wanted = pd.concat([
        pairs[["orig_adsh", "orig_quarter"]].set_axis(["adsh", "quarter"], axis=1),
        pairs[["amend_adsh", "amend_quarter"]].set_axis(["adsh", "quarter"], axis=1),
        controls[["adsh", "quarter"]],
    ]).drop_duplicates()
    cache = WORK / "facts_selected.parquet"
    facts = pd.read_parquet(cache) if cache.exists() else None
    if facts is None or set(facts["adsh"]) - set(wanted["adsh"]) or len(set(wanted["adsh"]) - set(facts["adsh"])) > 0.05 * len(wanted):
        # Rebuild when the cached selection does not match (some wanted filings legitimately have no NUM rows).
        facts = fsds.load_facts(ZIPS, wanted)
        facts.to_parquet(cache, index=False)
    by_adsh = dict(tuple(facts.groupby("adsh")))

    summaries, corrections = [], []
    for pair in pairs.itertuples(index=False):
        orig, amend = by_adsh.get(pair.orig_adsh), by_adsh.get(pair.amend_adsh)
        row = {"orig_adsh": pair.orig_adsh, "amend_adsh": pair.amend_adsh, "base_form": pair.base_form,
               "orig_facts": 0 if orig is None else len(orig), "amend_facts": 0 if amend is None else len(amend)}
        if orig is None or amend is None:
            row["kind"] = "no_numeric_data_in_one_side"
            summaries.append(row)
            continue
        diff = fsds.diff_pair(orig, amend)
        row["overlap"] = (diff["status"] == "both").sum() / len(orig)
        row["kind"] = "full_refiling" if row["overlap"] >= FULL_REFILING_OVERLAP else "partial_amendment"
        for change, count in diff["change"].value_counts().items():
            row["n_" + change] = int(count)
        retags, moves = fsds.detect_moves(diff)
        row["n_retag"], row["n_period_move"] = len(retags), len(moves)
        summaries.append(row)
        if row["kind"] != "full_refiling":
            continue
        changed = diff[(diff["status"] == "both") & (diff["change"] != "unchanged")]
        changed = changed.assign(correction_type=changed["change"], new_tag=pd.NA, new_ddate=pd.NA, new_qtrs=pd.NA)
        retag_rows = retags.assign(correction_type="retag", new_tag=retags["tag_new"], new_ddate=pd.NA,
                                   new_qtrs=pd.NA, amend_value=retags["amend_value_new"])
        move_rows = moves.assign(correction_type="period_move", new_tag=pd.NA, new_ddate=moves["ddate_new"],
                                 new_qtrs=moves["qtrs_new"], amend_value=moves["amend_value_new"])
        completeness = diff[diff["status"].isin(["added", "removed"])]
        completeness = completeness.assign(correction_type="fact_" + completeness["status"],
                                           new_tag=pd.NA, new_ddate=pd.NA, new_qtrs=pd.NA)
        for frame in (changed, retag_rows, move_rows, completeness):
            corrections.append(frame.assign(orig_adsh=pair.orig_adsh, amend_adsh=pair.amend_adsh,
                                            base_form=pair.base_form, cik=pair.cik))

    summary = pd.DataFrame(summaries).fillna(0)
    summary.to_csv(OUT / "pair_summary.csv", index=False)
    keep = ["orig_adsh", "amend_adsh", "cik", "base_form", "correction_type", "tag_ns", "tag", "new_tag",
            "ddate", "new_ddate", "qtrs", "new_qtrs", "uom", "segments", "coreg", "orig_value", "amend_value"]
    corr = pd.concat(corrections, ignore_index=True).reindex(columns=keep)
    corr.to_csv(OUT / "corrections.csv.gz", index=False)

    reviewable = corr[corr["correction_type"].isin(NUMERIC_TYPES + ["retag", "period_move"])]
    sample = pd.concat([group.sample(n=min(len(group), REVIEW_PER_STRATUM), random_state=SEED)
                        for _, group in reviewable.groupby("correction_type")])
    sample["orig_index_url"] = [edgar_index_url(c, a) for c, a in zip(sample["cik"], sample["orig_adsh"])]
    sample["amend_index_url"] = [edgar_index_url(c, a) for c, a in zip(sample["cik"], sample["amend_adsh"])]
    sample["human_decision"] = ""  # error_corrected / legitimate_restatement / representation_only / unclear
    sample["human_note"] = ""
    sample.to_csv(OUT / "review_sample.csv", index=False)

    full = summary[summary["kind"] == "full_refiling"]
    numeric_cols = [c for c in full.columns if c in {"n_" + t for t in NUMERIC_TYPES}]
    headline = {
        "quarters": [fsds.quarter_of(z) for z in ZIPS],
        "submissions": int(len(sub)),
        "amendments_10K_10Q": int((sub["is_amendment"] & sub["base_form"].isin(fsds.BASE_FORMS)).sum()),
        "paired_amendments": int(len(pairs)),
        "unmatched_amendments": int(len(unmatched)),
        "pairs_by_kind": summary["kind"].value_counts().to_dict(),
        "full_refilings_with_numeric_change": int((full[numeric_cols].sum(axis=1) > 0).sum()),
        "full_refilings_with_retag": int((full["n_retag"] > 0).sum()),
        "full_refilings_with_period_move": int((full["n_period_move"] > 0).sum()),
        "corrections_by_type": corr["correction_type"].value_counts().to_dict(),
        "control_filings": int(len(controls)),
    }
    (OUT / "summary.json").write_text(json.dumps(headline, indent=2))
    print(json.dumps(headline, indent=2))


if __name__ == "__main__":
    main()

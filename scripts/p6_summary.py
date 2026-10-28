"""P6: one table per evaluation dimension (E1-E5), all on explicitly stated filings and references.

E2/E4/E5 comparisons that involve official DQC or the AI judge are restricted to the filings where those
ran (DQC: 12 test filings; judge: 6 of them), so every control in a row is compared on the same variants.
Writes results/summary/*.csv and prints the headline tables.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
STRESS = ROOT / "results/p2_stress"
OUT = ROOT / "results/summary"
BASELINE = ["generic_schema", "stat_sign_rarity", "stat_magnitude", "stat_period_jump"]


def load(pattern: str) -> pd.DataFrame:
    return pd.concat([pd.read_csv(p, low_memory=False) for p in sorted(STRESS.glob(pattern))], ignore_index=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    injected = load("injected_detection*.csv.gz")
    injected = injected[(injected["applicable"] == True) & (injected["placement"] == "calibrated")]  # noqa: E712
    injected = injected[injected["adsh"].map(split_of) == "test"]
    dqc_filings = set(injected.loc[injected["control"] == "official_dqc", "adsh"])
    on_dqc = injected[injected["adsh"].isin(dqc_filings)]

    # E2: catch rate per error type on the DQC filings, every control on the same variants.
    e2 = on_dqc.pivot_table(index="operator", columns="control", values="detected_strict", aggfunc="mean").round(2)
    judge_path = ROOT / "results/p5_judge/judge_injected.csv"
    if judge_path.exists():
        judge = pd.read_csv(judge_path)
        judge = judge[judge["operator"] != "clean"]
        e2["ai_judge_qwen3 (6 filings)"] = judge.groupby("operator")["detected_strict"].mean().round(2)
    e2.to_csv(OUT / "E2_catch_rate_dqc_filings.csv")

    # E4: added value beyond existing controls (official DQC + statistical + generic) on the same variants.
    existing = on_dqc[on_dqc["control"].isin(BASELINE + ["official_dqc"])]
    caught_existing = existing.groupby(["adsh", "operator"])["detected_strict"].any().rename("existing")
    rows = []
    for control, part in on_dqc[~on_dqc["control"].isin(BASELINE + ["official_dqc", "naive_non_negative"])].groupby("control"):
        merged = part.set_index(["adsh", "operator"])[["detected_strict"]].join(caught_existing)
        rows.append({"control": control, "variants": len(merged),
                     "caught_by_existing": int(merged["existing"].sum()),
                     "caught_by_ai": int(merged["detected_strict"].sum()),
                     "added_beyond_existing": int((merged["detected_strict"] & ~merged["existing"]).sum())})
    if judge_path.exists():
        merged = judge.set_index(["adsh", "operator"])[["detected_strict"]].join(caught_existing, how="inner")
        rows.append({"control": "ai_judge_qwen3", "variants": len(merged), "caught_by_existing": int(merged["existing"].sum()),
                     "caught_by_ai": int(merged["detected_strict"].sum()),
                     "added_beyond_existing": int((merged["detected_strict"] & ~merged["existing"]).sum())})
    e4 = pd.DataFrame(rows)
    e4.to_csv(OUT / "E4_added_value_dqc_filings.csv", index=False)

    # E5: alerts on never-amended (clean) filings, per control.
    clean = load("clean_flags*.csv")
    clean = clean[clean["adsh"].map(split_of) == "test"]
    e5 = clean.groupby("control")["flags"].agg(filings="count", mean_alerts="mean", median_alerts="median").round(1)
    if judge_path.exists():
        judge_all = pd.read_csv(judge_path)
        e5.loc["ai_judge_qwen3 (cap 10)"] = [int((judge_all["operator"] == "clean").sum()),
                                              round(judge_all.loc[judge_all["operator"] == "clean", "flags"].mean(), 1),
                                              judge_all.loc[judge_all["operator"] == "clean", "flags"].median()]
    e5.to_csv(OUT / "E5_alerts_clean_filings.csv")

    # E3: correction candidates (unverified) flagged, per control, located non-dimensional facts only.
    natural = load("natural_detection*.csv.gz")
    natural = natural[(natural["correction_type"] != "__count__") & (natural["located"] == True)]  # noqa: E712
    controls = [c for c in natural.columns if c not in {"adsh", "tag", "correction_type", "level", "purpose", "located",
                                                        "control", "flags"}]
    e3 = pd.DataFrame({c: {"candidate_facts": int(natural[c].notna().sum()),
                           "flagged_share": round(natural[c].dropna().astype(float).mean(), 3),
                           "filings_with_a_flagged_candidate": round(natural.dropna(subset=[c]).groupby("adsh")[c].any().mean(), 2)}
                       for c in controls}).T
    e3.to_csv(OUT / "E3_correction_candidates.csv")

    for name, frame in [("E2", e2), ("E4", e4), ("E5", e5), ("E3", e3)]:
        print(f"\n{name}\n{frame.to_string()}")


if __name__ == "__main__":
    main()

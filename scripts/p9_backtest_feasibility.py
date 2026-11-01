"""Feasibility check for a time-ordered backtest (planned thesis RQ3), run on 1 November 2026.

Question: can we replay SEC filings in filing order, run the official DQC rules (Arelle + XULE) and pilot AI rules
on each original filing, link every alert to the filing, the rule, the ruleset version and the date the rule became
available, and compare the alerts with the student-verified corrections?

Filings: the 24 filings that already have official DQC runs (12 never corrected, 12 later corrected; filed 2023 to
2025) plus the original filings of the 20 student-verified corrections (downloaded here; needs SEC_USER_AGENT).
Rules:
- official DQC rules, ruleset V31 for the US GAAP taxonomy year of the filing (current rule code);
- AI rule set qwen2.5-coder-7b/discover_greedy_repair1 from pilot 2: the sub-rule kept by expert-aware
  qualification in the mini-pilot ("AccountingRelationship") and the other sub-rules of the same set (not kept).
Modes:
- historical stress test: every rule on every filing, whatever its date;
- time-bound: only DQC rules whose first release date (rule documentation) is on or before the filing date; the AI
  rules were created in October 2026 and are therefore not available for any filing in this period.
Limitation: time-bound mode filters by release date but still runs the current (V31) code of each rule; rule logic
may have changed between versions.
Outputs: results/backtest_feasibility/{filings.csv, alerts.csv.gz, weekly.csv, verified_check.csv, summary.json}
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

import pandas as pd
from dateutil import parser as dateparser

from dqstress.dqc import run_official
from dqstress.rules.sandbox import run_rule_batch
from dqstress.sec import edgar
from dqstress.sec.natural import gold_keys
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/backtest_feasibility"
STORE = ROOT / "data/sec_instances"
WORK = ROOT / "data/dqc_runs"
P1 = ROOT / "results/p1_corrections"
DOCS = Path("/home/user/dataqualitycommittee/dqc_us_rules/docs")
CONCEPTS = ROOT / "data/work/concepts.parquet"
AI_SET = ROOT / "results/p3_rules/generated/qwen2.5-coder-7b/discover_greedy_repair1.py"
AI_KEPT = "AccountingRelationship"
AI_CREATED = pd.Timestamp("2026-10-27")


def rule_release_dates() -> dict[str, pd.Timestamp]:
    dates = {}
    for folder in DOCS.glob("DQC_US_*"):
        docs = sorted(folder.glob("*.md"))
        if not docs:
            continue
        match = re.search(r"^Release date:?\s*(.+)$", docs[0].read_text(errors="ignore"), re.I | re.M)
        if match:
            try:
                dates[folder.name.split("_")[-1]] = pd.Timestamp(dateparser.parse(match.group(1), fuzzy=True))
            except (ValueError, OverflowError):
                pass
    return dates


def adsh_from_url(url: str) -> tuple[str, str]:
    match = re.search(r"/data/(\d+)/(\d{10})(\d{2})(\d{6})/", url)
    return match.group(1), f"{match.group(2)}-{match.group(3)}-{match.group(4)}"


def filing_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    pairs = pd.read_csv(P1 / "amendment_pairs.csv", dtype=str)
    controls = pd.read_csv(P1 / "control_filings.csv", dtype=str)
    existing = sample[sample["adsh"].isin([p.name for p in WORK.iterdir() if (p / "clean.done").exists()])]
    review = pd.read_csv(P1 / "human_review_batch1.csv", dtype=str)
    labels = pd.read_csv(P1 / "student_verified_review_batch1.csv", dtype=str)
    review[["cik", "adsh"]] = review["orig_document"].apply(lambda u: pd.Series(adsh_from_url(u)))
    verified = review.merge(labels[["item", "decision", "original_wrong"]], on="item")
    rows = []
    for row in existing.itertuples(index=False):
        rows.append({"adsh": row.adsh, "cik": row.cik, "instance": row.instance,
                     "group": "never_corrected" if row.group == "control" else "later_corrected"})
    for adsh, part in verified.groupby("adsh"):
        info = pairs[pairs["orig_adsh"] == adsh]
        if info.empty:
            continue
        rows.append({"adsh": adsh, "cik": part["cik"].iloc[0], "instance": info["orig_instance"].iloc[0],
                     "group": "verified_correction"})
    filings = pd.DataFrame(rows).drop_duplicates("adsh")
    accepted = dict(zip(pairs["orig_adsh"], pairs["orig_accepted"]))
    filed = dict(zip(controls["adsh"], controls["filed"]))
    filings["filed"] = [pd.Timestamp(accepted[a][:10]) if a in accepted else pd.Timestamp(filed[a]) if a in filed
                        else pd.NaT for a in filings["adsh"]]
    return filings.sort_values("filed").reset_index(drop=True), verified


def ensure_dqc(row) -> tuple[str, float]:
    instance = STORE / row.adsh / row.instance
    if not instance.exists():
        edgar.download(f"{edgar.filing_folder(row.cik, row.adsh)}/{row.instance}", instance)
    if not (STORE / row.adsh / "facts.parquet").exists():
        parse_instance(instance).to_parquet(STORE / row.adsh / "facts.parquet", index=False)
    folder = WORK / row.adsh
    if (folder / "clean.done").exists():
        return "ok (reused)", float("nan")
    if run_official.ruleset_for(instance) is None:
        return "no_matching_ruleset", float("nan")
    folder.mkdir(parents=True, exist_ok=True)
    run_official.fetch_support_files(row.cik, row.adsh, folder)
    shutil.copy(instance, folder / row.instance)
    start = time.time()
    status, _ = run_official.run(folder / row.instance, folder / "clean.json")
    return status, time.time() - start


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    filings, verified = filing_table()
    statuses, seconds, rulesets = [], [], []
    for row in filings.itertuples(index=False):
        try:
            status, took = ensure_dqc(row)
        except Exception as error:  # record and continue: the check is about what works
            status, took = f"error:{type(error).__name__}", float("nan")
        instance = STORE / row.adsh / row.instance
        ruleset = run_official.ruleset_for(instance) if instance.exists() else None
        statuses.append(status), seconds.append(took), rulesets.append(ruleset.stem if ruleset else None)
        print(row.adsh, row.group, status, "" if took != took else f"{took:.0f}s", flush=True)
    filings["dqc_status"], filings["dqc_seconds"], filings["ruleset"] = statuses, seconds, rulesets
    filings.to_csv(OUT / "filings.csv", index=False)

    released = rule_release_dates()
    alerts = []
    for row in filings.itertuples(index=False):
        log = WORK / row.adsh / "clean.json"
        if not row.dqc_status.startswith("ok") or not log.exists():
            continue
        for item in run_official.parse_log(log).itertuples(index=False):
            base = re.match(r"DQC\.US\.(\d{4})", item.rule_code)
            base = base.group(1) if base else None
            available = released.get(base) if base else None
            alerts.append({"adsh": row.adsh, "filed": row.filed, "group": row.group, "source": "official_dqc",
                           "rule": item.rule_code, "base_rule": base, "ruleset": row.ruleset,
                           "available_from": available, "qname": item.qname, "context_ref": item.context_ref})
    ok = filings[filings["dqc_status"].str.startswith("ok")]
    paths = [STORE / a / "facts.parquet" for a in ok["adsh"]]
    results = run_rule_batch(AI_SET.read_text(), paths, None, CONCEPTS)
    ai_status = {}
    for row in ok.itertuples(index=False):
        result = results[str((STORE / row.adsh / "facts.parquet").resolve())]
        ai_status[row.adsh] = result.status
        for flag in result.flagged:
            alerts.append({"adsh": row.adsh, "filed": row.filed, "group": row.group,
                           "source": "ai_kept" if flag["rule"] == AI_KEPT else "ai_not_kept",
                           "rule": flag["rule"], "base_rule": None, "ruleset": AI_SET.stem,
                           "available_from": AI_CREATED, "qname": flag["qname"], "context_ref": flag["context_ref"]})
    alerts = pd.DataFrame(alerts)
    alerts["filed"] = pd.to_datetime(alerts["filed"])
    alerts["available_from"] = pd.to_datetime(alerts["available_from"])
    alerts["available_at_filing"] = alerts["available_from"].notna() & (alerts["available_from"] <= alerts["filed"])
    alerts.to_csv(OUT / "alerts.csv.gz", index=False)

    alerts["week"] = alerts["filed"].dt.to_period("W").astype(str)
    stress = alerts.groupby(["week", "source"]).size().rename("stress_test")
    bound = alerts[alerts["available_at_filing"]].groupby(["week", "source"]).size().rename("time_bound")
    weekly = pd.concat([stress, bound], axis=1).fillna(0).astype(int).reset_index()
    weekly.to_csv(OUT / "weekly.csv", index=False)

    checks = []
    for item in verified.itertuples(index=False):
        row = filings[filings["adsh"] == item.adsh]
        if row.empty or not row["dqc_status"].iloc[0].startswith("ok"):
            checks.append({"item": item.item, "adsh": item.adsh, "decision": item.decision, "status": "not_run"})
            continue
        facts = pd.read_parquet(STORE / item.adsh / "facts.parquet")
        gold = pd.DataFrame([{"tag": item.tag, "qtrs": item.qtrs, "uom": item.uom, "ddate": item.period_end}])
        keys = gold_keys(facts, gold)[0]
        mine = alerts[alerts["adsh"] == item.adsh]
        hit = lambda frame: bool(keys & set(zip(frame["qname"], frame["context_ref"])))  # noqa: E731
        checks.append({"item": item.item, "adsh": item.adsh, "correction_type": item.correction_type,
                       "decision": item.decision, "original_wrong": item.original_wrong, "status": "ok",
                       "located": bool(keys),
                       "dqc_stress_test": hit(mine[mine["source"] == "official_dqc"]),
                       "dqc_time_bound": hit(mine[(mine["source"] == "official_dqc") & mine["available_at_filing"]]),
                       "ai_kept": hit(mine[mine["source"] == "ai_kept"]),
                       "ai_not_kept": hit(mine[mine["source"] == "ai_not_kept"])})
    checks = pd.DataFrame(checks)
    checks.to_csv(OUT / "verified_check.csv", index=False)

    dqc = alerts[alerts["source"] == "official_dqc"]
    per_filing = alerts.groupby(["adsh", "source"]).size().unstack(fill_value=0).reindex(ok["adsh"], fill_value=0)
    summary = {
        "filings": int(len(filings)), "filings_by_group": filings["group"].value_counts().to_dict(),
        "dqc_status": filings["dqc_status"].value_counts().to_dict(),
        "filed_range": [str(filings["filed"].min().date()), str(filings["filed"].max().date())],
        "dqc_seconds_median_new_runs": None if filings["dqc_seconds"].isna().all()
        else round(float(filings["dqc_seconds"].median()), 1),
        "ai_rule_status": pd.Series(ai_status).value_counts().to_dict(),
        "alerts": alerts["source"].value_counts().to_dict(),
        "alerts_fully_linked_share": round(float(alerts[["adsh", "filed", "rule", "ruleset", "available_from"]]
                                                 .notna().all(axis=1).mean()), 3),
        "dqc_rule_codes_without_release_date": sorted(dqc.loc[dqc["available_from"].isna(), "base_rule"]
                                                      .dropna().unique().tolist()),
        "dqc_alerts_not_available_at_filing": int((~dqc["available_at_filing"]).sum()),
        "mean_alerts_per_filing": per_filing.mean().round(2).to_dict(),
        "verified_items": int(len(checks)),
        "verified_items_run": int((checks["status"] == "ok").sum()),
        "verified_located": int(checks.get("located", pd.Series(dtype=bool)).fillna(False).sum()),
        "verified_flagged": {c: int(checks[c].fillna(False).sum()) for c in
                             ["dqc_stress_test", "dqc_time_bound", "ai_kept", "ai_not_kept"] if c in checks},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

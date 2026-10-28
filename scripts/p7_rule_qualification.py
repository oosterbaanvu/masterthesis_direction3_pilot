"""Mini-pilot, per-rule qualification: can the useful sub-rules be kept from AI rule sets that fail as a whole?

Candidates: every sub-rule (the "rule" name each flag carries) of the 13 generated discover and gap-closing rule
sets, including repaired versions. Data: the 66 TEST control filings (no model saw them) and their calibrated
injected variants. The test filings are split by company (hash of the CIK) into a selection half and an evaluation
half. A policy may only look at the selection half; results are reported on the evaluation half.

Policies, each under an alert budget of 1 and of 5 alerts per clean filing (fixed before looking at results):
- unfiltered: every sub-rule (the pilot setting).
- generic filter (in the spirit of LeDQeR's filters; not a reimplementation): the rule set runs without error,
  the sub-rule fires at least once, it fits the alert budget on clean filings, and it is not redundant with a
  sub-rule already kept. Uses no existing controls and no injected errors.
- expert-aware qualification: the rule set runs without error, the sub-rule catches at least one injected error
  that the existing controls (generic, statistical, and official DQC where it ran) miss, every kept sub-rule adds a
  new catch beyond the existing controls and the sub-rules kept before it, and the kept set fits the alert budget.
Outputs in results/minipilot/: subrule_flags/*.parquet (raw), qualification_results.csv, qualification_rules.csv.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from dqstress.inject.diff import injected_keys
from dqstress.rules.sandbox import run_rule_batch
from dqstress.splits import split_of

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/minipilot"
RAW = OUT / "subrule_flags"
STORE = ROOT / "data/sec_instances"
FACTS = ROOT / "data/stress_facts"
CONCEPTS = ROOT / "data/work/concepts.parquet"
EXISTING = ["generic_schema", "stat_sign_rarity", "stat_magnitude", "stat_period_jump", "official_dqc"]
BUDGETS = [1, 5]


def half_of(cik: str) -> str:
    return "selection" if int(hashlib.sha256(cik.encode()).hexdigest(), 16) % 2 == 0 else "evaluation"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    sample = pd.read_csv(ROOT / "results/p2_sample/sample.csv", dtype=str)
    tests = sample[(sample["group"] == "control") & (sample["adsh"].map(split_of) == "test")].copy()
    tests["half"] = tests["cik"].map(half_of)
    det = pd.concat([pd.read_csv(p, low_memory=False) for p in
                     [ROOT / "results/p2_stress/injected_detection.csv.gz",
                      ROOT / "results/p2_stress/injected_detection_official_dqc.csv.gz"]], ignore_index=True)
    det = det[(det["applicable"] == True) & (det["placement"] == "calibrated")  # noqa: E712
              & det["adsh"].isin(tests["adsh"])]
    variants = det[["adsh", "operator"]].drop_duplicates().reset_index(drop=True)
    existing = det[det["control"].isin(EXISTING)].groupby(["adsh", "operator"])["detected_strict"].any()
    return tests, variants, existing


def raw_flags(rule_path: Path, tests: pd.DataFrame, variants: pd.DataFrame) -> pd.DataFrame:
    target = RAW / f"{rule_path.parent.name}__{rule_path.stem}.parquet"
    if target.exists():
        return pd.read_parquet(target)
    clean = {a: STORE / a / "facts.parquet" for a in tests["adsh"]}
    var = {(v.adsh, v.operator): FACTS / v.adsh / f"{v.operator}_calibrated.parquet" for v in variants.itertuples()}
    paths = list(clean.values()) + list(var.values())
    results = run_rule_batch(rule_path.read_text(), paths, None, CONCEPTS)
    rows = []
    for key, path in [((a, "clean"), p) for a, p in clean.items()] + list(var.items()):
        res = results[str(Path(path).resolve())]
        rows.append({"adsh": key[0], "operator": key[1], "status": res.status, "rule": None,
                     "qname": None, "context_ref": None})
        rows += [{"adsh": key[0], "operator": key[1], "status": res.status, "rule": f.get("rule", "") or "(unnamed)",
                  "qname": f["qname"], "context_ref": f["context_ref"]} for f in res.flagged]
    frame = pd.DataFrame(rows)
    RAW.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(target, index=False)
    return frame


def subrule_table(tests: pd.DataFrame, variants: pd.DataFrame, existing: pd.Series) -> tuple[pd.DataFrame, dict]:
    """Per sub-rule: clean alerts per filing, catches per variant, set-level execution status."""
    injected = {}
    for v in variants.itertuples():
        injected[(v.adsh, v.operator)] = injected_keys(pd.read_parquet(STORE / v.adsh / "facts.parquet"),
                                                       pd.read_parquet(FACTS / v.adsh / f"{v.operator}_calibrated.parquet"))
    half = tests.set_index("adsh")["half"]
    rows, catches = [], {}
    for rule_path in sorted((ROOT / "results/p3_rules/generated").glob("*/*.py")):
        if rule_path.stem.startswith("DQC_"):
            continue
        raw = raw_flags(rule_path, tests, variants)
        set_name = f"{rule_path.parent.name}/{rule_path.stem}"
        status = raw.drop_duplicates(["adsh", "operator"]).assign(half=lambda d: d["adsh"].map(half))
        runs_clean = {h: bool((status.loc[status["half"] == h, "status"] == "ok").all()) for h in ("selection", "evaluation")}
        flags = raw[raw["rule"].notna()]
        for sub, part in flags.groupby("rule"):
            clean = part[part["operator"] == "clean"]
            clean_keys = {a: set(zip(g["qname"], g["context_ref"])) for a, g in clean.groupby("adsh")}
            caught = set()
            for (adsh, op), g in part[part["operator"] != "clean"].groupby(["adsh", "operator"]):
                new = set(zip(g["qname"], g["context_ref"])) - clean_keys.get(adsh, set())
                if new & injected[(adsh, op)]:
                    caught.add((adsh, op))
            rid = f"{set_name}::{sub}"
            catches[rid] = caught
            for h in ("selection", "evaluation"):
                filings = tests[tests["half"] == h]["adsh"]
                rows.append({"rule_id": rid, "set": set_name, "subrule": sub, "half": h, "set_runs_clean": runs_clean[h],
                             "alerts_per_clean_filing": clean[clean["adsh"].isin(filings)].groupby("adsh").size()
                             .reindex(filings, fill_value=0).mean(),
                             "catches": sum(1 for c in caught if half[c[0]] == h),
                             "catches_beyond_existing": sum(1 for c in caught if half[c[0]] == h
                                                            and not existing.get(c, False)),
                             "clean_keys": {a: k for a, k in clean_keys.items() if half.get(a) == h}})
    return pd.DataFrame(rows), catches


def select(policy: str, budget: float, sel: pd.DataFrame, catches: dict, existing: pd.Series, half: pd.Series) -> list:
    pool = sel[sel["set_runs_clean"]] if policy != "unfiltered" else sel
    if policy == "unfiltered":
        return list(sel["rule_id"])
    in_sel = lambda rid: {c for c in catches[rid] if half[c[0]] == "selection"}  # noqa: E731
    kept, alerts, covered = [], 0.0, set()
    if policy == "generic_filter":
        pool = pool[pool["alerts_per_clean_filing"] <= budget].sort_values("alerts_per_clean_filing")
        seen_keys = []
        for r in pool.itertuples():
            fired = r.alerts_per_clean_filing > 0 or in_sel(r.rule_id)
            keys = {(a, k) for a, ks in r.clean_keys.items() for k in ks} | {("v",) + c for c in in_sel(r.rule_id)}
            if not fired or any(keys <= other for other in seen_keys) or alerts + r.alerts_per_clean_filing > budget:
                continue
            kept.append(r.rule_id); seen_keys.append(keys); alerts += r.alerts_per_clean_filing
        return kept
    # expert-aware: rank by new catches beyond existing per alert, add while each adds a new catch and budget holds
    gaps = {rid: {c for c in in_sel(rid) if not existing.get(c, False)} for rid in pool["rule_id"]}
    cand = pool[pool["rule_id"].map(lambda rid: len(gaps[rid]) > 0)].copy()
    cand["score"] = cand["rule_id"].map(lambda rid: len(gaps[rid])) / (cand["alerts_per_clean_filing"] + 0.1)
    for r in cand.sort_values("score", ascending=False).itertuples():
        new = gaps[r.rule_id] - covered
        if not new or alerts + r.alerts_per_clean_filing > budget:
            continue
        kept.append(r.rule_id); covered |= new; alerts += r.alerts_per_clean_filing
    return kept


def evaluate(kept: list, ev: pd.DataFrame, catches: dict, existing: pd.Series, half: pd.Series,
             tests: pd.DataFrame, variants: pd.DataFrame) -> dict:
    rows = ev.set_index("rule_id").loc[kept] if kept else ev.iloc[0:0]
    filings = tests[tests["half"] == "evaluation"]["adsh"]
    alerts = pd.Series(0, index=filings, dtype=float)
    union = {a: set() for a in filings}
    for r in rows.itertuples():
        for a, ks in r.clean_keys.items():
            union[a] |= ks
    alerts = pd.Series({a: len(k) for a, k in union.items()})
    ev_vars = {(v.adsh, v.operator) for v in variants.itertuples() if half[v.adsh] == "evaluation"}
    caught = set().union(*[catches[rid] for rid in kept]) & ev_vars if kept else set()
    return {"rules_kept": len(kept), "variants": len(ev_vars),
            "caught_by_existing": sum(existing.get(c, False) for c in ev_vars),
            "caught_by_kept_rules": len(caught),
            "added_beyond_existing": sum(1 for c in caught if not existing.get(c, False)),
            "alerts_per_clean_filing": round(alerts.mean(), 2), "clean_filings": len(filings)}


def main() -> None:
    tests, variants, existing = load_inputs()
    half = tests.set_index("adsh")["half"]
    table, catches = subrule_table(tests, variants, existing)
    sel = table[table["half"] == "selection"]
    ev = table[table["half"] == "evaluation"]
    results, kept_rows = [], []
    for policy in ["unfiltered", "generic_filter", "expert_aware"]:
        for budget in (BUDGETS if policy != "unfiltered" else [None]):
            kept = select(policy, budget, sel, catches, existing, half)
            res = evaluate(kept, ev, catches, existing, half, tests, variants)
            results.append({"policy": policy, "budget": budget, **res})
            kept_rows += [{"policy": policy, "budget": budget, "rule_id": rid} for rid in kept
                          if policy != "unfiltered"]
    out = pd.DataFrame(results)
    out.to_csv(OUT / "qualification_results.csv", index=False)
    summary = table.drop(columns="clean_keys").pivot_table(
        index=["rule_id", "set", "subrule"], columns="half",
        values=["alerts_per_clean_filing", "catches", "catches_beyond_existing"]).round(2)
    summary.columns = [f"{a}_{b}" for a, b in summary.columns]
    summary.reset_index().to_csv(OUT / "qualification_subrules.csv", index=False)
    pd.DataFrame(kept_rows).to_csv(OUT / "qualification_rules.csv", index=False)
    print("test filings per half:", tests["half"].value_counts().to_dict())
    print("sub-rules:", table["rule_id"].nunique(), "with a catch beyond existing on selection:",
          int((sel["catches_beyond_existing"] > 0).sum()))
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()

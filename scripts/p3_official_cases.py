"""P3b: build the official reference cases for the rule-translation experiment.

For every DQC rule that needs no linkbase navigation and has official tests, collect each
expected-output log, the filing it ran on, and the facts each rule message references.
Remote filings are fetched as extracted XBRL instances and parsed to fact tables.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from dqstress.dqc import official
from dqstress.sec import edgar
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p3_rules"
STORE = ROOT / "data/dqc_cases"


def main() -> None:
    inventory = pd.read_csv(OUT / "rule_inventory.csv", dtype={"number": str})
    usable = inventory[(inventory["required_inputs"].isin(["facts_only", "taxonomy_metadata"]))
                       & (inventory["expected_outputs"] > 0)]
    cases, refs = [], []
    for rule in usable.itertuples(index=False):
        for log in official.expected_outputs(rule.number):
            source, flagged = official.parse_expected_output(log)
            case_id = log.stem
            row = {"rule": rule.rule, "number": rule.number, "case_id": case_id, "source": source,
                   "n_messages": int(flagged["message_no"].nunique()) if len(flagged) else 0,
                   "n_refs": len(flagged)}
            local = None
            if source and not source.startswith("http"):
                # Logs were produced on the committee's machine; map to the same file in our checkout.
                tail = source.replace("\\", "/").split("tests/input/")[-1]
                candidate = official.DQC_ROOT / "tests/input" / tail
                local = candidate if candidate.exists() else None
                row["input"] = str(local) if local else None
            elif source:
                url = official.instance_url_for(source)
                target = STORE / case_id / url.rsplit("/", 1)[-1]
                try:
                    edgar.download(url, target)
                    local = target
                    row["input"] = str(target)
                except Exception as error:
                    row["input"] = None
                    row["fetch_error"] = f"{type(error).__name__}: {error}"[:200]
            if local is not None:
                try:
                    facts = parse_instance(local)
                    facts_path = STORE / case_id / "facts.parquet"
                    facts_path.parent.mkdir(parents=True, exist_ok=True)
                    facts.to_parquet(facts_path, index=False)
                    row["facts_path"] = str(facts_path)
                    row["n_facts"] = len(facts)
                    # How many referenced facts can be located in our parsed table (id or concept+context)?
                    if len(flagged):
                        ids = set(facts["fact_id"].dropna())
                        keys = set(facts["prefix"] + ":" + facts["concept"] + "|" + facts["context_ref"])
                        located = [(r in ids) or (f"{q}|{c}" in keys)
                                   for r, q, c in zip(flagged["fact_ref"], flagged["qname"], flagged["context_ref"])]
                        row["refs_located"] = sum(located)
                except Exception as error:
                    row["parse_error"] = f"{type(error).__name__}: {error}"[:200]
            cases.append(row)
            if len(flagged):
                refs.append(flagged.assign(case_id=case_id, rule=rule.rule))
    pd.DataFrame(cases).to_csv(OUT / "official_cases.csv", index=False)
    pd.concat(refs).to_csv(OUT / "official_expected_refs.csv.gz", index=False)
    frame = pd.DataFrame(cases)
    print(len(frame), "cases;", frame["facts_path"].notna().sum(), "with parsed facts;",
          int(frame["n_refs"].sum()), "expected refs;", int(frame.get("refs_located", pd.Series()).sum()), "located")


if __name__ == "__main__":
    main()

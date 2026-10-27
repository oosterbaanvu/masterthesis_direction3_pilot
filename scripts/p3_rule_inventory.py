"""P3a: inventory of the DQC US rules: documentation, dates, required inputs and official tests.

Required inputs are read from the XULE source (text only, nothing is executed):
  facts_only           the rule needs only reported facts (plus lists published with the rule)
  taxonomy_metadata    the rule also reads concept properties (balance, period type, data type)
  dts_relationships    the rule navigates linkbase relationships (calculation, dimensions, presentation)
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DQC = Path("/home/user/dataqualitycommittee/dqc_us_rules")
OUT = ROOT / "results/p3_rules/rule_inventory.csv"


def doc_fields(md: str) -> dict:
    title = re.search(r"^#\s*(.+?)\s*$", md, re.MULTILINE)
    release = re.search(r"Release date:\s*([A-Za-z]+ \d{1,2},? \d{4})", md)
    effective = re.search(r"Effective date:\s*([A-Za-z]+ \d{1,2},? \d{4})", md)
    return {"title": title.group(1) if title else None,
            "release_date": pd.to_datetime(release.group(1).replace(",", "")) if release else pd.NaT,
            "effective_date": pd.to_datetime(effective.group(1).replace(",", "")) if effective else pd.NaT,
            "doc_chars": len(md)}


def source_fields(xule: str) -> dict:
    navigates = bool(re.search(r"\bnavigate\b", xule))
    taxonomy = bool(re.search(r"taxonomy\(\)|\.balance\b|\.period-type\b|\.data-type\b", xule))
    return {"source_lines": xule.count("\n"),
            "required_inputs": "dts_relationships" if navigates else ("taxonomy_metadata" if taxonomy else "facts_only")}


def main() -> None:
    tests = json.loads((DQC / "tests/secvalidationtests.json").read_text())
    per_rule = defaultdict(lambda: {"tests_remote": 0, "tests_local": 0})
    for block in tests:
        for infile in block["infiles"]:
            rule = infile.get("xule_run_only", "")
            if ".US." in rule:
                number = rule.split(".")[2]
                per_rule[number]["tests_remote" if infile["file"].startswith("http") else "tests_local"] += 1
    outputs = [p.name for p in (DQC / "tests/output").glob("*.xml")]
    rows = []
    for folder in sorted((DQC / "docs").glob("DQC_US_*")):
        number = folder.name.split("_")[-1]
        md_files = list(folder.glob("*.md"))
        if not md_files:
            continue
        row = {"rule": f"DQC_{number}", "number": number,
               "element_lists": ";".join(p.name for p in folder.glob("*.xlsx"))}
        row.update(doc_fields(md_files[0].read_text(errors="replace")))
        for year in ("2025", "2024", "2023"):
            source = DQC / f"dqc_us_rules/source/us/{year}/DQC_{number}.xule"
            if source.exists():
                row.update(source_fields(source.read_text(errors="replace")))
                row["source_year"] = year
                break
        row.update(per_rule.get(number, {"tests_remote": 0, "tests_local": 0}))
        row["expected_outputs"] = sum(1 for name in outputs if f"DQC.US.{number}" in name)
        rows.append(row)
    inventory = pd.DataFrame(rows)
    inventory.to_csv(OUT, index=False)
    print(len(inventory), "US rules documented")
    print(inventory["required_inputs"].value_counts(dropna=False).to_string())
    usable = inventory[(inventory["required_inputs"] != "dts_relationships") & (inventory["expected_outputs"] > 0)]
    print("usable for translate experiment (no linkbase navigation, has official tests):", len(usable))
    print(usable[["rule", "title", "release_date", "required_inputs", "tests_remote", "tests_local", "expected_outputs"]].to_string())


if __name__ == "__main__":
    main()

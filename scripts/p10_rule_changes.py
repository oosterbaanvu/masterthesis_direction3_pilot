"""Pilot B, step 1: corpus of real rule changes (rule maintenance), from DQC and EBA.

DQC: the v31 repository keeps one version of every US rule per US GAAP taxonomy year (source/us/2023 ... 2026).
For each pair of consecutive years and each assertion (sub-rule, e.g. US.0018.35) we compare the code without
comments and classify the change:
- unchanged: identical after removing comments and four-digit years;
- message_only: only the message text (between `message` and `severity`) differs;
- boilerplate: only bookkeeping lines differ (the 2025 rename of $rule_id, rule-focus and effectiveDate lines);
- logic: the code outside the message and the bookkeeping lines differs;
- added / removed: the assertion exists in only one of the two years.
Constant and taxonomy helper files (constant*.xule, base-taxonomy-*.xule, ...) are compared separately, because
element lists often change there rather than in the rule file.

EBA: the validation-rule workbook (all release sheets) records per rule and release a "Last Change" label
(for example Change, Reexpressed, 4 digits, Rename/Split table). For every row labelled as a change, the formula of
the previous release in which the rule appeared is paired with the new formula.

Outputs in results/pilot_b/: dqc_changes.csv.gz, dqc_helper_files.csv, eba_changes.csv.gz, corpus_summary.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "results/pilot_b"
DQC_SRC = Path("/home/user/dataqualitycommittee/dqc_us_rules/dqc_us_rules/source/us")
YEARS = ["2023", "2024", "2025", "2026"]


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def assertions(path: Path) -> dict[str, str]:
    """Split a XULE rule file into its assertions; the text before the first assertion is kept as '_preamble'."""
    code = strip_comments(path.read_text(errors="ignore"))
    parts = re.split(r"(?mi)^[ \t]*(?=(?:assert|output)\s+\S+)", code)
    blocks = {"_preamble": parts[0]}
    last = "_preamble"
    for part in parts[1:]:
        match = re.match(r"\s*(?:assert|output)\s+(\S+)", part, flags=re.I)
        if match is None:          # not an assertion header after all: keep it with the previous block
            blocks[last] += part
            continue
        last = match.group(1)
        blocks[last] = blocks.get(last, "") + part
    return blocks


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"20\d\d", "YYYY", text)).strip()


BOILERPLATE = [
    (r"\$rule_id\b", "$ruleId"),                       # variable renamed in 2025
    (r"(?mi)^\s*rule-focus\b[^\n]*$", ""),             # tells the processor which fact to report
    (r"(?mi)^\s*effectiveDate\b[^\n]*$", ""),          # effective-date bookkeeping
]


def without_boilerplate(text: str) -> str:
    for pattern, repl in BOILERPLATE:
        text = re.sub(pattern, repl, text)
    return text


def without_message(text: str) -> str:
    return re.sub(r"\bmessage\b.*?(?=\bseverity\b|\Z)", "message <MSG> ", text, flags=re.S | re.I)


def dqc_changes() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, helpers = [], []
    for old_year, new_year in zip(YEARS, YEARS[1:]):
        old_dir, new_dir = DQC_SRC / old_year, DQC_SRC / new_year
        names = sorted({p.name for p in old_dir.glob("*.xule")} | {p.name for p in new_dir.glob("*.xule")})
        for name in names:
            old_path, new_path = old_dir / name, new_dir / name
            if not name.startswith("DQC_"):
                if old_path.exists() and new_path.exists():
                    a = squash(strip_comments(old_path.read_text(errors="ignore")))
                    b = squash(strip_comments(new_path.read_text(errors="ignore")))
                    helpers.append({"file": name, "from": old_year, "to": new_year, "changed": a != b,
                                    "old_chars": len(a), "new_chars": len(b)})
                continue
            old = assertions(old_path) if old_path.exists() else {}
            new = assertions(new_path) if new_path.exists() else {}
            for key in sorted(set(old) | set(new)):
                a, b = old.get(key), new.get(key)
                if a is None:
                    kind = "added"
                elif b is None:
                    kind = "removed"
                elif squash(a) == squash(b):
                    kind = "unchanged"
                elif squash(without_message(a)) == squash(without_message(b)):
                    kind = "message_only"
                elif squash(without_message(without_boilerplate(a))) == squash(without_message(without_boilerplate(b))):
                    kind = "boilerplate"
                else:
                    kind = "logic"
                rows.append({"rule_file": name, "assertion": key, "from": old_year, "to": new_year, "kind": kind,
                             "old_code": a or "", "new_code": b or ""})
    return pd.DataFrame(rows), pd.DataFrame(helpers)


EBA_KIND = [("Rename/Split", "table_structure"), ("Reexpressed", "reexpressed"), ("Change", "change"),
            ("4 digits", "notation"), ("Severity", "severity"), ("XBRL Correction", "xbrl_correction")]


def eba_kind(label: str) -> str:
    kinds = [kind for key, kind in EBA_KIND if key.lower() in label.lower()]
    return "+".join(kinds) if kinds else "other"


def eba_changes() -> pd.DataFrame:
    from p8_eba_rules import load
    raw = load()
    raw = raw[raw["ID"].notna() & raw["Formula"].notna()].copy()
    raw["Last Change"] = raw["Last Change"].fillna("").astype(str).str.strip()
    raw = raw.sort_values(["ID", "release_order"])
    raw["prev_formula"] = raw.groupby("ID")["Formula"].shift(1)
    raw["prev_release"] = raw.groupby("ID")["release"].shift(1)
    labelled = raw[raw["Last Change"].str.contains("Change|Reexpressed|4 digits|Rename|Severity|XBRL Correction",
                                                    case=False) & raw["prev_formula"].notna()].copy()
    labelled["kind"] = labelled["Last Change"].map(eba_kind)
    labelled["formula_differs"] = labelled["Formula"].str.strip() != labelled["prev_formula"].str.strip()
    keep = ["ID", "Type", "prev_release", "release", "Last Change", "kind", "formula_differs", "prev_formula",
            "Formula"]
    keep = [c for c in keep if c in labelled.columns]
    return labelled[keep].rename(columns={"ID": "id", "Type": "type", "Last Change": "last_change",
                                          "prev_formula": "old_formula", "Formula": "new_formula"})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dqc, helpers = dqc_changes()
    dqc.to_csv(OUT / "dqc_changes.csv.gz", index=False)
    helpers.to_csv(OUT / "dqc_helper_files.csv", index=False)
    eba = eba_changes()
    eba.to_csv(OUT / "eba_changes.csv.gz", index=False)
    real = dqc[dqc["assertion"] != "_preamble"]
    summary = {
        "dqc_assertion_pairs_by_kind": {f"{a}->{b}": g["kind"].value_counts().to_dict()
                                        for (a, b), g in real.groupby(["from", "to"])},
        "dqc_rule_files_with_logic_change": {f"{a}->{b}": int(g.loc[g["kind"] == "logic", "rule_file"].nunique())
                                             for (a, b), g in real.groupby(["from", "to"])},
        "dqc_preamble_changed": {f"{a}->{b}": int((g["kind"] == "logic").sum())
                                 for (a, b), g in dqc[dqc["assertion"] == "_preamble"].groupby(["from", "to"])},
        "dqc_helper_files_changed": {f"{a}->{b}": g.loc[g["changed"], "file"].tolist()
                                     for (a, b), g in helpers.groupby(["from", "to"])},
        "eba_labelled_changes_by_kind": eba["kind"].value_counts().to_dict(),
        "eba_change_rows_with_different_formula": int((eba["kind"].str.contains("change")
                                                       & eba["formula_differs"]).sum()),
        "eba_change_rules": int(eba.loc[eba["kind"].str.contains("change"), "id"].nunique()),
        "eba_change_by_type": eba.loc[eba["kind"].str.contains("change"), "type"].value_counts().head(8).to_dict(),
    }
    (OUT / "corpus_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

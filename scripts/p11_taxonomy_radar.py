"""Pilot B, step 2: are DQC rule changes explained by documented taxonomy changes, and can a simple radar find them?

The US GAAP taxonomy publishes each year a "depcon" linkbase (us-gaap-depcon-def-YYYY.xml) that lists deprecated
concepts and, where one exists, the concept that replaces them (arcs with arcrole dep-*; the arc points from the
new concept to the deprecated one). Concepts deprecated in year Y+1 are those in the Y+1 file but not in the Y file.

1. Explained changes: a DQC assertion whose logic changed from Y to Y+1 is "explained" when a line removed from its
   code contains a concept that was newly deprecated in Y+1.
2. Radar baseline (no AI): before Y+1 rules are known, flag every rule file of year Y that mentions a concept
   newly deprecated in Y+1 ("flagged"), or any concept listed as deprecated in the Y+1 file ("flagged_any"),
   because the committee sometimes updates a rule a year after the concept was deprecated. "Listed" combines the
   depcon definition and presentation files of Y+1 with concepts that disappear from the taxonomy schema in Y+1. Compare with the rule files the committee actually changed (logic, added or removed
   assertions). Constant files are reported separately, because element lists often live there.
Outputs: results/pilot_b/radar.csv, results/pilot_b/explained_changes.csv, results/pilot_b/radar_summary.json.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/pilot_b"
TAX = ROOT / "data/taxonomy_dep"          # downloaded from https://xbrl.fasb.org/us-gaap/<year>/elts/ (not committed)
DEP_FILES = {y: TAX / f"us-gaap-depcon-def-{y}.xml" for y in ["2023", "2024", "2025", "2026"]}
PRE_FILES = {y: TAX / f"us-gaap-depcon-pre-{y}.xml" for y in DEP_FILES}
XSD_FILES = {y: TAX / f"us-gaap-{y}.xsd" for y in DEP_FILES}
DQC_SRC = Path("/home/user/dataqualitycommittee/dqc_us_rules/dqc_us_rules/source/us")
XL = "{http://www.w3.org/1999/xlink}"


def deprecations(path: Path) -> tuple[set[str], dict[str, str]]:
    """Deprecated concepts in a depcon file, and a map deprecated -> replacement (dep-concept-deprecatedConcept)."""
    root = ET.parse(path).getroot()
    deprecated, replacement = set(), {}
    for link in root.iter():
        if not link.tag.endswith("definitionLink"):
            continue
        locs = {}
        for loc in link:
            if loc.tag.endswith("loc"):
                locs[loc.get(XL + "label")] = loc.get(XL + "href").split("#")[-1].split("_", 1)[-1]
        for arc in link:
            role = arc.get(XL + "arcrole") or ""
            if arc.tag.endswith("definitionArc") and "/arcrole/dep-" in role:
                source, target = locs.get(arc.get(XL + "from")), locs.get(arc.get(XL + "to"))
                if target:
                    deprecated.add(target)
                    if role.endswith("dep-concept-deprecatedConcept") and source:
                        replacement[target] = source
    return deprecated, replacement


def listed_in_pre(path: Path) -> set[str]:
    """All concepts referenced in the deprecated-concepts presentation file."""
    text = path.read_text(errors="ignore")
    return set(re.findall(r"#us-gaap_([A-Za-z0-9]+)", text))


def elements(path: Path) -> set[str]:
    return set(re.findall(r"<xs:element[^>]*\sname='([A-Za-z0-9]+)'", path.read_text(errors="ignore")))


def words(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", text))


def main() -> None:
    dep = {year: deprecations(path) for year, path in DEP_FILES.items()}
    pre = {year: listed_in_pre(path) for year, path in PRE_FILES.items()}
    elts = {year: elements(path) for year, path in XSD_FILES.items()}
    changes = pd.read_csv(OUT / "dqc_changes.csv.gz", dtype={"from": str, "to": str}).fillna("")
    rows, explained = [], []
    summary = {}
    for old_year, new_year in [("2023", "2024"), ("2024", "2025"), ("2025", "2026")]:
        newly = dep[new_year][0] - dep[old_year][0]
        removed_from_taxonomy = elts[old_year] - elts[new_year]
        listed = dep[new_year][0] | pre[new_year] | removed_from_taxonomy   # deprecated or removed by year Y+1
        part = changes[(changes["from"] == old_year) & (changes["to"] == new_year)]
        changed_files = set(part.loc[part["kind"].isin(["logic", "added", "removed"]), "rule_file"])
        for f in sorted((DQC_SRC / old_year).glob("DQC_*.xule")):
            text_words = words(f.read_text(errors="ignore"))
            hits = sorted(text_words & newly)
            hits_any = sorted(text_words & listed)
            rows.append({"from": old_year, "to": new_year, "rule_file": f.name, "flagged": bool(hits),
                         "flagged_any": bool(hits_any), "deprecated_concepts": ";".join(hits_any[:20]),
                         "changed": f.name in changed_files})
        logic = part[(part["kind"] == "logic") & (part["assertion"] != "_preamble")]
        for r in logic.itertuples(index=False):
            removed = words(r.old_code) - words(r.new_code)
            hit = sorted(removed & newly)
            hit_any = sorted(removed & listed)
            explained.append({"from": old_year, "to": new_year, "rule_file": r.rule_file, "assertion": r.assertion,
                              "explained_by_deprecation": bool(hit), "explained_by_any_deprecation": bool(hit_any),
                              "deprecated_concepts": ";".join(hit_any[:10]),
                              "replacements": ";".join(f"{c}->{dep[new_year][1].get(c, '?')}" for c in hit_any[:10])})
        constants = []
        for name in ["constant-us-gaap.xule", "constant.xule"]:
            p = DQC_SRC / old_year / name
            if p.exists():
                constants += sorted(words(p.read_text(errors="ignore")) & newly)
        summary[f"{old_year}->{new_year}"] = {"newly_deprecated_concepts": len(newly),
                                               "removed_from_taxonomy": len(removed_from_taxonomy),
                                               "deprecated_or_removed": len(listed),
                                               "with_replacement": sum(1 for c in newly if c in dep[new_year][1]),
                                               "deprecated_concepts_in_constant_files": len(constants)}
    radar = pd.DataFrame(rows)
    radar.to_csv(OUT / "radar.csv", index=False)
    explained = pd.DataFrame(explained)
    explained.to_csv(OUT / "explained_changes.csv", index=False)
    for (old_year, new_year), g in radar.groupby(["from", "to"]):
        tp = int((g.flagged & g.changed).sum())
        s = summary[f"{old_year}->{new_year}"]
        s.update({"rule_files": len(g), "flagged": int(g.flagged.sum()), "changed": int(g.changed.sum()),
                  "flagged_and_changed": tp,
                  "radar_precision": round(tp / max(int(g.flagged.sum()), 1), 2),
                  "radar_recall": round(tp / max(int(g.changed.sum()), 1), 2)})
        tp_any = int((g.flagged_any & g.changed).sum())
        s.update({"flagged_any": int(g.flagged_any.sum()), "flagged_any_and_changed": tp_any,
                  "radar_any_precision": round(tp_any / max(int(g.flagged_any.sum()), 1), 2),
                  "radar_any_recall": round(tp_any / max(int(g.changed.sum()), 1), 2)})
        e = explained[(explained["from"] == old_year) & (explained["to"] == new_year)]
        s.update({"logic_changes": len(e), "explained_by_deprecation": int(e.explained_by_deprecation.sum()),
                  "explained_by_any_deprecation": int(e.explained_by_any_deprecation.sum())})
    (OUT / "radar_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

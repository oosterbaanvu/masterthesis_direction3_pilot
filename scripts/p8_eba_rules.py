"""EBA mini-pilot, step 1: one row per validation rule across all framework releases (v2.0 to 3.5), with labels.

Input: data/eba_raw/eba_vr_upto_3.5_2026-09-14.xlsx (one sheet per release).
Labels, all taken from the EBA workbook itself:
- deactivated: the rule carries a "Deactivated on" date in any release sheet (the EBA's list of rules to disregard,
  "primarily due to being identified as potentially incorrect"); deactivated_on is the latest such date;
- reactivated: a "Reactivated on" date (deactivation later withdrawn for that release onwards);
- corrected: "Correction" in "Last Change" ("business semantics of the rule had been incorrect").
Output: results/eba/rules.csv.gz and a printed summary.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/eba_raw/eba_vr_upto_3.5_2026-09-14.xlsx"
OUT = ROOT / "results/eba"


def release_key(sheet: str) -> tuple:
    nums = re.findall(r"\d+", sheet.split("(")[0])
    return tuple(int(n) for n in nums) + ((1,) if "Finrep Ind" in sheet else ())


def load() -> pd.DataFrame:
    book = pd.ExcelFile(SRC)
    sheets = sorted([s for s in book.sheet_names if s != "Explanation"], key=release_key)
    frames = []
    for order, sheet in enumerate(sheets):
        d = pd.read_excel(book, sheet_name=sheet, dtype=str)
        if str(d.columns[0]).startswith("Unnamed") and str(d.iloc[0, 0]).strip() == "ID":
            d = pd.read_excel(book, sheet_name=sheet, dtype=str, header=1)   # older sheets: two header rows
        d.columns = [re.sub(r"\s+", " ", str(c).replace("-", "")).strip() for c in d.columns]
        rename = {c: "Narrative" for c in d.columns if c.lower().startswith("narrative")}
        rename.update({c: "Prerequisites" for c in d.columns if c.lower().startswith("prerequisites")})
        rename.update({c: "Deactivated on" for c in d.columns if c.lower().startswith("deactivated")})
        rename.update({c: "Reactivated on" for c in d.columns if c.lower().startswith("reactivated")})
        d = d.rename(columns=rename)
        d["release"] = sheet
        d["release_order"] = order
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    raw = load()
    raw = raw[raw["ID"].notna() & raw["ID"].str.match(r"^[ev]\d", na=False)]
    for col in ["Deactivated on", "Reactivated on"]:
        raw[col + " (date)"] = pd.to_datetime(raw[col], errors="coerce")
    tables = [c for c in raw.columns if re.fullmatch(r"T\d", c)]
    raw["tables"] = raw[tables].apply(lambda r: ";".join(sorted({t for t in r if isinstance(t, str) and t.strip()})), axis=1)
    raw = raw.sort_values(["ID", "release_order"])
    first = raw.groupby("ID").first()
    last = raw.groupby("ID").last()
    rules = pd.DataFrame({
        "id": first.index,
        "first_release": first["release"].values,
        "last_release": last["release"].values,
        "type": last["Type"].str.strip().str.lower().values,
        "severity": last["Severity"].str.strip().str.lower().values,
        "tables": last["tables"].values,
        "formula_first": first["Formula"].values,
        "formula_last": last["Formula"].values,
        "narrative": last.get("Narrative", pd.Series(index=last.index, dtype=str)).values,
        "replaces": last.get("Replaces", pd.Series(index=last.index, dtype=str)).values,
        "deleted_in_last": last["Deleted"].fillna("").str.strip().str.lower().eq("y").values,
    }).reset_index(drop=True)
    grp = raw.groupby("ID")
    rules["deactivated_on"] = rules["id"].map(grp["Deactivated on (date)"].max())
    rules["reactivated_on"] = rules["id"].map(grp["Reactivated on (date)"].max())
    rules["deactivated"] = rules["deactivated_on"].notna()
    rules["corrected"] = rules["id"].map(grp["Last Change"].apply(lambda s: s.fillna("").str.contains("Correction").any()))
    rules["formula_changed"] = rules["formula_first"].fillna("") != rules["formula_last"].fillna("")
    OUT.mkdir(parents=True, exist_ok=True)
    rules.to_csv(OUT / "rules.csv.gz", index=False)
    print("release sheets:", raw["release"].nunique(), "| rules:", len(rules))
    print(rules["type"].value_counts().head(8).to_dict())
    print("deactivated:", int(rules["deactivated"].sum()), "| reactivated:", int(rules["reactivated_on"].notna().sum()),
          "| corrected:", int(rules["corrected"].sum()))
    print("deactivation rate by type:", rules.groupby("type")["deactivated"].agg(["sum", "count", "mean"]).round(3)
          .sort_values("count", ascending=False).head(8).to_dict(orient="index"))
    print("deactivations per year:", rules["deactivated_on"].dt.year.value_counts().sort_index().to_dict())
    manual = rules[rules["type"] == "manual"]
    print("manual rules:", len(manual), "deactivated:", int(manual["deactivated"].sum()),
          "after 2025-04-29:", int((manual["deactivated_on"] > "2025-04-29").sum()),
          "after 2024-11-12:", int((manual["deactivated_on"] > "2024-11-12").sum()))
    print("narrative filled (manual):", int(manual["narrative"].fillna("").str.len().gt(5).sum()))


if __name__ == "__main__":
    main()

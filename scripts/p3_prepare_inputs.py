"""P3c: prepare shared inputs for rule writing: concept metadata, rule selection and published element lists."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p3_rules"
WORK = ROOT / "data/work"
DQC_DOCS = Path("/home/user/dataqualitycommittee/dqc_us_rules/docs")
SEEN_CUTOFF = pd.Timestamp("2024-06-30")    # released before the oldest model (Nov 2024): possibly seen in training
UNSEEN_FROM = pd.Timestamp("2025-06-01")    # released after the newest model (Apr 2025): cannot be in training data
PER_STRATUM = 10


def build_concepts() -> None:
    frames = []
    for path in sorted((ROOT / "data/sec_fsds").glob("20*q*.zip")):
        with zipfile.ZipFile(path) as archive:
            tags = pd.read_csv(archive.open("tag.txt"), sep="\t", dtype=str, keep_default_na=False, quoting=3)
        frames.append(tags[tags["custom"] == "0"])
    tags = pd.concat(frames).drop_duplicates("tag", keep="last")
    tags[["tag", "version", "crdr", "iord", "datatype", "tlabel", "doc"]].to_parquet(WORK / "concepts.parquet", index=False)
    print("concepts", len(tags))


def select_rules() -> pd.DataFrame:
    inventory = pd.read_csv(OUT / "rule_inventory.csv", dtype={"number": str}, parse_dates=["release_date"])
    cases = pd.read_csv(OUT / "official_cases.csv", dtype={"number": str})
    cases["located_rate"] = cases["refs_located"] / cases["n_refs"]
    usable = cases[cases["facts_path"].notna()]
    per_rule = usable.groupby("rule").agg(cases=("case_id", "count"), positive_cases=("n_messages", lambda s: (s > 0).sum()),
                                          located=("located_rate", "mean")).reset_index()
    pool = inventory.merge(per_rule, on="rule")
    pool = pool[(pool["cases"] >= 2) & (pool["positive_cases"] >= 1) & (pool["located"] >= 0.9)]
    seen = pool[pool["release_date"] <= SEEN_CUTOFF].assign(stratum="released_before_models")
    unseen = pool[pool["release_date"] >= UNSEEN_FROM].assign(stratum="released_after_models")
    picked = pd.concat([part.sort_values(["cases", "rule"], ascending=[False, True]).head(PER_STRATUM)
                        for part in (seen, unseen)])
    picked.to_csv(OUT / "selected_rules.csv", index=False)
    print(picked[["rule", "title", "release_date", "stratum", "cases", "positive_cases", "required_inputs"]].to_string())
    return picked


def export_lists(picked: pd.DataFrame) -> None:
    manifest = {}
    for rule in picked.itertuples(index=False):
        folder = DQC_DOCS / f"DQC_US_{rule.number}"
        manifest[rule.rule] = {}
        for xlsx in folder.glob("*.xlsx"):
            frame = pd.read_excel(xlsx)
            target = WORK / "dqc_lists" / rule.rule / (xlsx.stem + ".csv")
            target.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(target, index=False)
            manifest[rule.rule][xlsx.stem] = str(target)
    (WORK / "dqc_lists" / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    build_concepts()
    export_lists(select_rules())

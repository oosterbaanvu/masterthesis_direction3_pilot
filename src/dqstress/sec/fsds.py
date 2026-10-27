"""Read SEC Financial Statement Data Sets (FSDS) and derive natural corrections.

An amendment (10-K/A or 10-Q/A) that re-files the same report lets us compare the
originally filed numbers with the numbers the filer submitted later. A value that
changed is a *correction candidate*: the filer itself replaced it. This is not
proof of an error (a restatement can also follow an accounting change), so the
protocol includes a human review sample.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

SUB_COLUMNS = ["adsh", "cik", "name", "sic", "form", "period", "fy", "fp",
               "filed", "accepted", "prevrpt", "afs", "instance"]
NUM_COLUMNS = ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value"]
CONTEXT = ["ddate", "qtrs", "uom", "segments", "coreg"]
FACT_KEY = ["tag_ns", "tag"] + CONTEXT
BASE_FORMS = {"10-K", "10-Q"}


def quarter_of(zip_path: Path) -> str:
    return Path(zip_path).stem


def load_submissions(zip_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in zip_paths:
        with zipfile.ZipFile(path) as archive:
            frame = pd.read_csv(archive.open("sub.txt"), sep="\t", dtype=str,
                                usecols=SUB_COLUMNS, keep_default_na=False)
        frame["quarter"] = quarter_of(path)
        frames.append(frame)
    sub = pd.concat(frames, ignore_index=True)
    sub["accepted"] = pd.to_datetime(sub["accepted"])
    sub["base_form"] = sub["form"].str.replace("/A", "", regex=False)
    sub["is_amendment"] = sub["form"].str.endswith("/A")
    return sub


def pair_amendments(sub: pd.DataFrame) -> pd.DataFrame:
    """Pair each 10-K/A or 10-Q/A with the most recent earlier filing of the same report.

    Same report = same CIK, base form, balance-sheet date and fiscal period. The
    earlier filing may itself be an amendment (chained amendments).
    """
    filings = sub[sub["base_form"].isin(BASE_FORMS)].sort_values("accepted")
    pairs = []
    for _, group in filings.groupby(["cik", "base_form", "period", "fp"], sort=False):
        rows = group.to_dict("records")
        for position, row in enumerate(rows):
            if not row["is_amendment"] or position == 0:
                continue
            previous = rows[position - 1]
            pairs.append({
                "orig_adsh": previous["adsh"], "amend_adsh": row["adsh"],
                "cik": row["cik"], "name": row["name"], "sic": row["sic"],
                "base_form": row["base_form"], "orig_form": previous["form"],
                "period": row["period"], "fy": row["fy"], "fp": row["fp"],
                "orig_accepted": previous["accepted"], "amend_accepted": row["accepted"],
                "orig_quarter": previous["quarter"], "amend_quarter": row["quarter"],
                "orig_prevrpt": previous["prevrpt"], "orig_instance": previous["instance"],
                "amend_instance": row["instance"],
            })
    return pd.DataFrame(pairs)


def unmatched_amendments(sub: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    amendments = sub[sub["is_amendment"] & sub["base_form"].isin(BASE_FORMS)]
    return amendments[~amendments["adsh"].isin(pairs["amend_adsh"])]


def load_facts(zip_paths: list[Path], wanted: pd.DataFrame, chunk_rows: int = 2_000_000) -> pd.DataFrame:
    """Load NUM rows for the submissions in `wanted` (columns adsh, quarter)."""
    frames = []
    for path in zip_paths:
        adsh_set = set(wanted.loc[wanted["quarter"] == quarter_of(path), "adsh"])
        if not adsh_set:
            continue
        with zipfile.ZipFile(path) as archive:
            reader = pd.read_csv(archive.open("num.txt"), sep="\t", dtype=str, usecols=NUM_COLUMNS,
                                 keep_default_na=False, chunksize=chunk_rows, quoting=3)
            for chunk in reader:
                frames.append(chunk[chunk["adsh"].isin(adsh_set)])
    facts = pd.concat(frames, ignore_index=True)
    facts["value"] = pd.to_numeric(facts["value"].replace("", np.nan), errors="coerce")
    facts["qtrs"] = facts["qtrs"].astype(int)
    # Custom (filer-defined) tags carry the accession number as version.
    facts["tag_ns"] = np.where(facts["version"] == facts["adsh"], "custom",
                               facts["version"].str.split("/").str[0])
    return facts


def classify_change(old: float, new: float) -> str:
    if old == new:
        return "unchanged"
    if old == 0 or new == 0:
        return "zero_change"
    if np.isclose(new, -old, rtol=1e-9, atol=0):
        return "sign_flip"
    exponent = np.log10(abs(new / old))
    if abs(exponent - round(exponent)) < 1e-6 and round(exponent) != 0:
        return "scale" if new * old > 0 else "scale_and_sign"
    if abs(new - old) / max(abs(old), abs(new)) < 1e-3:
        return "precision"
    return "other_value"


def diff_pair(orig: pd.DataFrame, amend: pd.DataFrame) -> pd.DataFrame:
    """Compare two filings fact by fact on (namespace, tag, date, quarters, unit, dimensions, co-registrant)."""
    left = orig[FACT_KEY + ["value"]].rename(columns={"value": "orig_value"})
    right = amend[FACT_KEY + ["value"]].rename(columns={"value": "amend_value"})
    merged = left.merge(right, on=FACT_KEY, how="outer", indicator=True)
    merged["status"] = merged["_merge"].astype(str).map({"left_only": "removed", "right_only": "added", "both": "both"})
    merged = merged.drop(columns="_merge")
    both = merged["status"] == "both"
    merged["change"] = merged["status"]
    merged.loc[both, "change"] = [
        ("unchanged" if (pd.isna(o) and pd.isna(n)) else "nil_change") if (pd.isna(o) or pd.isna(n))
        else classify_change(o, n)
        for o, n in zip(merged.loc[both, "orig_value"], merged.loc[both, "amend_value"])
    ]
    return merged


def detect_moves(diff: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find removed+added fact pairs with the same value that differ only in tag or only in period.

    retags: same context and value, different element (wrong-element corrections).
    period moves: same element and value, different period end or duration (wrong-period corrections).
    Zero values are ignored because they match too easily.
    """
    removed = diff[(diff["status"] == "removed") & diff["orig_value"].notna() & (diff["orig_value"] != 0)]
    added = diff[(diff["status"] == "added") & diff["amend_value"].notna() & (diff["amend_value"] != 0)]
    retags = removed.merge(added, left_on=CONTEXT + ["orig_value"], right_on=CONTEXT + ["amend_value"],
                           suffixes=("", "_new"))
    retags = retags[retags["tag"] != retags["tag_new"]]
    same_element = ["tag_ns", "tag", "uom", "segments", "coreg"]
    moves = removed.merge(added, left_on=same_element + ["orig_value"], right_on=same_element + ["amend_value"],
                          suffixes=("", "_new"))
    moves = moves[(moves["ddate"] != moves["ddate_new"]) | (moves["qtrs"] != moves["qtrs_new"])]
    return retags, moves

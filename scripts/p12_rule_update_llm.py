"""Pilot B, step 3: can a small local model update a DQC rule to a new taxonomy year?

Cases: assertions whose logic changed from year Y to Y+1 and whose removed code mentions a concept that is deprecated
or removed in the Y+1 taxonomy (results/pilot_b/explained_changes.csv), with old code of at most 3,000 characters.
Input: the Y version of the assertion plus change notes generated from the taxonomy files (concept deprecated or
removed in Y+1, and the replacing concept where the taxonomy names one). The model never sees the official Y+1 rule.

Compared with:
- no change: the old rule copied unchanged;
- find and replace (no AI): every deprecated concept with a named replacement is replaced by that concept.
Scoring against the official Y+1 assertion, after removing comments, four-digit years, bookkeeping lines and the
message text (messages are compared separately in the output file):
- exact: the normalised logic is identical;
- similarity: difflib ratio between token sequences;
- added_token_recall: share of the tokens that the official update added that also appear in the candidate;
- stale: deprecated or removed concepts that are still present in the candidate.
Model: qwen2.5-coder-7b (released 12 November 2024), so the 2025 and 2026 rule versions are newer than the model.
Outputs: results/pilot_b/update_cases.csv, update_results.csv (resumable), update_calls.jsonl.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from p10_rule_changes import squash, strip_comments, without_boilerplate, without_message  # noqa: E402
from p11_taxonomy_radar import DEP_FILES, PRE_FILES, XSD_FILES, deprecations, elements, listed_in_pre  # noqa: E402

from dqstress.llm.local import LocalModel, log_call  # noqa: E402

OUT = ROOT / "results/pilot_b"
MAX_CHARS = 3000

SYSTEM = ("You maintain data quality rules written in XULE for US GAAP XBRL filings. You update rules when the "
          "taxonomy changes. Return only the complete updated rule in one ```xule code block.")

TASK = """The US GAAP taxonomy changed from {old} to {new}. Update the rule below so that it works with the {new}
taxonomy. Change only what the taxonomy change requires; keep everything else as it is.

Taxonomy changes that concern concepts used in this rule:
{notes}

Rule ({old} version):
```xule
{code}
```"""


def logic(code: str) -> str:
    return squash(without_message(without_boilerplate(strip_comments(code))))


def tokens(code: str) -> list[str]:
    return re.findall(r"[A-Za-z_$@][A-Za-z0-9_.:-]*|\d+|[^\sA-Za-z0-9]", logic(code))


def score(candidate: str, old: str, new: str, stale_set: set[str]) -> dict:
    cand, ref, before = tokens(candidate), tokens(new), tokens(old)
    added = set(ref) - set(before)
    words = set(re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", candidate))
    return {"exact": logic(candidate) == logic(new),
            "similarity": round(difflib.SequenceMatcher(None, cand, ref, autojunk=False).ratio(), 3),
            "added_token_recall": round(len(added & set(cand)) / len(added), 2) if added else None,
            "stale": len(words & stale_set)}


def build_cases() -> pd.DataFrame:
    changes = pd.read_csv(OUT / "dqc_changes.csv.gz", dtype={"from": str, "to": str}).fillna("")
    explained = pd.read_csv(OUT / "explained_changes.csv", dtype={"from": str, "to": str}).fillna("")
    explained = explained[explained["explained_by_any_deprecation"]]
    cases = changes.merge(explained[["from", "to", "rule_file", "assertion"]], on=["from", "to", "rule_file",
                                                                                     "assertion"])
    cases = cases[cases["old_code"].str.len() <= MAX_CHARS].copy()
    dep = {y: deprecations(p) for y, p in DEP_FILES.items()}
    pre = {y: listed_in_pre(p) for y, p in PRE_FILES.items()}
    elts = {y: elements(p) for y, p in XSD_FILES.items()}
    notes, stale, find_replace = [], [], []
    for _, r in cases.iterrows():
        old_year, new_year = r["from"], r["to"]
        removed = elts[old_year] - elts[new_year]
        listed = dep[new_year][0] | pre[new_year] | removed
        used = set(re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", r.old_code)) & listed
        lines, replaced = [], r.old_code
        for c in sorted(used):
            new_name = dep[new_year][1].get(c)
            state = "removed from the taxonomy" if c in removed else "deprecated"
            lines.append(f"- {c}: {state} in {new_year}" + (f"; replaced by {new_name}" if new_name else
                                                              "; no replacement concept is named"))
            if new_name:
                replaced = re.sub(rf"\b{c}\b", new_name, replaced)
        notes.append("\n".join(lines))
        stale.append(";".join(sorted(used)))
        find_replace.append(replaced)
    cases["notes"], cases["stale_concepts"], cases["find_replace"] = notes, stale, find_replace
    return cases.reset_index(drop=True)


def extract(text: str) -> str:
    m = re.search(r"```(?:xule)?\s*\n(.*?)```", text, re.S)
    return m.group(1) if m else text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder-7b")
    parser.add_argument("--limit", type=int, default=16)
    args = parser.parse_args()
    cases = build_cases()
    cases.to_csv(OUT / "update_cases.csv", index=False)
    print("cases:", len(cases), cases.groupby(["from", "to"]).size().to_dict(), flush=True)
    picked = cases.head(args.limit)
    results_path = OUT / "update_results.csv"
    done = set(pd.read_csv(results_path)["case"]) if results_path.exists() else set()
    model = None
    for i, r in picked.iterrows():
        case = f"{r.rule_file}|{r.assertion}|{r['from']}-{r['to']}"
        if case in done:
            continue
        model = model or LocalModel(args.model, ROOT / "data/models")
        user = TASK.format(old=r["from"], new=r["to"], notes=r.notes, code=r.old_code.strip())
        completion = model.complete(SYSTEM, user, temperature=0.0, seed=0, max_tokens=1600)
        candidate = extract(completion.text)
        log_call(OUT / "update_calls.jsonl", {"experiment": "rule_update", "model": args.model, "case": case,
                                              "system": SYSTEM, "user": user, "response": completion.text,
                                              "seconds": round(completion.seconds, 1)})
        stale_set = set(filter(None, r.stale_concepts.split(";")))
        row = {"case": case, "from": r["from"], "to": r["to"], "seconds": round(completion.seconds, 1)}
        for name, text in [("no_change", r.old_code), ("find_replace", r.find_replace), ("llm", candidate)]:
            for k, v in score(text, r.old_code, r.new_code, stale_set).items():
                row[f"{name}_{k}"] = v
        previous = pd.read_csv(results_path) if results_path.exists() else pd.DataFrame()
        pd.concat([previous, pd.DataFrame([row])], ignore_index=True).to_csv(results_path, index=False)
        print(case, {k: row[k] for k in row if k.endswith(("exact", "similarity"))}, f"{completion.seconds:.0f}s",
              flush=True)


if __name__ == "__main__":
    main()

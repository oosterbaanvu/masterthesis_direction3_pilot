"""EBA mini-pilot, step 2: non-AI baselines for finding expert rules that will later be deactivated.

Same population and cutoff as p8_eba_llm.py: manual rules not deactivated by T = 2025-04-29; label 1 if deactivated
after T. Every score uses only information available at T:
- table history: share of the table's manual rules deactivated before T (a rule in a table with past problems);
- formula features: logistic regression trained on deactivations before T (formula as introduced: length,
  references, tables, operators, comparison, severity, framework letter);
- sibling rarity (after ExceLint): how unusual the rule's formula pattern is among manual rules of the same table;
- recency: rules introduced in a later framework release are assumed riskier (added after the first run, which
  showed that table history points the wrong way);
- length: number of characters of the formula as introduced (added after the LLM run; post hoc);
- random.
AUC treats ties as half; precision at k is the expected value when ties at the cut-off are broken at random.
Confidence intervals bootstrap over tables (positives come in families). auc_within_table uses only
positive-negative pairs from the same table.
Evaluation: AUC and precision at k on (a) the full pool, (b) only tables that contain a positive ("which rule in
this table?"), (c) the LLM sample, with the LLM score next to the baselines when it exists.
Output: results/eba/baseline_scores.csv, results/eba/evaluation.csv.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from p8_eba_llm import OUT, T, load_rules  # noqa: E402

RNG = np.random.default_rng(11)


def template(formula: str) -> str:
    f = str(formula)
    f = re.sub(r"\{[A-Z]{1,2} \d{2,3}\.\d{2}(\.[a-z])?,?", "{TAB,", f)
    f = re.sub(r"\b[rcs]\d{3,4}\b", "X", f)
    f = re.sub(r"\(X-X\)|\(X(, X)+\)|\(sNNN\)|\(sAll\)", "RANGE", f)
    f = re.sub(r"\d+(\.\d+)?%?", "N", f)
    return re.sub(r"\s+", " ", f).strip()


def features(r: pd.DataFrame) -> pd.DataFrame:
    f = r["formula_first"].astype(str)
    x = pd.DataFrame({
        "length": np.log1p(f.str.len()),
        "refs": np.log1p(f.str.count(r"\{")),
        "tables_in_formula": f.str.findall(r"[A-Z]{1,2} \d{2,3}\.\d{2}").apply(lambda t: len(set(t))),
        "has_sum": f.str.contains("sum(", regex=False).astype(int),
        "has_if": f.str.contains(r"\bif\b").astype(int),
        "has_div": f.str.contains("/", regex=False).astype(int),
        "has_mult": f.str.contains("*", regex=False).astype(int),
        "has_pct": f.str.contains("%", regex=False).astype(int),
        "equality": (f.str.contains(r"(?<![<>!])=") & ~f.str.contains(r"[<>]=?")).astype(int),
        "inequality": f.str.contains(r"[<>]").astype(int),
        "error": (r["severity"].fillna("") == "error").astype(int),
        "n_tables": r["tables"].fillna("").str.count(";") + 1,
    }, index=r.index)
    letters = r["t1"].str[0].fillna("?")
    for letter in sorted(letters.unique()):
        x[f"fw_{letter}"] = (letters == letter).astype(int)
    return x


def logistic(x: np.ndarray, y: np.ndarray, steps: int = 3000, lr: float = 0.1, l2: float = 1e-3) -> np.ndarray:
    x = np.hstack([np.ones((len(x), 1)), x])
    w = np.zeros(x.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-x @ w))
        w -= lr * (x.T @ (p - y) / len(y) + l2 * w)
    return w


def auc(score: pd.Series, label: pd.Series) -> float:
    """Rank-based AUC; ties count as half (average ranks)."""
    ranks = score.rank()
    pos = label == 1
    n1, n0 = pos.sum(), (~pos).sum()
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def auc_ci(part: pd.DataFrame, s: str, n: int = 1000) -> tuple[float, float]:
    """Bootstrap over tables, not rules: positives come in families of near-identical rules per table."""
    groups = [g for _, g in part.groupby("t1")]
    vals = []
    for _ in range(n):
        d = pd.concat([groups[i] for i in RNG.integers(0, len(groups), len(groups))], ignore_index=True)
        vals.append(auc(d[s], d["label"]))
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


def within_table_auc(part: pd.DataFrame, s: str) -> float:
    """AUC over positive-negative pairs from the same table only ("which rule in this table?")."""
    wins = pairs = 0.0
    for _, g in part.groupby("t1"):
        p, q = g.loc[g["label"] == 1, s].values, g.loc[g["label"] == 0, s].values
        if len(p) and len(q):
            wins += (p[:, None] > q[None, :]).sum() + 0.5 * (p[:, None] == q[None, :]).sum()
            pairs += len(p) * len(q)
    return float(wins / pairs) if pairs else float("nan")


def precision_at(score: pd.Series, label: pd.Series, k: int) -> float:
    """Expected precision of the top k when ties at the cut-off are broken at random."""
    k = min(k, len(score))
    cut = score.sort_values(ascending=False).iloc[k - 1]
    above, tied = score > cut, score == cut
    hits = label[above].sum() + (k - above.sum()) * label[tied].mean()
    return float(hits / k)


def main() -> None:
    all_rules = pd.read_csv(OUT / "rules.csv.gz", parse_dates=["deactivated_on"])
    manual = all_rules[(all_rules["type"] == "manual") & all_rules["formula_first"].notna()].copy()
    manual["t1"] = manual["tables"].fillna("").str.split(";").str[0]
    manual["before_T"] = (manual["deactivated_on"] <= T).astype(int)
    pool = load_rules()

    history = manual.groupby("t1")["before_T"].mean()
    pool["s_table_history"] = pool["t1"].map(history).fillna(0)

    xm = features(manual)
    cols = list(xm.columns)
    mu, sd = xm.mean(), xm.std().replace(0, 1)
    w = logistic(((xm - mu) / sd).values, manual["before_T"].values.astype(float))
    xp = features(pool).reindex(columns=cols, fill_value=0)
    pool["s_formula_features"] = 1 / (1 + np.exp(-np.hstack([np.ones((len(pool), 1)), ((xp - mu) / sd).values]) @ w))

    manual["tpl"] = manual["formula_first"].map(template)
    counts = manual.groupby(["t1", "tpl"]).size()
    pool["tpl"] = pool["formula_first"].map(template)
    pool["s_sibling_rarity"] = 1 / pool.apply(lambda r: counts.get((r["t1"], r["tpl"]), 1), axis=1)
    pool["s_recency"] = pool["first_order"].astype(float)
    pool["s_length"] = pool["formula_first"].astype(str).str.len().astype(float)
    pool["s_random"] = RNG.random(len(pool))
    scores = [c for c in pool.columns if c.startswith("s_")]
    pool[["id", "t1", "label"] + scores].to_csv(OUT / "baseline_scores.csv", index=False)

    rows = []
    pos_tables = pool.loc[pool["label"] == 1, "t1"].unique()
    recent = pool["first_order"] >= pool["first_order"].max() - 2
    sets = {"full_pool": pool, "tables_with_a_positive": pool[pool["t1"].isin(pos_tables)],
            "rules_from_last_3_releases": pool[recent],
            "newest_release_only": pool[pool["first_order"] == pool["first_order"].max()]}
    llm_path = OUT / "llm_scores.csv"
    if llm_path.exists():
        llm = pd.read_csv(llm_path).dropna(subset=["score"])
        sample = pool.merge(llm[["id", "score", "group"]], on="id")
        sample["s_llm"] = sample["score"]
        sets["llm_sample"] = sample
        sets["llm_sample_same_tables"] = sample[sample["group"] != "negative_other_table"]
        sets["llm_sample_last_3_releases"] = sample[sample["first_order"] >= pool["first_order"].max() - 2]
        sets["llm_sample_newest_release"] = sample[sample["first_order"] == pool["first_order"].max()]
    for name, part in sets.items():
        part = part.reset_index(drop=True)
        for s in [c for c in part.columns if c.startswith("s_")]:
            lo, hi = auc_ci(part, s, n=500)
            rows.append({"set": name, "rules": len(part), "positives": int(part["label"].sum()),
                         "tables": part["t1"].nunique(), "base_rate": round(part["label"].mean(), 4), "score": s,
                         "auc": round(auc(part[s], part["label"]), 3), "auc_lo": round(lo, 3), "auc_hi": round(hi, 3),
                         "auc_within_table": round(within_table_auc(part, s), 3),
                         "p_at_20": round(precision_at(part[s], part["label"], 20), 2),
                         "p_at_50": round(precision_at(part[s], part["label"], 50), 2)})
    ev = pd.DataFrame(rows)
    ev.to_csv(OUT / "evaluation.csv", index=False)
    print(ev.to_string(index=False))


if __name__ == "__main__":
    main()

"""Recover exactly which facts an injected variant changed, by comparing it with the clean filing.

More reliable than the injection log stored in CSV (that column could be truncated for long change lists).
"""
from __future__ import annotations

import pandas as pd


def _keyed(facts: pd.DataFrame) -> pd.Series:
    numeric = facts[facts["is_numeric"]]
    key = numeric["prefix"] + ":" + numeric["concept"] + "|" + numeric["context_ref"] + "|" + numeric["unit"].fillna("")
    return pd.Series(numeric["value"].values, index=key).groupby(level=0).first()


def injected_keys(clean: pd.DataFrame, variant: pd.DataFrame) -> set[tuple[str, str]]:
    """(qname, context_ref) of facts that are new, changed or gone in the variant."""
    before, after = _keyed(clean), _keyed(variant)
    changed = set(after.index) ^ set(before.index)
    common = before.index.intersection(after.index)
    differs = ~((before[common] == after[common]) | (before[common].isna() & after[common].isna()))
    changed |= set(common[differs.values])
    return {(key.split("|")[0], key.split("|")[1]) for key in changed}

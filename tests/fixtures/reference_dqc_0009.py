# Hand-written reference translation of DQC_0009 (used only to validate the evaluation harness).
import pandas as pd


def check(facts, lists, concepts):
    pairs = lists["DQC_0009_ListOfElements"][["Element name (fact1)", "Element name (fact2)"]].dropna()
    numeric = facts[facts["is_numeric"] & facts["value"].notna() & (facts["prefix"] == "us-gaap")]
    flagged = []
    for lesser, greater in pairs.itertuples(index=False):
        left = numeric[numeric["concept"] == lesser]
        right = numeric[numeric["concept"] == greater]
        if left.empty or right.empty:
            continue
        merged = left.merge(right, on=["end", "start", "dimensions", "unit"], suffixes=("_1", "_2"))
        for row in merged.itertuples(index=False):
            if row.value_1 > row.value_2:
                flagged.append({"qname": "us-gaap:" + lesser, "context_ref": row.context_ref_1})
                flagged.append({"qname": "us-gaap:" + greater, "context_ref": row.context_ref_2})
    return flagged

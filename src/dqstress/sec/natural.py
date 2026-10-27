"""Match natural corrections (FSDS rows) to facts of the original instance document."""
from __future__ import annotations

from datetime import date

import pandas as pd

GOLD_TYPES = ["sign_flip", "scale", "scale_and_sign", "other_value", "zero_change", "retag", "period_move"]


def load_gold(path) -> pd.DataFrame:
    corr = pd.read_csv(path, low_memory=False)
    return corr[corr["segments"].isna() & corr["correction_type"].isin(GOLD_TYPES)]


def gold_keys(facts: pd.DataFrame, gold: pd.DataFrame) -> list[set]:
    """For each corrected FSDS fact, the (qname, context_ref) keys of matching instance facts.

    FSDS rounds the period end to the nearest month end and counts durations in quarters, so a match
    requires the same element, unit and number of quarters and an end date within 31 days.
    """
    plain = facts[facts["is_numeric"] & (facts["dimensions"] == "")].copy()
    plain["qtrs"] = [round(((date.fromisoformat(e[:10]) - date.fromisoformat(s[:10])).days) / 91) if s and e else 0
                     for s, e in zip(plain["start"], plain["end"])]
    plain["end_ts"] = pd.to_datetime(plain["end"]).dt.to_period("M").dt.to_timestamp("M")
    keys = []
    for item in gold.itertuples(index=False):
        ddate = pd.to_datetime(str(int(item.ddate)))
        match = plain[(plain["concept"] == item.tag) & (plain["qtrs"] == int(item.qtrs)) & (plain["unit"] == item.uom)
                      & (plain["end_ts"].sub(ddate).abs().dt.days <= 31)]
        keys.append(set(zip(match["prefix"] + ":" + match["concept"], match["context_ref"])))
    return keys

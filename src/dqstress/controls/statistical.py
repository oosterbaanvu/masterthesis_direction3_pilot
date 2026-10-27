"""Statistical checks learned from history (reference statistics from earlier filings of other companies)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

MIN_REFERENCE_FILINGS = 30
RARE_NEGATIVE_SHARE = 0.02      # flag a negative value if fewer than 2% of filings report this element negative
MAGNITUDE_Z = 4.0               # robust z on log10 |value|
MIN_LOG_DEVIATION = 1.5         # and at least a factor ~30 from the typical magnitude
PERIOD_JUMP_LOG10 = 2.0         # current vs prior period differ by a factor >= 100


def _plain(facts: pd.DataFrame) -> pd.DataFrame:
    plain = facts[facts["is_numeric"] & facts["value"].notna() & (facts["dimensions"] == "")
                  & facts["unit"].isin(["USD", "shares"])].copy()
    plain["qname"] = plain["prefix"] + ":" + plain["concept"]
    return plain


def sign_rarity(facts: pd.DataFrame, reference: pd.DataFrame) -> list[tuple[str, str]]:
    plain = _plain(facts)
    plain = plain[(plain["prefix"] == "us-gaap") & (plain["value"] < 0)]
    merged = plain.merge(reference, left_on=["concept", "unit"], right_on=["tag", "uom"])
    rare = merged[(merged["filings"] >= MIN_REFERENCE_FILINGS) & (merged["share_negative"] < RARE_NEGATIVE_SHARE)]
    return list(zip(rare["qname"], rare["context_ref"]))


def magnitude_outlier(facts: pd.DataFrame, reference: pd.DataFrame) -> list[tuple[str, str]]:
    plain = _plain(facts)
    plain = plain[(plain["prefix"] == "us-gaap") & (plain["value"] != 0)]
    merged = plain.merge(reference, left_on=["concept", "unit"], right_on=["tag", "uom"])
    merged = merged[(merged["filings"] >= MIN_REFERENCE_FILINGS) & (merged["log_mad"] > 0)]
    deviation = np.log10(merged["value"].abs()) - merged["log_median"]
    z = deviation / (1.4826 * merged["log_mad"])
    out = merged[(z.abs() > MAGNITUDE_Z) & (deviation.abs() >= MIN_LOG_DEVIATION)]
    return list(zip(out["qname"], out["context_ref"]))


def _days(start, end) -> int:
    if not start or not end:
        return 0
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def period_jump(facts: pd.DataFrame) -> list[tuple[str, str]]:
    """Compare the latest value of an element with the previous period of the same length in the same filing."""
    plain = _plain(facts)
    plain = plain[plain["value"] != 0].copy()
    plain["length"] = [round(_days(s, e) / 91) for s, e in zip(plain["start"], plain["end"])]
    flagged = []
    for _, group in plain.groupby(["qname", "unit", "period_type", "length"]):
        if group["end"].nunique() < 2:
            continue
        ordered = group.sort_values("end")
        latest, previous = ordered.iloc[-1], ordered[ordered["end"] < ordered.iloc[-1]["end"]].iloc[-1]
        if np.sign(latest["value"]) == np.sign(previous["value"]):
            jump = abs(np.log10(abs(latest["value"])) - np.log10(abs(previous["value"])))
            if jump >= PERIOD_JUMP_LOG10:
                flagged += [(latest["qname"], latest["context_ref"]), (previous["qname"], previous["context_ref"])]
    return flagged


def controls(reference: pd.DataFrame) -> dict:
    return {
        "stat_sign_rarity": lambda facts: sign_rarity(facts, reference),
        "stat_magnitude": lambda facts: magnitude_outlier(facts, reference),
        "stat_period_jump": period_jump,
    }

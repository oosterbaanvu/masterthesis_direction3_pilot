"""Generic rules a data engineer writes without accounting knowledge."""
from __future__ import annotations

import pandas as pd


def _qname(facts: pd.DataFrame) -> pd.Series:
    return facts["prefix"] + ":" + facts["concept"]


def duplicate_conflict(facts: pd.DataFrame) -> list[tuple[str, str]]:
    """The same element, context and unit reported twice with different values."""
    numeric = facts[facts["is_numeric"] & facts["value"].notna()].assign(qname=_qname)
    groups = numeric.groupby(["qname", "context_ref", "unit"])["value"].nunique()
    conflicts = groups[groups > 1].reset_index()
    return list(zip(conflicts["qname"], conflicts["context_ref"]))


def required_document_facts(facts: pd.DataFrame) -> list[tuple[str, str]]:
    """Every filing must report its document type and period end date (flagged on the entity's main context)."""
    qnames = set(_qname(facts))
    missing = [q for q in ("dei:DocumentType", "dei:DocumentPeriodEndDate") if q not in qnames]
    return [(q, "") for q in missing]


def naive_non_negative(facts: pd.DataFrame) -> list[tuple[str, str]]:
    """A naive rule without domain knowledge: every monetary amount must be zero or positive."""
    money = facts[facts["is_numeric"] & (facts["unit"] == "USD") & (facts["value"] < 0)]
    return list(zip(_qname(money), money["context_ref"]))


CONTROLS = {
    "generic_schema": lambda facts: duplicate_conflict(facts) + required_document_facts(facts),
    "naive_non_negative": naive_non_negative,
}

"""Compare facts flagged by a rule with the facts referenced by official DQC messages."""
from __future__ import annotations

import pandas as pd


def message_recall(flagged: list[dict], expected: pd.DataFrame) -> dict:
    """Recall per official message: a message counts as found when the rule flags any fact it references.

    dei facts that DQC attaches as context (document type, period end date) are ignored unless a
    message references only dei facts.
    """
    flagged_keys = {(f["qname"], f["context_ref"]) for f in flagged}
    found = unlocatable = 0
    messages = expected.groupby("message_no")
    for _, refs in messages:
        core = refs[~refs["qname"].fillna("").str.startswith("dei:")]
        if core.empty:
            # The message only points at document-level dei facts, so it cannot be matched to the
            # fact that caused it; it is reported separately and left out of recall.
            unlocatable += 1
            continue
        keys = set(zip(core["qname"], core["context_ref"]))
        found += bool(keys & flagged_keys)
    all_refs = set(zip(expected["qname"], expected["context_ref"]))
    return {"official_messages": len(messages) - unlocatable, "unlocatable_messages": unlocatable,
            "messages_found": found,
            "flags": len(flagged_keys), "flags_matching_official": len(flagged_keys & all_refs),
            "flags_outside_official": len(flagged_keys - all_refs)}

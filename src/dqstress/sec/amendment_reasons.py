"""Classify the stated reason of an amendment from its explanatory note.

Deliberately simple keyword rules so that every label is traceable to the words
in the filing. Labels are not exclusive: one amendment can, for example, both
restate figures and correct XBRL tagging.
"""
from __future__ import annotations

import re

REASON_PATTERNS = {
    "restatement": r"\brestat(e|ed|ement|ing)\b|non-reliance|previously issued financial statements",
    "xbrl_tagging": r"\bxbrl\b|inline xbrl|interactive data|\btagg(ing|ed)\b|exhibit 101",
    "clerical_error": r"typographical|scrivener|clerical|inadvertent(ly)?|transposition|incorrect(ly)? (stated|reported|presented)",
    "auditor_report": r"report of independent registered|auditor'?s report|pcaob|audit opinion|consent of",
    "part_iii": r"\bpart iii\b|items? 10 through 14",
    "exhibits_certifications": r"\bexhibits?\b|certifications?|section 302|section 906",
    "cover_or_signature": r"cover page|signature|signed",
}


def classify_reason(note: str | None) -> dict[str, bool]:
    text = (note or "").lower()
    return {label: bool(re.search(pattern, text)) for label, pattern in REASON_PATTERNS.items()}


PURPOSE_CHARS = 1200
BOILERPLATE = re.compile(r"amends? and restates?\s+(the\s+)?(original\s+)?(report|filing|form|quarterly report|annual report)"
                         r"[^.]{0,60}in its entirety", re.IGNORECASE)
RESTATEMENT = r"restat(ed|ement|ing)|restates? (its|our|the)[^.]{0,40}financial statements|non-reliance|should no longer be relied"
NON_FINANCIAL = (r"exhibit|certification|signature|cover page|shell company|report of independent|audit(or)?'?s? report|"
                 r"pcaob|consent|part iii|items? 10 through 14|item 9a|internal control|disclosure controls|"
                 r"management'?s discussion|risk factors|comment(s)? (letter )?from the (sec|staff)|in response to (sec|staff) comments|"
                 r"directors|executive compensation|beneficial own|owned by")
FS_AMENDMENT = (r"amend(s|ing|ed)?\b[^.]{0,80}(consolidated |condensed |interim )*financial (statements|information)|"
                r"\bitem 8\b|reclassif|reverse (stock )?split|retroactively adjusted|immaterial (amendments|corrections)")
FINANCIAL_TERMS = (r"revenue|expense|income|loss|assets?|liabilit|equity|cash|balance sheet|statements? of|financial statements|"
                   r"earnings per share|amount|figure|total|number of shares|shares outstanding|weighted|footnote|note \d+|price")
CORRECTION = r"correct|typographical|scrivener|clerical|inadvertent|transposition|erroneous|incorrect|misstat"
XBRL = r"xbrl|interactive data|tagging|tagged"


def primary_purpose(note: str | None) -> str:
    """One label per amendment from the purpose stated at the start of its explanatory note.

    restatement    the filer restates previously issued financial statements
    targeted_fix   a specific correction of reported figures or financial-statement text, or an amendment of
                   the financial statements that is not called a restatement
    xbrl_fix       a correction of the XBRL data or tagging
    non_financial  exhibits, certifications, auditor report, cover page, Part III, controls or other disclosures
    unclear        none of the above can be read from the first part of the note
    Text extraction can glue words together ('RestatementThe'), so patterns avoid trailing word boundaries.
    """
    if not note:
        return "no_note"
    text = BOILERPLATE.sub(" ", note[:PURPOSE_CHARS]).lower()
    if re.search(RESTATEMENT, text):
        return "restatement"
    if re.search(XBRL, text):
        return "xbrl_fix"
    correction = re.search(CORRECTION, text)
    if correction:
        window = text[max(0, correction.start() - 150): correction.end() + 250]
        if re.search(FINANCIAL_TERMS, window) and not re.search(NON_FINANCIAL, window):
            return "targeted_fix"
    if re.search(FS_AMENDMENT, text):
        return "targeted_fix"
    if re.search(NON_FINANCIAL, text):
        return "non_financial"
    if correction:
        return "targeted_fix"
    return "unclear"

"""Prompts for the rule-writing experiments. Identical for every model."""
from __future__ import annotations

import re

import pandas as pd

SYSTEM = ("You are a careful data-quality engineer at a financial institution. You turn written "
          "data-quality requirements into deterministic, readable Python checks that a reviewer can "
          "approve. Answer with exactly one Python code block and nothing else.")

FACTS_SCHEMA = """`facts` is a pandas DataFrame with one row per reported XBRL fact of ONE filing:
- prefix (str): namespace prefix, e.g. 'us-gaap', 'dei', 'srt', or the company prefix
- concept (str): element local name, e.g. 'Assets', 'CommonStockSharesOutstanding'
- context_ref (str): context identifier of the fact
- period_type (str): 'instant' or 'duration'
- start (str or None): ISO start date for durations; end (str): ISO end date or instant date
- dimensions (str): '' when there are no dimensions, otherwise 'axisQName=memberQName' pairs joined by ';' and sorted,
  e.g. 'us-gaap:StatementClassOfStockAxis=us-gaap:CommonClassAMember'
- unit (str or None): e.g. 'USD', 'shares', 'pure', 'USD/shares'
- decimals (str or None): XBRL decimals attribute, e.g. '-3', '0', 'INF'
- is_numeric (bool), nil (bool)
- value (float or NaN): numeric value for numeric facts
- text (str or None): value of non-numeric facts (e.g. dei:DocumentPeriodEndDate as 'YYYY-MM-DD', dei:DocumentType)
A fact is identified by (prefix + ':' + concept, context_ref)."""

CONCEPTS_SCHEMA = """`concepts` is a pandas DataFrame with metadata for standard taxonomy elements (may be incomplete):
- tag (str): element local name; crdr (str): 'C' credit, 'D' debit or empty; iord (str): 'I' instant or 'D' duration;
- datatype (str): e.g. 'monetary', 'shares', 'perShare', 'percent'; tlabel (str): standard label; doc (str): definition"""

TASK = """Write a function

    def check(facts, lists, concepts):
        ...
        return flagged

that returns a list of dicts {{"qname": "<prefix>:<concept>", "context_ref": "<context_ref>"}}, one for every fact
that the rule above would report as an issue (include the facts the rule message refers to). Follow the rule
documentation as closely as possible, including its conditions and exceptions. Use only pandas, numpy, re, math and
datetime. Do not read or write files and do not use the network. If part of the rule needs information that is not
available in these inputs, implement the rest and explain the gap in a short comment.{lists_hint}"""


def trim_rule_doc(markdown: str, max_chars: int = 14000) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)          # images
    text = re.sub(r"\[([^\]]+)\]\((?:https?://)[^)]*\)", r"\1", text)  # keep link text only
    text = re.split(r"©\s*Copyright", text)[0]
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:max_chars]


def describe_lists(lists: dict[str, pd.DataFrame]) -> str:
    if not lists:
        return ""
    parts = ["\n\n`lists` is a dict of pandas DataFrames published with this rule:"]
    for name, frame in lists.items():
        parts.append(f"- lists['{name}']: {len(frame)} rows, columns {list(frame.columns)}; first rows:\n"
                     + frame.head(3).to_csv(index=False))
    return "\n".join(parts)


def translate_prompt(rule_doc: str, lists: dict[str, pd.DataFrame]) -> str:
    return (f"## Data-quality rule documentation\n\n{trim_rule_doc(rule_doc)}\n\n## Inputs\n\n{FACTS_SCHEMA}\n\n"
            f"{CONCEPTS_SCHEMA}\n\n## Task\n\n" + TASK.format(lists_hint=describe_lists(lists)))


DISCOVER_TASK = """You receive the financial-statement facts of SEC filings (schema above) and metadata for the most
common elements below. Without any given rule set, propose validation rules that would catch REPORTING ERRORS in a
filing: for example wrong signs, wrong scale, values that break accounting relationships between elements, values
assigned to the wrong period, or a value reported under the wrong element. Prefer rules with few false alarms on
correct filings.

Write ONE function

    def check(facts, lists, concepts):
        ...
        return flagged

containing several sub-rules. Return a list of dicts {{"qname": "<prefix>:<concept>", "context_ref": "<context_ref>",
"rule": "<short rule name>"}} for every fact a sub-rule reports. Start every sub-rule with a comment that states the
rule in one sentence. Use only pandas, numpy, re, math and datetime; no files, no network.

## Most common elements (name | balance | period type | data type | label)
{elements}
{feedback}"""


def element_table(concepts: pd.DataFrame, names: list[str]) -> str:
    rows = concepts.set_index("tag").reindex(names).reset_index()
    return "\n".join(f"{r.tag} | {r.crdr or '-'} | {r.iord or '-'} | {r.datatype or '-'} | {r.tlabel}"
                     for r in rows.itertuples(index=False))


def discover_prompt(concepts: pd.DataFrame, names: list[str], feedback: str = "") -> str:
    return (f"## Inputs\n\n{FACTS_SCHEMA}\n\n{CONCEPTS_SCHEMA}\n\n## Task\n\n"
            + DISCOVER_TASK.format(elements=element_table(concepts, names), feedback=feedback))


JUDGE_SYSTEM = ("You are a careful reviewer of SEC financial statements in XBRL. You look for reporting errors in "
                "the reported numbers. Answer only with JSON.")

JUDGE_TASK = """Below are the numeric facts (no dimensions, units USD or shares) of one filing, one per line as
`row | element | period | unit | value`. Periods are 'I:<date>' for instants and 'D:<start>..<end>' for durations.
Some facts may contain reporting errors such as a wrong sign, a wrong scale (e.g. x1000), an amount that does not fit
the other figures, a value under the wrong element, or a value assigned to the wrong period.

Return a JSON list with at most {budget} objects {{"row": <row number>, "reason": "<short reason>"}}, ordered from most
to least likely error. Return [] if nothing looks wrong.

{rows}"""


def judge_prompt(facts: pd.DataFrame, budget: int = 10, max_rows: int = 220) -> tuple[str, pd.DataFrame]:
    plain = facts[facts["is_numeric"] & facts["value"].notna() & (facts["dimensions"] == "")
                  & facts["unit"].isin(["USD", "shares"])].copy()
    latest = sorted(plain["end"].dropna().unique())[-2:]
    plain = plain[plain["end"].isin(latest)].head(max_rows).reset_index(drop=True)
    plain["period"] = ["I:" + e if t == "instant" else f"D:{s}..{e}" for t, s, e in
                       zip(plain["period_type"], plain["start"], plain["end"])]
    lines = [f"{i} | {p}:{c} | {per} | {u} | {v:,.0f}" for i, (p, c, per, u, v) in
             enumerate(zip(plain["prefix"], plain["concept"], plain["period"], plain["unit"], plain["value"]))]
    return JUDGE_TASK.format(budget=budget, rows="\n".join(lines)), plain

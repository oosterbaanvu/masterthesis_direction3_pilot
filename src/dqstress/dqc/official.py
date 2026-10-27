"""Read the official DQC test suite: which filing each rule was tested on and what it reported.

The DQC repository ships, per rule, real SEC filings (and synthetic test files) together
with the Arelle/XULE log the committee produced. Those logs are the reference output:
for each rule message we keep the facts it points to (QName + context + value).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from lxml import etree

DQC_ROOT = Path("/home/user/dataqualitycommittee/dqc_us_rules")
LOADED = re.compile(r"loaded in .* - (\S+)\s*$")


def test_inputs() -> pd.DataFrame:
    """All (rule element id, input file) pairs listed in secvalidationtests.json."""
    rows = []
    for block in json.loads((DQC_ROOT / "tests/secvalidationtests.json").read_text()):
        for infile in block["infiles"]:
            rows.append({"suite": block["name"], "file": infile["file"], "rule_code": infile.get("xule_run_only", "")})
    return pd.DataFrame(rows)


def parse_expected_output(path: Path) -> tuple[str | None, pd.DataFrame]:
    """Return the input file the log was produced from and one row per (DQC message, referenced fact)."""
    # Arelle appends to an existing log file, so some logs hold several XML documents in a row.
    raw = path.read_bytes()
    chunks = [b"<?xml" + part for part in raw.split(b"<?xml") if part.strip()]
    entries = []
    for chunk in chunks:
        entries.extend(etree.fromstring(chunk, etree.XMLParser(recover=True, huge_tree=True)))
    source = None
    rows = []
    for number, entry in enumerate(entries):
        message = entry.find("message")
        text = message.text if message is not None and message.text else ""
        if source is None:
            match = LOADED.search(text.strip())
            if match:
                source = match.group(1)
        code = entry.get("code", "")
        if not code.startswith("DQC."):
            continue
        for ref in entry.findall("ref"):
            props = {p.get("name"): p.get("value") for p in ref.findall("property")}
            rows.append({"message_no": number, "rule_code": code, "level": entry.get("level"),
                         "qname": props.get("QName"), "context_ref": props.get("contextRef"),
                         "value": props.get("value"), "fact_ref": (ref.get("href") or "").split("#")[-1],
                         "message": text[:300]})
    return source, pd.DataFrame(rows, columns=["message_no", "rule_code", "level", "qname", "context_ref",
                                               "value", "fact_ref", "message"])


def expected_outputs(rule_number: str) -> list[Path]:
    return sorted(p for p in (DQC_ROOT / "tests/output").glob(f"*DQC.US.{rule_number}*.xml"))


def instance_url_for(htm_url: str) -> str:
    """EDGAR stores the XBRL instance extracted from an inline document as '<doc>_htm.xml'."""
    base = htm_url.replace("http://", "https://")
    return re.sub(r"\.htm$", "_htm.xml", base)

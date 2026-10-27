"""Run the official DQC rules (Arelle + XULE + DQC plugin) on an instance document.

The instance may be a local, modified copy; its company schema and linkbases are downloaded once
per filing and placed next to it so that relative references resolve. Output: one row per
(DQC message, referenced fact) with QName and context, the same format as every other control.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pandas as pd

from dqstress.sec import edgar

ROOT = Path(__file__).resolve().parents[3]
ARELLE = ROOT / "data/env/bin/arelleCmdLine"
XULE_PLUGIN = Path("/home/user/xbrlus/xule/plugin/xule")
DQC_PLUGIN = Path("/home/user/xbrlus/xule/plugin/validate/DQC.py")
RULESETS = Path("/home/user/dataqualitycommittee/dqc_us_rules/dqc_us_rules")
SUPPORT_SUFFIXES = (".xsd", "_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")


def ruleset_for(instance: Path) -> Path | None:
    """Pick the compiled DQC ruleset that matches the US GAAP taxonomy year of the filing."""
    head = instance.read_bytes()[:200_000].decode("utf-8", errors="ignore")
    match = re.search(r"http://fasb\.org/us-gaap/(\d{4})", head)
    if not match:
        return None
    path = RULESETS / f"dqc-us-{match.group(1)}-V31-ruleset.zip"
    return path if path.exists() else None


def fetch_support_files(cik: str, adsh: str, folder: Path) -> list[str]:
    """Download the company schema and linkbases of a filing into `folder` (once)."""
    listing = json.loads(edgar.get(f"{edgar.filing_folder(cik, adsh)}/index.json").text)
    names = [item["name"] for item in listing["directory"]["item"] if item["name"].endswith(SUPPORT_SUFFIXES)]
    for name in names:
        edgar.download(f"{edgar.filing_folder(cik, adsh)}/{name}", folder / name)
    return names


def run(instance: Path, log_path: Path, timeout: int = 1800, reuse: bool = True) -> tuple[str, pd.DataFrame]:
    ruleset = ruleset_for(instance)
    if ruleset is None:
        return "no_matching_ruleset", pd.DataFrame()
    done_marker = log_path.with_suffix(".done")
    if reuse and done_marker.exists() and log_path.exists():
        return "ok", parse_log(log_path)
    if log_path.exists():
        log_path.unlink()  # Arelle appends to an existing log
    env = dict(os.environ, SSL_CERT_FILE="/root/.ccr/ca-bundle.crt", REQUESTS_CA_BUNDLE="/root/.ccr/ca-bundle.crt")
    command = [str(ARELLE), "--plugins", f"{XULE_PLUGIN}|{DQC_PLUGIN}", "-f", str(instance), "-v",
               "--httpUserAgent", edgar.user_agent(), "--xule-rule-set", str(ruleset), "--logFile", str(log_path)]
    try:
        subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "timeout", pd.DataFrame()
    if not log_path.exists():
        return "no_log", pd.DataFrame()
    done_marker.write_text("ok")
    return "ok", parse_log(log_path)


def parse_log(log_path: Path) -> pd.DataFrame:
    data = json.loads(log_path.read_text())
    entries = data.get("log", data) if isinstance(data, dict) else data
    rows = []
    for number, entry in enumerate(entries):
        code = str(entry.get("code", ""))
        if not code.startswith("DQC."):
            continue
        for ref in entry.get("refs", []):
            props = {p[0]: p[1] for p in ref.get("properties", []) if isinstance(p, list) and len(p) >= 2}
            rows.append({"message_no": number, "rule_code": code, "level": entry.get("level"),
                         "qname": props.get("QName"), "context_ref": props.get("contextRef"),
                         "value": props.get("value")})
    return pd.DataFrame(rows, columns=["message_no", "rule_code", "level", "qname", "context_ref", "value"])

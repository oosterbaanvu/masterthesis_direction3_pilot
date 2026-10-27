"""Rule registry with an evidence trail: who or what proposed a rule, how it was tested, who approved it.

Stored as JSON lines so every change is appended, never overwritten (the latest entry per rule id counts).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

STATUSES = {"proposed", "candidate", "approved", "rejected", "retired"}


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def append(registry: Path, entry: dict) -> dict:
    if entry.get("status") not in STATUSES:
        raise ValueError(f"unknown status {entry.get('status')}")
    record = dict(entry, recorded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    registry.parent.mkdir(parents=True, exist_ok=True)
    with open(registry, "a") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def current(registry: Path) -> dict[str, dict]:
    if not registry.exists():
        return {}
    latest: dict[str, dict] = {}
    for line in registry.read_text().splitlines():
        record = json.loads(line)
        latest[record["rule_id"]] = record
    return latest


def gate(metrics: dict, policy: dict) -> tuple[str, list[str]]:
    """Apply the approval policy to measured evidence. Returns (status, reasons)."""
    reasons = []
    if policy.get("reject_on_sandbox_failure") and metrics.get("sandbox_failures", 0) > 0:
        reasons.append(f"sandbox failures: {metrics['sandbox_failures']}")
    if metrics.get("alerts_per_clean_filing", 0) > policy["max_alerts_per_clean_filing"]:
        reasons.append(f"alerts per clean filing {metrics['alerts_per_clean_filing']:.2f} > "
                       f"{policy['max_alerts_per_clean_filing']}")
    if metrics.get("gap_catch_rate", 0) < policy["min_gap_catch_rate"]:
        reasons.append(f"catch rate on targeted gap {metrics.get('gap_catch_rate', 0):.2f} < {policy['min_gap_catch_rate']}")
    if reasons:
        return "rejected", reasons
    if metrics.get("runs_reproducing_rule", 0) < policy["min_runs_reproducing_rule"]:
        return "candidate", ["passes thresholds but was not reproduced across runs: reviewer must check carefully"]
    return "candidate", ["passes thresholds; awaiting human approval"]

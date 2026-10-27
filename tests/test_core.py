"""Unit tests for the parts whose correctness every result depends on."""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import pytest

from dqstress.inject.xbrl_inject import inject
from dqstress.rules.evaluate import message_recall
from dqstress.rules.sandbox import run_rule, static_check
from dqstress.sec.amendment_reasons import primary_purpose
from dqstress.sec.fsds import classify_change, diff_pair
from dqstress.sec.xbrl_instance import parse_instance

INSTANCE = """<?xml version="1.0" encoding="utf-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2024"
  xmlns:dei="http://xbrl.sec.gov/dei/2024" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">
  <xbrli:context id="c2024"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>
  <xbrli:context id="c2023"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period></xbrli:context>
  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
  <dei:DocumentType contextRef="c2024">10-K</dei:DocumentType>
  <us-gaap:Assets contextRef="c2024" unitRef="usd" decimals="-3" id="f1">1500000</us-gaap:Assets>
  <us-gaap:Assets contextRef="c2023" unitRef="usd" decimals="-3" id="f2">1200000</us-gaap:Assets>
  <us-gaap:NetIncomeLoss contextRef="c2024" unitRef="usd" decimals="-3" id="f3">300000</us-gaap:NetIncomeLoss>
</xbrli:xbrl>
"""


@pytest.fixture
def instance(tmp_path: Path) -> Path:
    path = tmp_path / "filing_htm.xml"
    path.write_text(INSTANCE)
    return path


def test_classify_change_types():
    assert classify_change(100.0, -100.0) == "sign_flip"
    assert classify_change(100.0, 100000.0) == "scale"
    assert classify_change(100.0, 100.04) == "precision"
    assert classify_change(100.0, 0.0) == "zero_change"
    assert classify_change(100.0, 150.0) == "other_value"


def test_diff_pair_marks_nil_on_both_sides_unchanged():
    key = {"tag_ns": "us-gaap", "tag": "Assets", "ddate": "20241231", "qtrs": 0, "uom": "USD", "segments": "", "coreg": ""}
    orig = pd.DataFrame([key | {"value": float("nan")}])
    amend = pd.DataFrame([key | {"value": float("nan")}])
    assert diff_pair(orig, amend)["change"].tolist() == ["unchanged"]


def test_parse_instance_reads_periods_units_and_values(instance):
    facts = parse_instance(instance)
    assets = facts[facts["concept"] == "Assets"].set_index("context_ref")
    assert assets.loc["c2024", "value"] == 1_500_000 and assets.loc["c2023", "end"] == "2023-12-31"
    assert assets.loc["c2024", "unit"] == "USD" and assets.loc["c2024", "dimensions"] == ""


@pytest.mark.parametrize("operator", ["sign_flip", "scale_x1000", "changed_amount", "one_digit", "period_swap", "drop_fact"])
def test_injection_changes_exactly_what_it_logs(instance, tmp_path, operator):
    target = tmp_path / f"{operator}.xml"
    result = inject(instance, operator, 1, random.Random(0), target, amount_ratios=[2.0])
    assert result is not None and result.changes
    before = parse_instance(instance).set_index(["concept", "context_ref"])["value"].dropna()
    after = parse_instance(target).set_index(["concept", "context_ref"])["value"].dropna()
    changed = {key for key in before.index if key not in after.index or before[key] != after[key]}
    logged = {(c["concept"].split(":")[1], c["context_ref"]) for c in result.changes}
    assert changed == logged


def test_retag_moves_value_to_confused_element(instance, tmp_path):
    target = tmp_path / "retag.xml"
    result = inject(instance, "retag", 1, random.Random(0), target, retag_pairs=[("ProfitLoss", "NetIncomeLoss", 1.0)])
    facts = parse_instance(target)
    assert result.changes[0]["new_concept"] == "us-gaap:ProfitLoss"
    assert "ProfitLoss" in set(facts["concept"]) and "NetIncomeLoss" not in set(facts["concept"])


def test_sandbox_rejects_file_and_network_access():
    assert static_check("import socket\ndef check(f, l, c): return []").startswith("import not allowed")
    assert static_check("def check(f, l, c):\n    return f.to_csv('x')").startswith("file access")
    assert static_check("def other(): pass") == "no top-level function named check"


def test_sandbox_runs_rule_and_returns_flags(instance, tmp_path):
    facts_path = tmp_path / "facts.parquet"
    parse_instance(instance).to_parquet(facts_path)
    code = ("def check(facts, lists, concepts):\n"
            "    big = facts[facts['value'] > 1_400_000]\n"
            "    return [{'qname': p + ':' + c, 'context_ref': r} for p, c, r in zip(big['prefix'], big['concept'], big['context_ref'])]\n")
    result = run_rule(code, facts_path)
    assert result.status == "ok" and result.flagged == [{"qname": "us-gaap:Assets", "context_ref": "c2024"}]


def test_message_recall_ignores_dei_only_messages():
    expected = pd.DataFrame({"message_no": [1, 2], "qname": ["us-gaap:Assets", "dei:DocumentType"],
                             "context_ref": ["c2024", "c0"]})
    result = message_recall([{"qname": "us-gaap:Assets", "context_ref": "c2024"}], expected)
    assert result["official_messages"] == 1 and result["messages_found"] == 1 and result["unlocatable_messages"] == 1


def test_purpose_classifier_reads_purpose_not_boilerplate():
    assert primary_purpose("This Amendment amends and restates the Original Report in its entirety solely to "
                           "include Exhibit 31.1 certifications.") == "non_financial"
    assert primary_purpose("The Company is filing this Amendment to restate its previously issued financial statements.") == "restatement"
    assert primary_purpose("This Amendment is filed solely to correct the number for Net cash provided by financing "
                           "activities in the Statement of Cash Flows.") == "targeted_fix"


def test_injection_changes_every_copy_of_a_duplicated_fact(tmp_path):
    duplicated = INSTANCE.replace(
        '<us-gaap:NetIncomeLoss contextRef="c2024" unitRef="usd" decimals="-3" id="f3">300000</us-gaap:NetIncomeLoss>',
        '<us-gaap:NetIncomeLoss contextRef="c2024" unitRef="usd" decimals="-3" id="f3">300000</us-gaap:NetIncomeLoss>'
        '<us-gaap:NetIncomeLoss contextRef="c2024" unitRef="usd" decimals="-3" id="f4">300000</us-gaap:NetIncomeLoss>')
    source = tmp_path / "dup_htm.xml"
    source.write_text(duplicated)
    target = tmp_path / "out.xml"
    weights = {"NetIncomeLoss": 1.0, "Assets": 1e-9}
    inject(source, "sign_flip", 1, random.Random(0), target, concept_weights=weights)
    facts = parse_instance(target)
    values = facts[facts["concept"] == "NetIncomeLoss"]["value"].tolist()
    assert values == [-300000.0, -300000.0]


def test_registry_gate_never_approves_automatically(tmp_path):
    from dqstress.registry import append, current, gate
    policy = {"max_alerts_per_clean_filing": 1.0, "min_gap_catch_rate": 0.2, "min_runs_reproducing_rule": 2,
              "reject_on_sandbox_failure": True}
    status, _ = gate({"alerts_per_clean_filing": 0.1, "gap_catch_rate": 0.9, "runs_reproducing_rule": 3}, policy)
    assert status == "candidate"
    status, reasons = gate({"alerts_per_clean_filing": 5.0, "gap_catch_rate": 0.9}, policy)
    assert status == "rejected" and "alerts per clean filing" in reasons[0]
    registry = tmp_path / "registry.jsonl"
    append(registry, {"rule_id": "r1", "status": "candidate"})
    append(registry, {"rule_id": "r1", "status": "approved", "approver": "reviewer"})
    assert current(registry)["r1"]["status"] == "approved"


def test_injected_keys_recovers_changed_facts(instance, tmp_path):
    from dqstress.inject.diff import injected_keys
    target = tmp_path / "v.xml"
    result = inject(instance, "sign_flip", 1, random.Random(0), target)
    keys = injected_keys(parse_instance(instance), parse_instance(target))
    assert keys == {(c["concept"], c["context_ref"]) for c in result.changes}

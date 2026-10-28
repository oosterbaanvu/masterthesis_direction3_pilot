"""dqstress: help a data team onboard a source, stress-test its controls and review AI-proposed rules.

Workflow for one source (an XBRL instance in this pilot):

  dqstress register  --instance FILE --name NAME     record the source with a fingerprint
  dqstress baseline  --name NAME                     run existing controls and list findings
  dqstress stress    --name NAME                     inject realistic errors and build the coverage matrix
  dqstress propose   --name NAME --model MODEL       let a local model propose rules for the gaps
  dqstress evaluate  --name NAME --rule FILE         test a proposed rule in the sandbox and apply the gate
  dqstress approve   --rule-id ID --by WHO --reason  record a human decision (approve or reject)
  dqstress report    --name NAME                     write an HTML report with evidence

Nothing is adopted automatically: the gate can only mark a rule as 'candidate'; a person approves it.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import time
from pathlib import Path

import pandas as pd

from dqstress import registry
from dqstress.controls import generic, statistical
from dqstress.inject.diff import injected_keys
from dqstress.inject.xbrl_inject import OPERATORS, inject
from dqstress.rules.sandbox import run_rule_batch
from dqstress.sec.xbrl_instance import parse_instance

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "data/workspace"
POLICY = ROOT / "configs/approval_policy.json"
REFERENCE = ROOT / "data/work/reference_stats.parquet"
CONCEPTS = ROOT / "data/work/concepts.parquet"
REGISTRY = WORKSPACE / "rule_registry.jsonl"
CALIBRATION = ROOT / "configs/injection_calibration.json"


def source_dir(name: str) -> Path:
    return WORKSPACE / "sources" / name


def baseline_controls() -> dict:
    reference = pd.read_parquet(REFERENCE) if REFERENCE.exists() else None
    controls = dict(generic.CONTROLS)
    controls.pop("naive_non_negative")  # shown in the research results, not a sensible production control
    if reference is not None:
        controls |= statistical.controls(reference)
    return controls


def approved_rules() -> dict[str, Path]:
    return {rid: Path(entry["code_path"]) for rid, entry in registry.current(REGISTRY).items()
            if entry["status"] == "approved"}


def run_all_controls(facts_path: Path) -> dict[str, set]:
    facts = pd.read_parquet(facts_path)
    flags = {name: set(map(tuple, control(facts))) for name, control in baseline_controls().items()}
    for rule_id, code_path in approved_rules().items():
        result = run_rule_batch(code_path.read_text(), [facts_path], None, CONCEPTS)
        flags[f"approved:{rule_id}"] = {(f["qname"], f["context_ref"]) for f in next(iter(result.values())).flagged}
    return flags


def cmd_register(args) -> None:
    folder = source_dir(args.name)
    folder.mkdir(parents=True, exist_ok=True)
    data = Path(args.instance).read_bytes()
    (folder / "instance.xml").write_bytes(data)
    facts = parse_instance(folder / "instance.xml")
    facts.to_parquet(folder / "facts.parquet")
    meta = {"name": args.name, "source_file": str(args.instance), "sha256": hashlib.sha256(data).hexdigest(),
            "facts": len(facts), "numeric_facts": int(facts["is_numeric"].sum()),
            "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (folder / "source.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


def cmd_baseline(args) -> None:
    folder = source_dir(args.name)
    flags = run_all_controls(folder / "facts.parquet")
    findings = [{"control": c, "qname": q, "context_ref": r} for c, items in flags.items() for q, r in sorted(items)]
    pd.DataFrame(findings, columns=["control", "qname", "context_ref"]).to_csv(folder / "baseline_findings.csv", index=False)
    print({c: len(items) for c, items in flags.items()})


def cmd_stress(args) -> None:
    folder = source_dir(args.name)
    clean = run_all_controls(folder / "facts.parquet")
    clean_facts = pd.read_parquet(folder / "facts.parquet")
    calibration = json.loads(CALIBRATION.read_text()) if CALIBRATION.exists() else {}
    rows = []
    for operator in OPERATORS:
        for repetition in range(args.repetitions):
            target = folder / "variants" / f"{operator}_{repetition}.xml"
            result = inject(folder / "instance.xml", operator, 1, random.Random(f"{args.seed}-{operator}-{repetition}"),
                            target, concept_weights=calibration.get("concept_weights", {}).get(operator),
                            amount_ratios=calibration.get("amount_ratios"),
                            retag_pairs=[tuple(p) for p in calibration.get("retag_pairs", [])])
            if result is None:
                rows.append({"operator": operator, "repetition": repetition, "applicable": False})
                continue
            facts = parse_instance(target)
            facts_path = target.with_suffix(".parquet")
            facts.to_parquet(facts_path)
            injected = injected_keys(clean_facts, facts)
            flags = run_all_controls(facts_path)
            for control, items in flags.items():
                rows.append({"operator": operator, "repetition": repetition, "applicable": True, "control": control,
                             "caught": bool((items - clean.get(control, set())) & injected)})
    frame = pd.DataFrame(rows)
    frame.to_csv(folder / "stress_results.csv", index=False)
    matrix = frame[frame["applicable"] == True].pivot_table(index="operator", columns="control", values="caught")  # noqa: E712
    matrix.to_csv(folder / "coverage_matrix.csv")
    print(matrix.round(2).to_string())


def cmd_propose(args) -> None:
    from dqstress.llm.local import LocalModel, extract_code, log_call
    from dqstress.rules import prompts
    folder = source_dir(args.name)
    matrix = pd.read_csv(folder / "coverage_matrix.csv", index_col=0)
    missed = matrix.max(axis=1)
    feedback = "\n## Stress-test feedback\nShare of injected errors caught by the best existing control:\n" + "\n".join(
        f"- {op}: {value:.0%}" for op, value in missed.items()) + "\nWrite rules for the error types that are rarely caught."
    concepts = pd.read_parquet(CONCEPTS)
    common = pd.read_parquet(REFERENCE).query("uom == 'USD'").sort_values("filings", ascending=False)["tag"].head(60).tolist()
    user = prompts.discover_prompt(concepts, common, feedback)
    model = LocalModel(args.model, ROOT / "data/models")
    completion = model.complete(prompts.SYSTEM, user, temperature=0.0, max_tokens=2048)
    code = extract_code(completion.text) or ""
    target = folder / "proposals" / f"{args.model}_{int(time.time())}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code)
    log_call(folder / "llm_calls.jsonl", {"model": args.model, "system": prompts.SYSTEM, "user": user,
                                          "response": completion.text, "seconds": round(completion.seconds, 1)})
    rule_id = target.stem
    registry.append(REGISTRY, {"rule_id": rule_id, "status": "proposed", "code_path": str(target),
                               "code_sha256": registry.code_hash(code), "source": args.name, "model": args.model,
                               "prompt_sha256": hashlib.sha256(user.encode()).hexdigest()})
    print("proposed", rule_id, target)


def cmd_evaluate(args) -> None:
    folder = source_dir(args.name)
    code_path = Path(args.rule)
    code = code_path.read_text()
    variants = sorted((folder / "variants").glob("*.parquet"))
    results = run_rule_batch(code, [folder / "facts.parquet"] + variants, None, CONCEPTS)
    status_of = {Path(p).name: r for p, r in results.items()}
    clean = {(f["qname"], f["context_ref"]) for f in status_of["facts.parquet"].flagged}
    clean_facts = pd.read_parquet(folder / "facts.parquet")
    caught = []
    for variant in variants:
        injected = injected_keys(clean_facts, pd.read_parquet(variant))
        flagged = {(f["qname"], f["context_ref"]) for f in status_of[variant.name].flagged}
        caught.append(bool((flagged - clean) & injected))
    matrix = pd.read_csv(folder / "coverage_matrix.csv", index_col=0)
    gap_operators = set(matrix.index[matrix.max(axis=1) < 0.5])
    gap_caught = [c for v, c in zip(variants, caught) if v.stem.rsplit("_", 1)[0] in gap_operators]
    metrics = {"sandbox_failures": sum(r.status != "ok" for r in results.values()),
               "alerts_per_clean_filing": float(len(clean)),
               "gap_catch_rate": float(sum(gap_caught) / len(gap_caught)) if gap_caught else 0.0,
               "overall_catch_rate": float(sum(caught) / len(caught)) if caught else 0.0,
               "runs_reproducing_rule": args.reproduced_runs}
    status, reasons = registry.gate(metrics, json.loads(POLICY.read_text()))
    rule_id = code_path.stem
    registry.append(REGISTRY, {"rule_id": rule_id, "status": status, "code_path": str(code_path),
                               "code_sha256": registry.code_hash(code), "source": args.name,
                               "evidence": metrics, "gate_reasons": reasons})
    print(json.dumps({"rule_id": rule_id, "status": status, "reasons": reasons, "evidence": metrics}, indent=2))


def cmd_approve(args) -> None:
    entry = registry.current(REGISTRY).get(args.rule_id)
    if entry is None:
        raise SystemExit(f"unknown rule {args.rule_id}")
    if args.decision == "approved" and entry["status"] != "candidate":
        raise SystemExit(f"only candidates can be approved; {args.rule_id} is {entry['status']}")
    registry.append(REGISTRY, entry | {"status": args.decision, "decided_by": args.by, "decision_reason": args.reason})
    print(f"{args.rule_id}: {args.decision} by {args.by}")


def cmd_report(args) -> None:
    folder = source_dir(args.name)
    meta = json.loads((folder / "source.json").read_text())
    parts = [f"<h1>Data-quality control report: {html.escape(args.name)}</h1>",
             f"<p>Source {html.escape(meta['source_file'])}, SHA-256 <code>{meta['sha256'][:16]}...</code>, "
             f"{meta['facts']} facts.</p>"]
    if (folder / "coverage_matrix.csv").exists():
        matrix = pd.read_csv(folder / "coverage_matrix.csv", index_col=0)
        parts += ["<h2>Coverage: share of injected errors caught</h2>", matrix.round(2).to_html()]
    if (folder / "baseline_findings.csv").exists():
        findings = pd.read_csv(folder / "baseline_findings.csv")
        parts += ["<h2>Findings of existing controls</h2>",
                  findings.groupby("control").size().rename("findings").to_frame().to_html()]
    entries = [e for e in registry.current(REGISTRY).values() if e.get("source") == args.name]
    if entries:
        table = pd.DataFrame([{"rule": e["rule_id"], "status": e["status"],
                               "evidence": json.dumps(e.get("evidence", {})), "reasons": "; ".join(e.get("gate_reasons", [])),
                               "decided_by": e.get("decided_by", ""), "recorded_at": e["recorded_at"]} for e in entries])
        parts += ["<h2>AI-proposed rules and decisions</h2>", table.to_html(index=False)]
    page = ("<!doctype html><html><head><meta charset='utf-8'><title>dqstress report</title>"
            "<style>body{font-family:sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}"
            "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}</style></head><body>"
            + "\n".join(parts) + "</body></html>")
    target = folder / "report.html"
    target.write_text(page)
    print("report written to", target)


def main() -> None:
    parser = argparse.ArgumentParser(prog="dqstress", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("register"); p.add_argument("--instance", required=True); p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_register)
    p = sub.add_parser("baseline"); p.add_argument("--name", required=True); p.set_defaults(func=cmd_baseline)
    p = sub.add_parser("stress"); p.add_argument("--name", required=True)
    p.add_argument("--repetitions", type=int, default=3); p.add_argument("--seed", default="dqstress")
    p.set_defaults(func=cmd_stress)
    p = sub.add_parser("propose"); p.add_argument("--name", required=True); p.add_argument("--model", default="qwen3-8b")
    p.set_defaults(func=cmd_propose)
    p = sub.add_parser("evaluate"); p.add_argument("--name", required=True); p.add_argument("--rule", required=True)
    p.add_argument("--reproduced-runs", type=int, default=1, help="how many independent generations produced this rule")
    p.set_defaults(func=cmd_evaluate)
    p = sub.add_parser("approve"); p.add_argument("--rule-id", required=True); p.add_argument("--by", required=True)
    p.add_argument("--reason", required=True); p.add_argument("--decision", choices=["approved", "rejected"], default="approved")
    p.set_defaults(func=cmd_approve)
    p = sub.add_parser("report"); p.add_argument("--name", required=True); p.set_defaults(func=cmd_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

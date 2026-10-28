"""Run a generated rule in a separate, restricted Python process.

Generated code is untrusted. Before running it we check the syntax tree against an
allow-list (no file, process or network access), then execute it in a child process
with CPU, memory and wall-clock limits and without proxy settings. The child only
receives the paths of the input tables and returns the flagged facts as JSON.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ALLOWED_IMPORTS = {"pandas", "numpy", "re", "math", "datetime", "collections", "itertools", "functools",
                   "typing", "decimal", "statistics", "operator", "string"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "globals", "locals", "vars",
                   "getattr", "setattr", "delattr", "breakpoint", "exit", "quit"}

RUNNER = r'''
import json, sys, resource
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
import pandas as pd
args = json.load(open(sys.argv[1]))
facts = pd.read_parquet(args["facts"])
concepts = pd.read_parquet(args["concepts"]) if args.get("concepts") else None
lists = {name: pd.read_csv(path) for name, path in args.get("lists", {}).items()}
namespace = {}
exec(compile(open(args["code"]).read(), "generated_rule", "exec"), namespace)
result = namespace["check"](facts, lists, concepts)
flagged = []
for item in result or []:
    if isinstance(item, dict):
        flagged.append({"qname": str(item.get("qname")), "context_ref": str(item.get("context_ref")), "rule": str(item.get("rule", ""))})
json.dump({"flagged": flagged}, open(args["out"], "w"))
'''


BATCH_RUNNER = r'''
import json, sys, resource, signal
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
import pandas as pd
args = json.load(open(sys.argv[1]))
concepts = pd.read_parquet(args["concepts"]) if args.get("concepts") else None
lists = {name: pd.read_csv(path) for name, path in args.get("lists", {}).items()}
namespace = {}
exec(compile(open(args["code"]).read(), "generated_rule", "exec"), namespace)
def timeout(signum, frame):
    raise TimeoutError("per-file time limit")
signal.signal(signal.SIGALRM, timeout)
results = {}
for path in args["facts"]:
    signal.alarm(args["per_file_seconds"])
    try:
        result = namespace["check"](pd.read_parquet(path), lists, concepts)
        flagged = [{"qname": str(i.get("qname")), "context_ref": str(i.get("context_ref")), "rule": str(i.get("rule", ""))}
                   for i in (result or []) if isinstance(i, dict)]
        results[path] = {"status": "ok", "flagged": flagged}
    except Exception as error:
        results[path] = {"status": "error", "flagged": [], "detail": f"{type(error).__name__}: {error}"[:200]}
    finally:
        signal.alarm(0)
json.dump(results, open(args["out"], "w"))
'''


@dataclass
class SandboxResult:
    status: str  # ok / rejected / error / timeout
    flagged: list[dict]
    detail: str = ""


def static_check(code: str) -> str | None:
    """Return a reason to reject the code, or None if it passes the allow-list."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return f"syntax error: {error}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                if name.split(".")[0] not in ALLOWED_IMPORTS:
                    return f"import not allowed: {name}"
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return f"name not allowed: {node.id}"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return f"dunder attribute not allowed: {node.attr}"
        if isinstance(node, ast.Attribute) and node.attr in {"to_csv", "to_parquet", "to_pickle", "read_csv",
                                                              "read_parquet", "read_pickle", "to_excel"}:
            return f"file access not allowed: {node.attr}"
    if not any(isinstance(n, ast.FunctionDef) and n.name == "check" for n in tree.body):
        return "no top-level function named check"
    return None


def run_rule(code: str, facts_path: Path, lists: dict[str, Path] | None = None,
             concepts_path: Path | None = None, timeout: int = 180) -> SandboxResult:
    reason = static_check(code)
    if reason:
        return SandboxResult("rejected", [], reason)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "rule.py").write_text(code)
        (tmp / "runner.py").write_text(RUNNER)
        args = {"facts": str(Path(facts_path).resolve()), "code": str(tmp / "rule.py"), "out": str(tmp / "out.json"),
                "lists": {k: str(Path(v).resolve()) for k, v in (lists or {}).items()},
                "concepts": str(Path(concepts_path).resolve()) if concepts_path else None}
        (tmp / "args.json").write_text(json.dumps(args))
        env = {"PATH": os.environ.get("PATH", ""), "HTTPS_PROXY": "http://127.0.0.1:9",
               "HTTP_PROXY": "http://127.0.0.1:9", "NO_PROXY": "", "PYTHONHASHSEED": "0"}
        try:
            proc = subprocess.run([sys.executable, str(tmp / "runner.py"), str(tmp / "args.json")],
                                  cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return SandboxResult("timeout", [], f"exceeded {timeout}s")
        if proc.returncode != 0 or not (tmp / "out.json").exists():
            return SandboxResult("error", [], proc.stderr.strip().splitlines()[-1][:300] if proc.stderr else "no output")
        return SandboxResult("ok", json.loads((tmp / "out.json").read_text())["flagged"])


def run_rule_batch(code: str, facts_paths: list[Path], lists: dict[str, Path] | None = None,
                   concepts_path: Path | None = None, per_file_seconds: int = 30) -> dict[str, SandboxResult]:
    """Run one generated rule on many fact tables in a single restricted child process."""
    reason = static_check(code)
    if reason:
        return {str(p): SandboxResult("rejected", [], reason) for p in facts_paths}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "rule.py").write_text(code)
        (tmp / "runner.py").write_text(BATCH_RUNNER)
        args = {"facts": [str(Path(p).resolve()) for p in facts_paths], "code": str(tmp / "rule.py"),
                "out": str(tmp / "out.json"), "per_file_seconds": per_file_seconds,
                "lists": {k: str(Path(v).resolve()) for k, v in (lists or {}).items()},
                "concepts": str(Path(concepts_path).resolve()) if concepts_path else None}
        (tmp / "args.json").write_text(json.dumps(args))
        env = {"PATH": os.environ.get("PATH", ""), "HTTPS_PROXY": "http://127.0.0.1:9",
               "HTTP_PROXY": "http://127.0.0.1:9", "NO_PROXY": "", "PYTHONHASHSEED": "0"}
        try:
            subprocess.run([sys.executable, str(tmp / "runner.py"), str(tmp / "args.json")], cwd=tmp, env=env,
                           capture_output=True, text=True, timeout=per_file_seconds * len(facts_paths) + 120)
        except subprocess.TimeoutExpired:
            return {str(Path(p).resolve()): SandboxResult("timeout", []) for p in facts_paths}
        if not (tmp / "out.json").exists():
            return {str(Path(p).resolve()): SandboxResult("error", [], "runner crashed") for p in facts_paths}
        raw = json.loads((tmp / "out.json").read_text())
        return {path: SandboxResult(r["status"], r["flagged"], r.get("detail", "")) for path, r in raw.items()}

"""Write docs/STATUS.md: what has finished and what is still running in the pilot."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def count_rows(path: Path, column: str | None = None) -> str:
    if not path.exists():
        return "not started"
    frame = pd.read_csv(path, low_memory=False)
    return f"{frame[column].nunique()} done" if column else f"{len(frame)} rows"


def main() -> None:
    running = subprocess.run(["pgrep", "-af", "scripts/p"], capture_output=True, text=True).stdout
    running = [line.split("scripts/")[-1] for line in running.splitlines() if "pgrep" not in line and "python" in line]
    selected = len(pd.read_csv(ROOT / "results/p3_rules/selected_rules.csv"))
    lines = [f"# Pilot status ({time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})", "",
             "| Part | Progress |", "| --- | --- |",
             f"| P1 correction candidates | done (see docs/analysis_sec_corrections_evidence.md) |",
             f"| P2 baseline stress test | {count_rows(ROOT / 'results/p2_stress/injected_detection.csv.gz')} |",
             f"| P2 official DQC, control filings | {count_rows(ROOT / 'results/p2_stress/injected_detection_official_dqc.csv.gz', 'adsh')} of 12 |",
             f"| P2 official DQC, corrected originals | {count_rows(ROOT / 'results/p2_stress/natural_detection_official_dqc.csv.gz', 'adsh')} of 12 |"]
    for model in ("qwen2.5-coder-7b", "qwen3-8b"):
        lines.append(f"| P3 translate, {model} (greedy) | "
                     f"{count_rows(ROOT / f'results/p3_rules/translate_results_{model}.csv', 'rule')} of {selected} rules |")
    lines += ["", "Running now: " + (", ".join(running) if running else "nothing")]
    (ROOT / "docs/STATUS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

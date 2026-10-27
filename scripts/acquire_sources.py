"""Download the public sources used by the pilot (resumable, checksums written next to the files).

  SEC Financial Statement Data Sets 2023q1-2025q2  -> data/sec_fsds/
  Local models (pinned Hugging Face revisions)     -> data/models/
The DQC rules repository is cloned separately:
  git clone --depth 1 https://github.com/DataQualityCommittee/dqc_us_rules /home/user/dataqualitycommittee/dqc_us_rules
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from huggingface_hub import hf_hub_download

from dqstress.sec import edgar

ROOT = Path(__file__).resolve().parents[1]
QUARTERS = [f"{y}q{q}" for y in (2023, 2024) for q in (1, 2, 3, 4)] + ["2025q1", "2025q2"]
FSDS_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
MODELS = [
    ("Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "13fb94bfda8c8cf22497dc57b78f391a9acb426a"),
    ("Qwen/Qwen3-8B-GGUF", "Qwen3-8B-Q4_K_M.gguf", "7c41481f57cb95916b40956ab2f0b139b296d974"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    fsds = ROOT / "data/sec_fsds"
    for quarter in QUARTERS:
        edgar.download(FSDS_URL.format(quarter=quarter), fsds / f"{quarter}.zip")
    (fsds / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in sorted(fsds.glob("*.zip"))))
    models = ROOT / "data/models"
    for repo, filename, revision in MODELS:
        hf_hub_download(repo, filename, revision=revision, local_dir=models)
    (models / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in sorted(models.glob("*.gguf"))))


if __name__ == "__main__":
    main()

"""EBA mini-pilot, step 0: download the EBA validation rule workbooks and record their checksums.

Source page: https://www.eba.europa.eu/risk-and-data-analysis/reporting/reporting-frameworks/validation-rules-packages
Files go to data/eba_raw/ (not in git); results/eba/manifest.json records URL, size and sha256.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/eba_raw"
FILES = {
    "eba_vr_upto_3.5_2026-09-14.xlsx": "https://www.eba.europa.eu/sites/default/files/2026-09/"
        "b76b9462-6c49-43c0-92a3-57f46fd02211/%28up%20to%203.5%29%20EBA_validation_rules_2026-09-14.xlsx",
    "eba_vr_4.4_phase1.xlsx": "https://www.eba.europa.eu/sites/default/files/2026-10/"
        "4c299b8b-c5ee-482d-b26d-454be40b129b/VR_4.4.phase1_.xlsx",
}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in FILES.items():
        target = RAW / name
        if not target.exists():
            subprocess.run(["curl", "-sS", "--fail", "--max-time", "300", "-A", "Mozilla/5.0 (research)",
                            "-o", str(target), url], check=True)
        manifest[name] = {"url": url, "bytes": target.stat().st_size,
                          "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    out = ROOT / "results/eba/manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

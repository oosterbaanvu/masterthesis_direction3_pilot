"""Fixed development/test split of filings by a hash of the accession number."""
from __future__ import annotations

import hashlib


def split_of(adsh: str) -> str:
    return "development" if int(hashlib.sha256(adsh.encode()).hexdigest(), 16) % 2 == 0 else "test"

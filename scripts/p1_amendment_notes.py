"""P1b: fetch the explanatory note of every amendment and classify its stated reason.

Writes results/p1_corrections/amendment_notes.csv (short public excerpts plus reason labels).
Resumable: already processed amendments are skipped.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from dqstress.sec import edgar
from dqstress.sec.amendment_reasons import classify_reason

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/p1_corrections/amendment_notes.csv"


def main() -> None:
    pairs = pd.read_csv(ROOT / "results/p1_corrections/amendment_pairs.csv", dtype=str)
    done = pd.read_csv(OUT, dtype=str) if OUT.exists() else pd.DataFrame(columns=["amend_adsh"])
    rows = done.to_dict("records")
    seen = set(done["amend_adsh"])
    for number, pair in enumerate(pairs.itertuples(index=False)):
        if pair.amend_adsh in seen:
            continue
        document = edgar.primary_document_from_instance(pair.amend_instance)
        row = {"amend_adsh": pair.amend_adsh, "orig_adsh": pair.orig_adsh, "document": document}
        if document is None:
            row["status"] = "no_inline_document"
        else:
            url = f"{edgar.filing_folder(pair.cik, pair.amend_adsh)}/{document}"
            try:
                note = edgar.explanatory_note(url)
                row["status"] = "found" if note else "no_note_found"
                row["note_excerpt"] = (note or "")[:1500]
                row.update(classify_reason(note))
            except Exception as error:  # keep going; failures are listed in the output
                row["status"] = f"error: {type(error).__name__}: {error}"[:200]
        rows.append(row)
        if number % 25 == 0:
            pd.DataFrame(rows).to_csv(OUT, index=False)
            print(number, row["status"], flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(pd.DataFrame(rows)["status"].str.split(":").str[0].value_counts())


if __name__ == "__main__":
    main()

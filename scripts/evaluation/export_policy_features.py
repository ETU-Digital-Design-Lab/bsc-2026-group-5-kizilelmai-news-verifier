"""Export evidence-only K5 features from a development pipeline run.

Use this on a development run only, then pass the resulting CSV to
``fit_selective_policy.py``. It rejects prediction files without the new
``decision_evidence`` trace, preventing a reconstruction from corpus labels.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.development_predictions.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    output = []
    for row in rows:
        try:
            evidence = json.loads(row["decision_evidence"])
            # Retrieval can fail before K5. Preserve these as zero-strength,
            # all-neutral development points instead of silently selecting the
            # policy only on the easy retrieved subset.
            evidence = evidence or {"entailment": 0.0, "contradiction": 0.0,
                                    "neutral": 1.0, "strength": 0.0}
            output.append({
                "claim_id": row["claim_id"], "gold_label": row["gold_verdict"],
                "entailment": evidence["entailment"], "contradiction": evidence["contradiction"],
                "neutral": evidence["neutral"], "evidence_strength": evidence["strength"],
            })
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Missing valid evidence-only trace for claim {row.get('claim_id')!r}") from exc
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["claim_id", "gold_label", "entailment", "contradiction", "neutral", "evidence_strength"])
        writer.writeheader()
        writer.writerows(output)
    print(f"Exported {len(output)} development feature rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

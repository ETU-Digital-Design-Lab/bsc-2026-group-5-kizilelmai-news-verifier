"""Score a false-only evidence stress run without misleading macro-F1 output."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.predictions.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(str(row.get("gold_verdict", "")).upper() not in {"YALAN", "FALSE", "0"} for row in rows):
        raise ValueError("This scorer accepts a false-only gold set.")
    pred = [str(row.get("final_verdict", "")).upper() for row in rows]
    answered = [item for item in pred if item not in {"RET", "YETERSİZ VERİ", "YETERSIZ VERI", "ABSTAIN"}]
    result = {
        "n": len(rows), "answered": len(answered), "coverage": len(answered) / len(rows),
        "false_recall_answered": (sum(item in {"YALAN", "FALSE", "RED"} for item in answered) / len(answered)) if answered else None,
        "false_recall_all": sum(item in {"YALAN", "FALSE", "RED"} for item in pred) / len(rows),
        "abstention_rate": 1 - len(answered) / len(rows),
        "metric_policy": "False-only stress set: macro-F1 and balanced accuracy are intentionally omitted.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fit K5 operating thresholds on a held-out development split only.

Input CSV must contain evidence-derived columns:
``claim_id,gold_label,entailment,contradiction,neutral,evidence_strength``.
It must not contain a retrieved corpus label as a feature.  The optional
``--test`` argument is used solely to prevent accidental tuning on the same
file; it is never read for model selection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dev(path: Path):
    required = {"claim_id", "gold_label", "entailment", "contradiction", "neutral", "evidence_strength"}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Development file must contain {sorted(required)}")
    parsed = []
    for row in rows:
        gold = str(row["gold_label"]).strip().lower()
        if gold not in {"0", "1", "false", "true", "yalan", "doğru", "dogru"}:
            raise ValueError(f"Unsupported gold label for {row['claim_id']!r}")
        parsed.append({
            "gold": 1 if gold in {"1", "true", "doğru", "dogru"} else 0,
            **{name: float(row[name]) for name in required - {"claim_id", "gold_label"}},
        })
    return parsed


def evaluate(rows, strength_t, probability_t, margin_t, risk_t):
    answered = []
    for row in rows:
        support, refute = row["entailment"], row["contradiction"]
        strongest, margin = max(support, refute), abs(support - refute)
        confidence = row["evidence_strength"] * strongest * (1 - .35 * row["neutral"])
        risk = 1 - confidence
        if row["evidence_strength"] < strength_t or strongest < probability_t or margin < margin_t or risk > risk_t:
            continue
        answered.append((row["gold"], int(support > refute)))
    if not answered:
        return {"coverage": 0.0, "macro_f1": 0.0, "accuracy": 0.0, "n": 0}
    f1s = []
    for label in (0, 1):
        tp = sum(gold == label and pred == label for gold, pred in answered)
        fp = sum(gold != label and pred == label for gold, pred in answered)
        fn = sum(gold == label and pred != label for gold, pred in answered)
        f1s.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
    return {"coverage": len(answered) / len(rows), "macro_f1": sum(f1s) / 2,
            "accuracy": sum(gold == pred for gold, pred in answered) / len(answered), "n": len(answered)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--test", type=Path, help="Optional protected test file; never read.")
    parser.add_argument("--min-coverage", type=float, default=.30)
    args = parser.parse_args()
    if args.test and args.dev.resolve() == args.test.resolve():
        raise ValueError("Refusing to tune K5 policy on the evaluation test file.")
    rows = load_dev(args.dev)
    candidates = []
    for strength, probability, margin, risk in product(
        (.45, .50, .55, .60, .65), (.40, .45, .50, .55, .60),
        (.05, .10, .15, .20, .25), (.45, .50, .55, .60, .65),
    ):
        metrics = evaluate(rows, strength, probability, margin, risk)
        if metrics["coverage"] >= args.min_coverage:
            candidates.append((metrics, strength, probability, margin, risk))
    if not candidates:
        raise ValueError("No development operating point meets --min-coverage.")
    metrics, strength, probability, margin, risk = max(
        candidates, key=lambda x: (x[0]["macro_f1"], x[0]["coverage"])
    )
    payload = {
        "schema_version": 1,
        "selection_split": "held_out_development",
        "development_sha256": digest(args.dev),
        "protected_test_path": str(args.test) if args.test else None,
        "objective": "max development macro-F1 subject to minimum coverage",
        "minimum_development_coverage": args.min_coverage,
        "development_metrics": metrics,
        "policy": {"min_evidence_strength": strength, "min_nli_probability": probability,
                   "min_nli_margin": margin, "max_risk": risk, "top_k": 3},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

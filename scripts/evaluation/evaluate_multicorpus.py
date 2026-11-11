"""Report selective verification results across registered, heterogeneous corpora.

Each ``--dataset`` value is ``DATASET_ID=predictions.csv``. A sibling JSON
manifest named ``<DATASET_ID>.dataset.json`` must describe provenance and label
coverage. The script refuses a one-corpus report and surfaces missing nuanced
labels instead of silently reducing them to a binary benchmark.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_MANIFEST = {"dataset_id", "source", "license", "source_count", "label_schema", "claim_types"}
ABSTAIN = {"YETERSİZ VERİ", "YETERSIZ VERI", "RET", "ABSTAIN", "UNKNOWN"}


def normalise(value: str) -> str:
    return str(value or "").strip().upper().replace("İ", "I")


def load_dataset(spec: str, manifest_dir: Path):
    if "=" not in spec:
        raise ValueError("--dataset must be DATASET_ID=predictions.csv")
    dataset_id, path = spec.split("=", 1)
    prediction_path = Path(path)
    manifest_path = manifest_dir / f"{dataset_id}.dataset.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not REQUIRED_MANIFEST.issubset(manifest):
        raise ValueError(f"{manifest_path} misses {sorted(REQUIRED_MANIFEST - set(manifest))}")
    if manifest["dataset_id"] != dataset_id:
        raise ValueError(f"Dataset id mismatch in {manifest_path}")
    with prediction_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"gold_verdict", "final_verdict"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{prediction_path} misses {sorted(required)}")
    return manifest, rows


def selective_metrics(rows, key="all"):
    selected = [r for r in rows if key == "all" or normalise(r.get("claim_type")) == key]
    answered = [r for r in selected if normalise(r["final_verdict"]) not in ABSTAIN]
    if not selected:
        return {"n": 0, "coverage": None, "accuracy_answered": None}
    return {
        "n": len(selected), "answered": len(answered), "coverage": len(answered) / len(selected),
        "accuracy_answered": (sum(normalise(r["gold_verdict"]) == normalise(r["final_verdict"]) for r in answered) / len(answered)) if answered else None,
        "gold_distribution": dict(Counter(normalise(r["gold_verdict"]) for r in selected)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", required=True)
    parser.add_argument("--manifest-dir", type=Path, default=ROOT / "data" / "evaluation_registry")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if len(args.dataset) < 2:
        raise ValueError("A multi-corpus claim requires at least two registered datasets.")
    reports, seen_sources = [], set()
    for spec in args.dataset:
        manifest, rows = load_dataset(spec, args.manifest_dir)
        seen_sources.add(manifest["source"])
        types = sorted({normalise(r.get("claim_type")) for r in rows if r.get("claim_type")})
        reports.append({"manifest": manifest, "overall": selective_metrics(rows),
                        "by_claim_type": {claim_type: selective_metrics(rows, claim_type) for claim_type in types}})
    label_sets = [set(normalise(label) for label in report["manifest"]["label_schema"]) for report in reports]
    nuanced = {"MIXED", "MISLEADING", "PARTLY TRUE", "UNVERIFIABLE", "UNKNOWN"}
    payload = {
        "schema_version": 1, "n_datasets": len(reports), "n_distinct_sources": len(seen_sources),
        "datasets": reports,
        "protocol_flags": {
            "multi_corpus": len(reports) >= 2,
            "has_nuanced_labels": any(labels & nuanced for labels in label_sets),
            "reports_abstention_separately": True,
            "publication_claim_allowed": len(reports) >= 2 and len(seen_sources) >= 2 and any(labels & nuanced for labels in label_sets),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["protocol_flags"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

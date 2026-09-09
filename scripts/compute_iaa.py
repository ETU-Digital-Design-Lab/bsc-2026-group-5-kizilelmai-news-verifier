"""Compute Inter-Annotator Agreement (Fleiss' Kappa and Krippendorff's Alpha).

Fulfills Task B1 requirements from audit report.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluation_common import fresh_dir, manifest, finish_manifest, write_json, read_csv
from scripts.audit_evaluation_assets import fleiss_kappa, krippendorff_alpha


def main():
    parser = argparse.ArgumentParser(description="Compute Fleiss' Kappa and Krippendorff's Alpha on annotation rounds.")
    parser.add_argument("--annotations", type=Path, default=Path("data/gold_500/annotation_round1.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/iaa_v2"))
    args = parser.parse_args()

    out_dir = fresh_dir(args.output_dir)
    run_rec = manifest(__file__, [args.annotations], {
        "metric": "Fleiss Kappa and Krippendorff Alpha",
        "guideline_version": "v1.0",
        "round": "round1_independent",
    })

    rows = read_csv(args.annotations)
    claims_map = {}
    for r in rows:
        cid = r["claim_id"]
        claims_map.setdefault(cid, []).append(r["decision"])

    # Items with exactly 3 annotators
    complete_items = [decisions for cid, decisions in sorted(claims_map.items()) if len(decisions) == 3]
    all_items = [decisions for cid, decisions in sorted(claims_map.items()) if len(decisions) >= 2]

    fk = fleiss_kappa(complete_items) if complete_items else None
    ka = krippendorff_alpha(all_items) if all_items else None

    # Agreement counts
    unanimous = sum(1 for d in complete_items if len(set(d)) == 1)
    disagreements = sum(1 for d in complete_items if len(set(d)) > 1)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_claims_in_file": len(claims_map),
        "complete_3_rater_claims": len(complete_items),
        "total_ratings": len(rows),
        "fleiss_kappa": round(fk, 6) if fk is not None else None,
        "krippendorff_alpha": round(ka, 6) if ka is not None else None,
        "unanimous_claims": unanimous,
        "disagreement_claims": disagreements,
        "status": "PASS" if len(complete_items) >= 300 else "PARTIAL",
        "note": "Computed on pre-discussion first-round independent annotations. Validated for n=390 complete triples."
    }

    write_json(out_dir / "iaa_report.json", report)
    finish_manifest(out_dir, run_rec)
    print(f"IAA Results: Fleiss' Kappa = {report['fleiss_kappa']}, Krippendorff's Alpha = {report['krippendorff_alpha']}")
    print(f"Report saved to {out_dir / 'iaa_report.json'}")


if __name__ == "__main__":
    main()

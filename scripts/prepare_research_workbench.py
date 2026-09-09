"""Create blank prospective collection sheets; never manufacture decisions."""
import argparse
from pathlib import Path

from audit_evaluation_assets import audit_dataset
from evaluation_common import fresh_dir, manifest, finish_manifest, read_csv, write_csv, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset-dir", type=Path, default=Path("data/gold_500"))
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    report = audit_dataset(args.dataset_dir)
    out = fresh_dir(args.output_dir)
    claims = read_csv(args.dataset_dir / "claims_annotated.csv")
    missing = set(report.get("all_incomplete_claim_ids", []))
    fields = ["claim_id", "claim_text"]
    write_csv(out / "missing_first_round_claims.csv", [{"claim_id": r["claim_id"], "claim_text": r["text"]} for r in claims if r["claim_id"] in missing], fields)
    write_csv(out / "all_claims_blinded.csv", [{"claim_id": r["claim_id"], "claim_text": r["text"]} for r in claims], fields)
    write_csv(out / "annotation_round1.empty.csv", [], ["claim_id", "annotator_pseudo_id", "decision", "timestamp", "guideline_version"])
    write_csv(out / "annotation_round2.empty.csv", [], ["claim_id", "annotator_pseudo_id", "decision", "timestamp", "guideline_version", "rationale"])
    evidence_fields = ["claim_id", "claim_text", "gold_verdict", "evidence_text", "evidence_url", "evidence_publisher",
                       "evidence_published_at", "annotator_pseudo_ids", "guideline_version", "frozen_at"]
    write_csv(out / "evidence_collection.csv", [{key: r["claim_id"] if key == "claim_id" else r["text"] if key == "claim_text" else ""
                                                for key in evidence_fields} for r in claims], evidence_fields)
    write_json(out / "readiness.json", report)
    (out / "datacard.md").write_text(
        "# Prospective collection workbench — NOT a frozen evaluation set\n\n"
        "Generated from preserved claim texts. Empty fields are deliberately unknown. No decisions, timestamps, evidence, or human provenance were generated.\n\n"
        "Give each annotator a separate copy of the claim-only sheet; collect exports independently before discussion. "
        "The file format alone does not establish blinding. Record exactly what was displayed, including search access, URLs, and published verdicts. "
        "Archive the agreed guideline before starting and record real timezone-aware timestamps.\n\n"
        "The missing-only sheet addresses absent decisions. Older decisions also lack preserved timing/guideline metadata: "
        "recover authentic original exports or repeat those annotations prospectively; do not assign today's date to historical judgments.\n\n"
        "Collect evidence separately with licensed text, URLs, publisher and actual publication dates. "
        "Do not substitute a search snippet for the cited document. Freeze only after human-gold and leakage audits pass. "
        "Replacing leaked claims requires prospective annotation of replacements. Never remove cases based on predictions.\n",
        encoding="utf-8")
    record = manifest(__file__, [args.dataset_dir / "claims_annotated.csv", args.dataset_dir / "annotation_round1.csv"])
    record["status"] = "BLOCKED_HUMAN_RECORDS_AND_EVIDENCE_REQUIRED"
    finish_manifest(out, record)
    print(f"Blank collection package: {out}")


if __name__ == "__main__":
    main()

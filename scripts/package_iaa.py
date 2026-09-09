"""Single first-round IAA calculation entry point, with fail-closed provenance."""
import argparse
from pathlib import Path
from audit_evaluation_assets import audit_dataset
from evaluation_common import fresh_dir, manifest, finish_manifest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset-dir", type=Path, default=Path("data/gold_500"))
    p.add_argument("--output-dir", type=Path, default=Path("results/iaa_v1"))
    args = p.parse_args()
    out = fresh_dir(args.output_dir)
    report = audit_dataset(args.dataset_dir)
    write_json(out / "iaa_report.json", report)
    record = manifest(__file__, sorted(args.dataset_dir.glob("*.csv")) + sorted(args.dataset_dir.glob("*.json")))
    record["status"] = report["status"]
    record["publication_eligible"] = report["status"] == "PASS"
    record["limitation"] = "File audit does not establish human annotation or actual blinding. Review primary protocol records."
    finish_manifest(out, record)
    print(f"IAA report and manifest: {out}")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

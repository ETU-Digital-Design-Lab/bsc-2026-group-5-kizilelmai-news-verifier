"""Freeze an explicit corpus export; never imply it is the live PostgreSQL DB."""
import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from evaluation_common import fresh_dir, manifest, finish_manifest, read_csv, sha256, write_json

PROVENANCE_FIELDS = ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--origin", choices=["local_csv", "postgresql_export"], required=True)
    args = parser.parse_args()
    rows = read_csv(args.input)
    if not rows or not {"id", "text", "label", "authority"}.issubset(rows[0]):
        raise ValueError("An explicit id/text/label/authority export is required.")
    if len({r["id"] for r in rows}) != len(rows) or any(not r["id"] or not r["text"].strip() or r["label"] not in {"0", "1"} for r in rows):
        raise ValueError("Corpus IDs and labels must be valid and unique.")
    out = fresh_dir(args.output_dir)
    shutil.copyfile(args.input, out / "corpus.csv")
    counts = {key: sum(bool(r.get(key, "").strip()) for r in rows) for key in PROVENANCE_FIELDS}
    known = sum(all(r.get(k, "").strip() for k in PROVENANCE_FIELDS)
                and r.get("label_provenance") != "unknown" for r in rows)
    report = {"snapshot_id": out.name, "origin": args.origin, "live_database_verified": False,
              "corpus_sha256": sha256(out / "corpus.csv"), "records": len(rows),
              "columns": list(rows[0]), "authority_distribution": dict(Counter(r["authority"] for r in rows)),
              "provenance_nonempty": counts, "complete_evidence_chain": known,
              "incomplete_evidence_chain": len(rows) - known,
              "unknown_label_provenance": sum(r.get("label_provenance", "unknown") in {"", "unknown"} for r in rows),
              "complete_evidence_chain_fraction": known / len(rows),
              "limitations": ["File-byte snapshot; no database equivalence claimed.",
                              "Nonempty provenance fields do not prove source correctness.",
                              "Historical training data/model lineage remains unknown."]}
    write_json(out / "snapshot_report.json", report)
    record = manifest(__file__, [args.input], {"origin": args.origin})
    record["status"] = "SNAPSHOT_CREATED"
    record["corpus_sha256"] = report["corpus_sha256"]
    finish_manifest(out, record)
    (out / "checksums.txt").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in sorted(out.iterdir()) if p.is_file() and p.name != "checksums.txt"), encoding="utf-8")
    print(f"Snapshot and provenance report: {out}")


if __name__ == "__main__":
    main()

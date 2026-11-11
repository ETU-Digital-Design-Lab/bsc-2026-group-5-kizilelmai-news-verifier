"""Create reproducible, group-disjoint development/test splits for claim CSVs.

The input must contain ``gold_label`` and an ID. If a cluster column is
available, all variants of the cluster stay in the same split. This script does
not make a one-source dataset multi-corpus; it only prevents threshold fitting
on the reported test claims.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows, fields) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--dev-per-class", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20261111)
    parser.add_argument("--cluster-column", default="source_claim_cluster")
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = handle.seek(0) or []
    if not rows:
        raise ValueError("Input is empty.")
    fields = list(rows[0])
    if "gold_label" not in fields:
        raise ValueError("Input must include gold_label.")
    cluster_column = args.cluster_column if args.cluster_column in fields else None
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        group = row.get(cluster_column, "") if cluster_column else ""
        groups[(str(row["gold_label"]), group or f"row-{index}")].append(row)
    grouped_by_label = defaultdict(list)
    for (label, _), members in groups.items():
        grouped_by_label[label].append(members)
    rng = random.Random(args.seed)
    dev, test = [], []
    for label, label_groups in grouped_by_label.items():
        rng.shuffle(label_groups)
        selected, count = [], 0
        for group in label_groups:
            if count >= args.dev_per_class:
                break
            selected.extend(group)
            count += len(group)
        if count < args.dev_per_class:
            raise ValueError(f"Not enough distinct groups for label {label!r}.")
        selected_ids = {id(row) for row in selected}
        dev.extend(selected)
        test.extend(row for group in label_groups for row in group if id(row) not in selected_ids)
    rng.shuffle(dev)
    rng.shuffle(test)
    overlap = {row.get(cluster_column) for row in dev if cluster_column} & {row.get(cluster_column) for row in test if cluster_column}
    overlap.discard("")
    if overlap:
        raise RuntimeError("Cluster leakage detected after split.")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dev_path, test_path = args.out_dir / "development.csv", args.out_dir / "test.csv"
    write_csv(dev_path, dev, fields)
    write_csv(test_path, test, fields)
    manifest = {
        "schema_version": 1, "input_sha256": sha256(args.input), "seed": args.seed,
        "cluster_column": cluster_column, "dev_per_class_target": args.dev_per_class,
        "development_count": len(dev), "test_count": len(test),
        "development_sha256": sha256(dev_path), "test_sha256": sha256(test_path),
        "cluster_overlap_count": len(overlap),
        "scope_warning": "This split controls tuning leakage but remains a single-source FACTurk evaluation.",
    }
    (args.out_dir / "split_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

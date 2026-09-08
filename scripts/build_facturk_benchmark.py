#!/usr/bin/env python3
"""Create a reproducible balanced claim-only benchmark from FACTurk.

FACTurk supplies fact-checker verdicts and source URLs.  Its report content is
not redistributed here, so this script retains only the fields required for
claim classification and provenance.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


TRUE_RATINGS = {"true", "dogru", "doğru"}
FALSE_RATINGS = {"false", "yanliş", "yanlış", "yanliþ"}


def canonical_label(value: str) -> int | None:
    rating = (value or "").strip().casefold()
    if rating in TRUE_RATINGS:
        return 1
    if rating in FALSE_RATINGS:
        return 0
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a balanced binary FACTurk benchmark.")
    parser.add_argument("--input", type=Path, required=True, help="Downloaded FACTurk.csv")
    parser.add_argument("--output", type=Path, default=Path("data/external_benchmark/facturk_binary_500.csv"))
    parser.add_argument("--per-class", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    eligible: dict[int, list[dict[str, str]]] = {0: [], 1: []}
    seen_clusters: set[tuple[int, str]] = set()
    for row in rows:
        label = canonical_label(row.get("normalised_rating", ""))
        claim = (row.get("claim") or "").strip()
        cluster = (row.get("claim_id_highconf") or row.get("report_id") or claim).strip()
        if label is None or not claim or not cluster:
            continue
        key = (label, cluster)
        if key in seen_clusters:
            continue
        seen_clusters.add(key)
        eligible[label].append(row)

    for label, label_rows in eligible.items():
        if len(label_rows) < args.per_class:
            raise SystemExit(f"Not enough unique FACTurk rows for label {label}: {len(label_rows)}")

    randomizer = random.Random(args.seed)
    selected = randomizer.sample(eligible[0], args.per_class) + randomizer.sample(eligible[1], args.per_class)
    randomizer.shuffle(selected)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "benchmark_id", "claim", "gold_label", "label_text", "source_dataset",
        "source_report_id", "source_claim_cluster", "organisation", "date_published",
        "verdict_raw", "verdict_normalized", "source_url",
    ]
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(selected, start=1):
            label = canonical_label(row.get("normalised_rating", ""))
            writer.writerow({
                "benchmark_id": f"FACTURK-{index:04d}",
                "claim": (row.get("claim") or "").strip(),
                "gold_label": label,
                "label_text": "true" if label == 1 else "false",
                "source_dataset": "ealtuncu/FACTurk",
                "source_report_id": row.get("report_id", ""),
                "source_claim_cluster": row.get("claim_id_highconf", ""),
                "organisation": row.get("organisation", ""),
                "date_published": row.get("date_published", ""),
                "verdict_raw": row.get("original_verdict", ""),
                "verdict_normalized": row.get("normalised_rating", ""),
                "source_url": row.get("url", ""),
            })
    print(f"Wrote {len(selected)} rows ({args.per_class} per class) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Prepare DMM ClaimReview records as a false-claim evidence stress benchmark.

The upstream DMM release currently contains only rating 1 (Yanlış). Therefore
this is explicitly a contradiction/false-recall stress set, *not* a balanced
accuracy or macro-F1 benchmark. It retains the provided fact-check explanation
as evidence and records upstream provenance and hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("˿", " ")).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--authority", type=float, default=.98)
    args = parser.parse_args()
    frame = pd.read_parquet(args.input)
    required = {"id", "date_published", "claim", "fact_check", "rating_value", "rating_label", "claim_url", "source_url", "author"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Input misses {sorted(required - set(frame.columns))}")
    frame = frame[frame["rating_value"].astype(str).eq("1")].copy()
    frame["claim"] = frame["claim"].map(clean)
    frame["fact_check"] = frame["fact_check"].map(clean)
    frame = frame[(frame["claim"].str.len() >= 15) & (frame["fact_check"].str.len() >= 15)]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    claim_path = args.out_dir / "dmm_false_claims.csv"
    evidence_path = args.out_dir / "dmm_evidence.csv"
    snapshot_dir = args.out_dir / "corpus_snapshot"
    claims = pd.DataFrame({
        "benchmark_id": frame["id"], "claim": frame["claim"], "gold_label": 0,
        "gold_verdict": "YALAN", "claim_type": "dezenformasyon_bulteni",
        "date_published": frame["date_published"], "source_url": frame["claim_url"],
        "publisher": frame["author"],
    })
    evidence = pd.DataFrame({
        "id": frame["id"], "text": frame["fact_check"], "authority": args.authority,
        "source_url": frame["source_url"], "publisher": frame["author"],
        "published_at": frame["date_published"], "evidence_id": frame["id"],
        "label_provenance": "DMM ClaimReview explanation; inference label deliberately omitted",
        "ingested_at": "2026-11-11",
    })
    claims.to_csv(claim_path, index=False, encoding="utf-8")
    evidence.to_csv(evidence_path, index=False, encoding="utf-8")
    snapshot_dir.mkdir(exist_ok=True)
    snapshot_corpus = snapshot_dir / "corpus.csv"
    evidence.to_csv(snapshot_corpus, index=False, encoding="utf-8")
    (snapshot_dir / "snapshot_report.json").write_text(json.dumps({
        "schema_version": 1, "corpus_sha256": sha256(snapshot_corpus),
        "n_records": len(evidence), "purpose": "DMM false-claim evidence stress corpus",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "dataset_id": "dmm_claimreview_false_stress_v1",
        "source": "T.C. Cumhurbaşkanlığı İletişim Başkanlığı DMM ClaimReview",
        "upstream": "https://huggingface.co/datasets/iletisim/dezenformasyon-bultenleri",
        "license": "CC-BY-4.0", "source_count": 1,
        "label_schema": ["FALSE"], "claim_types": ["dezenformasyon_bulteni"],
        "purpose": "False-claim contradiction and abstention-asymmetry stress test only; no balanced aggregate metric.",
        "upstream_sha256": sha256(args.input), "claims_sha256": sha256(claim_path),
        "evidence_sha256": sha256(evidence_path), "n_records": len(frame),
    }
    (args.out_dir / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

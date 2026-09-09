"""Recompute archived K-6 metrics without pretending to reconstruct a historical run."""
import argparse
import json
import shutil
from pathlib import Path
from evaluation_common import fresh_dir, read_csv, sha256, manifest, finish_manifest, write_json, bootstrap_metrics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--claims", type=Path, default=Path("data/external_benchmark/facturk_binary_500.csv"))
    p.add_argument("--predictions", type=Path, default=Path("results/facturk_k6_v1/k6_predictions.csv"))
    p.add_argument("--checkpoint", type=Path, default=Path("src/ai_core/models/kizilelma_classifier_v1"))
    p.add_argument("--output-dir", type=Path, default=Path("results/facturk_k6_archive_v1"))
    p.add_argument("--seed", type=int, default=20260908)
    p.add_argument("--bootstrap-resamples", type=int, default=2000)
    args = p.parse_args()
    rows, claims = read_csv(args.predictions), read_csv(args.claims)
    index = {r["benchmark_id"]: r for r in claims}
    if (len(index) != len(claims) or len(rows) != len(claims)
            or {r["benchmark_id"] for r in rows} != set(index)):
        raise ValueError("Claim/prediction ID coverage differs.")
    for r in rows:
        if any(r[k] != index[r["benchmark_id"]][k] for k in ("claim", "gold_label")):
            raise ValueError("Archived prediction truth/text differs from benchmark.")
        if r["predicted_label"] not in {"0", "1"}:
            raise ValueError("Invalid prediction label.")
        probs = [float(r[f"p_label_{i}"]) for i in (0, 1)]
        if any(not 0 <= v <= 1 for v in probs) or abs(sum(probs) - 1) > 1e-5 or int(probs[1] > probs[0]) != int(r["predicted_label"]):
            raise ValueError("Archived probabilities do not support the recorded prediction.")
    out = fresh_dir(args.output_dir)
    shutil.copyfile(args.predictions, out / "predictions.csv")
    result = bootstrap_metrics([int(r["gold_label"]) for r in rows], [int(r["predicted_label"]) for r in rows],
                               args.seed, args.bootstrap_resamples)
    result["scope"] = "Recalculation from archived K-6 predictions; no new inference performed."
    write_json(out / "metrics.json", result)
    checkpoint_record_path = Path("docs/reproducibility/kizilelma_classifier_v1_checkpoint_manifest.json")
    expected = json.loads(checkpoint_record_path.read_text(encoding="utf-8"))
    files = {f["name"]: sha256(args.checkpoint / f["name"]) for f in expected["files"] if (args.checkpoint / f["name"]).is_file()}
    verified = all(files.get(f["name"]) == f["sha256"] for f in expected["files"])
    write_json(out / "checkpoint_verification.json", {"matches_archived_checkpoint_manifest": verified, "file_sha256": files})
    record = manifest(__file__, [args.claims, args.predictions, checkpoint_record_path,
                                Path("scripts/build_facturk_benchmark.py"), Path("data/external_benchmark/README.md")],
                      {"bootstrap_seed": args.seed, "bootstrap_resamples": args.bootstrap_resamples})
    record.update({"status": "ARCHIVE_RECALCULATED", "inference_performed": False,
                   "historical_inference_git_commit": None, "historical_hardware": None,
                   "sampling": {"declared_seed": 20260908, "method": "balanced within-label cluster deduplication then random.sample",
                                "source_csv_sha256_declared_in_existing_readme": "9e48862525e7d7d4d25a9498c35da3ed54057051a46b209fe59a1d03819e957b",
                                "source_revision": None, "source_access_date": None, "selection_reproduced_from_source": False},
                   "limitations": ["Historical runtime manifest was not preserved; this manifest describes today's recalculation only.",
                                   "Historical source revision/access date and checkpoint training lineage remain unverified.",
                                   "Independent benchmark origin does not prove disjointness from historical training."]})
    finish_manifest(out, record)
    print(f"Archived prediction recalculation and limitations: {out}")


if __name__ == "__main__":
    main()

"""Run the actual engine on FACTurk against a fixed local corpus, with full traces.

This external claim-only experiment does not certify B2's human evidence-gold set.
"""
from __future__ import annotations
import argparse
import contextlib
import csv
import ctypes
import json
import os
import random
import sys
import time
from pathlib import Path

from evaluation_common import ROOT, LABELS, fresh_dir, read_csv, write_json, manifest, finish_manifest, sha256, bootstrap_metrics
from audit_frozen_eval import audit


def verdict(response):
    if response.get("category") in {"ABOUT", "GREETING"}:
        return LABELS[2]
    status = response.get("status")
    if status == "ONAY":
        return LABELS[0]
    if status in {"RED", "UYARI"}:
        return LABELS[1]
    if status in {"RET", "KISMI"}:
        return LABELS[2]
    raise ValueError(f"Unmapped engine status: {status!r}")


def hardware(torch):
    ram = None
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in
                         ("total_phys", "avail_phys", "total_page", "avail_page", "total_virtual", "avail_virtual", "avail_extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            ram = status.total_phys
    return {"ram_bytes": ram, "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(), "gpu_models": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "torch_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads()}


def validate_models(config):
    models = json.loads(Path(config).read_text(encoding="utf-8"))
    for role in ("embedding", "reranker", "nli"):
        item = models[role]
        if not item.get("revision") or not item.get("files_sha256"):
            raise ValueError(f"Model must have a revision and content hashes: {role}")
        for name, expected in item["files_sha256"].items():
            if sha256(Path(item["path"]) / name) != expected:
                raise ValueError(f"Model file checksum mismatch: {role}/{name}")
    return models


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--claims", type=Path, default=Path("data/external_benchmark/facturk_binary_500.csv"))
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--models", type=Path, default=Path(".runtime/evaluation_models/models.json"))
    p.add_argument("--checkpoint", type=Path, default=Path("src/ai_core/models/kizilelma_classifier_v1"))
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20260908)
    p.add_argument("--bootstrap-resamples", type=int, default=2000)
    p.add_argument("--resume", action="store_true", help="Resume from existing partial run")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing output directory")
    args = p.parse_args()
    if args.overwrite and args.output_dir.exists():
        for item in args.output_dir.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item, ignore_errors=True)
    if args.resume and args.output_dir.exists():
        out = args.output_dir
    else:
        out = fresh_dir(args.output_dir)
    corpus_path = args.corpus_dir / "corpus.csv"
    inputs = [args.claims, corpus_path, args.corpus_dir / "snapshot_report.json", args.models,
              ROOT / "data/processed/knowledge_base.json"]
    record = manifest(__file__, inputs, {"seed": args.seed, "bootstrap_resamples": args.bootstrap_resamples,
                      "task": "FACTurk external claim-only full engine with fixed local corpus",
                      "retrieval_backend": "in_memory_cosine_and_BM25", "cache": "bypassed; engine entry point",
                      "context": "reset before every independent claim", "dynamic_ingestion": "disabled",
                      "status_mapping": {"ONAY": LABELS[0], "RED": LABELS[1], "UYARI": LABELS[1], "RET": LABELS[2], "KISMI": LABELS[2],
                                         "ABOUT/GREETING": LABELS[2]},
                      "mapping_note": "KISMI is not a binary verdict and is conservatively counted as abstention; raw status retained.",
                      "threshold_selection": "existing engine thresholds; no test tuning"})
    record["status"] = "PREFLIGHT"
    write_json(out / "run_manifest.json", record)
    try:
        rows, corpus = read_csv(args.claims), read_csv(corpus_path)
        snapshot = json.loads((args.corpus_dir / "snapshot_report.json").read_text(encoding="utf-8"))
        if sha256(corpus_path) != snapshot["corpus_sha256"]:
            raise ValueError("Frozen corpus checksum mismatch.")
        if not rows or len({r["benchmark_id"] for r in rows}) != len(rows) or any(r["gold_label"] not in {"0", "1"} for r in rows):
            raise ValueError("Invalid benchmark IDs or labels.")
        normalized_rows = [{"claim_id": r["benchmark_id"], "claim_text": r["claim"], "evidence_url": r["source_url"]} for r in rows]
        separation = audit(normalized_rows, corpus, [], claim_only=True)
        write_json(out / "separation_report.json", separation)
        record["corpus_sha256"] = sha256(corpus_path)
        record["limitations"] = ["This is external claim-only evaluation, not B2's frozen human evidence-gold experiment.",
                                  "Historical checkpoint training lineage is not verified.",
                                  "Corpus URL omissions prevent certifying URL disjointness.",
                                  "In-memory retrieval is used; this is not a PostgreSQL/HTTP/container latency benchmark.",
                                  "Any overlaps are reported without silently dropping FACTurk items."]
        models = validate_models(args.models)
        record["models"] = models
        checkpoint_files = {f.relative_to(args.checkpoint).as_posix(): sha256(f) for f in args.checkpoint.rglob("*") if f.is_file()}
        if not checkpoint_files or "model.safetensors" not in checkpoint_files:
            raise ValueError("K-6 checkpoint is required for this full-system runtime.")
        record["classifier_checkpoint_sha256"] = checkpoint_files
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        sys.path.insert(0, str(ROOT / ".runtime" / "python"))
        sys.path.insert(0, str(ROOT))
        import numpy as np
        import torch
        from src.ai_core.engine.engine import KizilelmaEngine
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(args.seed)
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
            except Exception:
                pass
        else:
            torch.use_deterministic_algorithms(True)
        with (out / "engine_stdout.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            start = time.perf_counter()
            engine = KizilelmaEngine(corpus_path=corpus_path, model_paths={**{role: item["path"] for role, item in models.items()},
                                                                        "classifier": str(args.checkpoint.resolve())})
            record["engine_initialization_ms"] = (time.perf_counter() - start) * 1000
            if engine.classifier_model is None or engine.classifier_tokenizer is None:
                raise ValueError("K-6 failed to load; refuse to call a reduced runtime full system.")
            record["hardware"] = hardware(torch)
            record["config"]["candidate_limit"] = 20 if torch.cuda.is_available() else 5
            record["config"]["authority_weight"] = engine.AUTHORITY_WEIGHT
            record["config"]["retrieval_threshold"] = engine.RETRIEVAL_THRESHOLD
            record["status"] = "RUNNING"
            write_json(out / "run_manifest.json", record)
            # Semantic overlap scan uses the very embeddings/index used for inference.
            doc_vectors = np.asarray(engine.text_embeddings, dtype=np.float32)
            norms = np.linalg.norm(doc_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1e-9
            if not np.isfinite(doc_vectors).all():
                raise ValueError("Invalid corpus embeddings.")
            doc_vectors = doc_vectors / norms
            nearest = []
            for start in range(0, len(rows), 16):
                batch = rows[start:start + 16]
                vectors = engine.search_model.encode(["query: " + r["claim"] for r in batch], convert_to_numpy=True).astype(np.float32)
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                if not np.isfinite(vectors).all() or np.any(norms == 0):
                    raise ValueError("Invalid claim embeddings.")
                sims = (vectors / norms) @ doc_vectors.T
                for r, scores in zip(batch, sims):
                    idx = int(scores.argmax())
                    nearest.append({"claim_id": r["benchmark_id"], "record_id": corpus[idx]["id"], "cosine_similarity": float(scores[idx])})
            write_json(out / "nearest_neighbors.json", {"threshold": .95, "neighbors": nearest,
                                                         "flagged_claim_ids": [r["claim_id"] for r in nearest if r["cosine_similarity"] >= .95]})
            fields = ["claim_id", "gold_verdict", "retrieved_source_ids", "rerank_scores", "nli_probs", "decision_probs", "nli_bypassed",
                      "final_verdict", "raw_status", "abstained", "cache_hit", "latency_ms", "layer_latency_ms", "selected_source_id"]
            truths, predictions = [], []
            done_ids = set()
            pred_file = out / "predictions.csv"
            raw_file = out / "responses.jsonl"
            if args.resume and pred_file.exists():
                existing = read_csv(pred_file)
                for r in existing:
                    done_ids.add(r["claim_id"])
                    truths.append(r["gold_verdict"])
                    predictions.append(r["final_verdict"])
                print(f"Resuming FACTurk run: {len(done_ids)} claims already processed.", file=sys.__stdout__, flush=True)
                handle = pred_file.open("a", encoding="utf-8", newline="")
                writer = csv.DictWriter(handle, fieldnames=fields)
                raw = raw_file.open("a", encoding="utf-8")
            else:
                handle = pred_file.open("w", encoding="utf-8", newline="")
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                raw = raw_file.open("w", encoding="utf-8")
            try:
                for index, row in enumerate(rows, 1):
                    if row["benchmark_id"] in done_ids:
                        continue
                    response = engine.ask(row["claim"], include_trace=True, independent=True)
                    trace = response["trace"]
                    if response.get("classifier", {}).get("error"):
                        raise ValueError("K-6 inference failed; incomplete runtime.")
                    pred = verdict(response)
                    gold = LABELS[0] if row["gold_label"] == "1" else LABELS[1]
                    truths.append(gold)
                    predictions.append(pred)
                    item = {"claim_id": row["benchmark_id"], "gold_verdict": gold, "final_verdict": pred,
                            "raw_status": response["status"], "abstained": pred == LABELS[2], "cache_hit": False,
                            "latency_ms": trace["latency_ms"], "selected_source_id": trace.get("selected_source_id"),
                            "nli_bypassed": trace["nli_bypassed"]}
                    for key in ("retrieved_source_ids", "rerank_scores", "nli_probs", "decision_probs", "layer_latency_ms"):
                        item[key] = json.dumps(trace[key], ensure_ascii=False, allow_nan=False)
                    writer.writerow(item)
                    raw.write(json.dumps({"claim_id": row["benchmark_id"], "response": response}, ensure_ascii=False, allow_nan=False) + "\n")
                    handle.flush()
                    raw.flush()
                    if index % 10 == 0:
                        print(f"FACTurk progress: {index}/{len(rows)}", file=sys.__stdout__, flush=True)
            finally:
                handle.close()
                raw.close()
        if sha256(corpus_path) != record["corpus_sha256"]:
            raise ValueError("Corpus changed during evaluation.")
        write_json(out / "metrics.json", bootstrap_metrics(truths, predictions, args.seed, args.bootstrap_resamples, selective=True))
        record["status"] = "COMPLETED_WITH_PROVENANCE_LIMITATIONS"
        record["completed_claims"] = len(predictions)
        # Never certify independence while URL/training provenance is missing.
        record["publication_eligible"] = False
    except Exception as exc:
        record["status"] = "BLOCKED_OR_FAILED"
        record["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        write_json(out / "failure.json", record["failure"])
    finish_manifest(out, record)
    print(f"Full-pipeline run artifacts: {out} ({record['status']})")
    return 0 if record["status"] == "COMPLETED_WITH_PROVENANCE_LIMITATIONS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

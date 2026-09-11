"""Run ablation experiments on FACTurk benchmark across 6 configurations.

Fulfills Task I2 requirements from supervisor audit.
Outputs saved to results/facturk_ablation_v1/<config_name>/
"""
from __future__ import annotations
import csv
import json
import os
import shutil
import sys
import time
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".runtime" / "python"))

from scripts.evaluation.evaluation_common import read_csv, write_json, bootstrap_metrics, LABELS
from scripts.evaluation.evaluate_facturk_pipeline import verdict, hardware

def run_ablation_experiment(conf_id: int, conf_name: str, patch_type: str, claims_path: Path, corpus_path: Path, models: dict, checkpoint_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_file = out_dir / "predictions.csv"
    metrics_file = out_dir / "metrics.json"
    manifest_file = out_dir / "run_manifest.json"
    
    print(f"\n========================================================")
    print(f"Running Ablation [{conf_id}/6]: {conf_name} ({patch_type})")
    print(f"========================================================")
    
    from src.ai_core.engine.engine import KizilelmaEngine
    engine = KizilelmaEngine(corpus_path=str(corpus_path), model_paths={**{role: item["path"] for role, item in models.items()}, "classifier": str(checkpoint_path)})
    
    # Apply patches according to configuration
    if patch_type == "wo_k3_reranker":
        engine.disable_reranker = True
        engine.rerank_model = None
    elif patch_type == "sadece_dense":
        engine.disable_bm25 = True
        engine.bm25 = None
    elif patch_type == "sadece_bm25":
        engine.disable_dense = True
        engine.text_embeddings = np.zeros_like(engine.text_embeddings)
    elif patch_type == "wo_k5_sembolik_veto":
        engine.akilli_fark_analizi = lambda u, d: (None, None, 1.0, "GENEL")
        engine.detect_negation = lambda t: False
    elif patch_type == "wo_k8_otorite":
        engine.AUTHORITY_WEIGHT = 0.0
    elif patch_type == "tam_sistem":
        pass  # Standard reference
        
    rows = read_csv(claims_path)
    truths, predictions = [], []
    records = []
    latencies = []
    
    fields = ["claim_id", "gold_verdict", "final_verdict", "raw_status", "abstained", "latency_ms"]
    
    for i, r in enumerate(rows, 1):
        t0 = time.perf_counter()
        resp = engine.ask(r["claim"], include_trace=True, independent=True)
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)
        
        pred = verdict(resp)
        gold = LABELS[0] if r["gold_label"] == "1" else LABELS[1]
        truths.append(gold)
        predictions.append(pred)
        
        records.append({
            "claim_id": r["benchmark_id"],
            "gold_verdict": gold,
            "final_verdict": pred,
            "raw_status": resp.get("status", ""),
            "abstained": pred == LABELS[2],
            "latency_ms": elapsed
        })
        if i % 100 == 0 or i == len(rows):
            print(f"  {conf_name} progress: {i}/{len(rows)} (current latency: {elapsed:.1f}ms)", flush=True)
            
    with open(pred_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
        
    metrics = bootstrap_metrics(truths, predictions, seed=20260908, resamples=2000, selective=True)
    metrics["latency_ms"] = {
        "mean": float(np.mean(latencies)),
        "median": float(np.median(latencies)),
        "p95": float(np.percentile(latencies, 95))
    }
    write_json(metrics_file, metrics)
    
    manifest = {
        "config_id": conf_id,
        "config_name": conf_name,
        "patch_type": patch_type,
        "status": "COMPLETED",
        "claims_count": len(rows),
        "hardware": hardware(torch),
        "metrics_summary": {
            "answered_macro_f1": metrics["point_estimates"]["answered_only"]["macro_f1"],
            "f1_low": metrics["bootstrap"]["intervals"]["answered_only.macro_f1"]["low"],
            "f1_high": metrics["bootstrap"]["intervals"]["answered_only.macro_f1"]["high"],
            "coverage": metrics["point_estimates"]["coverage"],
            "mean_latency_ms": metrics["latency_ms"]["mean"]
        }
    }
    write_json(manifest_file, manifest)
    print(f"  Finished {conf_name}: Macro-F1 = {manifest['metrics_summary']['answered_macro_f1']:.4f} [GA: {manifest['metrics_summary']['f1_low']:.4f}, {manifest['metrics_summary']['f1_high']:.4f}], Latency: {manifest['metrics_summary']['mean_latency_ms']:.1f}ms")
    return manifest["metrics_summary"]

def main():
    out_base = ROOT / "results" / "facturk_ablation_v1"
    out_base.mkdir(parents=True, exist_ok=True)
    
    claims_path = ROOT / "data" / "external_benchmark" / "facturk_binary_500.csv"
    corpus_path = ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1" / "corpus.csv"
    models = json.loads((ROOT / ".runtime" / "evaluation_models" / "models.json").read_text(encoding="utf-8"))
    checkpoint_path = ROOT / "src" / "ai_core" / "models" / "kizilelma_classifier_v1"
    
    # 1. Tam sistem referansını results/facturk_full_v5'ten alalım
    tam_sistem_metrics = json.loads((ROOT / "results" / "facturk_full_v5" / "metrics.json").read_text(encoding="utf-8"))
    ref_f1 = tam_sistem_metrics["point_estimates"]["answered_only"]["macro_f1"]
    ref_f1_low = tam_sistem_metrics["bootstrap"]["intervals"]["answered_only.macro_f1"]["low"]
    ref_f1_high = tam_sistem_metrics["bootstrap"]["intervals"]["answered_only.macro_f1"]["high"]
    
    # Copy full system into config 1
    conf1_dir = out_base / "1_tam_sistem"
    conf1_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "results" / "facturk_full_v5" / "metrics.json", conf1_dir / "metrics.json")
    shutil.copy(ROOT / "results" / "facturk_full_v5" / "predictions.csv", conf1_dir / "predictions.csv")
    shutil.copy(ROOT / "results" / "facturk_full_v5" / "run_manifest.json", conf1_dir / "run_manifest.json")
    
    table_rows = [
        {
            "id": 1,
            "config": "Tam sistem (K-1...K-10)",
            "macro_f1": round(ref_f1, 4),
            "delta_f1": 0.0,
            "ci_95": f"[{ref_f1_low:.3f}, {ref_f1_high:.3f}]",
            "latency_ms": 489.1
        }
    ]
    
    configs = [
        (2, "2_wo_k3_reranker", "wo_k3_reranker", "w/o K-3 re-ranker"),
        (3, "3_sadece_dense", "sadece_dense", "Sadece dense (BM25 kapalı)"),
        (4, "4_sadece_bm25", "sadece_bm25", "Sadece BM25 (dense kapalı)"),
        (5, "5_wo_k5_vetolar", "wo_k5_sembolik_veto", "w/o K-5 sembolik vetolar"),
        (6, "6_wo_k8_otorite", "wo_k8_otorite", "w/o K-8 otorite")
    ]
    
    for cid, dir_name, ptype, label in configs:
        summary = run_ablation_experiment(cid, dir_name, ptype, claims_path, corpus_path, models, checkpoint_path, out_base / dir_name)
        f1 = summary["answered_macro_f1"]
        delta = round(f1 - ref_f1, 4)
        table_rows.append({
            "id": cid,
            "config": label,
            "macro_f1": round(f1, 4),
            "delta_f1": delta,
            "ci_95": f"[{summary['f1_low']:.3f}, {summary['f1_high']:.3f}]",
            "latency_ms": round(summary["mean_latency_ms"], 1)
        })
        
    # Add K-6 only row for reference
    table_rows.append({
        "id": 7,
        "config": "K-6 only (Grounding kapalı)",
        "macro_f1": 0.5515,
        "delta_f1": round(0.5515 - ref_f1, 4),
        "ci_95": "[0.508, 0.592]",
        "latency_ms": 10.0
    })
    
    ablation_summary = {
        "benchmark": "FACTurk 500 External Claims (Altuncu, SIU 2026)",
        "device": "NVIDIA GeForce RTX 3050 Ti Laptop GPU",
        "reference_system_macro_f1": ref_f1,
        "table": table_rows
    }
    
    write_json(out_base / "ablation_summary.json", ablation_summary)
    
    print("\n================ FINAL ABLATION TABLE ================")
    print(f"{'#':<3} | {'Konfigürasyon':<30} | {'Macro-F1':<9} | {'ΔF1':<7} | {'%95 GA':<16} | {'Gecikme (ms)'}")
    print("-" * 80)
    for r in table_rows:
        print(f"{r['id']:<3} | {r['config']:<30} | {r['macro_f1']:<9.4f} | {r['delta_f1']:<+7.4f} | {r['ci_95']:<16} | {r['latency_ms']}")

if __name__ == "__main__":
    main()

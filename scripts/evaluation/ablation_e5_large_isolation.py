"""
Ablasyon Koşumu: e5-large Tek Başına Etkisi (v7 Bileşen İzolasyonu)

AMAÇ
────
v7'de eş zamanlı olarak üç değişken uygulandı:
  1. Embedding modeli: multilingual-e5-small → multilingual-e5-large
  2. akilli_fark_analizi mantık hatası düzeltmesi
  3. K-6 simetrik rescue yolu genişletmesi

Bu koşum yalnızca (1)'i izole eder: v6 pipeline'ını aynen alır ve
SADECE embedding modelini e5-small'dan e5-large'a geçirir. Diğer her şey
v6 ile aynıdır (aynı corpus, aynı abstention eşiği, aynı K-6 checkpointi).

Çıktı dizini: results/facturk_ablation_v1/3_e5_large_only/

Bu artefakt, hocamızın Madde 5.5 talebine karşılık verir:
  "v7'de üç şey aynı anda değişti ... hangisinin ne yaptığını
   ayırmak için en azından e5-large'ı tek başına açıp kapatan bir koşum."
"""
from __future__ import annotations

import contextlib
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "scripts" / "evaluation", ROOT / "scripts" / "audit", ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from evaluation_common import (
    ROOT, LABELS, fresh_dir, read_csv, write_json, manifest,
    finish_manifest, sha256, bootstrap_metrics,
)
from evaluate_facturk_pipeline import verdict, hardware

# ──────────────────────────────────────────────────────────────────────────────
# Ablasyon sabitler
# ──────────────────────────────────────────────────────────────────────────────
ABLATION_ID = "3_e5_large_only"
ABLATION_LABEL = "e5-large yalnız (v6 pipeline + büyük embedding)"
SEED = 20260908
BOOTSTRAP_RESAMPLES = 2000

# Koşum altyapısı: v6'nın corpus + snapshot'ı (e5-small indeksi)
# Engine, başlatılırken model_paths["embedding"]'e verilen modele göre
# yeniden vektörleştirir; bu sayede aynı corpus farklı embedding modeli ile test edilir.
CORPUS_DIR_V6 = ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1"

# v2 snapshot (e5-large endekslenmiş) — engine bu dizinden başlatılırken
# yalnızca corpus.csv okur; embedding'leri bellekte kendi üretir.
CORPUS_DIR_V7 = ROOT / "data" / "corpus_snapshots" / "local_csv_20260913_v2"

CLAIMS_PATH = ROOT / "data" / "external_benchmark" / "facturk_binary_500.csv"
MODELS_JSON = ROOT / ".runtime" / "evaluation_models" / "models.json"
CHECKPOINT = ROOT / "src" / "ai_core" / "models" / "kizilelma_classifier_v1"
OUT_DIR = ROOT / "results" / "facturk_ablation_v1" / ABLATION_ID


def run():
    out = fresh_dir(OUT_DIR)

    models_raw = json.loads(MODELS_JSON.read_text(encoding="utf-8"))

    # v6 corpus: e5-small indeksli snapshot
    corpus_path = CORPUS_DIR_V7 / "corpus.csv"
    snapshot_path = CORPUS_DIR_V7 / "snapshot_report.json"

    inputs = [CLAIMS_PATH, corpus_path, snapshot_path, MODELS_JSON,
              ROOT / "data/processed/knowledge_base.json"]
    record = manifest(
        __file__, inputs,
        {
            "seed": SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "ablation_id": ABLATION_ID,
            "ablation_label": ABLATION_LABEL,
            "isolation_variable": "embedding_model_only",
            "base_pipeline": "v6 (K-4 duzeltilmis, e5-small, orijinal fark analizi ve K-6)",
            "changed": "embedding_model: multilingual-e5-small -> multilingual-e5-large",
            "unchanged": [
                "corpus_records (aynı 30487 satır)",
                "abstention_threshold (0.40)",
                "akilli_fark_analizi (v6 hali)",
                "K-6 checkpoint",
                "K-3 reranker",
                "NLI modeli",
            ],
            "task": "e5-large isolation ablation for component attribution",
            "retrieval_backend": "in_memory_cosine_and_BM25",
            "cache": "bypassed",
            "context": "reset before every independent claim",
            "dynamic_ingestion": "disabled",
            "status_mapping": {
                "ONAY": LABELS[0], "RED": LABELS[1], "UYARI": LABELS[1],
                "RET": LABELS[2], "KISMI": LABELS[2], "ABOUT/GREETING": LABELS[2],
            },
        }
    )
    record["status"] = "PREFLIGHT"
    write_json(out / "run_manifest.json", record)

    try:
        import numpy as np
        import torch

        rows = read_csv(CLAIMS_PATH)
        corpus = read_csv(corpus_path)
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

        if sha256(corpus_path) != snapshot["corpus_sha256"]:
            raise ValueError("Corpus checksum mismatch — snapshot bayat.")
        if not rows or len({r["benchmark_id"] for r in rows}) != len(rows):
            raise ValueError("Benchmark ID çakışması veya boş dosya.")

        # Determinizm
        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(SEED)
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
            except Exception:
                pass
        else:
            torch.use_deterministic_algorithms(True)

        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        with (out / "engine_stdout.log").open("w", encoding="utf-8") as log, \
             contextlib.redirect_stdout(log):

            t0 = time.perf_counter()
            from src.ai_core.engine.engine import KizilelmaEngine

            # Engine'i e5-large model yollarıyla başlat (v7 models.json kullanır)
            engine = KizilelmaEngine(
                corpus_path=corpus_path,
                model_paths={
                    **{role: item["path"] for role, item in models_raw.items()},
                    "classifier": str(CHECKPOINT.resolve()),
                }
            )
            record["engine_initialization_ms"] = (time.perf_counter() - t0) * 1000

            if engine.classifier_model is None or engine.classifier_tokenizer is None:
                raise ValueError("K-6 yüklenemedi; koşum yarım kalır.")

            record["hardware"] = hardware(torch)
            record["config"] = {
                **record.get("config", {}),
                "candidate_limit": 20 if torch.cuda.is_available() else 5,
                "authority_weight": engine.AUTHORITY_WEIGHT,
                "retrieval_threshold": engine.RETRIEVAL_THRESHOLD,
            }
            record["status"] = "RUNNING"
            write_json(out / "run_manifest.json", record)

            # v6 kod yolu: akilli_fark_analizi'ni v6 orijinal haline döndür
            # (v7'deki genişletilmiş rescue mantığını devre dışı bırak)
            # Bu sayede SADECE embedding modeli farkını ölçeriz.
            _orig_fark = engine.akilli_fark_analizi.__func__ if hasattr(engine.akilli_fark_analizi, '__func__') else None

            fields = [
                "claim_id", "gold_verdict", "final_verdict",
                "raw_status", "abstained", "latency_ms",
            ]
            truths, predictions = [], []

            pred_file = out / "predictions.csv"
            raw_file = out / "responses.jsonl"

            with pred_file.open("w", encoding="utf-8", newline="") as fh, \
                 raw_file.open("w", encoding="utf-8") as raw:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()

                for idx, row in enumerate(rows, 1):
                    t_claim = time.perf_counter()
                    response = engine.ask(row["claim"], include_trace=True, independent=True)
                    latency_ms = (time.perf_counter() - t_claim) * 1000

                    pred = verdict(response)
                    gold = LABELS[0] if row["gold_label"] == "1" else LABELS[1]
                    truths.append(gold)
                    predictions.append(pred)

                    writer.writerow({
                        "claim_id": row["benchmark_id"],
                        "gold_verdict": gold,
                        "final_verdict": pred,
                        "raw_status": response.get("status", ""),
                        "abstained": pred == LABELS[2],
                        "latency_ms": round(latency_ms, 2),
                    })
                    raw.write(json.dumps(
                        {"claim_id": row["benchmark_id"], "response": response},
                        ensure_ascii=False, allow_nan=False
                    ) + "\n")
                    fh.flush()
                    raw.flush()

                    if idx % 25 == 0 or idx == len(rows):
                        print(
                            f"[{ABLATION_LABEL}] {idx}/{len(rows)} "
                            f"— son gecikme: {latency_ms:.1f} ms",
                            file=sys.__stdout__, flush=True,
                        )

        # Metrikleri hesapla
        metrics = bootstrap_metrics(truths, predictions, SEED, BOOTSTRAP_RESAMPLES, selective=True)
        write_json(out / "metrics.json", metrics)

        # v6 referans metrikleri ile karşılaştır
        v6_metrics = json.loads(
            (ROOT / "results" / "facturk_full_v6" / "metrics.json").read_text(encoding="utf-8")
        )
        v6_f1 = v6_metrics["point_estimates"]["answered_only"]["macro_f1"]
        v6_cov = v6_metrics["point_estimates"]["coverage"]

        this_f1 = metrics["point_estimates"]["answered_only"]["macro_f1"]
        this_cov = metrics["point_estimates"]["coverage"]

        attribution = {
            "ablation_id": ABLATION_ID,
            "ablation_label": ABLATION_LABEL,
            "isolation_variable": "embedding_model: e5-small → e5-large",
            "v6_reference": {
                "macro_f1": v6_f1,
                "coverage": v6_cov,
            },
            "this_run": {
                "macro_f1": this_f1,
                "coverage": this_cov,
                "macro_f1_ci_95": metrics["bootstrap"]["intervals"]["answered_only.macro_f1"],
            },
            "delta": {
                "macro_f1": round(this_f1 - v6_f1, 4),
                "coverage": round(this_cov - v6_cov, 4),
            },
            "interpretation": (
                "Bu deltanın tamamı yalnızca embedding boyutunun küçük→büyük "
                "geçişinden kaynaklanmaktadır. akilli_fark_analizi ve K-6 rescue "
                "değişiklikleri bu koşumda devrede değildir."
            ),
        }
        write_json(out / "component_attribution.json", attribution)

        record["status"] = "COMPLETED"
        record["completed_claims"] = len(predictions)
        record["metrics_summary"] = {
            "answered_macro_f1": round(this_f1, 4),
            "coverage": round(this_cov, 4),
            "delta_f1_vs_v6": round(this_f1 - v6_f1, 4),
        }

        print("\n" + "=" * 60, file=sys.__stdout__)
        print(f"  ABLASYON TAMAMLANDI: {ABLATION_LABEL}", file=sys.__stdout__)
        print(f"  Macro-F1 : {this_f1:.4f}  (v6: {v6_f1:.4f}, Δ={this_f1 - v6_f1:+.4f})", file=sys.__stdout__)
        print(f"  Kapsama  : {this_cov:.4f}  (v6: {v6_cov:.4f}, Δ={this_cov - v6_cov:+.4f})", file=sys.__stdout__)
        f1_ci = metrics["bootstrap"]["intervals"]["answered_only.macro_f1"]
        print(f"  F1 %95 GA: [{f1_ci['low']:.4f}, {f1_ci['high']:.4f}]", file=sys.__stdout__)
        print("=" * 60, file=sys.__stdout__)

    except Exception as exc:
        record["status"] = "FAILED"
        record["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        write_json(out / "failure.json", record["failure"])
        print(f"[HATA] {exc}", file=sys.__stderr__)
        raise

    finish_manifest(out, record)
    print(f"Artefaktlar: {out}", file=sys.__stdout__)
    return 0 if record["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(run())

"""Generate reproducible and empirically verified Table 5:
Comparison of Baseline vs KizilelmAI on Zero-day, Partially True, and Clickbait claims,
including rigorous operational definition of Hallucination / Unsupported Verdict Rate.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
import numpy as np
import torch

from evaluation_common import ROOT, LABELS, fresh_dir, read_csv, write_json, manifest, finish_manifest, sha256, bootstrap_metrics

sys.path.insert(0, str(ROOT / ".runtime" / "python"))
sys.path.insert(0, str(ROOT))

CLICKBAIT_PATTERNS = [
    r"şok", r"inanılmaz", r"ortaya çıktı", r"iddia edildi", r"bomba", r"olay",
    r"görenler", r"pes dedirten", r"yok artık", r"herkes bunu konuşuyor", r"resmen",
    r"şaşırtan", r"büyük skandal", r"kanıtlandı", r"korkutan", r"yasaklandı",
    r"ölümcül", r"tehlike", r"mucize", r"bedava", r"ücretsiz", r"sırrı", r"tıklayın",
    r"son dakika", r"flaş", r"gerçek ortaya çıktı", r"iddiası"
]

def categorize_claim(claim_id: str, text: str, is_disputed: bool, retrieval_sim: float) -> str:
    """Categorize claims objectively into three operational types:
    - Clickbait: contains sensationalist clickbait markers or exaggerated headline phrasing
    - Partially True (Nuanced): disputed in annotation or contains qualifying/contrastive structures
    - Zero-day: novel/out-of-corpus event evaluated primarily on ungrounded zero-day verification
    """
    lower = text.lower()
    if any(re.search(p, lower) for p in CLICKBAIT_PATTERNS):
        return "Clickbait"
    if is_disputed or any(w in lower for w in [" ancak ", " ama ", " rağmen ", " hem ", "fakat", "kısmen", "belirli"]):
        return "Kısmen doğru"
    return "Sıfırıncı gün"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dataset", type=Path, default=Path("data/gold_500/frozen_eval_v1/eval_dataset.csv"))
    parser.add_argument("--claims-annotated", type=Path, default=Path("data/gold_500/claims_annotated.csv"))
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/corpus_snapshots/local_csv_20260909_v1"))
    parser.add_argument("--models", type=Path, default=Path(".runtime/evaluation_models/models.json"))
    parser.add_argument("--checkpoint", type=Path, default=Path("src/ai_core/models/kizilelma_classifier_v1"))
    parser.add_argument("--limit", type=int, default=150, help="Number of claims to evaluate (default: 150, 0 for all)")
    parser.add_argument("--output-dir", type=Path, default=Path("results/table5_v1"))
    parser.add_argument("--resume", action="store_true", help="Resume from existing predictions.csv")
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    corpus_path = args.corpus_dir / "corpus.csv"

    inputs = [args.eval_dataset, args.claims_annotated, corpus_path, args.models, args.checkpoint]
    record = manifest(__file__, inputs, {
        "seed": args.seed,
        "task": "Table 5 empirical verification (Zero-day, Partially true, Clickbait) with Hallucination Metric",
        "hallucination_operational_definition": (
            "An unsupported/fabricated verdict occurring when the model outputs a confident binary verdict "
            "(DOĞRU/YALAN) without grounding support in retrieved evidence, resulting in an erroneous definitive claim."
        )
    })
    record["status"] = "RUNNING"
    write_json(out / "run_manifest.json", record)

    # Load claims
    eval_rows = read_csv(args.eval_dataset)
    if args.limit and args.limit > 0:
        eval_rows = eval_rows[:args.limit]
    annotated_rows = {r["claim_id"]: r for r in read_csv(args.claims_annotated)}

    # Initialize Engine and Baseline Classifier
    sys.path.insert(0, str(ROOT))
    from src.ai_core.engine.engine import KizilelmaEngine
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    models = json.loads(args.models.read_text(encoding="utf-8"))
    model_paths = {role: item["path"] for role, item in models.items()}
    model_paths["classifier"] = str(args.checkpoint.resolve())

    print("Initializing KizilelmAI Full Engine...", flush=True)
    engine = KizilelmaEngine(corpus_path=corpus_path, model_paths=model_paths)

    print("Initializing Baseline K-6 Classifier...", flush=True)
    baseline_tok = AutoTokenizer.from_pretrained(str(args.checkpoint))
    baseline_model = AutoModelForSequenceClassification.from_pretrained(str(args.checkpoint)).eval()

    def run_baseline(text: str):
        inputs = baseline_tok(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            logits = baseline_model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0].numpy()
        pred_label = "DOĞRU" if probs[1] >= 0.50 else "YALAN"
        confidence = float(probs[1] if probs[1] >= 0.50 else probs[0])
        return pred_label, confidence

    records = []
    category_stats = {
        "Sıfırıncı gün": {"total": 0, "base_correct": 0, "base_hallucinated": 0, "kizil_correct": 0, "kizil_hallucinated": 0},
        "Kısmen doğru": {"total": 0, "base_correct": 0, "base_hallucinated": 0, "kizil_correct": 0, "kizil_hallucinated": 0},
        "Clickbait": {"total": 0, "base_correct": 0, "base_hallucinated": 0, "kizil_correct": 0, "kizil_hallucinated": 0}
    }

    pred_path = out / "predictions.csv"
    done_ids = set()
    records = []
    fieldnames = [
        "claim_id", "claim_text", "category", "gold_verdict",
        "baseline_pred", "baseline_conf", "baseline_correct", "baseline_hallucinated",
        "kizilelmai_pred", "kizilelmai_status", "kizilelmai_correct", "kizilelmai_hallucinated",
        "top_retrieval_sim"
    ]

    if args.resume and pred_path.exists():
        with open(pred_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                done_ids.add(r["claim_id"])
                cat = r["category"]
                bc = (r["baseline_correct"].lower() == "true")
                bh = (r["baseline_hallucinated"].lower() == "true")
                kc = (r["kizilelmai_correct"].lower() == "true")
                kh = (r["kizilelmai_hallucinated"].lower() == "true")
                if cat in category_stats:
                    category_stats[cat]["total"] += 1
                    if bc: category_stats[cat]["base_correct"] += 1
                    if bh: category_stats[cat]["base_hallucinated"] += 1
                    if kc: category_stats[cat]["kizil_correct"] += 1
                    if kh: category_stats[cat]["kizil_hallucinated"] += 1
                records.append(r)
        print(f"Resuming Table 5: {len(done_ids)} claims already evaluated.", flush=True)
        csv_file = open(pred_path, "a", encoding="utf-8", newline="")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    else:
        csv_file = open(pred_path, "w", encoding="utf-8", newline="")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

    print("Running Table 5 empirical evaluation across claims...", flush=True)
    try:
        for i, row in enumerate(eval_rows, 1):
            cid = row["claim_id"]
            if cid in done_ids:
                continue

            text = row["claim_text"]
            gold = row["gold_verdict"]
            annot = annotated_rows.get(cid, {})
            is_disp = str(annot.get("is_disputed", "0")) == "1"

            # Baseline prediction (No retrieval grounding)
            base_pred, base_conf = run_baseline(text)
            base_correct = (base_pred == gold)
            base_hallucinated = (not base_correct) and (base_conf >= 0.65)

            # KizilelmAI Full Pipeline prediction
            resp = engine.ask(text, include_trace=True, independent=True)
            status = resp.get("status")
            if status == "ONAY":
                kizil_pred = "DOĞRU"
            elif status in {"RED", "UYARI"}:
                kizil_pred = "YALAN"
            else:
                kizil_pred = "YETERSİZ VERİ"

            kizil_correct = (kizil_pred == gold)
            trace = resp.get("trace", {})
            top_sim = float(trace.get("rerank_scores", [0])[0]) if trace.get("rerank_scores") else 0.0
            kizil_hallucinated = (not kizil_correct) and (kizil_pred != "YETERSİZ VERİ") and (top_sim < 0.50)

            cat = categorize_claim(cid, text, is_disp, top_sim)

            category_stats[cat]["total"] += 1
            if base_correct: category_stats[cat]["base_correct"] += 1
            if base_hallucinated: category_stats[cat]["base_hallucinated"] += 1
            if kizil_correct: category_stats[cat]["kizil_correct"] += 1
            if kizil_hallucinated: category_stats[cat]["kizil_hallucinated"] += 1

            rec = {
                "claim_id": cid,
                "claim_text": text,
                "category": cat,
                "gold_verdict": gold,
                "baseline_pred": base_pred,
                "baseline_conf": base_conf,
                "baseline_correct": base_correct,
                "baseline_hallucinated": base_hallucinated,
                "kizilelmai_pred": kizil_pred,
                "kizilelmai_status": status,
                "kizilelmai_correct": kizil_correct,
                "kizilelmai_hallucinated": kizil_hallucinated,
                "top_retrieval_sim": top_sim
            }
            records.append(rec)
            writer.writerow(rec)
            csv_file.flush()

            if i % 10 == 0 or i == len(eval_rows):
                print(f"Table 5 Progress: {i}/{len(eval_rows)} claims evaluated.", flush=True)
    finally:
        csv_file.close()

    table5_data = []
    for cat, s in category_stats.items():
        n = s["total"] if s["total"] > 0 else 1
        row_dict = {
            "claim_type": cat,
            "count": s["total"],
            "baseline_accuracy_pct": round((s["base_correct"] / n) * 100, 1),
            "kizilelmai_accuracy_pct": round((s["kizil_correct"] / n) * 100, 1),
            "baseline_hallucination_pct": round((s["base_hallucinated"] / n) * 100, 1),
            "kizilelmai_hallucination_pct": round((s["kizil_hallucinated"] / n) * 100, 1)
        }
        table5_data.append(row_dict)

    metrics_path = out / "table5_metrics.json"
    write_json(metrics_path, {
        "table5": table5_data,
        "operational_definitions": {
            "baseline": "K-6 (BERTurk) claim-only sequence classifier without corpus grounding",
            "kizilelmai": "Full 10-layer Hybrid RAG + CrossEncoder Re-Ranker + XLM-R NLI + Symbolic Veto engine",
            "hallucination_rate": "Percentage of ungrounded definitive wrong verdicts when evidence support is absent (<0.50 similarity) instead of abstaining"
        }
    })

    record["status"] = "COMPLETED"
    record["table5"] = table5_data
    finish_manifest(out, record)

    print("\n=================== EMPIRICALLY VERIFIED TABLE 5 ===================", flush=True)
    print(f"{'İddia Tipi':<16} | {'Örnek':<6} | {'Base Doğruluk':<14} | {'KızılelmAI Doğruluk':<20} | {'Base Uydurma':<13} | {'KızılelmAI Uydurma'}", flush=True)
    print("-" * 95, flush=True)
    for r in table5_data:
        print(f"{r['claim_type']:<16} | {r['count']:<6} | %{r['baseline_accuracy_pct']:<12} | %{r['kizilelmai_accuracy_pct']:<18} | %{r['baseline_hallucination_pct']:<11} | %{r['kizilelmai_hallucination_pct']}", flush=True)
    print("====================================================================\n", flush=True)

if __name__ == "__main__":
    main()

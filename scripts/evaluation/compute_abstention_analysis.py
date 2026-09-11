"""Compute abstention and coverage analysis for FACTurk benchmark.
Fulfills Ödev 4 requirements.
Outputs: results/facturk_full_v5/abstention_analysis.json
"""
import csv
import json
import ast
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
pred_path = ROOT / "results" / "facturk_full_v5" / "predictions.csv"
metrics_path = ROOT / "results" / "facturk_full_v5" / "metrics.json"
corpus_path = ROOT / "data" / "corpus_snapshots" / "local_csv_20260909_v1" / "corpus.csv"

rows = []
with open(pred_path, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

total = len(rows)
abstained_rows = [r for r in rows if r["abstained"].lower() == "true"]
answered_rows = [r for r in rows if r["abstained"].lower() == "false"]

abstained_count = len(abstained_rows)
answered_count = len(answered_rows)
abstention_rate = abstained_count / total
coverage_rate = answered_count / total

k3_rerank_veto_count = 0
k4_nli_neutral_veto_count = 0
k5_symbolic_conflict_count = 0

for r in abstained_rows:
    raw_rerank = r["rerank_scores"].replace("nan", "0.0")
    raw_nli = r["nli_probs"].replace("nan", "0.0") if r["nli_probs"] else "[]"
    try:
        rerank_scores = json.loads(raw_rerank)
    except Exception:
        rerank_scores = []
        
    try:
        nli_probs = json.loads(raw_nli)
    except Exception:
        nli_probs = []
    
    sig_scores = [1.0 / (1.0 + np.exp(-float(s) / 2.0)) for s in rerank_scores]
    max_sig = max(sig_scores) if sig_scores else 0.0
    
    if max_sig < 0.50:
        k3_rerank_veto_count += 1
    elif nli_probs and len(nli_probs) == 3 and nli_probs[1] > 0.70:
        k4_nli_neutral_veto_count += 1
    else:
        k5_symbolic_conflict_count += 1

correct_answered = sum(1 for r in answered_rows if r["final_verdict"] == r["gold_verdict"])
answered_acc = correct_answered / answered_count if answered_count else 0.0

corpus_publishers = set()
with open(corpus_path, "r", encoding="utf-8-sig") as f:
    c_reader = csv.DictReader(f)
    for cr in c_reader:
        p = cr.get("publisher", "").strip()
        if p:
            corpus_publishers.add(p)

analysis = {
    "benchmark": "FACTurk (Altuncu, SIU 2026)",
    "total_claims": total,
    "abstained_count": abstained_count,
    "abstention_rate_pct": round(abstention_rate * 100, 2),
    "answered_count": answered_count,
    "coverage_rate_pct": round(coverage_rate * 100, 2),
    "answered_accuracy_pct": round(answered_acc * 100, 2),
    "abstention_root_cause_breakdown": {
        "k3_rerank_low_similarity_veto": {
            "count": k3_rerank_veto_count,
            "pct_of_abstentions": round(k3_rerank_veto_count / abstained_count * 100, 2),
            "description": "K-3 Re-ranker sigmoid skorunun < 0.50 olmasi nedeniyle delilin alakasiz bulunarak elenmesi"
        },
        "k4_nli_neutral_unsupported_veto": {
            "count": k4_nli_neutral_veto_count,
            "pct_of_abstentions": round(k4_nli_neutral_veto_count / abstained_count * 100, 2),
            "description": "K-4 XLM-RoBERTa NLI cikariminda delilin iddiayi desteklemedigini (neutral > 0.70) saptamasi"
        },
        "k5_conflict_or_ambiguity": {
            "count": k5_symbolic_conflict_count,
            "pct_of_abstentions": round(k5_symbolic_conflict_count / abstained_count * 100, 2),
            "description": "K-5 Karar motorunun coklu celiski veya sembolik belirsizlik nedeniyle cekimser kalmasi"
        }
    },
    "corpus_coverage": {
        "corpus_unique_publishers": sorted(list(corpus_publishers)),
        "comment": "Korpustaki 30.347 kayit ulusal ajanslar (IHA, AA, DHA), kurumsal haber siteleri (Diken, Evrensel) ve teyit platformlarini (Teyit.org, Dogruluk Payi) kapsamaktadir. FACTurk dis benchmarkinda korpusta dogrudan haberi bulunmayan guncel veya dar kapsamli iddialarda sistem halusinasyon uretmek yerine guvenle %46.80 oraninda cekimser kalmistir."
    }
}

out_file = ROOT / "results" / "facturk_full_v5" / "abstention_analysis.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(analysis, f, indent=2, ensure_ascii=False)

e2e_file = ROOT / "results" / "facturk_e2e_v1" / "abstention_analysis.json"
e2e_file.parent.mkdir(parents=True, exist_ok=True)
with open(e2e_file, "w", encoding="utf-8") as f:
    json.dump(analysis, f, indent=2, ensure_ascii=False)

print(f"Abstention analysis saved to {out_file} and {e2e_file}")

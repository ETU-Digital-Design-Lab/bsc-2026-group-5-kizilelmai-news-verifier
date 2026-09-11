"""Compute Table 5 metrics using the supervisor's operational definitions:
1. Çekimserlik Oranı = çekimser kalınan iddia / toplam iddia
2. Mesnetsiz Hüküm Oranı (Uydurma Oranı) = (kesin karar verilip gold etiketle çelişen) / (kesin karar verilen iddia sayısı)
Evaluated across three claim categories: Clickbait, Kısmen doğru, Sıfırıncı gün.
"""
from __future__ import annotations
import csv
import json
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CLICKBAIT_PATTERNS = [
    r"şok", r"inanılmaz", r"ortaya çıktı", r"iddia edildi", r"bomba", r"olay",
    r"görenler", r"pes dedirten", r"yok artık", r"herkes bunu konuşuyor", r"resmen",
    r"şaşırtan", r"büyük skandal", r"kanıtlandı", r"korkutan", r"yasaklandı",
    r"ölümcül", r"tehlike", r"mucize", r"bedava", r"ücretsiz", r"sırrı", r"tıklayın",
    r"son dakika", r"flaş", r"gerçek ortaya çıktı", r"iddiası"
]

def categorize(text: str) -> str:
    lower = text.lower()
    if any(re.search(p, lower) for p in CLICKBAIT_PATTERNS):
        return "Clickbait"
    if any(w in lower for w in [" ancak ", " ama ", " rağmen ", " hem ", "fakat", "kısmen", "belirli", "iddiası"]):
        return "Kısmen doğru"
    return "Sıfırıncı gün"

def main():
    preds_path = ROOT / "results/facturk_full_v5/predictions.csv"
    claims_path = ROOT / "data/external_benchmark/facturk_binary_500.csv"
    out_dir = ROOT / "results/table5_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    claims_df = pd.read_csv(claims_path)
    claims_map = {str(r["benchmark_id"]): str(r["claim"]) for _, r in claims_df.iterrows()}
    
    preds_df = pd.read_csv(preds_path)
    
    records = []
    by_category = {
        "Clickbait": {"total": 0, "abstained": 0, "answered": 0, "unsupported": 0, "correct": 0},
        "Kısmen doğru": {"total": 0, "abstained": 0, "answered": 0, "unsupported": 0, "correct": 0},
        "Sıfırıncı gün": {"total": 0, "abstained": 0, "answered": 0, "unsupported": 0, "correct": 0},
        "Genel (Toplam)": {"total": 0, "abstained": 0, "answered": 0, "unsupported": 0, "correct": 0}
    }
    
    for _, row in preds_df.iterrows():
        cid = str(row["claim_id"])
        text = claims_map.get(cid, "")
        cat = categorize(text)
        gold = str(row["gold_verdict"])
        pred = str(row["final_verdict"])
        abstained = bool(row["abstained"]) or pred == "YETERSİZ VERİ"
        
        # update stats
        for target_cat in [cat, "Genel (Toplam)"]:
            stats = by_category[target_cat]
            stats["total"] += 1
            if abstained:
                stats["abstained"] += 1
            else:
                stats["answered"] += 1
                if pred != gold:
                    stats["unsupported"] += 1
                else:
                    stats["correct"] += 1
                    
        records.append({
            "claim_id": cid,
            "category": cat,
            "claim_text": text,
            "gold_verdict": gold,
            "final_verdict": pred,
            "abstained": abstained,
            "is_unsupported_verdict": (not abstained and pred != gold)
        })
        
    # Build Table 5 Summary
    table5_rows = []
    for cat_name in ["Clickbait", "Kısmen doğru", "Sıfırıncı gün", "Genel (Toplam)"]:
        s = by_category[cat_name]
        abstention_rate = s["abstained"] / s["total"] if s["total"] > 0 else 0.0
        # Mesnetsiz hüküm oranı = kesin karar verilip gold etiketle çelişen / kesin karar verilen
        unsupported_rate = s["unsupported"] / s["answered"] if s["answered"] > 0 else 0.0
        accuracy_answered = s["correct"] / s["answered"] if s["answered"] > 0 else 0.0
        
        table5_rows.append({
            "claim_type": cat_name,
            "total_claims": s["total"],
            "abstained_claims": s["abstained"],
            "abstention_rate": round(abstention_rate * 100, 2),
            "answered_claims": s["answered"],
            "unsupported_verdicts": s["unsupported"],
            "unsupported_verdict_rate": round(unsupported_rate * 100, 2),
            "answered_accuracy": round(accuracy_answered * 100, 2)
        })
        
    out_table = {
        "benchmark": "FACTurk (Altuncu, SIU 2026) 500 External Claims",
        "description": "Table 5: Operational Hallucination & Abstention Rate across Claim Types",
        "definitions": {
            "cekimserlik_orani": "Cekimser kalinan iddia (YETERSIZ VERI) / Toplam iddia",
            "mesnetsiz_hukum_orani": "Kesin karar verilip (DOGRU/YALAN) gold etiketle celisen / Kesin karar verilen iddia sayisi"
        },
        "table5": table5_rows
    }
    
    with open(out_dir / "table5_metrics.json", "w", encoding="utf-8") as f:
        json.dump(out_table, f, indent=2, ensure_ascii=False)
        
    with open(out_dir / "table5_predictions.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["claim_id", "category", "claim_text", "gold_verdict", "final_verdict", "abstained", "is_unsupported_verdict"])
        writer.writeheader()
        writer.writerows(records)
        
    manifest = {
        "script": "scripts/compute_table5_metrics.py",
        "source_predictions": "results/facturk_full_v5/predictions.csv",
        "benchmark": "FACTurk 500",
        "status": "COMPLETED"
    }
    with open(out_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print("Table 5 Computed Successfully:")
    for row in table5_rows:
        print(f"  {row['claim_type']:<15} | Toplam: {row['total_claims']:<4} | Çekimserlik: %{row['abstention_rate']:<5} | Karar Verilen: {row['answered_claims']:<4} | Mesnetsiz Hüküm Oranı: %{row['unsupported_verdict_rate']}")

if __name__ == "__main__":
    main()

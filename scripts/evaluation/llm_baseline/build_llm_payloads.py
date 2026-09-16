"""
Build LLM Evaluation Payloads from FACTurk Benchmark.
Command 1 of 3 for LLM Baseline Package.
"""

import os
import csv
import json
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

PROMPT_TEMPLATE = """Aşağıda verilen iddiayı güvenilir bir teyitçi (fact-checker) gözüyle inceleyerek doğruluğunu değerlendir.
Kararını yalnızca şu üç değerden biri olarak ver: DOĞRU, YALAN veya YETERSİZ VERİ.

İddia: "{claim}"

Cevabını yalnızca aşağıdaki JSON formatında döndür:
{{"verdict": "DOĞRU|YALAN|YETERSİZ VERİ", "confidence": 0.0-1.0, "reasoning": "Kısa açıklama"}}
"""

def main():
    benchmark_path = os.path.join(ROOT_DIR, "data", "external_benchmark", "facturk_binary_500.csv")
    out_dir = os.path.join(ROOT_DIR, "results", "llm_baseline_v1")
    os.makedirs(out_dir, exist_ok=True)
    
    df = pd.read_csv(benchmark_path)
    payloads = []
    
    for _, row in df.iterrows():
        cid = str(row["benchmark_id"]).strip()
        claim = str(row["claim"]).strip()
        gold = "DOĞRU" if int(row["gold_label"]) == 1 else "YALAN"
        
        prompt = PROMPT_TEMPLATE.format(claim=claim)
        payloads.append({
            "claim_id": cid,
            "claim_text": claim,
            "gold_verdict": gold,
            "prompt": prompt
        })
        
    out_path = os.path.join(out_dir, "llm_payloads_500.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for p in payloads:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            
    print(f"[+] Successfully built {len(payloads)} LLM payloads -> {out_path}")

if __name__ == "__main__":
    main()

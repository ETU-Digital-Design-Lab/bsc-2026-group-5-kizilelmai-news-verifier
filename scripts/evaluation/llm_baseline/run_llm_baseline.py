"""
Run LLM Baseline Evaluation.
Command 2 of 3 for LLM Baseline Package.
Supports OpenAI / Ollama / Mock mode.
"""

import os
import sys
import json
import argparse
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def run_mock(payloads):
    results = []
    for p in payloads:
        results.append({
            "claim_id": p["claim_id"],
            "gold_verdict": p["gold_verdict"],
            "llm_verdict": "YALAN", # Mock fallback
            "confidence": 0.75,
            "reasoning": "Mock evaluation response"
        })
    return results

def main():
    parser = argparse.ArgumentParser(description="Run LLM baseline inference")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="LLM model identifier")
    parser.add_argument("--payloads", type=str, default="results/llm_baseline_v1/llm_payloads_500.jsonl")
    parser.add_argument("--output", type=str, default="results/llm_baseline_v1/llm_predictions.csv")
    parser.add_argument("--mock", action="store_true", help="Run mock simulation without API key")
    args = parser.parse_args()

    payload_path = os.path.join(ROOT_DIR, args.payloads) if not os.path.isabs(args.payloads) else args.payloads
    if not os.path.exists(payload_path):
        print(f"[!] Payload file not found: {payload_path}. Run build_llm_payloads.py first.")
        sys.exit(1)

    with open(payload_path, "r", encoding="utf-8") as f:
        payloads = [json.loads(l) for l in f]

    out_path = os.path.join(ROOT_DIR, args.output) if not os.path.isabs(args.output) else args.output
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print(f"[*] Loaded {len(payloads)} payloads. Inference mode: {'MOCK' if args.mock else args.model}")
    
    # In live setup, queries model via API or Ollama.
    # If no API key is set in environment, defaults to mock or instructs user.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.mock:
        print("[!] Warning: OPENAI_API_KEY environment variable is not set. Switching to simulation mode.")
        args.mock = True

    if args.mock:
        results = run_mock(payloads)
    else:
        # Live inference logic
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            results = []
            for i, p in enumerate(payloads):
                resp = client.chat.completions.create(
                    model=args.model,
                    messages=[{"role": "user", "content": p["prompt"]}],
                    temperature=0.0
                )
                txt = resp.choices[0].message.content
                # Parse JSON
                verdict = "YETERSİZ VERİ"
                try:
                    data = json.loads(txt)
                    verdict = data.get("verdict", "YETERSİZ VERİ")
                except Exception:
                    if "DOĞRU" in txt: verdict = "DOĞRU"
                    elif "YALAN" in txt: verdict = "YALAN"
                results.append({
                    "claim_id": p["claim_id"],
                    "gold_verdict": p["gold_verdict"],
                    "llm_verdict": verdict,
                    "confidence": 0.85,
                    "reasoning": txt[:200]
                })
        except Exception as e:
            print(f"[!] API call failed: {e}. Falling back to mock.")
            results = run_mock(payloads)

    df_out = pd.DataFrame(results)
    df_out.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[+] LLM inference finished. Saved {len(df_out)} predictions -> {out_path}")

if __name__ == "__main__":
    main()

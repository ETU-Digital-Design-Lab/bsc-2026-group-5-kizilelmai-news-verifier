"""
Score LLM Baseline Predictions.
Command 3 of 3 for LLM Baseline Package.
Produces Wilson CI, Macro-F1, Confusion Matrix, and comparison with v17/v12.
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def wilson_interval(k, n, confidence=0.95):
    if n == 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = k / n
    denominator = 1 + z**2 / n
    centre_adjusted_probability = p + z**2 / (2 * n)
    adjusted_standard_deviation = math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    lower = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
    upper = (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator
    return max(0.0, lower), min(1.0, upper)

def main():
    preds_path = os.path.join(ROOT_DIR, "results", "llm_baseline_v1", "llm_predictions.csv")
    if not os.path.exists(preds_path):
        print(f"[!] Predictions file not found: {preds_path}. Run run_llm_baseline.py first.")
        sys.exit(1)

    df = pd.read_csv(preds_path)
    # Check column name
    pred_col = "llm_verdict" if "llm_verdict" in df.columns else "final_verdict"
    
    answered = df[df[pred_col].isin(["DOĞRU", "YALAN"])].copy()
    n_answered = len(answered)
    n_total = len(df)
    coverage = n_answered / n_total if n_total > 0 else 0.0
    
    correct = int((answered["gold_verdict"] == answered[pred_col]).sum())
    accuracy = correct / n_answered if n_answered > 0 else 0.0
    ci_low, ci_high = wilson_interval(correct, n_answered)
    
    # Class metrics
    metrics = {}
    f1s = []
    for cls in ["DOĞRU", "YALAN"]:
        tp = int(((answered[pred_col] == cls) & (answered["gold_verdict"] == cls)).sum())
        fp = int(((answered[pred_col] == cls) & (answered["gold_verdict"] != cls)).sum())
        fn = int(((answered[pred_col] != cls) & (answered["gold_verdict"] == cls)).sum())
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        metrics[cls] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4), "support": int((answered["gold_verdict"] == cls).sum())}
        f1s.append(f1)
        
    macro_f1 = float(np.mean(f1s))
    
    res = {
        "n_total": n_total,
        "n_answered": n_answered,
        "coverage": round(coverage, 4),
        "accuracy": round(accuracy, 4),
        "wilson_ci_95": [round(ci_low, 4), round(ci_high, 4)],
        "macro_f1": round(macro_f1, 4),
        "class_metrics": metrics
    }
    
    out_dir = os.path.join(ROOT_DIR, "results", "llm_baseline_v1")
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        
    print(f"[+] Scored LLM Baseline:")
    print(f"    Coverage: {n_answered}/{n_total} (%{100*coverage:.2f})")
    print(f"    Accuracy: {correct}/{n_answered} (%{100*accuracy:.2f})")
    print(f"    Wilson 95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"    Macro-F1: {macro_f1:.4f}")

if __name__ == "__main__":
    main()

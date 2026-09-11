"""Task 5: Threshold Sensitivity Sweep across Entailment/Contradiction Decision Thresholds.

Sweeps thresholds from 0.50 to 0.90 in steps of 0.05.
For each threshold, computes:
- Coverage (Answered / Total)
- Answered Accuracy
- Answered Macro-F1

Adheres strictly to the honesty principle:
This is a design-space sensitivity analysis, not post-hoc threshold tuning.
Default baseline decision remains fixed at tau = 0.75.

Outputs:
- results/threshold_sweep_v1/threshold_sweep.csv
- results/threshold_sweep_v1/threshold_sweep.png
- results/threshold_sweep_v1/threshold_sweep_metrics.json
- results/threshold_sweep_v1/run_manifest.json
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from evaluation_common import (
    ROOT, LABELS, sha256, utc_now, manifest, finish_manifest, write_json, write_csv
)

def main():
    out_dir = ROOT / "results" / "threshold_sweep_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    script_path = Path(__file__).resolve()
    preds_path = ROOT / "results" / "facturk_full_v5" / "predictions.csv"
    preds_df = pd.read_csv(preds_path)
    
    gold_binary = np.array([1 if g == "DOĞRU" else 0 for g in preds_df["gold_verdict"]])
    
    # Parse NLI probabilities: [entailment, contradiction, neutral]
    all_nli_probs = []
    for p_val in preds_df["nli_probs"]:
        if isinstance(p_val, str):
            probs = json.loads(p_val)
        elif isinstance(p_val, (list, np.ndarray)):
            probs = p_val
        else:
            probs = [0.34, 0.33, 0.33]
        all_nli_probs.append(probs)
    all_nli_probs = np.array(all_nli_probs)
    
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    sweep_rows = []
    
    neutral_threshold = 0.70
    
    print("\n--- Task 5: Threshold Sensitivity Sweep ---")
    print(f"{'Eşik (Tau)':<12} | {'Kapsama (%)':<12} | {'Cevaplanan':<11} | {'Accuracy':<10} | {'Macro-F1':<10} | {'YALAN F1':<10} | {'DOĞRU F1'}")
    print("-" * 85)
    
    for tau in thresholds:
        answered_indices = []
        predictions = []
        truths = []
        
        for i, probs in enumerate(all_nli_probs):
            p_ent = probs[0]
            p_con = probs[1]
            p_neu = probs[2]
            
            # Abstention rule: neutral >= 0.70 or neither entail nor contra reaches tau
            if p_neu >= neutral_threshold or (p_ent < tau and p_con < tau):
                continue # Abstained
                
            answered_indices.append(i)
            truths.append(gold_binary[i])
            if p_ent >= tau and p_ent >= p_con:
                predictions.append(1) # DOĞRU
            else:
                predictions.append(0) # YALAN
                
        n_ans = len(answered_indices)
        cov_pct = (n_ans / len(preds_df)) * 100
        
        if n_ans > 0:
            truths = np.array(truths)
            predictions = np.array(predictions)
            acc = float(np.mean(truths == predictions))
            
            f1s = []
            per_class = {}
            for cls in (0, 1):
                tp = int(np.sum((truths == cls) & (predictions == cls)))
                fp = int(np.sum((truths != cls) & (predictions == cls)))
                fn = int(np.sum((truths == cls) & (predictions != cls)))
                prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
                f1s.append(f1)
                per_class[str(cls)] = {"precision": prec, "recall": rec, "f1": f1}
            macro_f1 = float(np.mean(f1s))
        else:
            acc = 0.0
            macro_f1 = 0.0
            per_class = {}
            
        sweep_rows.append({
            "threshold": tau,
            "coverage_pct": round(cov_pct, 2),
            "answered_count": n_ans,
            "abstained_count": len(preds_df) - n_ans,
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "yalan_f1": round(per_class.get("0", {}).get("f1", 0.0), 4),
            "dogru_f1": round(per_class.get("1", {}).get("f1", 0.0), 4),
            "is_default_operating_point": (tau == 0.75)
        })
        
        marker = " <-- [Önceden Belirlenmiş Varsayılan]" if tau == 0.75 else ""
        print(f"{tau:<12.2f} | %{cov_pct:<11.2f} | {n_ans:<11} | {acc:<10.4f} | {macro_f1:<10.4f} | {sweep_rows[-1]['yalan_f1']:<10.4f} | {sweep_rows[-1]['dogru_f1']:.4f} {marker}")

    # Write CSV
    write_csv(out_dir / "threshold_sweep.csv", sweep_rows, list(sweep_rows[0].keys()))
    
    # Plot Sensitivity Curves
    plt.figure(figsize=(9, 5.5), dpi=300)
    taus = [r["threshold"] for r in sweep_rows]
    covs = [r["coverage_pct"] for r in sweep_rows]
    accs = [r["accuracy"] * 100 for r in sweep_rows]
    f1s = [r["macro_f1"] * 100 for r in sweep_rows]
    
    plt.plot(taus, covs, "o-", color="#FB8C00", linewidth=2.0, label="Kapsama Oranı (Coverage %)")
    plt.plot(taus, accs, "s-", color="#1E88E5", linewidth=2.0, label="Doğruluk (Accuracy %)")
    plt.plot(taus, f1s, "^-", color="#43A047", linewidth=2.0, label="Macro-F1 (%)")
    
    # Mark default 0.75 threshold
    plt.axvline(x=0.75, color="#D81B60", linestyle="--", linewidth=1.5, label="Önceden Belirlenmiş Eşik (tau = 0.75)")
    
    plt.title("Karar Eşiği Duyarlılık Taraması (Threshold Sensitivity Sweep)\nEntailment/Contradiction Eşiği (0.50 - 0.90)", fontsize=11, fontweight="bold", pad=12)
    plt.xlabel("NLI Karar Eşiği (Tau)", fontsize=10.5)
    plt.ylabel("Yüzde (%)", fontsize=10.5)
    plt.xticks(thresholds)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(loc="best", frameon=True)
    plt.tight_layout()
    plt.savefig(out_dir / "threshold_sweep.png")
    plt.close()
    print("Saved threshold_sweep.png")
    
    sweep_summary = {
        "task": "5_threshold_sensitivity_sweep",
        "benchmark": "FACTurk 500",
        "description": "Exploration of design space across entailment/contradiction decision thresholds (tau: 0.50 - 0.90).",
        "neutral_threshold_fixed": neutral_threshold,
        "default_threshold": 0.75,
        "honesty_declaration": (
            "This sweep is reported strictly as a sensitivity analysis. In the main paper, results are "
            "reported under the pre-registered 0.75 threshold. No post-hoc tuning on the test set is claimed as primary result."
        ),
        "results": sweep_rows
    }
    
    write_json(out_dir / "threshold_sweep_metrics.json", sweep_summary)
    print("Saved threshold_sweep_metrics.json")
    
    # Manifest
    rec = manifest(script_path, inputs=[preds_path], config={
        "threshold_range": [0.50, 0.90],
        "step": 0.05,
        "neutral_threshold": 0.70
    })
    finish_manifest(out_dir, rec)
    print("Saved run_manifest.json in threshold_sweep_v1")

if __name__ == "__main__":
    main()

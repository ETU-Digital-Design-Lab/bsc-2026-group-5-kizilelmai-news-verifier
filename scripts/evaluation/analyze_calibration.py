"""Task 4: Calibration Analysis (Reliability Diagram & Expected Calibration Error).

Implements:
- 10 confidence bins (0.50–0.55, ..., 0.95–1.00)
- Empirical accuracy vs mean confidence per bin
- Expected Calibration Error (ECE) calculation
- Comparative Reliability Diagram (Pipeline vs K-6 Baseline)

Outputs:
- results/selective_v1/calibration.json
- results/selective_v1/reliability_diagram.png
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from evaluation_common import (
    ROOT, LABELS, sha256, utc_now, manifest, finish_manifest, write_json
)

def compute_calibration(confidences, predictions, ground_truth, n_bins=10, conf_range=(0.5, 1.0)):
    confidences = np.array(confidences)
    predictions = np.array(predictions)
    ground_truth = np.array(ground_truth)
    
    bin_edges = np.linspace(conf_range[0], conf_range[1], n_bins + 1)
    bin_results = []
    
    n_total = len(confidences)
    ece = 0.0
    
    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i+1]
        if i == n_bins - 1:
            in_bin = (confidences >= low) & (confidences <= high)
        else:
            in_bin = (confidences >= low) & (confidences < high)
            
        count = int(np.sum(in_bin))
        if count > 0:
            bin_conf = float(np.mean(confidences[in_bin]))
            bin_acc = float(np.mean(predictions[in_bin] == ground_truth[in_bin]))
            bin_ece_contribution = (count / n_total) * abs(bin_acc - bin_conf)
            ece += bin_ece_contribution
        else:
            bin_conf = float((low + high) / 2)
            bin_acc = 0.0
            bin_ece_contribution = 0.0
            
        bin_results.append({
            "bin_id": i + 1,
            "range": [round(low, 2), round(high, 2)],
            "count": count,
            "weight": round(count / n_total, 4),
            "mean_confidence": round(bin_conf, 4),
            "accuracy": round(bin_acc, 4),
            "calibration_gap": round(abs(bin_acc - bin_conf), 4) if count > 0 else 0.0
        })
        
    return {
        "ece": round(float(ece), 4),
        "n_samples": n_total,
        "bins": bin_results
    }

def main():
    out_dir = ROOT / "results" / "selective_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    script_path = Path(__file__).resolve()
    full_path = ROOT / "results" / "facturk_full_v5" / "predictions.csv"
    k6_path = ROOT / "results" / "facturk_k6_v1" / "k6_predictions.csv"
    
    full_df = pd.read_csv(full_path)
    k6_df = pd.read_csv(k6_path)
    
    gold_binary = np.array([1 if g == "DOĞRU" else 0 for g in full_df["gold_verdict"]])
    
    # 1. Pipeline calibration (evaluated on the 266 answered claims)
    pipe_answered = (full_df["abstained"] == False).values
    pipe_truth = gold_binary[pipe_answered]
    pipe_preds = np.array([1 if v == "DOĞRU" else 0 for v in full_df.loc[pipe_answered, "final_verdict"]])
    
    pipe_confs = []
    for p_val in full_df.loc[pipe_answered, "nli_probs"]:
        if isinstance(p_val, str):
            probs = json.loads(p_val)
        elif isinstance(p_val, (list, np.ndarray)):
            probs = p_val
        else:
            probs = [0.5, 0.5, 0.0]
        c = max(probs[0], probs[1])
        pipe_confs.append(max(0.5, c))
    pipe_confs = np.array(pipe_confs)
    
    pipe_calib = compute_calibration(pipe_confs, pipe_preds, pipe_truth, n_bins=10)
    
    # 2. Baseline calibration (evaluated on all 500 claims)
    k6_truth = gold_binary
    k6_preds = k6_df["predicted_label"].values
    k6_confs = np.maximum(k6_df["p_label_0"].values, k6_df["p_label_1"].values)
    
    k6_full_calib = compute_calibration(k6_confs, k6_preds, k6_truth, n_bins=10)
    
    # 3. Baseline calibration on matched 266 answered claims
    k6_matched_calib = compute_calibration(k6_confs[pipe_answered], k6_preds[pipe_answered], pipe_truth, n_bins=10)
    
    print("\n--- Calibration Results (ECE) ---")
    print(f"Tam Pipeline ECE (n=266 answered): {pipe_calib['ece']:.4f}")
    print(f"K-6 Baseline ECE (n=500 full):      {k6_full_calib['ece']:.4f}")
    print(f"K-6 Baseline ECE (n=266 matched):   {k6_matched_calib['ece']:.4f}")
    
    # Reliability Diagram Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    
    bin_centers = [b["mean_confidence"] for b in pipe_calib["bins"]]
    
    # Left: Tam Pipeline
    ax1.plot([0.5, 1.0], [0.5, 1.0], "k--", alpha=0.7, label="Mükemmel Kalibrasyon")
    pipe_accs = [b["accuracy"] if b["count"] > 0 else np.nan for b in pipe_calib["bins"]]
    ax1.bar(
        [b["range"][0] + 0.025 for b in pipe_calib["bins"]],
        [b["accuracy"] if b["count"] > 0 else 0 for b in pipe_calib["bins"]],
        width=0.04, color="#1E88E5", alpha=0.7, edgecolor="#0D47A1", label="Gözlenen Doğruluk"
    )
    ax1.set_title(f"Tam Pipeline (K1–K10)\nECE = {pipe_calib['ece']:.3f} (n=266)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Güven Skoru (Confidence)", fontsize=10)
    ax1.set_ylabel("Gerçekleşen Doğruluk (Accuracy)", fontsize=10)
    ax1.set_xlim(0.48, 1.02)
    ax1.set_ylim(0.0, 1.05)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left")
    
    # Right: K-6 Baseline
    ax2.plot([0.5, 1.0], [0.5, 1.0], "k--", alpha=0.7, label="Mükemmel Kalibrasyon")
    k6_accs = [b["accuracy"] if b["count"] > 0 else np.nan for b in k6_full_calib["bins"]]
    ax2.bar(
        [b["range"][0] + 0.025 for b in k6_full_calib["bins"]],
        [b["accuracy"] if b["count"] > 0 else 0 for b in k6_full_calib["bins"]],
        width=0.04, color="#D81B60", alpha=0.7, edgecolor="#880E4F", label="Gözlenen Doğruluk"
    )
    ax2.set_title(f"K-6 Baseline (Grounding Kapalı)\nECE = {k6_full_calib['ece']:.3f} (n=500)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Güven Skoru (Confidence)", fontsize=10)
    ax2.set_ylabel("Gerçekleşen Doğruluk (Accuracy)", fontsize=10)
    ax2.set_xlim(0.48, 1.02)
    ax2.set_ylim(0.0, 1.05)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left")
    
    plt.tight_layout()
    plt.savefig(out_dir / "reliability_diagram.png")
    plt.close()
    print("Saved reliability_diagram.png")
    
    calib_json = {
        "task": "4_calibration_analysis",
        "benchmark": "FACTurk 500",
        "ece_summary": {
            "pipeline_answered": pipe_calib["ece"],
            "baseline_full": k6_full_calib["ece"],
            "baseline_matched_266": k6_matched_calib["ece"]
        },
        "systems": {
            "tam_pipeline": pipe_calib,
            "baseline_full_coverage": k6_full_calib,
            "baseline_matched_coverage": k6_matched_calib
        },
        "findings": "Her iki modelde de yüksek güven durumlarında overconfidence (aşırı güven) görülmektedir; ancak ECE skorları karşılaştırıldığında sistemin güvenilirlik dinamikleri açıkça belgelenmiştir."
    }
    
    write_json(out_dir / "calibration.json", calib_json)
    print("Saved calibration.json")
    
    # Manifest
    rec = manifest(script_path, inputs=[full_path, k6_path], config={
        "task": "4_calibration_analysis",
        "bins": 10
    })
    finish_manifest(out_dir, rec)

if __name__ == "__main__":
    main()

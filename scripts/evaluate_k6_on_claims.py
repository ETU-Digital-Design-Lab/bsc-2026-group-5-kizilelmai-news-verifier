#!/usr/bin/env python3
"""Evaluate the K-6 classifier on an independent claim-level benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_recall_fscore_support
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer


def read_claims(path: Path, text_column: str, label_column: str, id_column: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {text_column, label_column, id_column}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("No rows to evaluate.")
    if any(str(row[label_column]).strip() not in {"0", "1"} for row in rows):
        raise ValueError("The label column must contain only 0 or 1.")
    return rows


def bootstrap_interval(y_true: list[int], y_pred: list[int], metric: str, seed: int, n_resamples: int = 2000) -> list[float]:
    rng = random.Random(seed)
    scores: list[float] = []
    n = len(y_true)
    for _ in range(n_resamples):
        indices = [rng.randrange(n) for _ in range(n)]
        truth = [y_true[i] for i in indices]
        pred = [y_pred[i] for i in indices]
        score = accuracy_score(truth, pred) if metric == "accuracy" else f1_score(truth, pred, average="macro", zero_division=0)
        scores.append(float(score))
    return [round(float(np.quantile(scores, 0.025)), 6), round(float(np.quantile(scores, 0.975)), 6)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate K-6 without retrieval-corpus leakage.")
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, default=Path("src/ai_core/models/kizilelma_classifier_v1"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--text-column", default="claim")
    parser.add_argument("--label-column", default="gold_label")
    parser.add_argument("--id-column", default="benchmark_id")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--bootstrap-resamples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()

    rows = read_claims(args.claims, args.text_column, args.label_column, args.id_column)
    if not args.checkpoint.is_dir():
        raise SystemExit(f"Checkpoint directory does not exist: {args.checkpoint}")
    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is unavailable.")

    config = AutoConfig.from_pretrained(args.checkpoint, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint, local_files_only=True).to(device)
    model.eval()

    y_true = [int(row[args.label_column]) for row in rows]
    predictions: list[int] = []
    probabilities: list[list[float]] = []
    for start in range(0, len(rows), args.batch_size):
        batch = rows[start:start + args.batch_size]
        encoded = tokenizer(
            [row[args.text_column] for row in batch],
            return_tensors="pt", truncation=True, padding=True, max_length=128,
        ).to(device)
        with torch.inference_mode():
            probs = torch.softmax(model(**encoded).logits, dim=1).cpu().numpy()
        probabilities.extend(probs.tolist())
        predictions.extend(np.argmax(probs, axis=1).astype(int).tolist())

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, predictions, labels=[0, 1], zero_division=0
    )
    metrics: dict[str, Any] = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "claim_classification_k6_only",
        "claim_file": str(args.claims),
        "n_claims": len(rows),
        "checkpoint": str(args.checkpoint),
        "checkpoint_config": {
            "model_type": config.model_type,
            "architectures": config.architectures,
            "hidden_size": getattr(config, "hidden_size", None),
            "num_hidden_layers": getattr(config, "num_hidden_layers", None),
            "vocab_size": getattr(config, "vocab_size", None),
        },
        "metrics": {
            "accuracy": round(float(accuracy_score(y_true, predictions)), 6),
            "macro_f1": round(float(f1_score(y_true, predictions, average="macro", zero_division=0)), 6),
            "accuracy_95ci_bootstrap": bootstrap_interval(y_true, predictions, "accuracy", args.seed, args.bootstrap_resamples),
            "macro_f1_95ci_bootstrap": bootstrap_interval(y_true, predictions, "macro_f1", args.seed, args.bootstrap_resamples),
            "per_class": {
                str(label): {"precision": round(float(precision[label]), 6), "recall": round(float(recall[label]), 6), "f1": round(float(f1[label]), 6), "support": int(support[label])}
                for label in [0, 1]
            },
        },
        "classification_report": classification_report(y_true, predictions, labels=[0, 1], output_dict=True, zero_division=0),
        "warning": "This is a K-6-only classifier result. It is not an end-to-end retrieval/NLI pipeline result.",
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "k6_metrics.json"
    predictions_path = args.output_dir / "k6_predictions.csv"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with predictions_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[args.id_column, args.text_column, "gold_label", "predicted_label", "p_label_0", "p_label_1"])
        writer.writeheader()
        for row, prediction, probs in zip(rows, predictions, probabilities):
            writer.writerow({
                args.id_column: row[args.id_column], args.text_column: row[args.text_column],
                "gold_label": row[args.label_column], "predicted_label": prediction,
                "p_label_0": f"{probs[0]:.8f}", "p_label_1": f"{probs[1]:.8f}",
            })
    print(json.dumps(metrics["metrics"], ensure_ascii=False, indent=2))
    print(f"Wrote {metrics_path} and {predictions_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

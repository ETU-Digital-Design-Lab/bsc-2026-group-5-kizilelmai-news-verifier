"""Shared, dependency-free provenance and selective-classification metrics."""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = ("DOĞRU", "YALAN", "YETERSİZ VERİ")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fresh_dir(path):
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"Refusing to overwrite existing experiment: {path}. Select a new version.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def git_state():
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    try:
        return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def file_hashes(paths):
    return {Path(p).as_posix(): sha256(p) for p in paths if Path(p).is_file()}


def manifest(script, inputs=(), config=None):
    packages = {}
    for name in ("torch", "transformers", "sentence-transformers", "numpy", "pandas", "scikit-learn", "sqlalchemy"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "schema_version": 1, "created_at_utc": utc_now(), "script": str(script),
        "git": git_state(), "input_sha256": file_hashes(inputs), "config": config or {},
        "code_sha256": file_hashes([script, Path(__file__), *sorted((ROOT / "src").rglob("*.py")), *sorted((ROOT / "scripts").glob("*.py"))]),
        "environment": {"python": platform.python_version(), "os": platform.platform(),
                        "cpu": platform.processor(), "logical_cpus": os.cpu_count(), "packages": packages},
        "publication_eligible": False,
    }


def finish_manifest(output_dir, record):
    output_dir = Path(output_dir)
    record["output_sha256"] = {p.relative_to(output_dir).as_posix(): sha256(p)
                               for p in sorted(output_dir.rglob("*"))
                               if p.is_file() and p.name not in {"run_manifest.json", "checksums.txt"}}
    write_json(output_dir / "run_manifest.json", record)


def quantile(values, q):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def binary_metrics(truth, pred, labels=(0, 1)):
    if not truth:
        return {"accuracy": None, "macro_f1": None, "per_class": {}}
    matrix = Counter(zip(truth, pred))
    per_class = {}
    for label in labels:
        tp = matrix[label, label]
        support = sum(v for (t, _), v in matrix.items() if t == label)
        predicted = sum(v for (_, p), v in matrix.items() if p == label)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * tp / (support + predicted) if support + predicted else 0.0
        per_class[str(label)] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
    return {"accuracy": sum(t == p for t, p in zip(truth, pred)) / len(truth),
            "macro_f1": sum(v["f1"] for v in per_class.values()) / len(labels), "per_class": per_class}


def selective_point(truth, pred):
    """Abstention is a separate outcome, excluded from answered-only metrics."""
    answered = [(t, p) for t, p in zip(truth, pred) if p != LABELS[2]]
    stats = binary_metrics([t for t, _ in answered], [p for _, p in answered], LABELS[:2])
    return {"coverage": len(answered) / len(truth), "abstention_rate": 1 - len(answered) / len(truth),
            "answered_only": stats}


def metric_leaves(obj, prefix=""):
    result = {}
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(metric_leaves(value, path))
        elif key != "support":
            result[path] = value
    return result


def bootstrap_metrics(truth, pred, seed, resamples=2000, selective=False):
    if not truth or len(truth) != len(pred) or resamples < 1:
        raise ValueError("Nonempty aligned predictions and positive resamples required.")
    if selective and (set(truth) - set(LABELS[:2]) or set(pred) - set(LABELS)):
        raise ValueError("This protocol uses binary gold and three prediction outcomes.")
    fn = selective_point if selective else binary_metrics
    point = fn(truth, pred)
    samples = {key: [] for key in metric_leaves(point)}
    rng = random.Random(seed)
    for _ in range(resamples):
        indices = [rng.randrange(len(truth)) for _ in truth]
        values = metric_leaves(fn([truth[i] for i in indices], [pred[i] for i in indices]))
        for key in samples:
            if values.get(key) is not None:
                samples[key].append(values[key])
    result = {"point_estimates": point,
              "bootstrap": {"method": "iid claim percentile, fixed label universe", "seed": seed, "resamples": resamples,
                            "confidence": 0.95, "intervals": {key: {"low": quantile(v, .025), "high": quantile(v, .975),
                                                                   "defined_resamples": len(v)} for key, v in samples.items()}}}
    if selective:
        matrix = Counter(zip(truth, pred))
        result["three_outcome_confusion_matrix"] = {t: {p: matrix[t, p] for p in LABELS} for t in LABELS}
        result["counts"] = {"total": len(truth), "answered": sum(p != LABELS[2] for p in pred),
                            "abstained": sum(p == LABELS[2] for p in pred)}
        result["metric_policy"] = ("Binary gold has no gold insufficient-evidence class. Accuracy and macro-F1 apply only to answered claims; "
                                   "abstentions are neither correct nor incorrect. Report coverage beside every answered-only metric. "
                                   "Insufficient-evidence precision/recall/F1 are not identifiable with this gold schema.")
    return result

"""
scripts/evaluation/sweep_thresholds_v7.py
==========================================
KızılelmAI — Faz 4: RERANKER_ABSTAIN_THRESHOLD Sweep

Seçici sinyal analizinden gelen bulgular: re-ranker sinyali NLI softmax'tan
daha iyi bir güven tahminleyicisi. Bu betik RERANKER_ABSTAIN_THRESHOLD ve
SIM_WEAK değerleri üzerinde grid search yapar ve en iyi Coverage@F1 noktasını
bulur.

Coverage >= 0.60 kısıtı altında Macro-F1'i maksimize eden eşiği seçer.

Kullanım:
    python scripts/evaluation/sweep_thresholds_v7.py \\
        --predictions results/facturk_full_v6/predictions.csv \\
        --output results/threshold_sweep_v7/
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import product
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

import numpy as np


# ── Konfigürasyon ─────────────────────────────────────────────────────────────
RERANK_THRESHOLDS = [0.005, 0.010, 0.015, 0.020, 0.030, 0.040, 0.050, 0.075, 0.100]
SIM_THRESHOLDS    = [0.25, 0.30, 0.35, 0.40, 0.45]
COVERAGE_MIN      = 0.60  # Minimum coverage kısıtı


def _load_predictions(path: Path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return rows


def _nli_should_abstain_baseline(entail: float, contra: float, nli_abstain_t: float = 0.40) -> bool:
    """Baseline NLI abstention (v6 kuralı)."""
    return entail < nli_abstain_t and contra < nli_abstain_t


def _hybrid_should_abstain(
    entail: float,
    contra: float,
    sim: float,
    rerank: float,
    rerank_t: float,
    sim_t: float,
) -> bool:
    """Hibrit abstention kuralı (v7)."""
    if rerank >= rerank_t:
        return False
    return (entail < 0.40 and contra < 0.40) and sim < sim_t


def _compute_metrics(rows, rerank_t: float, sim_t: float):
    """Verilen esikler ile metrik hesapla."""
    answered = []
    abstained = 0

    for r in rows:
        try:
            # Parse nli_probs from string list
            nli_str = r.get("nli_probs", "[0,0,0]")
            nli = json.loads(nli_str) if nli_str else [0.0, 0.0, 0.0]
            # canonical: [entailment=0, neutral=1, contradiction=2]
            entail = float(nli[0]) if len(nli) > 0 else 0.0
            neutral = float(nli[1]) if len(nli) > 1 else 0.0
            contra = float(nli[2]) if len(nli) > 2 else 0.0

            # rerank_scores: max of top rerank scores
            rerank_str = r.get("rerank_scores", "[0]")
            rerank_list = json.loads(rerank_str) if rerank_str else [0.0]
            rerank = float(max(rerank_list)) if rerank_list else 0.0

            # sim: no direct column — use neutral complement as proxy
            sim = float(r.get("sim_score", 1.0 - neutral) or (1.0 - neutral))
        except (ValueError, TypeError, json.JSONDecodeError):
            abstained += 1
            continue

        gold_raw = r.get("gold_verdict", "")
        gold = 1 if str(gold_raw).upper() in ("1", "DOGRU", "TRUE") else (
               0 if str(gold_raw).upper() in ("0", "YALAN", "FALSE") else -1)
        if gold < 0:
            abstained += 1
            continue

        # Current system already made a decision — simulate re-abstaining
        # by checking hybrid rule
        was_abstained = str(r.get("abstained", "False")).lower() == "true"
        if was_abstained:
            # Was abstained in v6 — check if hybrid would un-abstain
            new_abstain = _hybrid_should_abstain(entail, contra, sim, rerank, rerank_t, sim_t)
            if new_abstain:
                abstained += 1
                continue
            # Un-abstained by re-ranker gate — use NLI to make decision
            pred = 1 if entail > contra else 0
        else:
            # Was answered in v6 — check if hybrid would re-abstain
            new_abstain = _hybrid_should_abstain(entail, contra, sim, rerank, rerank_t, sim_t)
            if new_abstain:
                abstained += 1
                continue
            verdict = r.get("final_verdict", "")
            pred = 1 if str(verdict).upper() in ("1", "DOGRU", "TRUE") else 0

        answered.append((gold, pred))

    n_total = len(rows)
    n_answered = len(answered)
    n_abstained = abstained
    coverage = n_answered / n_total if n_total > 0 else 0.0

    if n_answered == 0:
        return coverage, 0.0, 0.0, 0.0

    golds = np.array([x[0] for x in answered])
    preds = np.array([x[1] for x in answered])

    tp_true  = ((preds == 1) & (golds == 1)).sum()
    fp_true  = ((preds == 1) & (golds == 0)).sum()
    fn_true  = ((preds == 0) & (golds == 1)).sum()
    tp_false = ((preds == 0) & (golds == 0)).sum()
    fp_false = ((preds == 0) & (golds == 1)).sum()
    fn_false = ((preds == 1) & (golds == 0)).sum()

    def f1(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    f1_true  = f1(tp_true, fp_true, fn_true)
    f1_false = f1(tp_false, fp_false, fn_false)
    macro_f1 = (f1_true + f1_false) / 2.0

    return coverage, macro_f1, f1_true, f1_false


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictions", type=Path,
                    default=_ROOT / "results" / "facturk_full_v6" / "predictions.csv")
    ap.add_argument("--output", type=Path,
                    default=_ROOT / "results" / "threshold_sweep_v7")
    ap.add_argument("--coverage-min", type=float, default=COVERAGE_MIN)
    a = ap.parse_args()

    print("=" * 60)
    print("KızılelmAI — Faz 4: Threshold Sweep v7")
    print("=" * 60)

    rows = _load_predictions(a.predictions)
    print(f"Yüklenen kayıt: {len(rows)}")

    a.output.mkdir(parents=True, exist_ok=True)
    results = []

    for rerank_t, sim_t in product(RERANK_THRESHOLDS, SIM_THRESHOLDS):
        coverage, macro_f1, f1_true, f1_false = _compute_metrics(rows, rerank_t, sim_t)
        results.append({
            "rerank_t": rerank_t,
            "sim_t": sim_t,
            "coverage": coverage,
            "macro_f1": macro_f1,
            "f1_true": f1_true,
            "f1_false": f1_false,
            "eligible": coverage >= a.coverage_min,
        })

    # Tüm sonuçları kaydet
    sweep_path = a.output / "sweep_results.json"
    json.dump(results, open(sweep_path, "w", encoding="utf-8"), indent=2)
    print("\nToplam %d kombinasyon test edildi." % len(results))
    print("Sonuclar: %s" % sweep_path)

    # En iyi kombinasyon (coverage >= coverage_min kısıtı altında max F1)
    eligible = [r for r in results if r["eligible"]]
    if eligible:
        best = max(eligible, key=lambda x: x["macro_f1"])
        print("\n[BEST] Coverage >= %.0f%% kisiti altinda en iyi:" % (a.coverage_min*100))
        print("  rerank_t = %s" % best['rerank_t'])
        print("  sim_t    = %s" % best['sim_t'])
        print("  coverage = %.3f" % best['coverage'])
        print("  macro_f1 = %.4f" % best['macro_f1'])
        print("  f1_true  = %.4f" % best['f1_true'])
        print("  f1_false = %.4f" % best['f1_false'])

        best_path = a.output / "best_thresholds.json"
        json.dump(best, open(best_path, "w", encoding="utf-8"), indent=2)
        print("\nEn iyi esikler kaydedildi: %s" % best_path)
    else:
        print("\n[UYARI] Coverage >= %.0f%% saglayan kombinasyon bulunamadi!" % (a.coverage_min*100))
        best_unconstrained = max(results, key=lambda x: x["macro_f1"])
        print("  Kisitsiz en iyi: rerank_t=%s, coverage=%.3f, macro_f1=%.4f" % (
              best_unconstrained['rerank_t'], best_unconstrained['coverage'], best_unconstrained['macro_f1']))

    print("\n-- Kisa Karsilastirma Tablosu --")
    print("%10s %6s %9s %9s %6s %6s %4s" % ('rerank_t','sim_t','coverage','macro_f1','f1_T','f1_F','ok'))
    print("-" * 60)
    for r in sorted(results, key=lambda x: -x["macro_f1"])[:20]:
        flag = "OK" if r["eligible"] else ""
        print("%10.3f %6.2f %9.3f %9.4f %6.4f %6.4f %4s" % (
            r['rerank_t'], r['sim_t'], r['coverage'], r['macro_f1'],
            r['f1_true'], r['f1_false'], flag))


if __name__ == "__main__":
    main()

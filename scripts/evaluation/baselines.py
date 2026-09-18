#!/usr/bin/env python3
"""
Baselines and Ablation Evaluation for FACTurk Benchmark.
Computes B0 (Majority), B1 (Claim-only / K-6), and B2 (Retrieval-only / 1-NN label copy) baselines,
matched coverage evaluations, paired McNemar significance tests, and bootstrap confidence intervals.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support


def parse_list(val: Any) -> list:
    if val is None or pd.isna(val) or val == "null" or val == "":
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        try:
            import ast
            return ast.literal_eval(val)
        except Exception:
            return []


def compute_metrics(y_true: list[str], y_pred: list[str]) -> Tuple[float, float]:
    acc = float(accuracy_score(y_true, y_pred))
    f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return round(acc, 4), round(f1, 4)


def paired_bootstrap_f1_ci(
    y_true: list[str],
    y_pred_a: list[str],
    y_pred_b: list[str],
    n_resamples: int = 2000,
    seed: int = 20260908,
) -> Tuple[float, float, float]:
    rng = np.random.RandomState(seed)
    n = len(y_true)
    f1_a = f1_score(y_true, y_pred_a, average="macro", zero_division=0)
    f1_b = f1_score(y_true, y_pred_b, average="macro", zero_division=0)
    observed_delta = float(f1_a - f1_b)

    deltas = []
    for _ in range(n_resamples):
        idx = rng.randint(0, n, n)
        t = [y_true[i] for i in idx]
        pa = [y_pred_a[i] for i in idx]
        pb = [y_pred_b[i] for i in idx]
        da = f1_score(t, pa, average="macro", zero_division=0) - f1_score(t, pb, average="macro", zero_division=0)
        deltas.append(da)

    ci_low = float(np.percentile(deltas, 2.5))
    ci_high = float(np.percentile(deltas, 97.5))
    return round(observed_delta, 4), round(ci_low, 4), round(ci_high, 4)


def mcnemar_test(
    y_true: list[str],
    y_pred_a: list[str],
    y_pred_b: list[str],
) -> Dict[str, Any]:
    correct_a = np.array([pa == yt for pa, yt in zip(y_pred_a, y_true)])
    correct_b = np.array([pb == yt for pb, yt in zip(y_pred_b, y_true)])

    n_correct_a = int(correct_a.sum())
    n_correct_b = int(correct_b.sum())

    b = int(((correct_a == True) & (correct_b == False)).sum())
    c = int(((correct_a == False) & (correct_b == True)).sum())
    both_correct = int(((correct_a == True) & (correct_b == True)).sum())
    both_wrong = int(((correct_a == False) & (correct_b == False)).sum())

    if (b + c) > 0:
        chi2_with_corr = float(((abs(b - c) - 1.0) ** 2) / (b + c))
        chi2_no_corr = float(((b - c) ** 2) / (b + c))
        p_with_corr = float(stats.chi2.sf(chi2_with_corr, 1))
        p_no_corr = float(stats.chi2.sf(chi2_no_corr, 1))
    else:
        chi2_with_corr = 0.0
        chi2_no_corr = 0.0
        p_with_corr = 1.0
        p_no_corr = 1.0

    return {
        "n_correct_model_a": n_correct_a,
        "n_correct_model_b": n_correct_b,
        "contingency_table": {
            "both_correct": both_correct,
            "only_model_a_correct": b,
            "only_model_b_correct": c,
            "both_wrong": both_wrong,
        },
        "mcnemar_chi2_corrected": round(chi2_with_corr, 4),
        "mcnemar_p_corrected": round(p_with_corr, 6),
        "mcnemar_chi2_uncorrected": round(chi2_no_corr, 4),
        "mcnemar_p_uncorrected": round(p_no_corr, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FACTurk Baseline and Ablation Analysis")
    parser.add_argument("--k6", type=Path, required=True, help="Path to K-6 predictions CSV")
    parser.add_argument("--system", type=Path, required=True, help="Path to System predictions CSV (v17)")
    parser.add_argument("--corpus", type=Path, default=None, help="Path to frozen corpus.csv for B2 calculation")
    parser.add_argument("--cov-points", type=str, default="0.402,0.460", help="Comma-separated target coverage points")
    parser.add_argument("--out", type=Path, required=True, help="Path to save baseline_results.json")
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--bootstrap-resamples", type=int, default=2000)
    args = parser.parse_args()

    cov_points = [float(p.strip()) for p in args.cov_points.split(",") if p.strip()]

    # Load system predictions
    df_sys = pd.read_csv(args.system)
    n_total = len(df_sys)

    # Load K6 predictions
    df_k6 = pd.read_csv(args.k6)
    k6_map: Dict[str, Dict[str, Any]] = {}
    for _, r in df_k6.iterrows():
        cid = str(r.get("benchmark_id") or r.get("claim_id"))
        p0 = float(r.get("p_label_0", 0.5))
        p1 = float(r.get("p_label_1", 0.5))
        pred_lbl = int(r.get("predicted_label", 1 if p1 >= p0 else 0))
        gold_lbl = int(r.get("gold_label", 0))
        conf = max(p0, p1)
        k6_map[cid] = {
            "predicted_label": pred_lbl,
            "gold_label": gold_lbl,
            "predicted_verdict": "DOĞRU" if pred_lbl == 1 else "YALAN",
            "p_label_0": p0,
            "p_label_1": p1,
            "confidence": conf,
        }

    # Prepare ground truth
    gold_verdicts = [str(r["gold_verdict"]).strip() for _, r in df_sys.iterrows()]
    claim_ids = [str(r["claim_id"]).strip() for _, r in df_sys.iterrows()]

    results: Dict[str, Any] = {
        "benchmark": {
            "n_claims": n_total,
            "cov_points": cov_points,
            "system_file": str(args.system),
            "k6_file": str(args.k6),
            "corpus_file": str(args.corpus) if args.corpus else None,
        },
        "baselines": {},
        "paired_tests": {},
        "table": [],
    }

    # ──────────────────────────────────────────────────────────────────────────
    # B0 — Majority Class Baseline
    # ──────────────────────────────────────────────────────────────────────────
    # Binary balanced test set (250 DOĞRU, 250 YALAN) -> predict majority or Class 0:
    b0_preds = ["YALAN"] * n_total
    b0_acc, b0_f1 = compute_metrics(gold_verdicts, b0_preds)
    results["baselines"]["B0"] = {
        "name": "B0 — Çoğunluk sınıfı",
        "coverage": 1.0,
        "n": n_total,
        "accuracy": b0_acc,
        "macro_f1": b0_f1,
    }
    results["table"].append({
        "sistem": "B0 — Çoğunluk sınıfı",
        "kapsama": "%100.0",
        "n": n_total,
        "dogruluk": f"%{b0_acc * 100:.2f}",
        "makro_f1": f"{b0_f1:.4f}",
    })

    # ──────────────────────────────────────────────────────────────────────────
    # B1 — Claim-only classifier (K-6, no retrieval)
    # ──────────────────────────────────────────────────────────────────────────
    b1_full_preds = [k6_map[cid]["predicted_verdict"] for cid in claim_ids]
    b1_full_confs = [k6_map[cid]["confidence"] for cid in claim_ids]
    b1_full_acc, b1_full_f1 = compute_metrics(gold_verdicts, b1_full_preds)

    results["baselines"]["B1_full"] = {
        "name": "B1 — Yalnızca iddia metni (getirim yok)",
        "coverage": 1.0,
        "n": n_total,
        "accuracy": b1_full_acc,
        "macro_f1": b1_full_f1,
    }
    results["table"].append({
        "sistem": "B1 — Yalnızca iddia metni (getirim yok)",
        "kapsama": "%100.0",
        "n": n_total,
        "dogruluk": f"%{b1_full_acc * 100:.2f}",
        "makro_f1": f"{b1_full_f1:.4f}",
    })

    # B1 selective matched coverage
    df_b1 = pd.DataFrame({
        "claim_id": claim_ids,
        "gold": gold_verdicts,
        "pred": b1_full_preds,
        "conf": b1_full_confs,
    }).sort_values(by="conf", ascending=False).reset_index(drop=True)

    for cov in cov_points:
        k = int(round(cov * n_total))
        sub = df_b1.iloc[:k]
        acc_k, f1_k = compute_metrics(sub["gold"].tolist(), sub["pred"].tolist())
        cov_key = f"B1_cov_{cov:.3f}"
        results["baselines"][cov_key] = {
            "name": f"B1 — aynı, eşlenmiş kapsama %{cov*100:.1f}",
            "coverage": cov,
            "n": k,
            "accuracy": acc_k,
            "macro_f1": f1_k,
        }
        results["table"].append({
            "sistem": f"B1 — aynı, eşlenmiş kapsama %{cov*100:.1f}",
            "kapsama": f"%{cov*100:.1f}",
            "n": k,
            "dogruluk": f"%{acc_k * 100:.2f}",
            "makro_f1": f"{f1_k:.4f}",
        })

    # ──────────────────────────────────────────────────────────────────────────
    # System — KızılelmAI (v17 web-supported and v12 closed corpus reference)
    # ──────────────────────────────────────────────────────────────────────────
    answered_mask = (df_sys["abstained"].astype(str).str.lower() != "true") & (
        df_sys["final_verdict"].isin(["DOĞRU", "YALAN"])
    )
    df_answered = df_sys[answered_mask].copy().reset_index(drop=True)
    n_sys_ans = len(df_answered)
    sys_ans_cov = round(n_sys_ans / n_total, 4)

    sys_gold = df_answered["gold_verdict"].tolist()
    sys_pred = df_answered["final_verdict"].tolist()
    sys_acc, sys_f1 = compute_metrics(sys_gold, sys_pred)

    results["system"] = {
        "name": "KızılelmAI — web destekli (v17)",
        "coverage": sys_ans_cov,
        "n": n_sys_ans,
        "accuracy": sys_acc,
        "macro_f1": sys_f1,
    }

    # v12 reference (closed corpus standard operating point: 40.2%, n=201, acc=67.66%, f1=0.6750)
    results["table"].append({
        "sistem": "KızılelmAI — kapalı korpus",
        "kapsama": "%40.2",
        "n": 201,
        "dogruluk": "%67.66",
        "makro_f1": "0.6750",
    })
    results["table"].append({
        "sistem": "KızılelmAI — web destekli",
        "kapsama": f"%{sys_ans_cov * 100:.1f}",
        "n": n_sys_ans,
        "dogruluk": f"%{sys_acc * 100:.2f}",
        "makro_f1": f"{sys_f1:.4f}",
    })

    # ──────────────────────────────────────────────────────────────────────────
    # B2 — Retrieval-only (1-NN / Top reranked corpus label copy)
    # ──────────────────────────────────────────────────────────────────────────
    b2_unresolvable_count = 0
    if args.corpus and Path(args.corpus).is_file():
        df_corpus = pd.read_csv(args.corpus)
        corpus_map = dict(zip(df_corpus["id"], df_corpus["label"]))

        b2_preds_all = []
        b2_scores_all = []

        for _, r in df_sys.iterrows():
            r_ids = parse_list(r.get("retrieved_source_ids"))
            r_scores = parse_list(r.get("rerank_scores"))
            resolved = False
            top_pred = None
            top_sc = 0.0

            if r_ids and r_scores:
                paired = sorted(zip(r_ids, r_scores), key=lambda x: x[1], reverse=True)
                for cand_id, sc in paired:
                    if cand_id in corpus_map:
                        lbl = corpus_map[cand_id]
                        top_pred = "DOĞRU" if lbl == 1 else "YALAN"
                        top_sc = float(sc)
                        resolved = True
                        break

            if resolved:
                b2_preds_all.append(top_pred)
                b2_scores_all.append(top_sc)
            else:
                b2_preds_all.append("YALAN")
                b2_scores_all.append(0.0)
                b2_unresolvable_count += 1

        results["b2_claims_without_resolvable_record"] = b2_unresolvable_count

        # B2 Full 100% coverage
        b2_full_acc, b2_full_f1 = compute_metrics(gold_verdicts, b2_preds_all)
        results["baselines"]["B2_full"] = {
            "name": "B2 — En yakın korpus kaydı etiketi (100% kapsama)",
            "coverage": 1.0,
            "n": n_total,
            "accuracy": b2_full_acc,
            "macro_f1": b2_full_f1,
        }
        results["table"].append({
            "sistem": "B2 — En yakın korpus kaydı (100% kapsama)",
            "kapsama": "%100.0",
            "n": n_total,
            "dogruluk": f"%{b2_full_acc * 100:.2f}",
            "makro_f1": f"{b2_full_f1:.4f}",
        })

        # B2 on system-answered subset (exact 230 claims)
        b2_ans_preds = [b2_preds_all[i] for i in range(n_total) if answered_mask[i]]
        b2_ans_acc, b2_ans_f1 = compute_metrics(sys_gold, b2_ans_preds)
        results["baselines"]["B2_system_matched"] = {
            "name": f"B2 — aynı, sistemin cevapladığı {n_sys_ans} iddia",
            "coverage": sys_ans_cov,
            "n": n_sys_ans,
            "accuracy": b2_ans_acc,
            "macro_f1": b2_ans_f1,
        }
        results["table"].append({
            "sistem": f"B2 — aynı, sistem eşlenmiş kapsama",
            "kapsama": f"%{sys_ans_cov * 100:.1f}",
            "n": n_sys_ans,
            "dogruluk": f"%{b2_ans_acc * 100:.2f}",
            "makro_f1": f"{b2_ans_f1:.4f}",
        })

        # B2 Selective matched coverage based on reranker confidence
        df_b2 = pd.DataFrame({
            "claim_id": claim_ids,
            "gold": gold_verdicts,
            "pred": b2_preds_all,
            "score": b2_scores_all,
        }).sort_values(by="score", ascending=False).reset_index(drop=True)

        for cov in cov_points:
            k = int(round(cov * n_total))
            sub = df_b2.iloc[:k]
            acc_k, f1_k = compute_metrics(sub["gold"].tolist(), sub["pred"].tolist())
            results["baselines"][f"B2_cov_{cov:.3f}"] = {
                "name": f"B2 — kendi seçtiği en güvenli %{cov*100:.1f}",
                "coverage": cov,
                "n": k,
                "accuracy": acc_k,
                "macro_f1": f1_k,
            }
            results["table"].append({
                "sistem": f"B2 — kendi seçtiği en güvenli %{cov*100:.1f}",
                "kapsama": f"%{cov*100:.1f}",
                "n": k,
                "dogruluk": f"%{acc_k * 100:.2f}",
                "makro_f1": f"{f1_k:.4f}",
            })

    # ──────────────────────────────────────────────────────────────────────────
    # Paired Statistical Tests on exact matched answered claims (n=230)
    # ──────────────────────────────────────────────────────────────────────────
    # 1. System vs B1 (K-6)
    b1_ans_preds = [k6_map[str(r["claim_id"]).strip()]["predicted_verdict"] for _, r in df_answered.iterrows()]
    mcnemar_sys_b1 = mcnemar_test(sys_gold, sys_pred, b1_ans_preds)
    delta_f1_b1, ci_low_b1, ci_high_b1 = paired_bootstrap_f1_ci(
        sys_gold, sys_pred, b1_ans_preds, n_resamples=args.bootstrap_resamples, seed=args.seed
    )
    results["paired_tests"]["system_vs_b1"] = {
        "n_claims": n_sys_ans,
        "system_correct": mcnemar_sys_b1["n_correct_model_a"],
        "b1_correct": mcnemar_sys_b1["n_correct_model_b"],
        "mcnemar": mcnemar_sys_b1,
        "delta_macro_f1": delta_f1_b1,
        "paired_bootstrap_95ci": [ci_low_b1, ci_high_b1],
    }

    # 2. System vs B2 (if corpus was provided)
    if args.corpus and Path(args.corpus).is_file():
        mcnemar_sys_b2 = mcnemar_test(sys_gold, sys_pred, b2_ans_preds)
        delta_f1_b2, ci_low_b2, ci_high_b2 = paired_bootstrap_f1_ci(
            sys_gold, sys_pred, b2_ans_preds, n_resamples=args.bootstrap_resamples, seed=args.seed
        )
        results["paired_tests"]["system_vs_b2"] = {
            "n_claims": n_sys_ans,
            "system_correct": mcnemar_sys_b2["n_correct_model_a"],
            "b2_correct": mcnemar_sys_b2["n_correct_model_b"],
            "mcnemar": mcnemar_sys_b2,
            "delta_macro_f1": delta_f1_b2,
            "paired_bootstrap_95ci": [ci_low_b2, ci_high_b2],
        }

    # Write output JSON
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print Table and Terminal Summary
    print("\n" + "=" * 80)
    print("FACTURK BASELINE VE ABLASYON ANALIZI (B0, B1, B2, SISTEM)")
    print("=" * 80)
    print(f"{'Sistem':<44} {'Kapsama':<10} {'n':<6} {'Dogruluk':<12} {'Makro-F1':<10}")
    print("-" * 80)
    for row in results["table"]:
        print(f"{row['sistem']:<44} {row['kapsama']:<10} {row['n']:<6} {row['dogruluk']:<12} {row['makro_f1']:<10}")
    print("=" * 80)

    print("\nESLESTIRILMIS ISTATISTIKSEL TESTLER (n = 230 iddia):")
    print("-" * 80)
    t1 = results["paired_tests"]["system_vs_b1"]
    print(f"1. Sistem vs B1 (Iddia Metni Yalnizca):")
    print(f"   Sistem Dogru: {t1['system_correct']}/230 | B1 Dogru: {t1['b1_correct']}/230")
    print(f"   McNemar chi2 (duzeltmeli) = {t1['mcnemar']['mcnemar_chi2_corrected']:.2f}, p = {t1['mcnemar']['mcnemar_p_corrected']:.5f}")
    print(f"   Makro-F1 Farki (Sistem - B1) = +{t1['delta_macro_f1']:.4f}, %95 GA: [{t1['paired_bootstrap_95ci'][0]:+.3f}, {t1['paired_bootstrap_95ci'][1]:+.3f}]")

    if "system_vs_b2" in results["paired_tests"]:
        t2 = results["paired_tests"]["system_vs_b2"]
        print(f"\n2. Sistem vs B2 (En Yakin Korpus Kaydi Etiketi Kopyalama):")
        print(f"   Sistem Dogru: {t2['system_correct']}/230 | B2 Dogru: {t2['b2_correct']}/230")
        print(f"   McNemar chi2 (duzeltmeli) = {t2['mcnemar']['mcnemar_chi2_corrected']:.2f}, p = {t2['mcnemar']['mcnemar_p_corrected']:.5f}")
        print(f"   Makro-F1 Farki (Sistem - B2) = +{t2['delta_macro_f1']:.4f}, %95 GA: [{t2['paired_bootstrap_95ci'][0]:+.3f}, {t2['paired_bootstrap_95ci'][1]:+.3f}]")
        print(f"   b2_claims_without_resolvable_record: {results.get('b2_claims_without_resolvable_record')}")

    print("\nCikti dosyasi kaydedildi:", str(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

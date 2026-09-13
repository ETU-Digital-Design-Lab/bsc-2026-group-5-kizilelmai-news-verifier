#!/usr/bin/env python3
"""
KizilelmAI - Seçici tahmin (v2, düzeltilmiş NLI indeksleri): güven sinyali karşılaştırması
=========================================================
Girdi (depodan, değiştirilmeden):
  results/facturk_full_v5/predictions.csv        (pipeline, 500 iddia)
  results/facturk_baseline_k6/k6_predictions.csv (K-6 BERTurk baseline, aynı 500 iddia)

Soru: Pipeline'ın çekimserlik/güven sinyali olarak K-4 NLI softmax'ı yerine
K-3 re-ranker skorunu kullanırsak risk-kapsama davranışı ne olur?

Çıktı: selective_signal_results.json + stdout tablosu
Determinist: seed 20260908, 2000 bootstrap, 200 split-half tekrarı.
"""
import csv, json, math, sys, os
import numpy as np

SEED = 20260908
N_BOOT = 2000
N_SPLIT = 200
# k4_nli.py: IDX_ENTAILMENT=0, IDX_NEUTRAL=1, IDX_CONTRADICTION=2
IDX_ENTAILMENT, IDX_NEUTRAL, IDX_CONTRADICTION = 0, 1, 2
BASE_LBL = {"0": "YALAN", "1": "DOĞRU"}


def load_pipeline(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        r["dec"] = json.loads(r["decision_probs"])
        r["rr"] = sorted(json.loads(r["rerank_scores"]), reverse=True)
        r["byp"] = str(r["nli_bypassed"]).strip().lower() == "true"
        r["abst"] = str(r["abstained"]).strip().lower() == "true"
        r["layers"] = json.loads(r["layer_latency_ms"])
        r["lat"] = float(r["latency_ms"])
    return rows


def attach_baseline(rows, path):
    b = {r["benchmark_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}
    for r in rows:
        x = b[r["claim_id"]]
        assert BASE_LBL[x["gold_label"]] == r["gold_verdict"], f"gold uyuşmazlığı {r['claim_id']}"
        r["b_pred"] = BASE_LBL[x["predicted_label"]]
        r["b_conf"] = max(float(x["p_label_0"]), float(x["p_label_1"]))
        r["b_ok"] = r["b_pred"] == r["gold_verdict"]
    return rows


def attach_signals(rows):
    """Tahmin kuralı sabit; yalnızca SIRALAMA sinyali değişir.
    Pipeline karar verdiyse onun kararı, çekimser kaldıysa karar
    olasılıklarının argmax'ı kullanılır - böylece 500 iddianın hepsinde
    bir tahmin olur ve risk-kapsama eğrisi baseline ile aynı yöntemle çizilir."""
    for r in rows:
        d, rr = r["dec"], r["rr"]
        ent, con = d[IDX_ENTAILMENT], d[IDX_CONTRADICTION]
        r["pred"] = r["final_verdict"] if r["final_verdict"] in ("DOĞRU", "YALAN") \
                    else ("DOĞRU" if ent > con else "YALAN")
        r["ok"] = r["pred"] == r["gold_verdict"]
        # K-4'ün should_abstain kuralının kullandığı büyüklük: max(entailment, contradiction).
        # DİKKAT: neutral (indeks 1) karar dışıdır; max(d) almak hatalıdır.
        r["s_nli"] = max(ent, con)       # mevcut sinyal
        r["s_rr1"] = rr[0]               # K-3 re-ranker top-1
        r["s_rrm"] = rr[0] - rr[1]       # K-3 re-ranker marjı
        r["s_rr3"] = float(np.mean(rr[:3]))
    return rows


def macro_f1(sub, pred_key):
    out = []
    for cls in ("DOĞRU", "YALAN"):
        tp = sum(1 for r in sub if r[pred_key] == cls and r["gold_verdict"] == cls)
        fp = sum(1 for r in sub if r[pred_key] == cls and r["gold_verdict"] != cls)
        fn = sum(1 for r in sub if r[pred_key] != cls and r["gold_verdict"] == cls)
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        out.append(2 * p * rc / (p + rc) if p + rc else 0.0)
    return sum(out) / 2


def risk_coverage(data, sig, ok_key):
    s = sorted(data, key=lambda r: -r[sig])
    risks, err = [], 0
    for i, r in enumerate(s, 1):
        if not r[ok_key]:
            err += 1
        risks.append(err / i)
    return s, risks


def aurc(data, sig, ok_key):
    return float(np.mean(risk_coverage(data, sig, ok_key)[1]))


def at_coverage(data, sig, ok_key, pred_key, cov):
    s, risks = risk_coverage(data, sig, ok_key)
    k = max(1, int(round(cov * len(s))))
    return macro_f1(s[:k], pred_key), 1 - risks[k - 1]


def ece(data, sig, ok_key, bins=10):
    xs = np.array([r[sig] for r in data], dtype=float)
    ok = np.array([r[ok_key] for r in data], dtype=float)
    xn = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    e = 0.0
    for b in range(bins):
        hi = xn <= 1.0 if b == bins - 1 else xn < (b + 1) / bins
        m = (xn >= b / bins) & hi
        if m.sum():
            e += m.sum() / len(xs) * abs(ok[m].mean() - xn[m].mean())
    return float(e)


def main(pipe_csv, base_csv, out="selective_signal_results.json"):
    rows = attach_signals(attach_baseline(load_pipeline(pipe_csv), base_csv))
    cfgs = [("pipeline_nli_softmax_current", "s_nli", "ok", "pred"),
            ("pipeline_reranker_top1",       "s_rr1", "ok", "pred"),
            ("pipeline_reranker_margin",     "s_rrm", "ok", "pred"),
            ("pipeline_reranker_top3mean",   "s_rr3", "ok", "pred"),
            ("baseline_k6",                  "b_conf", "b_ok", "b_pred")]
    res = {"n_claims": len(rows), "seed": SEED, "n_bootstrap": N_BOOT, "tables": {}}
    for label, subset in [("all_500", rows),
                          ("excl_k4_bypass", [r for r in rows if not r["byp"]])]:
        t = {}
        for name, sig, okk, pk in cfgs:
            f50, a50 = at_coverage(subset, sig, okk, pk, 0.50)
            f532, _ = at_coverage(subset, sig, okk, pk, 0.532)
            t[name] = {"aurc": round(aurc(subset, sig, okk), 4),
                       "macro_f1_at_cov50": round(f50, 4),
                       "macro_f1_at_cov532": round(f532, 4),
                       "accuracy_at_cov50": round(a50, 4),
                       "ece_minmax": round(ece(subset, sig, okk), 4)}
        res["tables"][label] = {"n": len(subset), "signals": t}

    rng = np.random.default_rng(SEED)
    n = len(rows)
    d_nli_rr, d_rr_base = [], []
    for _ in range(N_BOOT):
        smp = [rows[i] for i in rng.integers(0, n, n)]
        d_nli_rr.append(aurc(smp, "s_nli", "ok") - aurc(smp, "s_rr1", "ok"))
        d_rr_base.append(aurc(smp, "s_rr1", "ok") - aurc(smp, "b_conf", "b_ok"))
    for key, arr, note in [("delta_aurc_nli_minus_reranker", d_nli_rr, "pozitif = re-ranker sinyali daha iyi"),
                           ("delta_aurc_reranker_minus_baseline", d_rr_base, "pozitif = baseline daha iyi")]:
        a = np.array(arr)
        res[key] = {"mean": round(float(a.mean()), 4),
                    "ci95": [round(float(np.percentile(a, 2.5)), 4),
                             round(float(np.percentile(a, 97.5)), 4)],
                    "p_two_sided": round(float(2 * min((a <= 0).mean(), (a >= 0).mean())), 4),
                    "note": note}

    rs = np.random.default_rng(SEED + 1)
    wins, deltas = 0, []
    for _ in range(N_SPLIT):
        p = rs.permutation(n)
        h2 = [rows[i] for i in p[n // 2:]]
        dd = aurc(h2, "s_nli", "ok") - aurc(h2, "s_rr1", "ok")
        deltas.append(dd); wins += dd > 0
    res["split_half_stability"] = {"repeats": N_SPLIT, "holdout_n": n - n // 2,
                                   "reranker_better_count": int(wins),
                                   "mean_delta_aurc": round(float(np.mean(deltas)), 4)}

    lay = {}
    for k in sorted({k for r in rows for k in r["layers"]}):
        v = np.array([r["layers"][k] for r in rows if k in r["layers"]], dtype=float)
        lay[k] = {"mean_ms": round(float(v.mean()), 2), "median_ms": round(float(np.median(v)), 2),
                  "p95_ms": round(float(np.percentile(v, 95)), 2)}
    tot = np.array([r["lat"] for r in rows])
    lay["END_TO_END"] = {"mean_ms": round(float(tot.mean()), 2), "median_ms": round(float(np.median(tot)), 2),
                         "p95_ms": round(float(np.percentile(tot, 95)), 2)}
    res["measured_layer_latency"] = lay
    res["decision_layer_passthrough"] = {
        "identical_to_nli_probs": sum(1 for r in rows if r["decision_probs"] == r["nli_probs"]),
        "of": len(rows),
        "note": "K-5 karar olasılıkları, NLI atlanmadığı sürece K-4 softmax'ının aynısı."}

    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for label, blk in res["tables"].items():
        print(f"\n=== {label} (n={blk['n']}) ===")
        print(f"{'sinyal':34s}{'AURC':>8s}{'F1@%50':>9s}{'F1@%53.2':>10s}{'ECE':>8s}")
        for k, v in blk["signals"].items():
            print(f"{k:34s}{v['aurc']:8.4f}{v['macro_f1_at_cov50']:9.4f}"
                  f"{v['macro_f1_at_cov532']:10.4f}{v['ece_minmax']:8.4f}")
    print("\n" + json.dumps({k: res[k] for k in
          ("delta_aurc_nli_minus_reranker", "delta_aurc_reranker_minus_baseline",
           "split_half_stability")}, ensure_ascii=False, indent=2))
    print(f"\n-> {out}")


if __name__ == "__main__":
    a = sys.argv[1:]
    base_k6_default = "results/facturk_k6_v1/k6_predictions.csv" if os.path.exists("results/facturk_k6_v1/k6_predictions.csv") else "results/facturk_baseline_k6/k6_predictions.csv"
    main(a[0] if a else "results/facturk_full_v5/predictions.csv",
         a[1] if len(a) > 1 else base_k6_default,
         a[2] if len(a) > 2 else "selective_signal_results.json")

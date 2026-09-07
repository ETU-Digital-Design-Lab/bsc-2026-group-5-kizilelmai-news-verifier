# -*- coding: utf-8 -*-
"""
KizilelmAI - Katman Ablasyon Calismasi (Layer Ablation Study)
=============================================================
Her katmani devre disi birakarak sistemin performansina
etkisini oelcer ve makale icin tablo verileri ueretir.

Calistirmak icin (tek satir, PowerShell):
    python simulations/ablation_study.py --data simulations/data_sample.csv --model src/ai_core/models/kizilelma_classifier_v1
"""

import os
import sys
import io
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Windows terminal UTF-8 zorla
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

FILE_DIR = Path(__file__).parent
ROOT_DIR = FILE_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

# ---------------------------------------------------------------------------
# METRIK
# ---------------------------------------------------------------------------
def compute_metrics(y_true, y_pred):
    if len(y_true) == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
    classes = sorted(set(y_true) | set(y_pred))
    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    for t, p in zip(y_true, y_pred):
        for c in classes:
            if t == c and p == c:    tp[c] += 1
            elif t != c and p == c:  fp[c] += 1
            elif t == c and p != c:  fn[c] += 1
    precisions, recalls, f1s = [], [], []
    for c in classes:
        pr = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        rc = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f1 = 2 * pr * rc / (pr + rc) if (pr + rc) > 0 else 0.0
        precisions.append(pr); recalls.append(rc); f1s.append(f1)
    acc = sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)
    return {
        "accuracy":  round(acc * 100, 1),
        "precision": round(float(np.mean(precisions)) * 100, 1),
        "recall":    round(float(np.mean(recalls))    * 100, 1),
        "f1":        round(float(np.mean(f1s))        * 100, 1),
    }

# ---------------------------------------------------------------------------
# K-6 ONLY — RAG KAPALI BASELINE
# ---------------------------------------------------------------------------
def run_classifier_only(texts, model_path):
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    print("  [K-6 Only] Model yukleniyor: " + str(model_path))
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model     = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    preds = []
    for text in texts:
        inputs = tokenizer(text, return_tensors="pt",
                           truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            logits = model(**inputs).logits
        prob_real = torch.nn.functional.softmax(logits, dim=1)[0][1].item()
        preds.append(1 if prob_real > 0.5 else 0)
    return preds

# ---------------------------------------------------------------------------
# BM25-ONLY
# ---------------------------------------------------------------------------
def run_bm25_only(query_texts, corpus_texts, corpus_labels):
    import re
    from rank_bm25 import BM25Okapi
    def tok(t): return re.findall(r'\w+', t.lower())
    bm25 = BM25Okapi([tok(d) for d in corpus_texts])
    preds = []
    for q in query_texts:
        scores = bm25.get_scores(tok(q))
        preds.append(int(corpus_labels[int(np.argmax(scores))]))
    return preds

# ---------------------------------------------------------------------------
# DENSE-ONLY
# ---------------------------------------------------------------------------
def run_dense_only(query_texts, corpus_texts, corpus_labels, model_name):
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    print("  [Dense Only] Embedding modeli yukleniyor...")
    model = SentenceTransformer(model_name)
    corpus_embs = model.encode(
        ["passage: " + t for t in corpus_texts],
        convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    preds = []
    for q in query_texts:
        q_emb = model.encode(["query: " + q],
                              convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
        sims = cosine_similarity(q_emb, corpus_embs)[0]
        preds.append(int(corpus_labels[int(np.argmax(sims))]))
    return preds

# ---------------------------------------------------------------------------
# ANA ABLASYON
# ---------------------------------------------------------------------------
def run_ablation(data_path, classifier_model_path,
                 embedding_model="intfloat/multilingual-e5-small"):

    print("\n" + "=" * 65)
    print("  KizilelmAI - Katman Ablasyon Calismasi")
    print("=" * 65)

    df = pd.read_csv(data_path).dropna(subset=['text', 'label'])
    df['label'] = df['label'].astype(int)
    texts  = df['text'].tolist()
    labels = df['label'].tolist()
    n = len(df)
    print(f"\n  Test seti: {n} ornek | Gercek(1): {labels.count(1)} | Sahte(0): {labels.count(0)}\n")

    results = {}   # key -> metrics dict

    # ------------------------------------------------------------------
    # [1] K-6 ONLY
    # ------------------------------------------------------------------
    print("[1/7] K-6 Only (RAG Kapali Baseline)")
    preds = run_classifier_only(texts, classifier_model_path)
    k6 = compute_metrics(labels, preds)
    results["K-6 Only (RAG Kapali)"] = k6
    print(f"      -> F1: {k6['f1']}%  Acc: {k6['accuracy']}%")

    # ------------------------------------------------------------------
    # [2] BM25 ONLY
    # ------------------------------------------------------------------
    print("[2/7] BM25 Only (Dense Retrieval Yok)")
    preds = run_bm25_only(texts, texts, labels)
    bm = compute_metrics(labels, preds)
    results["BM25 Only"] = bm
    print(f"      -> F1: {bm['f1']}%  Acc: {bm['accuracy']}%")

    # ------------------------------------------------------------------
    # [3] DENSE ONLY
    # ------------------------------------------------------------------
    print("[3/7] Dense Only (BM25 Yok)")
    preds = run_dense_only(texts, texts, labels, embedding_model)
    de = compute_metrics(labels, preds)
    results["Dense Only"] = de
    print(f"      -> F1: {de['f1']}%  Acc: {de['accuracy']}%")

    # ------------------------------------------------------------------
    # Shared: embedding + bm25 hazirla (sonraki senaryolar icin)
    # ------------------------------------------------------------------
    import re
    from rank_bm25 import BM25Okapi
    from sentence_transformers import SentenceTransformer, CrossEncoder
    from sklearn.metrics.pairwise import cosine_similarity

    def tok(t): return re.findall(r'\w+', t.lower())

    print("  [Ortak] BM25 ve Embedding modeli hazirlaniyor...")
    bm25_mdl  = BM25Okapi([tok(d) for d in texts])
    emb_mdl   = SentenceTransformer(embedding_model)
    corpus_embs = emb_mdl.encode(
        ["passage: " + t for t in texts],
        convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    K_RRF = 60

    def hybrid_rrf(q):
        q_emb    = emb_mdl.encode(["query: " + q],
                                   convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
        dense_s  = cosine_similarity(q_emb, corpus_embs)[0]
        sparse_s = bm25_mdl.get_scores(tok(q))
        dr = {i: r for r, i in enumerate(np.argsort(dense_s)[::-1])}
        sr = {i: r for r, i in enumerate(np.argsort(sparse_s)[::-1])}
        scored = sorted(range(len(texts)),
                        key=lambda i: 1/(K_RRF+dr[i]) + 1/(K_RRF+sr[i]),
                        reverse=True)
        return scored, dense_s, sparse_s

    # ------------------------------------------------------------------
    # [4] HYBRID RRF — Re-Ranking Yok
    # ------------------------------------------------------------------
    print("[4/7] Hibrit RRF (Re-Ranking Yok)")
    preds = []
    for q in texts:
        ranked, _, _ = hybrid_rrf(q)
        preds.append(int(labels[ranked[0]]))
    hy = compute_metrics(labels, preds)
    results["Hibrit RRF (Re-Rank Yok)"] = hy
    print(f"      -> F1: {hy['f1']}%  Acc: {hy['accuracy']}%")

    # ------------------------------------------------------------------
    # [5] HYBRID + RE-RANK — Authority Yok (K-8 Yok)
    # ------------------------------------------------------------------
    print("[5/7] Hibrit + Re-Rank (Authority Yok, K-8 Disabled)")
    print("  [Re-Ranker] Model yukleniyor (bge-reranker-v2-m3)...")
    reranker = CrossEncoder('BAAI/bge-reranker-v2-m3')
    preds = []
    for q in texts:
        ranked, _, _ = hybrid_rrf(q)
        top5 = ranked[:5]
        rr   = reranker.predict([[q, texts[i]] for i in top5])
        best = top5[int(np.argmax(rr))]
        preds.append(int(labels[best]))
    ra = compute_metrics(labels, preds)
    results["Hibrit + Re-Rank (Authority Yok)"] = ra
    print(f"      -> F1: {ra['f1']}%  Acc: {ra['accuracy']}%")

    # ------------------------------------------------------------------
    # [6] + AUTHORITY — Consensus Yok (K-9 Yok)
    # ------------------------------------------------------------------
    print("[6/7] + Authority (Konsensus Yok, K-9 Disabled)")
    AUTH = 0.85
    preds = []
    for q in texts:
        ranked, _, _ = hybrid_rrf(q)
        top5  = ranked[:5]
        rr    = reranker.predict([[q, texts[i]] for i in top5])
        sig   = [1 / (1 + np.exp(-s / 2)) for s in rr]
        w     = [sig[i] * 0.7 + AUTH * 0.3 for i in range(len(top5))]
        best  = top5[int(np.argmax(w))]
        preds.append(int(labels[best]))
    au = compute_metrics(labels, preds)
    results["+ Authority (Konsensus Yok)"] = au
    print(f"      -> F1: {au['f1']}%  Acc: {au['accuracy']}%")

    # ------------------------------------------------------------------
    # [7] TAM SISTEM — K1-K9 + NLI
    # ------------------------------------------------------------------
    print("[7/7] TAM SISTEM (K1-K9 + NLI)")
    print("  [NLI] Model yukleniyor (xlm-roberta-large-xnli)...")
    import torch
    nli = CrossEncoder('joeddav/xlm-roberta-large-xnli')
    preds = []
    for q in texts:
        ranked, _, _ = hybrid_rrf(q)
        top5  = ranked[:5]
        rr    = reranker.predict([[q, texts[i]] for i in top5])
        sig   = [1 / (1 + np.exp(-s / 2)) for s in rr]
        w     = [sig[i] * 0.7 + AUTH * 0.3 for i in range(len(top5))]
        w_sorted = sorted(range(len(top5)), key=lambda i: w[i], reverse=True)
        top3  = [top5[w_sorted[i]] for i in range(min(3, len(w_sorted)))]

        # K-9: Konsensus oylama
        votes = [labels[i] for i in top3]
        cons_label = max(set(votes), key=votes.count)

        # K-4: NLI
        logits = nli.predict([[texts[top3[0]], q]])[0]
        probs  = torch.nn.functional.softmax(
            torch.tensor(logits, dtype=torch.float32), dim=0).numpy()
        # probs: [contradiction, neutral, entailment]
        pred = cons_label
        if   probs[0] > 0.50:  pred = 1 - cons_label
        elif probs[2] > 0.45:  pred = cons_label
        preds.append(int(pred))

    fs = compute_metrics(labels, preds)
    results["TAM SISTEM (K1-K9)"] = fs
    print(f"      -> F1: {fs['f1']}%  Acc: {fs['accuracy']}%")

    # ------------------------------------------------------------------
    # SONUC TABLOSU
    # ------------------------------------------------------------------
    baseline_f1 = fs['f1']
    print("\n" + "=" * 70)
    print("  ABLASYON SONUC TABLOSU")
    print("=" * 70)
    print(f"  {'Senaryo':<38} {'Acc%':>5} {'P%':>6} {'R%':>6} {'F1%':>6}  {'Delta':>7}")
    print("-" * 70)
    for name, m in results.items():
        delta = m['f1'] - baseline_f1
        tag   = "(BASELINE)" if name == "TAM SISTEM (K1-K9)" else f"({delta:+.1f} pp)"
        print(f"  {name:<38} {m['accuracy']:>5} {m['precision']:>6} {m['recall']:>6} {m['f1']:>6}  {tag:>10}")
    print("=" * 70)
    print("\n  Not: Delta = o katman olmadan tam sistemden F1 sapma miktari")
    print("  Negatif delta = o katman olmadan performans duesuyor\n")

    # JSON kaydet
    out = FILE_DIR / "ablation_results.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({"n_samples": n, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"  Sonuclar kaydedildi: {out}\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",  default="simulations/data_sample.csv")
    parser.add_argument("--model", default="src/ai_core/models/kizilelma_classifier_v1")
    parser.add_argument("--embedding", default="intfloat/multilingual-e5-small")
    args = parser.parse_args()
    run_ablation(args.data, args.model, args.embedding)

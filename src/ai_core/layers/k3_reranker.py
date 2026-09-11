"""
K3 — Cross-Encoder Re-Ranker (Keskin Nişancı)
Geri çağrılan adayları çapraz kodlayıcıyla yeniden puanlar,
en alakalı kaydı öne getirir.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    cross_encoder,          # CrossEncoder nesnesi (None ise atla)
    top_k: int = 5,
    score_key: str = "rerank_score",
) -> List[Dict[str, Any]]:
    """
    `candidates` listesindeki her kaydı cross-encoder ile puanlar,
    en yüksek skorlu top_k kaydı döndürür.

    Parameters
    ----------
    query      : Kullanıcı sorgusunun temizlenmiş hali.
    candidates : K2'den gelen aday kayıtlar. Her biri 'text' alanı içermelidir.
    cross_encoder : sentence_transformers.CrossEncoder nesnesi.
    top_k      : Döndürülecek maksimum aday sayısı.
    score_key  : Kayıda eklenen skor anahtarı.
    """
    if cross_encoder is None or not candidates:
        return candidates[:top_k]

    pairs = [(query, str(c.get("text", ""))) for c in candidates]
    try:
        scores = cross_encoder.predict(pairs)
    except Exception:
        return candidates[:top_k]

    for cand, score in zip(candidates, scores):
        cand[score_key] = float(score)

    ranked = sorted(candidates, key=lambda c: c.get(score_key, 0.0), reverse=True)
    return ranked[:top_k]


def top_rerank_score(candidates: List[Dict[str, Any]], score_key: str = "rerank_score") -> float:
    """En yüksek re-rank skorunu döndürür (normalize 0-1)."""
    if not candidates:
        return 0.0
    scores = [c.get(score_key, 0.0) for c in candidates]
    raw = max(scores)
    # sigmoid normalizasyon (CrossEncoder çıktısı log-odds aralığında)
    import math
    return 1.0 / (1.0 + math.exp(-raw))

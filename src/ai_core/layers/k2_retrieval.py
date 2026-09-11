"""
K2 — Retrieval (Hibrit Arama)
- BM25 seyrek geri çağırma
- Yoğun vektör benzerliği (Dense Retrieval)
- Hibrit skor füzyonu
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


# ─── BM25 Arama ──────────────────────────────────────────────────────────────

def bm25_search(
    bm25_index,           # BM25Okapi nesnesi
    tokenized_corpus: List[List[str]],
    query: str,
    top_k: int = 10,
) -> List[Tuple[int, float]]:
    """
    BM25 skoru hesaplar, en yüksek top_k indeks-skor çiftini döndürür.
    Returns: [(idx, score), ...]
    """
    tokens = query.lower().split()
    scores = bm25_index.get_scores(tokens)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0]


# ─── Dense (Vektör) Arama ────────────────────────────────────────────────────

def dense_search(
    query_embedding: np.ndarray,
    corpus_embeddings: np.ndarray,
    top_k: int = 10,
) -> List[Tuple[int, float]]:
    """
    Kosinüs benzerliği ile en yakın top_k komşuları bulur.
    Returns: [(idx, similarity), ...]
    """
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    sims = cosine_similarity([query_embedding], corpus_embeddings)[0]
    top_indices = np.argsort(sims)[::-1][:top_k]
    return [(int(i), float(sims[i])) for i in top_indices]


# ─── Hibrit Füzyon ───────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: List[List[Tuple[int, float]]],
    k: int = 60,
) -> List[Tuple[int, float]]:
    """
    Reciprocal Rank Fusion (RRF) ile birden fazla sıralı listeyi birleştirir.
    Returns: sıralı [(idx, rrf_score), ...]
    """
    scores: Dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (idx, _) in enumerate(ranked):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_items


def hybrid_search(
    query: str,
    query_embedding: np.ndarray,
    bm25_index,
    corpus_embeddings: np.ndarray,
    top_k: int = 10,
    bm25_weight: float = 0.3,
    dense_weight: float = 0.7,
    disable_bm25: bool = False,
    disable_dense: bool = False,
) -> List[Tuple[int, float]]:
    """
    BM25 + Dense sonuçlarını RRF ile birleştirir.
    `disable_bm25` / `disable_dense` ablasyon bayrakları desteklenmektedir.
    """
    ranked_lists: List[List[Tuple[int, float]]] = []
    if not disable_bm25 and bm25_index is not None:
        ranked_lists.append(bm25_search(bm25_index, [], query, top_k=top_k))
    if not disable_dense and corpus_embeddings is not None:
        ranked_lists.append(dense_search(query_embedding, corpus_embeddings, top_k=top_k))

    if not ranked_lists:
        return []
    if len(ranked_lists) == 1:
        return ranked_lists[0]

    return reciprocal_rank_fusion(ranked_lists)[:top_k]

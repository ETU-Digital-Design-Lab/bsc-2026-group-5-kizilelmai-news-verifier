"""
K1 — Girdi İşleme ve Niyet Analizi
- Metin temizleme ve normalizasyon
- Niyet sınıflandırması (doğrulama / sohbet / sayısal)
- Sorgu genişletme
- K7 bağlam birleştirici (stateless fonksiyon)
"""
from __future__ import annotations

import re
from typing import List, Optional


# ─── Normalizasyon ───────────────────────────────────────────────────────────

def normalize(query: str) -> str:
    """Temel metin temizleme: fazla boşluk, özel karakter, lowercase."""
    query = query.strip()
    query = re.sub(r"\s+", " ", query)
    return query


# ─── Niyet Analizi ───────────────────────────────────────────────────────────

INTENT_VERIFICATION = "doğrulama"
INTENT_CHAT         = "sohbet"
INTENT_NUMERIC      = "sayısal"

_CHAT_KEYWORDS = frozenset([
    "merhaba", "selam", "nasılsın", "hello", "hi", "naber", "teşekkür",
    "sağ ol", "tamam", "iyi", "güzel",
])

_NUMERIC_PATTERN = re.compile(r"\b\d[\d,.]+\b")


def classify_intent(query: str) -> str:
    """Sorgunun niyetini belirler."""
    lower = query.lower()
    if any(kw in lower for kw in _CHAT_KEYWORDS):
        return INTENT_CHAT
    if _NUMERIC_PATTERN.search(query):
        return INTENT_NUMERIC
    return INTENT_VERIFICATION


# ─── Sorgu Genişletme ────────────────────────────────────────────────────────

def expand_query(query: str) -> List[str]:
    """
    Orijinal sorguya ek varyantlar üretir (eş anlamlı, soru formu vb.).
    Engine içindeki query_expander metodunun saf-fonksiyon versiyonu.
    """
    variants: List[str] = [query]

    # Soru formu: "... mı?" → "... doğru mu?"
    if not query.endswith("?"):
        variants.append(query + " doğru mu?")

    # Kısaltılmış form (ilk 60 karakter)
    if len(query) > 60:
        variants.append(query[:60].rsplit(" ", 1)[0])

    return list(dict.fromkeys(variants))  # deduplicate, order-preserving


# ─── K7 Bağlam Birleştirici (Stateless Helper) ───────────────────────────────

def merge_context(context_buffer: List[str], current_query: str, window: int = 3) -> str:
    """
    Son `window` sohbet turunu ve mevcut sorguyu birleştirir.
    Engine.context_merger() metodunun saf-fonksiyon karşılığıdır.
    """
    recent = context_buffer[-window:] if context_buffer else []
    parts  = recent + [current_query]
    return " | ".join(parts)

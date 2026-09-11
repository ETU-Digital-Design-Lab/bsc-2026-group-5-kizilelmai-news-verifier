"""
K9 — Çoklu Kaynak Konsensüsü (Multi-Source Consensus)
Birden fazla aday kaynağı arasındaki etiket uyumunu analiz eder.
Çakışma var mı? Çoğunluk ne diyor?
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional


def compute_consensus(
    candidates: List[Dict[str, Any]],
    min_sources: int = 2,
    agreement_ratio: float = 0.6,
) -> Dict[str, Any]:
    """
    Aday kayıtlar arasında label konsensüsü hesaplar.

    Returns
    -------
    {
        "total_sources"   : int,
        "label"           : int | None,   # çoğunluk etiketi
        "agreement_count" : int,
        "has_conflict"    : bool,
        "agreement_ratio" : float,
    }
    """
    if not candidates or len(candidates) < min_sources:
        return {
            "total_sources": len(candidates),
            "label": None,
            "agreement_count": 0,
            "has_conflict": False,
            "agreement_ratio": 1.0,
        }

    labels = [c.get("label") for c in candidates if c.get("label") is not None]
    if not labels:
        return {
            "total_sources": len(candidates),
            "label": None,
            "agreement_count": 0,
            "has_conflict": False,
            "agreement_ratio": 1.0,
        }

    counter = Counter(labels)
    majority_label, majority_count = counter.most_common(1)[0]
    ratio = majority_count / len(labels)
    has_conflict = ratio < agreement_ratio

    return {
        "total_sources":   len(candidates),
        "label":           majority_label if not has_conflict else None,
        "agreement_count": majority_count,
        "has_conflict":    has_conflict,
        "agreement_ratio": round(ratio, 3),
    }

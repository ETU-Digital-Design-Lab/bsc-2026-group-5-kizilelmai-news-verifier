"""
K8 — Kaynak Otorite Ağırlıklandırması
Adayları yayıncı güvenilirlik skoruna göre yeniden ağırlıklandırır.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ai_core.layers.constants import SOURCE_AUTHORITY_TABLE, DEFAULT_AUTHORITY


def resolve_authority(record: Dict[str, Any]) -> float:
    """
    Bir kayıt için otorite skorunu döndürür.
    Önce `authority` alanına bakar, yoksa SOURCE_AUTHORITY_TABLE'dan arar.
    """
    stored = record.get("authority")
    if stored is not None:
        try:
            val = float(stored)
            if 0.0 < val <= 1.0:
                return val
        except (TypeError, ValueError):
            pass

    publisher = str(record.get("publisher") or record.get("source") or "").lower().strip()
    for key, score in SOURCE_AUTHORITY_TABLE.items():
        if key in publisher:
            return score

    return DEFAULT_AUTHORITY


def weight_candidates(
    candidates: List[Dict[str, Any]],
    sim_weight: float = 0.70,
    authority_weight: float = 0.30,
) -> List[Dict[str, Any]]:
    """
    Her adayın sim_score + otorite skorunu birleştirerek `weighted_score` ekler.
    Listemi `weighted_score` azalan sırayla döndürür.
    """
    for cand in candidates:
        sim   = float(cand.get("sim_score", 0.0))
        auth  = resolve_authority(cand)
        cand["authority_score"]  = auth
        cand["weighted_score"]   = sim_weight * sim + authority_weight * auth

    return sorted(candidates, key=lambda c: c["weighted_score"], reverse=True)

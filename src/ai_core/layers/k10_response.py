"""
K10 — Yanıt Oluşturucu (Response Builder)
Karar motoru çıktısını kullanıcıya sunulacak formata dönüştürür.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ai_core.layers.constants import STATUS_APPROVE, STATUS_REJECT, STATUS_WARN, STATUS_RETURN

# ── Durum → Kullanıcı Mesajı Eşlemesi ────────────────────────────────────────
_STATUS_LABELS = {
    STATUS_APPROVE: ("✅ ONAYLANDI", "İddia güvenilir kaynaklarla desteklenmektedir."),
    STATUS_REJECT:  ("❌ REDDEDİLDİ", "İddia mevcut kaynaklarla çelişmektedir."),
    STATUS_WARN:    ("⚠️ UYARI", "İddia hakkında çelişkili veya zayıf kanıt bulunmaktadır."),
    STATUS_RETURN:  ("🔍 YETERSİZ VERİ", "Bu iddia hakkında yeterli kanıt bulunamadı."),
}


def build_response(
    decision: Dict[str, Any],
    top_candidate: Optional[Dict[str, Any]],
    query: str,
    category: str = "GENEL",
) -> Dict[str, Any]:
    """
    K5 karar sözlüğü + en iyi aday kaydından kullanıcı yanıtı üretir.

    Returns
    -------
    ChatResponse şemasıyla uyumlu sözlük.
    """
    status = decision.get("status", STATUS_RETURN)
    confidence = int(decision.get("confidence", 0))
    risk = int(decision.get("risk", 50))

    msg, description = _STATUS_LABELS.get(status, ("❓", "Bilinmeyen durum."))

    source      = "-"
    source_url  = None
    source_name = None
    source_id   = None
    publisher   = "Belirlenemedi"
    authority   = 0.0

    if top_candidate:
        source      = str(top_candidate.get("text", ""))[:200]
        source_url  = top_candidate.get("source_url")
        source_name = top_candidate.get("publisher") or top_candidate.get("source_name")
        source_id   = top_candidate.get("id")
        publisher   = top_candidate.get("publisher") or "Belirlenemedi"
        authority   = float(top_candidate.get("authority_score", top_candidate.get("authority", 0.0)))

    result_text = _compose_result_text(status, query, source, publisher, confidence, risk)

    return {
        "result":                result_text,
        "status":                status,
        "msg":                   msg,
        "description":           description,
        "confidence":            confidence,
        "risk":                  risk,
        "category":              category,
        "source":                source,
        "source_url":            source_url,
        "source_name":           source_name,
        "source_id":             source_id,
        "source_channel":        publisher,
        "source_attribution_basis": "k8_authority_weighted",
        "evidence_metadata": {
            "authority_score": authority,
            "decision_reason": decision.get("reason", ""),
        },
    }


def _compose_result_text(
    status: str,
    query: str,
    source: str,
    publisher: str,
    confidence: int,
    risk: int,
) -> str:
    if status == STATUS_RETURN:
        return (
            f"'{query[:80]}' iddiası hakkında yeterli kanıt bulunamadı. "
            "Lütfen güvenilir kaynaklardan doğrulayın."
        )
    if status == STATUS_APPROVE:
        return (
            f"İddia doğrulandı (%{confidence} güven). "
            f"Kaynak: {publisher}. "
            f"Kanıt: \"{source[:120]}...\""
        )
    if status == STATUS_REJECT:
        return (
            f"İddia reddedildi (Dezenformasyon riski: %{risk}). "
            f"Kaynak: {publisher}."
        )
    # UYARI
    return (
        f"İddia hakkında çelişkili kanıt bulundu (Güven: %{confidence}). "
        f"Dikkatli olmanız önerilir."
    )

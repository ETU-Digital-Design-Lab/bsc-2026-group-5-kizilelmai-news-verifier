"""
K5 — Karar Motoru (Decision Engine)
NLI olasılıkları, benzerlik skoru, K6 sınıflandırıcı sinyali ve
K9 konsensüs bilgisini birleştirerek nihai kararı üretir.

Durum çıktıları:
  ONAY  → İddia doğrulandı
  RED   → İddia yanlış / dezenformasyon
  UYARI → Zayıf kanıt, dikkatli ol
  RET   → Yetersiz kanıt, abstain

──────────────────────────────────────────────────────────────────────────
DEĞİŞİKLİK (v7 — 2026-09-13): HİBRİT RE-RANKER GATED ABSTENTİON
──────────────────────────────────────────────────────────────────────────
Seçici tahmin analizi (selective_signal_analysis.py) şunu kanıtladı:
  K-3 Re-Ranker Top-1 sinyali: AURC = 0.3321 (daha düşük risk)
  K-4 NLI Softmax sinyali:     AURC = 0.3600 (daha yüksek risk)
  200 split-half tekrarının 187'sinde (%93.5) re-ranker daha iyi

Sorun: Korpus 2021 öncesi belgelerle sınırlı. 2022-2026 arası iddiaların
getirilen belgeleri içerik olarak alakalıdır (rerank_score yüksek) fakat
zaman damgası yüzünden detaylar farklılaşabilir => NLI neutral der.
Sağlıklı bir NLI modeli için bu davranış beklentidir ve abstention
yanlış kararla sonuçlanır.

Yeni kural:
  abstain = (NLI_zayıf AND sim < SIM_WEAK)
            AND (sig_rerank < RERANKER_ABSTAIN_THRESHOLD)

Re-ranker yüksekse => belge gerçekten alakalı => abstain etme.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ai_core.layers.constants import (
    STATUS_APPROVE, STATUS_REJECT, STATUS_WARN, STATUS_RETURN,
    LABEL_TRUE, LABEL_FALSE,
)
from src.ai_core.layers.k4_nli import IDX_ENTAILMENT, IDX_CONTRADICTION, should_abstain

# ── Eşik Değerleri ───────────────────────────────────────────────────────────
SIM_STRONG    = 0.72   # benzerlik >= bu → güçlü eşleşme
SIM_WEAK      = 0.40   # benzerlik < bu → zayıf eşleşme / RET
CONF_HIGH     = 80     # güven skoru (0-100)
CONF_MED      = 50
K6_CONF_MIN   = 0.70   # K6 sınıflandırıcı minimum güven eşiği

# ── Hibrit Re-Ranker Abstention Eşiği (Faz 1 — v7) ──────────────────────────
# Selective signal analizi: re-ranker top-1 bu değerin üzerindeyse belge
# gerçekten alakalı demektir → NLI neutral verse de abstain etme.
RERANKER_ABSTAIN_THRESHOLD = 0.015  # Bu değerin üzerindeki rerank_score → abstain engellenir


def should_abstain_hybrid(
    nli_probs: List[float],
    sim_score: float,
    sig_rerank: float,
) -> bool:
    """
    Hibrit abstention kararı: NLI + benzerlik + re-ranker sinyali.

    Eski kural: abstain = NLI_zayıf AND sim < 0.40
    Yeni kural: abstain = (NLI_zayıf AND sim < 0.40) AND (rerank < eşik)

    Re-ranker yüksekse => belge gerçekten alakalı => abstain etme.
    """
    if sig_rerank >= RERANKER_ABSTAIN_THRESHOLD:
        # Re-ranker yüksek güven: NLI neutral dese bile bilgi var demektir
        return False
    # Hem NLI zayıf hem benzerlik zayıf hem re-ranker zayıf => gerçek abstain
    return should_abstain(nli_probs) and sim_score < SIM_WEAK


def make_decision(
    nli_probs: List[float],
    sim_score: float,
    db_label: Optional[int],
    sig_rerank: float = 0.0,
    k6_prediction: Optional[Dict[str, Any]] = None,
    k9_consensus: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tüm sinyalleri birleştirerek nihai karar sözlüğünü döndürür.

    Returns
    -------
    dict with keys: status, confidence (0-100), risk (0-100), reason
    """
    result: Dict[str, Any] = {
        "status": STATUS_RETURN,
        "confidence": 0,
        "risk": 50,
        "reason": "abstain",
    }

    # ── Hibrit Abstention Kontrolü (Faz 1: Re-Ranker Gated) ──────────────────
    if should_abstain_hybrid(nli_probs, sim_score, sig_rerank):
        result["reason"] = "k4_abstain_hybrid_low_rerank_and_sim"
        return result

    entail = nli_probs[IDX_ENTAILMENT] if len(nli_probs) > IDX_ENTAILMENT else 0.0
    contra = nli_probs[IDX_CONTRADICTION] if len(nli_probs) > IDX_CONTRADICTION else 0.0

    # Re-Ranker güçlüyse entailment/contradiction değerlerini yukarı ağırlıklandır
    rerank_boost = min(1.0, sig_rerank * 5)  # 0.02 → 0.10 boost, 0.20 → 1.0 boost

    effective_entail = min(1.0, entail + rerank_boost * 0.15)
    effective_contra = min(1.0, contra + rerank_boost * 0.05)

    # ── Temel NLI + benzerlik kararı ─────────────────────────────────────────
    if effective_entail > effective_contra and sim_score >= SIM_WEAK:
        if db_label == LABEL_TRUE:
            result["status"]     = STATUS_APPROVE
            result["confidence"] = int(min(100, effective_entail * 100 * (1 + 0.2 * sig_rerank)))
            result["risk"]       = max(0, 100 - result["confidence"])
            result["reason"]     = "nli_entailment_hybrid"
        else:
            result["status"]     = STATUS_WARN
            result["confidence"] = int(effective_entail * 60)
            result["risk"]       = 60
            result["reason"]     = "nli_entailment_label_conflict"
    elif effective_contra > effective_entail and sim_score >= SIM_WEAK:
        result["status"]     = STATUS_REJECT
        result["confidence"] = int(min(100, effective_contra * 100))
        result["risk"]       = 90
        result["reason"]     = "nli_contradiction_hybrid"
    elif sim_score >= SIM_STRONG:
        result["status"]     = STATUS_WARN
        result["confidence"] = 45
        result["risk"]       = 55
        result["reason"]     = "sim_only_no_nli"
    elif sig_rerank >= RERANKER_ABSTAIN_THRESHOLD:
        # Sadece re-ranker sinyali var, NLI zayıf ama belge alakalı
        result["status"]     = STATUS_WARN
        result["confidence"] = int(min(60, sig_rerank * 300))
        result["risk"]       = 65
        result["reason"]     = "reranker_only_nli_neutral"

    # ── K9 Konsensüs Geçişi ───────────────────────────────────────────────────
    if k9_consensus and isinstance(k9_consensus, dict):
        if k9_consensus.get("has_conflict"):
            result["status"] = STATUS_WARN
            result["risk"]   = max(result["risk"], 65)
            result["reason"] += "+k9_conflict"
        elif k9_consensus.get("total_sources", 1) >= 2:
            maj = k9_consensus.get("label")
            if maj == LABEL_TRUE and result["status"] == STATUS_APPROVE:
                result["confidence"] = min(100, result["confidence"] + 10)
            elif maj == LABEL_FALSE:
                result["status"] = STATUS_REJECT
                result["risk"]   = max(result["risk"], 85)
                result["reason"] += "+k9_majority_false"

    # ── K6 Sınıflandırıcı Sinyali ─────────────────────────────────────────────
    if k6_prediction and isinstance(k6_prediction, dict) and k6_prediction.get("available"):
        k6_label = k6_prediction.get("predicted_label")
        k6_conf  = float(k6_prediction.get("confidence") or 0.0)
        if k6_conf >= K6_CONF_MIN:
            if k6_label == LABEL_FALSE and result["status"] == STATUS_APPROVE:
                result["status"] = STATUS_WARN
                result["risk"]   = max(result["risk"], 70)
                result["reason"] += "+k6_override"
            elif k6_label == LABEL_TRUE and result["status"] == STATUS_RETURN:
                result["status"]     = STATUS_WARN
                result["confidence"] = int(k6_conf * 60)
                result["risk"]       = 55
                result["reason"]     += "+k6_rescue"

    return result

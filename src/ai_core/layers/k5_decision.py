"""
K5 — Karar Motoru (Decision Engine)
NLI olasılıkları, benzerlik skoru, K6 sınıflandırıcı sinyali ve
K9 konsensüs bilgisini birleştirerek nihai kararı üretir.

Durum çıktıları:
  ONAY  → İddia doğrulandı
  RED   → İddia yanlış / dezenformasyon
  UYARI → Zayıf kanıt, dikkatli ol
  RET   → Yetersiz kanıt, abstain
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ai_core.layers.constants import (
    STATUS_APPROVE, STATUS_REJECT, STATUS_WARN, STATUS_RETURN,
    LABEL_TRUE, LABEL_FALSE,
)
from src.ai_core.layers.k4_nli import IDX_ENTAILMENT, IDX_CONTRADICTION, should_abstain

# ── Eşik Değerleri ───────────────────────────────────────────────────────────
SIM_STRONG    = 0.72   # benzerlik ≥ bu → güçlü eşleşme
SIM_WEAK      = 0.40   # benzerlik < bu → zayıf eşleşme / RET
CONF_HIGH     = 80     # güven skoru (0-100)
CONF_MED      = 50
K6_CONF_MIN   = 0.70   # K6 sınıflandırıcı minimum güven eşiği


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

    if should_abstain(nli_probs) and sim_score < SIM_WEAK:
        result["reason"] = "k4_abstain_low_sim"
        return result

    entail = nli_probs[IDX_ENTAILMENT] if len(nli_probs) > IDX_ENTAILMENT else 0.0
    contra = nli_probs[IDX_CONTRADICTION] if len(nli_probs) > IDX_CONTRADICTION else 0.0

    # ── Temel NLI + benzerlik kararı ─────────────────────────────────────────
    if entail > contra and sim_score >= SIM_WEAK:
        if db_label == LABEL_TRUE:
            result["status"]     = STATUS_APPROVE
            result["confidence"] = int(min(100, entail * 100 * (1 + 0.2 * sig_rerank)))
            result["risk"]       = max(0, 100 - result["confidence"])
            result["reason"]     = "nli_entailment"
        else:
            result["status"]     = STATUS_WARN
            result["confidence"] = int(entail * 60)
            result["risk"]       = 60
            result["reason"]     = "nli_entailment_label_conflict"
    elif contra > entail and sim_score >= SIM_WEAK:
        result["status"]     = STATUS_REJECT
        result["confidence"] = int(min(100, contra * 100))
        result["risk"]       = 90
        result["reason"]     = "nli_contradiction"
    elif sim_score >= SIM_STRONG:
        result["status"]     = STATUS_WARN
        result["confidence"] = 45
        result["risk"]       = 55
        result["reason"]     = "sim_only_no_nli"

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

"""
K4 — NLI Doğrulama (Natural Language Inference)
İddia-kanıt çifti için entailment/contradiction/neutral olasılıklarını hesaplar.
Düşük güven → abstention (RET).
"""
from __future__ import annotations

from typing import List, Optional, Tuple


# NLI sınıf indeksleri (varsayılan: nli-deberta / xlm-roberta-xnli)
IDX_ENTAILMENT   = 0
IDX_NEUTRAL      = 1
IDX_CONTRADICTION = 2

# Abstention eşiği — entailment veya contradiction bu değerin altındaysa RET
ABSTENTION_THRESHOLD = 0.40


def run_nli(
    claim: str,
    evidence: str,
    nli_model,          # transformers pipeline("zero-shot-classification") veya uyumlu model
    device: int = -1,   # -1 = CPU, 0 = CUDA:0
) -> List[float]:
    """
    NLI pipeline'ı çalıştırır.
    Returns: [entailment_prob, neutral_prob, contradiction_prob]
    """
    if nli_model is None:
        return [0.34, 0.33, 0.33]

    candidate_labels = ["entailment", "neutral", "contradiction"]
    try:
        result = nli_model(
            f"{claim} [SEP] {evidence}",
            candidate_labels=candidate_labels,
            multi_label=False,
        )
        label_to_prob = dict(zip(result["labels"], result["scores"]))
        return [
            label_to_prob.get("entailment",    0.0),
            label_to_prob.get("neutral",        0.0),
            label_to_prob.get("contradiction",  0.0),
        ]
    except Exception:
        return [0.34, 0.33, 0.33]


def should_abstain(nli_probs: List[float], threshold: float = ABSTENTION_THRESHOLD) -> bool:
    """
    Hem entailment hem contradiction eşiğin altındaysa abstention (RET) önerilir.
    """
    if not nli_probs or len(nli_probs) < 3:
        return True
    entail = nli_probs[IDX_ENTAILMENT]
    contra = nli_probs[IDX_CONTRADICTION]
    return entail < threshold and contra < threshold


def dominant_nli_label(nli_probs: List[float]) -> Tuple[str, float]:
    """En yüksek olasılıklı NLI sınıfını ve olasılığını döndürür."""
    if not nli_probs or len(nli_probs) < 3:
        return "neutral", 0.0
    labels = ["entailment", "neutral", "contradiction"]
    idx = max(range(len(nli_probs)), key=lambda i: nli_probs[i])
    return labels[idx], nli_probs[idx]

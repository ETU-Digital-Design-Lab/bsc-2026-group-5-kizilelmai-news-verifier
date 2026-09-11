"""
K6 — Sınıflandırıcı Danışmanı (Classifier Advisory)
Fine-tune edilmiş kizilelma_classifier_v1 modeliyle
bağımsız bir ikili sınıf tahmini yapar; K5 kararına danışmanlık sinyali sağlar.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def predict(
    query: str,
    tokenizer,
    model,
    device_str: str = "cpu",
    confidence_threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    İddiayı kizilelma_classifier_v1 ile sınıflandırır.

    Returns
    -------
    {
        "available"      : bool,
        "predicted_label": int   (0=yalan, 1=doğru),
        "confidence"     : float (0.0–1.0),
        "raw_logits"     : list,
    }
    """
    if tokenizer is None or model is None:
        return {"available": False, "predicted_label": None, "confidence": 0.0, "raw_logits": []}

    try:
        import torch  # type: ignore

        device = torch.device(device_str)
        enc = tokenizer(
            query,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128,
        )
        enc = {k: v.to(device) for k, v in enc.items()}

        with torch.no_grad():
            out = model(**enc)

        probs = torch.softmax(out.logits, dim=-1)[0].tolist()
        pred_label = int(torch.argmax(out.logits, dim=-1).item())
        confidence = float(probs[pred_label])

        return {
            "available": True,
            "predicted_label": pred_label,
            "confidence": confidence,
            "raw_logits": out.logits[0].tolist(),
        }
    except Exception as exc:
        return {"available": False, "predicted_label": None, "confidence": 0.0, "raw_logits": [], "error": str(exc)}


def is_advisory_confident(prediction: Dict[str, Any], threshold: float = 0.70) -> bool:
    """Tahmin güvenilir danışmanlık sinyali mi?"""
    return prediction.get("available", False) and float(prediction.get("confidence", 0.0)) >= threshold

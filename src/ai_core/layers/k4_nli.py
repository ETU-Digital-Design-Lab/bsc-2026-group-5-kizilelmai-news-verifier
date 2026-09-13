"""
K4 — NLI Doğrulama (Natural Language Inference)  [DÜZELTİLMİŞ SÜRÜM]

İddia-kanıt çifti için entailment/neutral/contradiction olasılıklarını hesaplar.
Düşük güven → abstention (RET).

────────────────────────────────────────────────────────────────────────────
NEDEN DEĞİŞTİ
────────────────────────────────────────────────────────────────────────────
Eski sürüm modeli şöyle çağırıyordu:

    nli_model(f"{claim} [SEP] {evidence}",
              candidate_labels=["entailment", "neutral", "contradiction"])

Bu bir `zero-shot-classification` pipeline'ıdır. Yaptığı iş, metnin
"This example is entailment." gibi ŞABLON CÜMLELERİ gerektirip
gerektirmediğini ölçmektir. İddia ile kanıt arasındaki çıkarım ilişkisini
ölçmez. Sonuç: FACTurk koşusunda 483 iddianın 329'unda en yüksek sınıf
"neutral" çıktı, neutral olasılığının medyanı 0.962 oldu; katman fiilen
sinyal üretmedi.

Doğrusu, NLI modelini premise/hypothesis ÇİFTİ olarak çağırmaktır:
    premise    = kanıt metni
    hypothesis = iddia
ve modelin kendi üç sınıflı başlığını okumaktır.

DİKKAT — indeks sırası: xlm-roberta-large-xnli'nin id2label sırası
{0: contradiction, 1: neutral, 2: entailment} olup bu modülün kendi
sabitlerinin TERSİDİR. Bu yüzden sıra asla elle varsayılmaz; her zaman
model.config.id2label'dan okunur ve bu modülün kanonik sırasına
([entailment, neutral, contradiction]) çevrilir. Downstream kod
(k5_decision.py) değişmeden çalışmaya devam eder.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# NLI sınıf indeksleri — BU MODÜLÜN KANONİK SIRASI (değiştirmeyin)
IDX_ENTAILMENT = 0
IDX_NEUTRAL = 1
IDX_CONTRADICTION = 2

# Abstention eşiği — entailment ve contradiction'ın ikisi de bunun altındaysa RET
ABSTENTION_THRESHOLD = 0.40

DEFAULT_MODEL = "joeddav/xlm-roberta-large-xnli"
MAX_LENGTH = 512

_CANON = ("entailment", "neutral", "contradiction")


class NLIModel:
    """premise/hypothesis çifti alan gerçek bir NLI sınıflandırıcısı."""

    def __init__(self, model, tokenizer, order: Sequence[int], device: str):
        self.model = model
        self.tokenizer = tokenizer
        self.order = list(order)   # kanonik sıradaki her sınıfın model içindeki indeksi
        self.device = device

    def predict_batch(self, pairs: Sequence[Tuple[str, str]], batch_size: int = 16) -> List[List[float]]:
        """pairs: (premise=kanıt, hypothesis=iddia) çiftleri.
        Döndürür: her çift için [entailment, neutral, contradiction]."""
        import torch

        out: List[List[float]] = []
        self.model.eval()
        with torch.no_grad():
            for i in range(0, len(pairs), batch_size):
                chunk = pairs[i:i + batch_size]
                enc = self.tokenizer([p for p, _ in chunk], [h for _, h in chunk],
                                     truncation=True, max_length=MAX_LENGTH,
                                     padding=True, return_tensors="pt").to(self.device)
                probs = torch.softmax(self.model(**enc).logits, dim=-1).cpu().tolist()
                out.extend([[row[j] for j in self.order] for row in probs])
        return out


def load_nli_model(model_name: str = DEFAULT_MODEL, device: int = -1) -> NLIModel:
    """NLI modelini yükler ve sınıf sırasını model config'inden çözer."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    dev = "cuda:%d" % device if (device is not None and device >= 0 and torch.cuda.is_available()) else "cpu"
    tok = AutoTokenizer.from_pretrained(model_name)
    mdl = AutoModelForSequenceClassification.from_pretrained(model_name).to(dev)
    if dev.startswith("cuda"):
        mdl = mdl.half()

    id2label: Dict[int, str] = {int(k): str(v).lower() for k, v in mdl.config.id2label.items()}
    order: List[int] = []
    for canon in _CANON:
        hit = [i for i, lab in id2label.items() if re.sub(r"[^a-z]", "", lab) == canon]
        if not hit:
            raise RuntimeError(
                f"NLI modelinin sınıf adları çözülemedi: {id2label}. "
                f"'{canon}' bulunamadı — bu model üç sınıflı bir NLI modeli olmayabilir.")
        order.append(hit[0])
    if len(set(order)) != 3:
        raise RuntimeError(f"Sınıf eşlemesi tekil değil: {id2label} -> {order}")
    return NLIModel(mdl, tok, order, dev)


def run_nli(claim: str, evidence: str, nli_model: Any, device: int = -1) -> List[float]:
    """
    Tek çift için NLI. Returns: [entailment_prob, neutral_prob, contradiction_prob]

    nli_model, load_nli_model() ile üretilmiş bir NLIModel olmalıdır.
    Eski zero-shot pipeline'ı geçilirse SESSİZCE ÇÖP ÜRETMEK YERİNE hata verir —
    bu katmanın bozukluğu tam olarak sessiz kalabildiği için fark edilmemişti.
    """
    if nli_model is None:
        return [0.34, 0.33, 0.33]
    if not isinstance(nli_model, NLIModel):
        raise TypeError(
            "run_nli artık NLIModel bekliyor. `pipeline('zero-shot-classification')` "
            "nesnesi geçersizdir: iddia-kanıt çiftini değil şablon cümleleri puanlar. "
            "load_nli_model() kullanın.")
    if not claim or not evidence:
        return [0.0, 1.0, 0.0]
    try:
        return nli_model.predict_batch([(evidence, claim)])[0]
    except Exception:
        return [0.34, 0.33, 0.33]


def run_nli_batch(pairs: Sequence[Tuple[str, str]], nli_model: Any,
                  batch_size: int = 16) -> List[List[float]]:
    """pairs: (claim, evidence) çiftleri — premise/hypothesis çevrimi burada yapılır."""
    if not isinstance(nli_model, NLIModel):
        raise TypeError("run_nli_batch NLIModel bekliyor; load_nli_model() kullanın.")
    return nli_model.predict_batch([(ev, cl) for cl, ev in pairs], batch_size=batch_size)


def should_abstain(nli_probs: List[float], threshold: float = ABSTENTION_THRESHOLD) -> bool:
    """Hem entailment hem contradiction eşiğin altındaysa abstention (RET) önerilir."""
    if not nli_probs or len(nli_probs) < 3:
        return True
    return (nli_probs[IDX_ENTAILMENT] < threshold and
            nli_probs[IDX_CONTRADICTION] < threshold)


def dominant_nli_label(nli_probs: List[float]) -> Tuple[str, float]:
    """En yüksek olasılıklı NLI sınıfını ve olasılığını döndürür."""
    if not nli_probs or len(nli_probs) < 3:
        return "neutral", 0.0
    idx = max(range(3), key=lambda i: nli_probs[i])
    return list(_CANON)[idx], nli_probs[idx]

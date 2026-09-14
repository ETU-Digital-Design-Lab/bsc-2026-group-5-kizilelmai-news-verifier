"""
Response Generator Modülü.

KızılelmAI için Türkçe zengin yanıt üretimi, kaynak kanalı tespiti ve
yapılandırılmış JSON çıktısı oluşturma yetenekleri.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

PROVENANCE_FIELDS = ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at")


class ResponseGeneratorMixin:
    """KizilelmaEngine için yanıt formatlama ve kaynak kanalı çözümleme yetenekleri."""

    def detect_source_channel(self, text):
        """Metin içerisinden haber kaynağını/kanalını tespit etmeye çalışır."""
        if not text or text == '-':
            return "Belirlenemedi"
            
        text_lower = text.lower()
        
        match = re.match(r'^\[Kaynak:\s*([^\]]+)\]', text)
        if match:
            return match.group(1).strip()
            
        if "ihlas haber ajansı" in text_lower or "iha" in text_lower:
            return "İhlas Haber Ajansı (İHA)"
        if "demirören haber ajansı" in text_lower or "dha" in text_lower:
            return "Demirören Haber Ajansı (DHA)"
        if "anadolu ajansı" in text_lower or "aa" in text_lower:
            return "Anadolu Ajansı (AA)"
        if "trt haber" in text_lower or "trt" in text_lower:
            return "TRT Haber"
        if "türkiye büyük millet meclisi" in text_lower or "tbmm" in text_lower:
            return "TBMM"
        if "iletişim başkanlığı" in text_lower or "dezenformasyon" in text_lower:
            return "T.C. İletişim Başkanlığı"
            
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            domain = urls[0].replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            return domain.upper()
            
        return "Resmi / Doğrulanmış Haber Kaynağı"

    def local_response_engine(self, query, cand, res, classifier_prediction=None):
        """Dış API olmadan profesyonel Türkçe yanıt üretir ve detaylı metadata döner."""
        status_msg = res['msg']
        detail = res['desc']
        trust = int(res.get('conf', 0))
        risk = int(res.get('risk', 0))
        cat = res.get('cat', 'GENEL')
        source = cand.get('text', '-')
        
        source_channel = cand.get('publisher') if cand.get('source_url') and cand.get('publisher') else "Kaynak kaydı eksik"
        
        display_source = source
        if display_source.startswith(f"[Kaynak: {source_channel}]"):
            display_source = display_source[len(f"[Kaynak: {source_channel}]"):].strip()
        else:
            display_source = re.sub(r'^\[Kaynak:[^\]]+\]\s*', '', display_source)

        cons = res.get('consensus', {})
        cons_text = ""
        if cons.get('is_consensus'):
            cons_text = f" (Konsensüs: {cons.get('agreement_count')}/{cons.get('total_sources')} kaynak uyumlu)"
        else:
            cons_text = " (⚠️ Dikkat: Kaynaklar arasında çelişki tespit edildi!)"

        header = f"{status_msg}\n{detail}"
        extra = ""
        if res.get('status') == 'KISMI':
            extra = f"\n⚠️ **Dikkat:** Analizimize göre bu iddia, özellikle **{cat}** kategorisinde kaynaklarla tam uyuşmamaktadır."
        elif res.get('status') == 'RED':
            extra = f"\n❌ **Not:** {cat} bazlı hatalar nedeniyle bu bilgi güvenilir kabul edilmemiştir."

        classifier_line = ""
        if classifier_prediction and classifier_prediction.get("available"):
            label = "GERÇEK" if classifier_prediction["predicted_label"] == 1 else "YALAN"
            score = classifier_prediction["confidence"] * 100
            classifier_line = f"• **AI Sınıflandırıcı Tahmini (yardımcı):** % {score:.1f} {label}\n"

        formatted_text = f"{header}\n\n🔍 **DERİN ANALİZ RAPORU (v3.0):**\n• **Kaynak Kanalı:** {source_channel}\n• **Hata Kategorisi:** {cat}\n{classifier_line}• **Otorite Puanı:** % {int(cand.get('authority', 0.85)*100)}\n• **Tespit Türü:** {'Doğrudan Çelişki' if risk > 50 else 'Semantik Örtüşme'}{cons_text}\n{extra}\n🛡️ **Doğruluk:** %{trust} | 📉 **Risk:** %{risk}\n-----------------------------\n📄 **Kaynak Metin:** {display_source}"

        return {
            "result": formatted_text,
            "status": res.get('status'),
            "msg": status_msg,
            "description": detail,
            "confidence": trust,
            "risk": risk,
            "category": cat,
            "source": display_source,
            "source_channel": source_channel,
            "source_id": cand.get('id'),
            "source_url": cand.get('source_url') or None,
            "source_name": cand.get('publisher') or None,
            "evidence_metadata": {key: str(cand[key]) if cand.get(key) is not None else None for key in PROVENANCE_FIELDS if key in cand},
            "source_attribution_basis": "stored_metadata" if cand.get('source_url') and cand.get('publisher') else "unknown",
            "classifier": classifier_prediction or {
                "available": False,
                "advisory_only": True,
                "predicted_label": None,
                "p_false": None,
                "p_true": None,
                "confidence": None,
            }
        }

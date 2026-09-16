"""
KızılelmAI — 10 Katmanlı RAG Pipeline Sabitleri ve Türleri
Bu modül tüm katmanların paylaştığı sabit değerleri, tip tanımlarını
ve yardımcı yapıları merkezi bir yerde tutar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# ── Karar Etiketi Sabitleri ──────────────────────────────────────────────────
LABEL_TRUE  = 1   # DOĞRU
LABEL_FALSE = 0   # YALAN
LABEL_INSUF = 2   # YETERSİZ VERİ

STATUS_APPROVE = "ONAY"
STATUS_REJECT  = "RED"
STATUS_WARN    = "UYARI"
STATUS_RETURN  = "RET"    # Abstain — yetersiz kanıt

# ── K-8: Kaynak Otorite Tablosu ─────────────────────────────────────────────
# NOT: teyit.org, malumatfurus.org, dogrulukpayi gibi teyit siteleri etiket sızıntısını
# önlemek amacıyla kara listeye (BLACKLIST_DOMAINS) alınmıştır; birincil kanıt boru
# hattında otorite puanı taşımazlar. En yüksek otorite resmi kurum ve haber ajanslarına aittir.
SOURCE_AUTHORITY_TABLE: Dict[str, float] = {
    "resmigazete": 0.99,
    "cumhurbaskanligi": 0.98,
    "tccb": 0.98,
    "tbmm": 0.98,
    "t.c. iletisim baskanligi": 0.97,
    "iletisim baskanligi": 0.97,
    "anadolu ajansi": 0.96,
    "aa": 0.96,
    "dha": 0.94,
    "iha": 0.94,
    "trt haber": 0.94,
    "trt": 0.94,
    "ntv": 0.90,
    "haberturk": 0.88,
    "milliyet": 0.87,
    "hurriyet": 0.87,
    "sozcu": 0.85,
    "cumhuriyet": 0.85,
    "star": 0.83,
    "sabah": 0.82,
    "a haber": 0.80,
    "habertürk": 0.88,
    "kaggle": 0.75,
    "wikipedia": 0.72,
    "hugging face": 0.70,
    "github": 0.68,
    "bilinmeyen": 0.60,
    "unknown": 0.60,
}

DEFAULT_AUTHORITY = 0.60

# ── K-9: Konsensüs Eşikleri ─────────────────────────────────────────────────
CONSENSUS_MIN_SOURCES = 2

# ── K-4: NLI Sınıf İndeksleri ───────────────────────────────────────────────
NLI_ENTAILMENT   = 0
NLI_NEUTRAL      = 1
NLI_CONTRADICTION = 2

# ── Provenance Alanları ──────────────────────────────────────────────────────
PROVENANCE_FIELDS = (
    "source_url", "publisher", "published_at",
    "evidence_id", "label_provenance", "ingested_at",
)


@dataclass
class LayerTrace:
    """Her katmanın gecikme ve meta bilgisini tutar."""
    layer_latency_ms: Dict[str, float] = field(default_factory=dict)
    context_reset: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """_ask() boyunca taşınan durum nesnesi."""
    raw_query: str
    normalized_query: str = ""
    intent: str = "doğrulama"
    expanded_queries: List[str] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    top_candidate: Optional[Dict[str, Any]] = None
    nli_probs: Optional[List[float]] = None
    k6_prediction: Optional[Dict[str, Any]] = None
    k9_consensus: Optional[Dict[str, Any]] = None
    sim_score: float = 0.0
    sig_rerank: float = 0.0
    trace: LayerTrace = field(default_factory=LayerTrace)

import os
import sys
import re
import json
import time
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

_runtime_py = Path(__file__).resolve().parents[3] / ".runtime" / "python"
if _runtime_py.exists() and str(_runtime_py) not in sys.path:
    sys.path.insert(0, str(_runtime_py))

import numpy as np # type: ignore
import pandas as pd # type: ignore
import torch # type: ignore
from sentence_transformers import SentenceTransformer, CrossEncoder, util # type: ignore
from sklearn.metrics.pairwise import cosine_similarity # type: ignore
from rank_bm25 import BM25Okapi # type: ignore
from sqlalchemy import create_engine, text # type: ignore

# import google.generativeai as genai  # KALDIRILDI: Dış API kullanılmayacak
import warnings

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

_evaluation_trace = ContextVar("evaluation_trace", default=None)

from .text_heuristics import (
    TextAnalysisMixin, turkish_lower, to_ascii_tr, split_numbers_letters
)
from .knowledge_store import KnowledgeStoreMixin, PROVENANCE_FIELDS
from .response_generator import ResponseGeneratorMixin
from .classifier import LearnedDecisionClassifier

# K-8: Kaynak bazlı otorite tablosu (çeşitlendirilmiş güvenilirlik skorları)
SOURCE_AUTHORITY_TABLE = {
    "teyit.org": 0.98,
    "malumatfurus.org": 0.97,
    "dogruluk payi": 0.97,
    "cumhurbaskanligi": 0.97,
    "tbmm": 0.96,
    "t.c. iletisim baskanligi": 0.96,
    "iletisim baskanligi": 0.96,
    "anadolu ajansi": 0.95,
    "aa": 0.95,
    "trt haber": 0.93,
    "trt": 0.93,
    "dha": 0.92,
    "demiroren haber ajansi": 0.92,
    "iha": 0.90,
    "ihlas haber ajansi": 0.90,
    "diken": 0.82,
    "hurriyet": 0.82,
    "milliyet": 0.82,
    "sabah": 0.80,
    "haberturk": 0.80,
    "cnn turk": 0.82,
    "ntv": 0.82,
    "cumhuriyet": 0.80,
    "evrensel": 0.80,
    "sozcu": 0.75,
    "limon": 0.60,
    "resmi / dogrulanmis haber kaynagi": 0.88,
    "belirlenemedi": 0.85,
}


def trace_elapsed(layer, start):
    trace = _evaluation_trace.get()
    if trace is not None:
        trace["layer_latency_ms"][layer] = trace["layer_latency_ms"].get(layer, 0.0) + (time.perf_counter() - start) * 1000


class KizilelmaEngine(TextAnalysisMixin, KnowledgeStoreMixin, ResponseGeneratorMixin):
    """
    KızılelmAI'nin tüm zekasını barındıran sınıf.
    Veriyi yükler, modelleri hazırlar ve sorulara cevap üretir.
    """
    def __init__(self, lazy_load=False, *, corpus_path=None, model_paths=None, enable_web_retrieval=False):
        print("[System] KizilElma Motoru Baslatiliyor...")
        
        # --- 1. Sabitler ve Ayarlar ---
        self.frozen_corpus_path = str(corpus_path) if corpus_path else None
        self.model_paths = model_paths or {}
        self.enable_web_retrieval = enable_web_retrieval or (os.environ.get("ENABLE_WEB_RETRIEVAL", "0") == "1")
        self._web_retriever = None
        self.root_dir = "" # type: Any
        self.csv_path = "" # type: Any
        self.local_model_path = "" # type: Any
        self.kb_path = "" # type: Any
        self.RETRIEVAL_THRESHOLD = 0.40
        self.SAFE_SIMILARITY_ZONE = 0.65
        self.SYNONYM_THRESHOLD = 0.76
        self.IRRELEVANT_THRESHOLD = 0.25
        self.SEMANTIC_SHIFT_THRESHOLD = 0.55
        self.AUTHORITY_WEIGHT = 0.3 # Katman 8: Otorite ağırlığı
        self.CONSENSUS_THRESHOLD = 2 # Katman 9: En az kaç kaynak aynı fikirde olmalı?
        self.STOP_WORDS = {
            'mi', 'mı', 'mu', 'mü', 'mıdır', 'midir', 'mudur', 'müdür', 'nin', 'nın', 'nun', 'nün', 'de', 'da', 'te', 'ta', 'den', 'dan',
            'ile', 've', 'veya', 'ki', 'bu', 'şu', 'o', 'bir', 'olan', 'eden', 'olarak',
            'için', 'diye', 'kadar', 'sonra', 'önce', 'daha', 'en', 'ise', 'nedir', 'kimdir', 'nasil',
            'neden', 'niçin', 'miydi', 'miyim', 'mıyım'
        }
        self.SKEPTIC_KEYWORDS = {'yalan', 'uydurma', 'kurgu', 'montaj', 'fake', 'palavra', 'efsane', 'iftira', 'yanlış'}
        self.RED_LIST_TITLES = ['cumhurbaşkanı', 'vali', 'ceo', 'kurucu', 'belediye başkanı', 'rektör', 'bakan']
        self.MONTHS = ['ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık']

        # --- 2. Bellek Alanları ---
        self.df = pd.DataFrame() # type: ignore
        self.texts = [] # type: list[str]
        self.text_embeddings = [] # type: Any
        self.bm25 = None # type: Any
        db_url = os.environ.get("DATABASE_URL", "postgresql://kizilelmai_user:kizilelmai_pass@localhost:5433/kizilelmai")
        self.db_engine = None if corpus_path else create_engine(db_url)
        self.kb = {} # type: Any
        self.search_model = None # type: Any
        self.nli_model = None # type: Any
        self.rerank_model = None # type: Any
        self.context_buffer = [] # type: List[Dict[str, Any]]
        self.MAX_CONTEXT = 3
        
        self.decision_classifier = LearnedDecisionClassifier()

        # --- Thread Safety ---
        self._model_lock = threading.Lock()
        self._sync_lock = threading.Lock()
        self._last_sync_time = 0.0   # sync_db throttle icin
        self.SYNC_INTERVAL = 60.0    # Saniyede en fazla 1 kez sync_db calissin

        # --- 3. Başlatma Sırası ---
        if not torch.cuda.is_available():
            torch.set_num_threads(4)
            try:
                torch.set_num_interop_threads(2)
            except RuntimeError:
                pass  # Process-global setting cannot be reset by a second engine.
            print("[System] CPU Modu: PyTorch thread limitleri ayarlandı (threads=4).")
        else:
            print("[System] CUDA Modu: GPU üzerinden çalıştırılıyor!")

        self.setup_paths()
        self.load_data()
        # Baslangic kayit sayisini baseline olarak kaydet (dynamic_records hesabi icin)
        self.baseline_records = len(self.df)
        if not lazy_load:
            self.load_search_model()
            self.load_heavy_models()
            print("🚀 Motor Hazır!")
        else:
            print("💤 Tembel Yükleme Modu: Modeller ihtiyaç anında yüklenecek.")

    def setup_paths(self):
        # Bu dosya: src/ai_core/pipeline/logic.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Proje kökü: KIZILELMAI/
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        
        # Otomatik olarak .runtime/evaluation_models/models.json içindeki yerel offline yolları al
        models_json_path = os.path.join(self.root_dir, '.runtime', 'evaluation_models', 'models.json')
        if os.path.exists(models_json_path) and not self.model_paths:
            try:
                import json as _json
                with open(models_json_path, encoding='utf-8') as _mf:
                    _m = _json.load(_mf)
                for role in ('embedding', 'reranker', 'nli'):
                    if role in _m and _m[role].get('path') and os.path.exists(_m[role]['path']):
                        self.model_paths[role] = _m[role]['path']
            except Exception:
                pass

        # Varsayılan korpus: v2 snapshot (e5-large precomputed vektörlü)
        v2_corpus = os.path.join(self.root_dir, 'data', 'corpus_snapshots', 'local_csv_20260913_v2', 'corpus.csv')
        default_csv = v2_corpus if os.path.exists(v2_corpus) else os.path.join(self.root_dir, 'data', 'processed', 'egitim_verisi_final.csv')
        self.csv_path = os.environ.get("KIZILELMAI_CSV_PATH", default_csv)

        self.local_model_path = os.path.join(self.root_dir, 'src', 'ai_core', 'models', 'kizilelma_model_v1')
        self.classifier_model_path = os.path.join(self.root_dir, 'src', 'ai_core', 'models', 'kizilelma_classifier_v1')
        self.kb_path = os.path.join(self.root_dir, 'data', 'processed', 'knowledge_base.json')
        self.dynamic_csv_path = os.path.join(self.root_dir, 'data', 'processed', 'knowledge_base_dynamic.csv')
        self.local_model_path = self.model_paths.get("embedding", self.local_model_path)
        self.classifier_model_path = self.model_paths.get("classifier", self.classifier_model_path)
        if self.frozen_corpus_path:
            self.csv_path = self.frozen_corpus_path



    def load_data(self):
        print("📂 PostgreSQL Veritabanına Bağlanılıyor...")
        self.db_connected = False
        try:
            if self.frozen_corpus_path:
                self.df = pd.read_csv(self.frozen_corpus_path, keep_default_na=False)
            else:
                with self.db_engine.connect() as conn:
                    self.df = pd.read_sql("SELECT * FROM knowledge_base ORDER BY id", conn).drop(columns=["embedding"], errors="ignore")
            
            print(f"✅ Veri seti yüklendi: {len(self.df)} kayıt (PostgreSQL).")
            self.texts = self.df['text'].tolist()
            self.db_connected = not bool(self.frozen_corpus_path)
            
        except Exception as e:
            print(f"❌ Hata: Veritabanına bağlanılamadı veya tablo yok! {e}")
            print("⚠️ ÇEVRİMDIŞI MOD: Yerel CSV dosyasından veri yükleniyor...")
            
            if self.frozen_corpus_path:
                raise RuntimeError("Frozen corpus could not be read; fallback is forbidden.") from e
            loaded = False
            for path in [self.csv_path, os.path.join(self.root_dir, 'data', 'processed', 'egitim_verisi_30k.csv')]:
                if os.path.exists(path):
                    try:
                        self.df = pd.read_csv(path)
                        if 'id' not in self.df.columns:
                            self.df['id'] = range(1, len(self.df) + 1)
                        if 'authority' not in self.df.columns:
                            self.df['authority'] = 0.85
                        if 'label' not in self.df.columns:
                            self.df['label'] = 1
                        self.texts = self.df['text'].astype(str).tolist()
                        print(f"✅ Veri seti yüklendi: {len(self.df)} kayıt (Yerel CSV: {os.path.basename(path)}).")
                        loaded = True
                        break
                    except Exception as csv_err:
                        print(f"⚠️ CSV yükleme hatası ({os.path.basename(path)}): {csv_err}")
            
            if not loaded:
                print("❌ Kritik Hata: Yerel CSV dosyası da bulunamadı!")
                self.df = pd.DataFrame(columns=['id', 'text', 'label', 'authority'])
                self.texts = []

        # BM25 İndeksi Oluşturma
        for field in PROVENANCE_FIELDS:
            if field not in self.df.columns:
                self.df[field] = "unknown" if field == "label_provenance" else ""
            else:
                self.df[field] = self.df[field].fillna("")

        if self.texts:
            def tokenize(text):
                return re.findall(r'\w+', turkish_lower(text))
            
            tokenized_corpus = [tokenize(doc) for doc in self.texts]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print("🔍 BM25 Kelime İndeksi hazırlandı.")
        else:
            print("⚠️ Uyarı: Metin bulunamadığı için BM25 İndeksi oluşturulamadı.")

        # --- YENI: Knowledge Base (Öğrenme Dosyası) Yükleme ---
        try:
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                self.kb = json.load(f) # type: ignore
            print("🧠 Yerel bilgi birikimi (Knowledge Base) yüklendi.")
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"Uyari: knowledge_base.json bulunamiyor veya bozuk ({type(e).__name__}), bos ayarlar kullanilacak.")
            self.kb = {"greetings": [], "synonyms": {}, "responses": {}} # type: ignore

    def load_search_model(self):
        if self.search_model is not None:
            return
        print("Vektor Arama (Embedding) modeli yukleniyor...")
        if os.path.exists(self.local_model_path):
            print("Yerel model kullaniliyor: %s" % self.local_model_path)
            self.search_model = SentenceTransformer(self.local_model_path)
        else:
            # Faz 2 (2026-09-13): multilingual-e5-small yerine e5-large kullan
            # models.json içinde embedding.model_id zaten güncellendi.
            _models_json = os.path.join(self.root_dir, '.runtime', 'evaluation_models', 'models.json')
            _emb_model_id = 'intfloat/multilingual-e5-large'
            _cache_dir = os.path.join(self.root_dir, '.runtime', 'evaluation_models', 'cache')
            if os.path.exists(_models_json):
                try:
                    import json as _json
                    _models_data = _json.loads(open(_models_json, encoding='utf-8').read())
                    _emb_model_id = _models_data.get('embedding', {}).get('model_id', _emb_model_id)
                    _emb_path = _models_data.get('embedding', {}).get('path', '')
                    if _emb_path and os.path.exists(_emb_path):
                        self.search_model = SentenceTransformer(_emb_path)
                    else:
                        self.search_model = SentenceTransformer(_emb_model_id, cache_folder=_cache_dir)
                except Exception as _e:
                    print("models.json okunamadi, fallback: %s" % _e)
                    self.search_model = SentenceTransformer(_emb_model_id, cache_folder=_cache_dir)
            else:
                self.search_model = SentenceTransformer(_emb_model_id, cache_folder=_cache_dir)
        self.search_model.half()
        print("Vektor Arama modeli hazir (FP16)!")

        # Embeddings Hesapla (Eğer PostgreSQL bağlı değilse RAM'e yükle - Hızlı Başlangıç Önbellekli)
        if not getattr(self, 'db_connected', False) and self.texts:
            # Faz 2: e5-large precomputed embeddings önce kontrol et
            _snapshot_dir = os.path.join(self.root_dir, 'data', 'corpus_snapshots', 'local_csv_20260913_v2')
            _e5_large_npy = os.path.join(_snapshot_dir, 'embeddings_e5_large.npy')
            npy_path = self.csv_path.replace('.csv', '_embeddings.npy')

            # e5-large precomputed dosyası var mı ve boyut uyuşuyor mu?
            _loaded_from_precomputed = False
            if os.path.exists(_e5_large_npy):
                try:
                    _loaded = np.load(_e5_large_npy)
                    if len(_loaded) == len(self.texts):
                        self.text_embeddings = _loaded
                        print("e5-large onceden hesaplanmis vektorler yuklendi: %d vektor, dim=%d" % (
                              len(self.text_embeddings), self.text_embeddings.shape[1]))
                        _loaded_from_precomputed = True
                    else:
                        print("e5-large boyut uyusmuyor (%d vs %d), yeniden hesaplaniyor..." % (
                              len(_loaded), len(self.texts)))
                except Exception as _e:
                    print("e5-large npy yuklenemedi: %s" % _e)

            if not _loaded_from_precomputed:
                # Legacy npy cache kontrol et
                if os.path.exists(npy_path):
                    print("Vektor onbellegi bulundu: %s" % os.path.basename(npy_path))
                    try:
                        self.text_embeddings = np.load(npy_path)
                        if len(self.text_embeddings) == len(self.texts):
                            print("%d vektor oncellekten yuklendi." % len(self.text_embeddings))
                        else:
                            print("Vektor sayisi uyusmuyor, yeniden hesaplaniyor...")
                            self.text_embeddings = []
                    except Exception as cache_err:
                        print("Onbellek okunamadi: %s" % cache_err)
                        self.text_embeddings = []

            if len(self.text_embeddings) == 0:
                print("Vekorler RAM'e yukleniyor (e5-large)...")
                try:
                    passage_texts = ["passage: " + str(t) for t in self.texts]
                    self.text_embeddings = self.search_model.encode(
                        passage_texts, convert_to_numpy=True,
                        show_progress_bar=False, batch_size=64
                    ).astype(np.float32)
                    if not self.frozen_corpus_path:
                        np.save(npy_path, self.text_embeddings)
                    print("%d vektor RAM'e yuklendi." % len(self.text_embeddings))
                except Exception as e:
                    print("Vektorler hesaplanirken hata: %s" % e)
                    self.text_embeddings = []
                    if self.frozen_corpus_path:
                        raise RuntimeError("Frozen-run embeddings failed; evaluation cannot fall back.") from e
        else:
            print("⏳ Vektörler veritabanından sorgulanacak, RAM'e yüklenmiyor.")
            self.text_embeddings = []

    def load_heavy_models(self):
        with self._model_lock:
            if self.nli_model is not None and (self.rerank_model is not None or getattr(self, "disable_reranker", False)):
                return
            print("Agir modeller yukleniyor (NLI + ReRanker)...")

        # NLI Modeli (Gerekçelendirme) — K-4 Doğrulama Katmanı
        if self.nli_model is None:
            from src.ai_core.layers.k4_nli import load_nli_model
            dev = 0 if torch.cuda.is_available() else -1
            self.nli_model = load_nli_model(self.model_paths.get('nli', 'joeddav/xlm-roberta-large-xnli'), device=dev)

        # --- YENI: Layer 3 Re-Ranker Modeli (Keskin Nişancı) ---
        if not getattr(self, "disable_reranker", False):
            if self.rerank_model is None:
                print("⏳ Re-Ranker model yükleniyor (bge-reranker-v2-m3)...")
                self.rerank_model = CrossEncoder(self.model_paths.get('reranker', 'BAAI/bge-reranker-v2-m3'))
                if hasattr(self.rerank_model, 'model') and self.rerank_model.model:
                    self.rerank_model.model.half()
        else:
            self.rerank_model = None

        # --- YENI: Sınıflandırma Modeli Yükleme ---
        self.classifier_model = None
        self.classifier_tokenizer = None
        if os.path.exists(self.classifier_model_path):
            print(f"📂 Yerel sınıflandırma modeli yükleniyor: {self.classifier_model_path}")
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            try:
                self.classifier_tokenizer = AutoTokenizer.from_pretrained(self.classifier_model_path)
                self.classifier_model = AutoModelForSequenceClassification.from_pretrained(self.classifier_model_path)
                self.classifier_model = self.classifier_model.half()
                if torch.cuda.is_available():
                    self.classifier_model = self.classifier_model.to("cuda")
                self.classifier_model.eval()
                print("✅ Sınıflandırma modeli hazır (FP16)!")
            except Exception as e:
                print(f"⚠️ Sınıflandırma modeli yüklenirken hata oldu: {e}")
        print("✅ Tüm Akıl Yürütme modelleri hazır!")

    # --- MANTIK FONKSİYONLARI ---

    def context_merger(self, current_query):
        """
        NLP Konsept Birleştirici (Katman 7): Eğer yeni sorgu eksikse 
        (örn: 'peki ya Ankara?'), önceki sorgunun bağlamıyla birleştirir.
        """
        if not self.context_buffer:
            return current_query

        q_clean = turkish_lower(current_query).strip()
        tokens = q_clean.split()
        
        # Takip sorusu tetikleyicileri
        follow_up_triggers = {'peki', 'ya', 've', 'kim', 'nerede', 'ne', 'nasıl', 'neden'}
        
        # Sadece takip sorusu tetikleyicisi varsa veya sorgu çok kısaysa ve bir soru eki/takip belirtisi barındırıyorsa bağlam ara
        is_follow_up = False
        if tokens:
            if tokens[0] in follow_up_triggers:
                is_follow_up = True
            elif len(tokens) <= 2 and any(t in q_clean for t in ['ya', 'peki', 've', 'ki', 'mu', 'mi', 'mı', 'mü']):
                is_follow_up = True

        if is_follow_up:
            last_query = self.context_buffer[-1]['query']
            merged = f"{last_query} {current_query}"
            print(f"🔗 NLP Katman 7 (Konsept Birleştirme): '{current_query}' -> '{merged}'")
            return merged

        return current_query

    # --- METİN VE NİYET ANALİZİ (TextAnalysisMixin üzerinden kalıtımla sağlanır) ---

    def resolve_source_authority(self, record):
        """K-8: Dinamik otorite skorunu kaynak, url veya kanal bilgisine göre belirler."""
        pub = str(record.get('publisher', '') or '').lower().strip()
        url = str(record.get('source_url', '') or '').lower().strip()
        for src, auth in SOURCE_AUTHORITY_TABLE.items():
            if src in pub or src in url:
                return auth
        text = str(record.get('text', '') or '')
        channel = self.detect_source_channel(text).lower()
        for src, auth in SOURCE_AUTHORITY_TABLE.items():
            if src in channel:
                return auth
        return float(record.get('authority', 0.85))

    def _calibrate_decision(self, res, k6_prediction, k9_consensus, db_label, sim_score):
        """K-6 (sınıflandırıcı) ve K-9 (çoklu kaynak konsensüsü) sinyalleri ile nihai kararı kalibre eder."""
        if not res or not isinstance(res, dict):
            return res

        status = res.get("status")
        conf = float(res.get("conf", 0))
        risk = float(res.get("risk", 0))
        desc = res.get("desc", "")

        # 1. K-9 Konsensüs Analizi
        if k9_consensus and isinstance(k9_consensus, dict):
            has_conflict = k9_consensus.get("has_conflict", False)
            majority_label = k9_consensus.get("label")
            total_sources = k9_consensus.get("total_sources", 1)
            agreement_count = k9_consensus.get("agreement_count", 1)

            # Eğer birden fazla kaynak varsa ve konsensüs çoğunluğu en iyi adayla çelişiyorsa
            if total_sources >= 2 and majority_label is not None and majority_label != db_label:
                res["k9_majority_override"] = True
                conf = max(40.0, conf - 25.0)
                risk = min(90.0, risk + 25.0)
                desc += f" (⚠️ Çoklu kaynak konsensüsünde {total_sources} kaynaktan {agreement_count}'i aksi yönde etiketlenmiştir.)"
                if status == "ONAY":
                    status = "KISMI"
                    res["msg"] = "⚠️ **KAYNAK UYUŞMAZLIĞI / ÇELİŞKİLİ KONSENSÜS**"
            elif has_conflict:
                conf = max(50.0, conf - 10.0)
                risk = min(85.0, risk + 15.0)
                desc += " (Kaynaklar arasında kısmi görüş ayrılığı mevcuttur.)"

        # 2. K-6 Model Tahmini ile Kalibrasyon
        if k6_prediction and isinstance(k6_prediction, dict) and k6_prediction.get("available"):
            k6_label = k6_prediction.get("predicted_label")  # 0: yalan, 1: doğru
            k6_conf = float(k6_prediction.get("confidence") or 0.0)

            if k6_conf >= 0.70:
                # NLI ve K-6 uyumlu ise güven pekiştirilir
                if (status in ("RED", "UYARI") and k6_label == 0) or (status == "ONAY" and k6_label == 1):
                    conf = min(99.0, conf + 5.0)
                    risk = max(5.0, risk - 5.0) if status == "ONAY" else min(95.0, risk + 5.0)
                # NLI ONAY demiş ama K-6 yüksek güvenle YALAN diyorsa
                elif status == "ONAY" and k6_label == 0 and k6_conf >= 0.85:
                    conf = max(55.0, conf - 20.0)
                    risk = max(risk, 55.0)
                    desc += " (⚠️ Yardımcı sınıflandırıcı metin yapısını şüpheli buldu.)"

        res["status"] = status
        res["conf"] = round(conf, 1)
        res["risk"] = round(risk, 1)
        res["desc"] = desc
        return res

    def karar_motoru(self, user_query, db_record, nli_probs, sim_score, sig_rerank=0.0, k6_prediction=None, k9_consensus=None):
        res = self._raw_karar_motoru(user_query, db_record, nli_probs, sim_score, sig_rerank)
        return self._calibrate_decision(res, k6_prediction, k9_consensus, db_record.get('label'), sim_score)

    def _raw_karar_motoru(self, user_query, db_record, nli_probs, sim_score, sig_rerank=0.0):
        db_text = db_record['text']
        db_label = db_record['label']
        
        # 1. KELİME ÇAPASI
        is_relevant, missing_words = self.kelime_capasi_kontrolu(user_query, db_text, sim_score, sig_rerank)
        if not is_relevant:
            missing_str = ", ".join([w.upper() for w in missing_words])
            return {
                "status": "RET", "msg": "ℹ️ **BULUNAMADI / ALAKASIZ**",
                "desc": f"Veri tabanımda **'{missing_str}'** ile ilgili kayıt yok.", "conf": 0, "risk": 0, "cat": "YOK"
            }

        # 2. FARK ANALİZİ
        diff_user, diff_source, diff_match_score, diff_cat = self.akilli_fark_analizi(user_query, db_text)
        diff_msg = ""
        if diff_user and diff_source:
            diff_msg = f"\n⚠️ **Farklı Detay:** Siz **'{diff_user.upper()}'** dediniz, kaynakta **'{diff_source.upper()}'** geçiyor."

        # 3. NLI ANALİZİ — K-4 Kanonik Sıra: [entailment=0, neutral=1, contradiction=2]
        from src.ai_core.layers.k4_nli import IDX_ENTAILMENT, IDX_NEUTRAL, IDX_CONTRADICTION
        score_entail = nli_probs[IDX_ENTAILMENT]
        score_neutral = nli_probs[IDX_NEUTRAL]
        score_contra = nli_probs[IDX_CONTRADICTION]
        confidence = max(score_contra, score_neutral, score_entail) * 100
        
        # NLI modeli Nötr (Alakasız) diyorsa reddet.
        # Kritik fark kontrolü (YER, KİŞİ, SAYI), ancak belge ile iddia arasında asgari bir
        # anlamsal bağ varsa anlamlıdır. Tamamen alakasız bir belgedeki sayı/kişi farkı
        # bilgi yanlışlığı değil, alakasızlıktır.
        has_relevance = (sig_rerank >= 0.55 or sim_score >= 0.55)
        has_critical_mismatch = (
            has_relevance and
            diff_user is not None and 
            diff_source is not None and 
            diff_cat in ["YER", "KİŞİ", "SAYI", "KRİTİK UNVAN", "KİŞİ/YER/UNVAN"]
        )

        neutral_threshold = 0.65
        if sig_rerank > 0.65 or sim_score > 0.65:
            neutral_threshold = 0.80  # Güvenli eşleşmelerde eşiği esnetiyoruz
            
        if score_neutral > neutral_threshold and not has_critical_mismatch:
            return {
                "status": "RET", "msg": "ℹ️ **BULUNAMADI / ALAKASIZ**",
                "desc": "Veri tabanımda bu iddiayı doğrulayacak veya yalanlayacak mantıksal bir kayıt yok.", "conf": 0, "risk": 0, "cat": "GENEL"
            }

        # --- LABEL 1: DOĞRU HABERLER ---
        if db_label == 1:
            # A. Olumsuzluk farkı kontrolü
            user_neg = self.detect_negation(user_query)
            source_relevant_text = self.get_relevant_sentences(user_query, db_text, top_n=1)
            source_neg = self.detect_negation(source_relevant_text)
            if user_neg != source_neg:
                return {
                    "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**",
                    "desc": "Yalanlandı, iddianızın olumluluk/olumsuzluk yapısı kaynakla örtüşmüyor.",
                    "conf": 95, "risk": 85, "cat": "OLAY_OLUMSUZLUK"
                }

            # B. Hiçbir fark bulunamadıysa veya NLI entailment güçlüyse doğrula
            if score_entail >= 0.60 or ((not diff_user and not diff_source) and score_entail >= 0.40 and score_entail >= score_contra):
                return {
                    "status": "ONAY", "msg": "✅ **DOĞRULANDI**",
                    "desc": "Doğrulandı, bilgi güvenilir kaynaklarla uyuşuyor.",
                    "conf": max(int(sim_score * 100), 95), "risk": 5, "cat": "GENEL"
                }

            # C. Kritik Fark Kontrolleri (Yalnızca NLI güçlü bir entailment vermediyse devreye girer)
            if diff_user and diff_source and score_entail < 0.70:
                if diff_cat == "SAYI":
                    return {
                        "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**",
                        "desc": f"Yalanlandı, sayısal değerde hata var. Siz '{diff_user}' dediniz, kaynakta '{diff_source}' geçiyor.",
                        "conf": 99, "risk": 75, "cat": "SAYI"
                    }
                elif diff_cat == "KRİTİK UNVAN":
                    return {
                        "status": "RED", "msg": "🚨 **KRİTİK UNVAN HATASI**",
                        "desc": f"Yalanlandı, unvanda kritik hata tespit edildi. {diff_msg}",
                        "conf": 95, "risk": 85, "cat": "KRİTİK UNVAN"
                    }
                elif diff_cat == "ZAMAN AŞIMI":
                    return {
                        "status": "KISMI", "msg": "⏳ **GÜNCEL DEĞİL / ZAMAN AŞIMI**",
                        "desc": f"Kısmen doğru, ancak bu bilgi artık geçerliliğini yitirmiş olabilir. {diff_msg}",
                        "conf": 85, "risk": 45, "cat": "ZAMAN AŞIMI"
                    }
                elif diff_cat in ["YER", "KİŞİ", "KİŞİ/YER/UNVAN"]:
                    return {
                        "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**",
                        "desc": f"Yalanlandı, kişi, yer veya unvan bilgisinde hata var. {diff_msg}",
                        "conf": 95, "risk": 70, "cat": diff_cat
                    }

            # C. NLI Kararı (Fark yoksa NLI modeline güvenebiliriz)
            if score_contra > 0.50:
                 return { "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**", "desc": "Yalanlandı, bilgi güvenilir kaynaklarla çelişiyor.", "conf": max(confidence, 85), "risk": 60, "cat": diff_cat }
            if score_entail > 0.40 and score_entail >= score_contra:
                # DENGELİ RİSK: Onaylandığında risk düşük olmalı
                return { "status": "ONAY", "msg": "✅ **DOĞRULANDI**", "desc": "Doğrulandı, bilgi güvenilir kaynaklarla uyuşuyor.", "conf": confidence, "risk": max(10, 100 - confidence), "cat": diff_cat }
            elif sim_score > 0.60:
                # Diğer ufak anlamsal farklar
                msg = "⚠️ **KISMİ DOĞRU / DETAY HATASI**"
                desc = f"Kısmen doğru, ancak detaylarda hata var.{diff_msg}"
                
                if diff_match_score > self.SEMANTIC_SHIFT_THRESHOLD:
                    return { "status": "KISMI", "msg": msg, "desc": desc, "conf": sim_score * 100, "risk": 45, "cat": diff_cat }
                else:
                     return { "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**", "desc": f"Yalanlandı, detaylar güvenilir kaynaklarla uyuşmuyor.{diff_msg}", "conf": 80, "risk": 65, "cat": diff_cat }
            else:
                 return { "status": "RET", "msg": "ℹ️ **BULUNAMADI**", "desc": "Kaynaklarda eşleşme bulunamadı.", "conf": 0, "risk": 0, "cat": "BELİRSİZ" }

        # --- LABEL 0: YALAN HABERLER ---
        else:
            # A. Olumsuzluk farkı kontrolü (Yalan habere karşı olumsuzluk kontrolü)
            user_neg = self.detect_negation(user_query)
            source_relevant_text = self.get_relevant_sentences(user_query, db_text, top_n=1)
            source_neg = self.detect_negation(source_relevant_text)
            if user_neg != source_neg:
                # Yalan haberi "olumsuz" sorduysa (örn: yalanlanmış bir şeyi yapılmadı dedi) durum değişir
                # Ancak güvenli tarafta kalıp uyarı göstermek mantıklıdır
                pass

            # B. Hiçbir fark bulunamadıysa (kullanıcı yalan haberi aynen tekrarlıyorsa)
            if not diff_user and not diff_source:
                user_is_skeptic = any(w in turkish_lower(user_query) for w in self.SKEPTIC_KEYWORDS)
                if user_is_skeptic:
                    return {
                        "status": "ONAY", "msg": "✅ **DOĞRU TESPİT**",
                        "desc": "Doğrulandı, şüpheleriniz haklı. Bu haber aslısız/yalan olarak teyit edilmiştir.",
                        "conf": 99, "risk": 10, "cat": "GENEL"
                    }
                else:
                    return {
                        "status": "UYARI", "msg": "❌ **HAYIR / ASILSIZ İDDİA**",
                        "desc": "Yalanlandı, bu iddia gerçeği yansıtmıyor. Kaynaklar bu bilginin aslısız olduğunu gösteriyor.",
                        "conf": 99, "risk": 95, "cat": "GENEL"
                    }

            user_is_skeptic = any(w in turkish_lower(user_query) for w in self.SKEPTIC_KEYWORDS)
            if user_is_skeptic and score_entail > 0.40:
                 return { "status": "ONAY", "msg": "✅ **DOĞRU TESPİT**", "desc": "Doğrulandı, şüpheleriniz haklı. Bu haberin yalan olduğu kaynakta kayıtlıdır.", "conf": 95, "risk": 15, "cat": diff_cat }
            
            if score_entail > 0.45:
                return { "status": "UYARI", "msg": "❌ **HAYIR / ASILSIZ İDDİA**", "desc": "Yalanlandı, bu bilgi aslısız haber olarak işaretlenmiştir.", "conf": 99, "risk": 90, "cat": diff_cat }
            
            if score_contra > 0.45:
                return { "status": "ONAY", "msg": "✅ **DOĞRU TESPİT**", "desc": "Doğrulandı, karşı çıktığınız iddia zaten aslısız haber olarak işaretlenmiştir.", "conf": 99, "risk": 10, "cat": diff_cat }
            
            return { "status": "RET", "msg": "ℹ️ **YETERLİ VERİ YOK**", "desc": "Kaynaklarda net eşleşme bulunamadı.", "conf": 50, "risk": 40, "cat": "YOK" }

    def ask(self, raw_query, *, claim_date=None, include_trace=False, independent=False):
        if independent and not self.frozen_corpus_path:
            raise ValueError("Independent evaluation requires an explicit frozen corpus.")
        if independent:
            self.context_buffer.clear()
        trace = {"retrieved_source_ids": [], "rerank_scores": [], "nli_probs": None,
                 "decision_probs": None, "nli_bypassed": False, "cache_hit": False,
                 "layer_latency_ms": {}, "context_reset": independent}
        token = _evaluation_trace.set(trace if include_trace else None)
        start = time.perf_counter()
        try:
            result = self._ask(raw_query, claim_date=claim_date)
            if include_trace:
                trace["latency_ms"] = (time.perf_counter() - start) * 1000
                trace["raw_status"] = result.get("status")
                result["trace"] = trace
            return result
        finally:
            _evaluation_trace.reset(token)

    def _ask(self, raw_query, claim_date=None):
        """Dış dünyadan gelen soruya cevap veren ana fonksiyon"""
        stage_start = time.perf_counter()
        raw_query = split_numbers_letters(raw_query)
        # Veritabanındaki yeni kayıtları senkronize et
        self.sync_db()
        
        self.load_search_model()
        self.load_heavy_models()
        
        # 0. Girdi Doğrulama
        alphanumeric_query = re.sub(r'[^\w\s]', '', raw_query)
        if len(alphanumeric_query.strip()) < 2: # 'Ya?' gibi kısa takipleri de artık kabul edebiliriz
            return {
                "result": "⚠️ GEÇERSİZ GİRDİ: Lütfen doğrulamak istediğiniz iddiayı açıkça yazın.",
                "status": "RET", "msg": "⚠️ GEÇERSİZ GİRDİ", 
                "description": "Çok kısa veya tanımsız sorgu.", 
                "confidence": 0, "risk": 0, "category": "YOK", "source": "-"
            }
            
        # 0.1. Katman 7: Konsept Birleştirme
        trace_elapsed("K1_input_and_readiness", stage_start)
        stage_start = time.perf_counter()
        contextual_query = self.context_merger(raw_query)
        trace_elapsed("K7_context", stage_start)
        stage_start = time.perf_counter()
        clean_query = self.temizle_ve_normallestir(contextual_query)
        trace_elapsed("K1_normalization", stage_start)
        print(f"\n📩 Gelen: {raw_query} | Analitik Bağlam: {contextual_query}")

        # Tek kelimelik anlamsız aramaları engelle (Eğer selamlaşma değilse)
        # Sadece 1 kelime girildiyse (örn: "sinan"), bunu bir iddia olarak kabul etme.
        if len(clean_query.split()) < 2 and clean_query not in self.kb.get("greetings", []):
            return {
                "result": "⚠️ Lütfen doğrulamak istediğiniz iddiayı tam bir cümle veya daha detaylı olarak yazın. Sadece isim veya tek bir kelime girdiğinizde doğrulama yapılamamaktadır.",
                "status": "RET", "msg": "⚠️ EKSİK İDDİA", 
                "description": "Sorgu tek kelimeden oluşuyor, geçerli bir iddia barındırmıyor.", 
                "confidence": 0, "risk": 0, "category": "YOK", "source": "-"
            }

        # Katman 6 bağımsız, yardımcı bir sinyaldir. Nihai doğrulama kararına
        # girmez; çağrıya özgü sözlükte tutulur, böylece eşzamanlı istekler
        # birbirinin sınıflandırıcı sonucunu paylaşmaz.
        stage_start = time.perf_counter()
        classifier_prediction = self.predict_classifier(contextual_query)
        trace_elapsed("K6_advisory", stage_start)

        # 1. Niyet Analizi
        stage_start = time.perf_counter()
        intent = self.intent_analyzer(clean_query)
        trace_elapsed("K1_intent", stage_start)
        if intent == "ABOUT":
            about_text = (
                "KızılelmAI'nin amacı, internette ve sosyal medyada yayılan haber ve iddiaların doğruluğunu "
                "pgvector (vektörel arama) ve BM25 (kelime bazlı arama) hibrit algoritmalarıyla resmi ve "
                "güvenilir kaynaklardan saniyeler içinde teyit etmektir. Bu proje, 3 üniversite öğrencisi olan "
                "İbrahim Sinan AKBULUT, Doğukan KILIÇ ve Merve ATILGAN tarafından geliştirilmiştir."
            )
            return {
                "result": about_text,
                "status": "ONAY", "msg": "🛡️ KIZILELMAI HAKKINDA",
                "description": "Proje amacı ve geliştirici ekibi hakkında bilgilendirme.",
                "confidence": 100, "risk": 0, "category": "ABOUT", "source": "-"
            }
        if intent == "GREETING":
            greet_text = self.kb["responses"].get("greeting", "Merhaba! Size nasıl yardımcı olabilirim?")
            return {
                "result": greet_text,
                "status": "ONAY", "msg": "👋 MERHABA", 
                "description": "KızılelmAI hazır bekliyor.", 
                "confidence": 100, "risk": 0, "category": "GREETING", "source": "-"
            }

        # 2. Sorgu Genişletme (Öğretilen kelimeleri kullan)
        stage_start = time.perf_counter()
        search_query = self.query_expander(clean_query)
        print(f"🔍 Arama Sorgusu (Genişletilmiş): {search_query}")

        # 1. DENSE RETRIEVAL (Semantic - Vektör Arama PostgreSQL veya in-memory)
        query_text = f"query: {search_query}"
        query_emb = self.search_model.encode([query_text])[0].astype(np.float32)
        
        dense_sims = np.zeros(len(self.texts))
        
        if getattr(self, 'db_connected', False):
            try:
                with self.db_engine.connect() as conn:
                    query_emb_str = "[" + ",".join(map(str, query_emb.tolist())) + "]"
                    # pgvector <=> operatörü kosinüs mesafesi döndürür (1 - cosine_similarity). Biz benzerlik (sim) istiyoruz.
                    sql = text("SELECT id, 1 - (embedding <=> :q) as sim FROM knowledge_base")
                    result = conn.execute(sql, {"q": query_emb_str}).fetchall()
                    
                id_to_idx = {row_id: idx for idx, row_id in enumerate(self.df['id'])}
                for row in result:
                    if row.id in id_to_idx:
                        dense_sims[id_to_idx[row.id]] = row.sim
            except Exception as e:
                print(f"Vektör arama hatası: {e}. RAM üzerinden aramaya geçiliyor...")
                if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                    dense_sims = cosine_similarity([query_emb], self.text_embeddings)[0]
        if getattr(self, "disable_dense", False):
            dense_sims = np.zeros(len(self.texts))
        else:
            if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                dense_sims = cosine_similarity([query_emb], self.text_embeddings)[0]
        
        # 2. SPARSE RETRIEVAL (Keyword - BM25 Arama)
        if getattr(self, "disable_bm25", False) or self.bm25 is None:
            bm25_scores = np.zeros(len(self.texts))
        else:
            tokenized_query = re.findall(r'\w+', turkish_lower(search_query))
            bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # 3. RECIPROCAL RANK FUSION (Hibrit Harmanlama)
        candidate_limit = 40 if torch.cuda.is_available() else 20
        if getattr(self, "disable_dense", False):
            sparse_order = np.argsort(bm25_scores)[::-1]
            top_indices = list(sparse_order[:candidate_limit])
        elif getattr(self, "disable_bm25", False):
            dense_order = np.argsort(dense_sims)[::-1]
            top_indices = list(dense_order[:candidate_limit])
        else:
            dense_order = np.argsort(dense_sims)[::-1]
            dense_rank = {idx: rank for rank, idx in enumerate(dense_order)}
            
            sparse_order = np.argsort(bm25_scores)[::-1]
            sparse_rank = {idx: rank for rank, idx in enumerate(sparse_order)}
            
            k = 60
            fused_scores = {}
            for idx in range(len(self.texts)):
                score = (1 / (k + dense_rank[idx])) + (1 / (k + sparse_rank[idx]))
                fused_scores[idx] = score
                
            top_indices = sorted(list(fused_scores.keys()), key=lambda x: fused_scores[x], reverse=True)[:candidate_limit] # type: ignore
        
        # --- KATMAN 3: RE-RANKING (The Sniper) ---
        trace_elapsed("K2_retrieval", stage_start)
        trace = _evaluation_trace.get()
        if trace is not None:
            trace["retrieved_source_ids"] = [int(self.df.iloc[idx]["id"]) for idx in top_indices]
        stage_start = time.perf_counter()
        if not getattr(self, "disable_reranker", False) and self.rerank_model is not None:
            rerank_pairs = [[search_query, self.texts[idx]] for idx in top_indices]
            rerank_output = self.rerank_model.predict(rerank_pairs) if self.rerank_model else None # type: ignore
            rerank_scores = list(rerank_output) if rerank_output is not None else [0.0] * len(top_indices)
        else:
            # Re-ranker bypass: keep retrieval order with descending positive scores
            rerank_scores = [float(2.0 - (i * 0.05)) for i in range(len(top_indices))]
        trace_elapsed("K3_reranker", stage_start)
        if trace is not None:
            trace["rerank_scores"] = [float(v) for v in rerank_scores]
        stage_start = time.perf_counter()
        
        # Yeni skorlarla adayları tekrar eşleştir ve sırala
        ranked_candidates = []
        for i, idx in enumerate(top_indices):
            # Katman 8: Otorite Ağırlıklandırması (Normalizasyon ve Dinamik Kaynak Otoritesi ile)
            auth = self.resolve_source_authority(self.df.iloc[idx])
            
            # Reranker skoru: Eğer model çıktısı zaten [0, 1] aralığında bir olasılık ise doğrudan kullan;
            # raw logit ise yumuşatılmış sigmoid uygula.
            raw_rerank = float(rerank_scores[i])
            if 0.0 <= raw_rerank <= 1.0:
                sig_rerank = raw_rerank
            else:
                sig_rerank = 1 / (1 + np.exp(-raw_rerank / 2)) # Yumuşatılmış sigmoid
            
            # Hibrit Skor = (Sigmoid(Rerank) * 0.7) + (Authority * 0.3)
            weighted_score = (sig_rerank * (1 - self.AUTHORITY_WEIGHT)) + (auth * self.AUTHORITY_WEIGHT)
            
            ranked_candidates.append({
                'idx': int(idx),
                'rerank_score': raw_rerank,
                'sig_rerank': sig_rerank,
                'weighted_score': weighted_score,
                'dense_sim': float(dense_sims[idx]),
                'bm25_score': float(bm25_scores[idx]),
                'authority': auth
            })
        
        # Ağırlıklı skora göre sırala
        ranked_candidates = sorted(ranked_candidates, key=lambda x: x['weighted_score'], reverse=True)
        trace_elapsed("K8_weighted_ranking", stage_start)
        stage_start = time.perf_counter()
        
        candidates = []
        # Re-ranker veto eşiği: Re-ranker alaka olasılığı %30'un altındaki adayları filtrele
        RERANK_VETO_THRESHOLD = 0.30 

        for cand in ranked_candidates:
            idx = cand['idx']
            s_score = cand['sig_rerank']
            
            if s_score >= RERANK_VETO_THRESHOLD:
                if cand['dense_sim'] > self.RETRIEVAL_THRESHOLD or cand['bm25_score'] > 1.5:
                    candidates.append({
                        'id': int(self.df.iloc[idx]['id']) if 'id' in self.df.columns else idx,
                        'text': self.df.iloc[idx]['text'], 
                        'label': int(self.df.iloc[idx]['label']), 
                        'sim': cand['dense_sim'],
                        'rerank_score': cand['rerank_score'],
                        'authority': cand['authority'],
                        'sig_rerank': cand['sig_rerank'],
                        **{key: self.df.iloc[idx].get(key, "") for key in PROVENANCE_FIELDS}
                    })

        trace_elapsed("K3_candidate_filters", stage_start)
        
        # Yerel korpusta iddia ile doğrudan örtüşen güçlü kanıt var mı?
        corpus_has_strong_evidence = False
        if candidates:
            best_local = candidates[0]
            is_rel, _ = self.kelime_capasi_kontrolu(clean_query, best_local['text'], best_local['sim'], best_local['sig_rerank'])
            if is_rel and (best_local['sig_rerank'] >= 0.50 or (best_local['sig_rerank'] >= 0.35 and best_local['sim'] >= 0.60)):
                corpus_has_strong_evidence = True

        if not corpus_has_strong_evidence:
            # K-2 Web Fallback: Yerel korpus yetersiz kaldığında birincil kaynaklardan kanıt ara
            if getattr(self, "enable_web_retrieval", False) or not self.frozen_corpus_path:
                web_candidates = self._try_web_retrieval(raw_query, claim_date=claim_date)
                if web_candidates:
                    if not candidates or web_candidates[0]['sig_rerank'] >= candidates[0]['sig_rerank']:
                        candidates = web_candidates
                        if trace is not None:
                            trace["web_retrieval_used"] = True
                    else:
                        candidates = sorted(candidates + web_candidates, key=lambda x: x['sig_rerank'], reverse=True)
                # Not: Webden sonuç dönmese bile yerel adaylar (varsa) korunur!

        if trace is not None:
            trace["accepted_source_ids"] = [c["id"] for c in candidates]
        if not candidates:
            return self.local_response_engine(raw_query, {'text': '-'}, {
                "status": "RET", "msg": "📭 KAYIT BULUNAMADI", 
                "desc": "Veri tabanımda bu konuyla örtüşen bir bilgiye ulaşılamadı.", 
                "conf": 0, "risk": 0, "cat": "YOK"
            }, classifier_prediction)
            
        # Katman 9: Multi-Source Consensus (Konsensüs Analizi)
        stage_start = time.perf_counter()
        top_k = min(3, len(candidates))
        top_sources = candidates[:top_k]
        labels = [c['label'] for c in top_sources]
        
        most_common_label = max(set(labels), key=labels.count)
        agreement_count = labels.count(most_common_label)
        is_consensus = agreement_count == len(labels) if len(labels) >= 2 else True
        has_conflict = not is_consensus and len(labels) >= 2
        
        best_cand = top_sources[0]
        
        consensus_info = {
            "is_consensus": is_consensus,
            "has_conflict": has_conflict,
            "total_sources": len(top_sources),
            "agreement_count": agreement_count,
            "label": most_common_label
        }
        trace_elapsed("K9_advisory_consensus", stage_start)
        stage_start = time.perf_counter()
        if trace is not None:
            trace["selected_source_id"] = best_cand["id"]
        
        print(f"🎯 Sniper Seçimi (Ağırlıklı): {best_cand['text'][:50]}... | Otorite: {best_cand['authority']}")
        
        # Mantıksal NLI Bypass Optimizasyonu:
        diff_user, diff_source, diff_match_score, diff_cat = self.akilli_fark_analizi(raw_query, best_cand['text'])
        
        # Fark yoksa, semantik uyuşma çok yüksekse ve kaynak yalanlama içermiyorsa NLI bypass et
        cand_text_lower = best_cand['text'].lower()
        has_debunk_kw = any(w in cand_text_lower for w in ["yalan", "iddia", "asılsız", "sahte", "montaj", "şüphe", "iddiası"])
        if diff_user is None and diff_source is None and best_cand['sim'] >= 0.88 and not has_debunk_kw and best_cand.get('label') == 1:
            print("⚡ NLP Mantıksal Bypass: Eşleşmede fark tespit edilmedi, NLI modeli atlandı (Bypass).")
            probs = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # Kanonik: [entailment=1, neutral=0, contradiction=0]
            if trace is not None:
                trace["nli_bypassed"] = True
        else:
            # NLI Tahmini: K-4 katmanı üzerinden premise=kaynak, hypothesis=iddia
            from src.ai_core.layers.k4_nli import run_nli
            probs_list = run_nli(clean_query, best_cand['text'], self.nli_model)
            probs = np.array(probs_list, dtype=np.float32)
            if trace is not None:
                trace["nli_probs"] = [float(p) for p in probs]
            print(f"🔍 Kaynak: {best_cand['text']} | Sim: {best_cand['sim']:.2f} | NLI: {probs}")

        # Karar
        trace_elapsed("K4_nli_and_bypass_check", stage_start)
        if trace is not None:
            trace["decision_probs"] = [float(p) for p in probs]
        stage_start = time.perf_counter()
        res = self.karar_motoru(
            raw_query, best_cand, probs,
            best_cand['sim'], best_cand.get('sig_rerank', 0.0),
            k6_prediction=classifier_prediction,
            k9_consensus=consensus_info
        )
        trace_elapsed("K5_decision", stage_start)
        res['consensus'] = consensus_info # Konsensüs verisini ekle

        # Eğer yerel korpus adayı yetersiz/nötr kaldıysa web getirimine ikinci şans ver
        if res.get('status') == 'RET' and (trace is None or not trace.get("web_retrieval_used")):
            if getattr(self, "enable_web_retrieval", False) or not self.frozen_corpus_path:
                web_candidates = self._try_web_retrieval(raw_query, claim_date=claim_date)
                if web_candidates:
                    best_cand = web_candidates[0]
                    if trace is not None:
                        trace["web_retrieval_used"] = True
                        trace["accepted_source_ids"] = [c["id"] for c in web_candidates]
                        trace["selected_source_id"] = best_cand["id"]

                    from src.ai_core.layers.k4_nli import run_nli
                    probs_list = run_nli(clean_query, best_cand['text'], self.nli_model)
                    probs = np.array(probs_list, dtype=np.float32)
                    if trace is not None:
                        trace["nli_probs"] = [float(p) for p in probs]
                        trace["decision_probs"] = [float(p) for p in probs]

                    web_consensus = {
                        "is_consensus": True,
                        "has_conflict": False,
                        "total_sources": len(web_candidates),
                        "agreement_count": len(web_candidates),
                        "label": 1
                    }
                    res = self.karar_motoru(
                        raw_query, best_cand, probs,
                        best_cand['sim'], best_cand.get('sig_rerank', 0.0),
                        k6_prediction=classifier_prediction,
                        k9_consensus=web_consensus
                    )
                    res['consensus'] = web_consensus
        
        # Katman 7: Context Güncelleme (Sadece geçerli iddiaları sakla)
        if res.get('status') != 'RET':
            self.context_buffer.append({"query": raw_query, "category": res.get('cat')})
            if len(self.context_buffer) > self.MAX_CONTEXT:
                self.context_buffer.pop(0)

        # Artık yapılandırılmış bir sözlük (dict) dönüyoruz
        return self.local_response_engine(raw_query, best_cand, res, classifier_prediction)

    def predict_classifier(self, query):
        """Return the K-6 auxiliary prediction without affecting the verdict."""
        prediction = {
            "available": False,
            "advisory_only": True,
            "predicted_label": None,
            "p_false": None,
            "p_true": None,
            "confidence": None,
        }
        if not self.classifier_model or not self.classifier_tokenizer:
            return prediction
        try:
            import torch.nn.functional as F
            device = next(self.classifier_model.parameters()).device
            inputs = self.classifier_tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                logits = self.classifier_model(**inputs).logits
            probs = F.softmax(logits, dim=1)[0]
            p_false = float(probs[0].item())
            p_true = float(probs[1].item())
            predicted_label = 1 if p_true > 0.5 else 0
            return {
                "available": True,
                "advisory_only": True,
                "predicted_label": predicted_label,
                "p_false": p_false,
                "p_true": p_true,
                "confidence": max(p_false, p_true),
            }
        except Exception as e:
            print(f"⚠️ Sınıflandırma tahmini hatası: {e}")
            prediction["error"] = type(e).__name__
            return prediction

    def _try_web_retrieval(self, query: str, claim_date: Optional[str] = None):
        """
        K-2 Web Fallback: Yerel korpus yetersiz kaldığında veya güncel iddialarda
        tarih kısıtlı birincil haber/resmi kaynak araması yapar ve kanıt adayları üretir.
        """
        try:
            if getattr(self, "_web_retriever", None) is None:
                from src.ai_core.layers.k2_web_retrieval import TemporalWebRetriever
                self._web_retriever = TemporalWebRetriever()

            web_evidence = self._web_retriever.search_evidence(query, claim_date=claim_date)
            if not web_evidence:
                return []

            self.load_search_model()
            q_emb = self.search_model.encode([f"query: {query}"], convert_to_numpy=True)[0]
            norm_q = float(np.linalg.norm(q_emb))

            passage_texts = [f"passage: {c['text']}" for c in web_evidence]
            p_embs = self.search_model.encode(passage_texts, convert_to_numpy=True)

            pairs = [[query, c["text"]] for c in web_evidence]
            rerank_scores = [0.0] * len(web_evidence)
            sig_scores = [0.5] * len(web_evidence)
            if hasattr(self, "rerank_model") and self.rerank_model is not None:
                raw_s = self.rerank_model.predict(pairs)
                rerank_scores = [float(s) for s in raw_s]
                sig_scores = [float(s) if 0.0 <= float(s) <= 1.0 else float(1.0 / (1.0 + np.exp(-float(s) / 2.0))) for s in raw_s]

            scored_candidates = []
            for i, c in enumerate(web_evidence):
                norm_p = float(np.linalg.norm(p_embs[i]))
                sim = float(np.dot(q_emb, p_embs[i]) / (norm_q * norm_p)) if norm_q > 0 and norm_p > 0 else 0.0

                # Asgari anlamsal bağ ve kelime çapası kontrolü
                is_rel, _ = self.kelime_capasi_kontrolu(query, c["text"], sim, sig_scores[i])
                if is_rel and (sig_scores[i] >= 0.28 or (sig_scores[i] >= 0.20 and sim >= 0.48)):
                    c["sim"] = sim
                    c["rerank_score"] = rerank_scores[i]
                    c["sig_rerank"] = sig_scores[i]
                    
                    t_lower = c["text"].lower()
                    is_debunk = any(k in t_lower for k in [
                        "yalanlandı", "asılsız", "iddiası yalan", "gerçeği yansıtmıyor", 
                        "dezenformasyon", "doğru değil", "montaj olduğu", "kurgu olduğu", 
                        "sahte olduğu", "iddialar asılsız", "iddiaları yalanladı"
                    ])
                    c["label"] = 0 if is_debunk else 1
                    scored_candidates.append(c)

            scored_candidates.sort(key=lambda x: x["sig_rerank"], reverse=True)
            return scored_candidates
        except Exception as e:
            print(f"⚠️ [WebRetrieval] Arama hatası: {e}")
            return []

    # --- YANIT FORMATLAMA VE KANAL TESPİTİ (ResponseGeneratorMixin üzerinden kalıtımla sağlanır) ---

import os
import sys
import re
import json
import time
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
import uuid
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
PROVENANCE_FIELDS = ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at")

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

def turkish_lower(text):
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.replace('İ', 'i').replace('I', 'ı').lower()

def to_ascii_tr(text):
    """Türkçe özel karakterleri ASCII karşılıklarına dönüştürür (encoding güvenliği için)"""
    if not text:
        return ""
    tr_map = str.maketrans(
        'çÇğĞıIİöÖşŞüÜâÂêÊîÎûÛ',
        'cCgGiIioosSuUaAeEiIuU'
    )
    return text.translate(tr_map).lower()

def split_numbers_letters(text):
    if not text:
        return ""
    # Sayılardan sonra gelen harfleri ayır (örn: 25saatte -> 25 saatte)
    text = re.sub(r'(\d+)([^\d\s\W]+)', r'\1 \2', text)
    # Harflerden sonra gelen sayıları ayır (örn: saat25 -> saat 25)
    text = re.sub(r'([^\d\s\W]+)(\d+)', r'\1 \2', text)
    return text

class KizilelmaEngine:
    """
    KızılelmAI'nin tüm zekasını barındıran sınıf.
    Veriyi yükler, modelleri hazırlar ve sorulara cevap üretir.
    """
    def __init__(self, lazy_load=False, *, corpus_path=None, model_paths=None):
        print("[System] KizilElma Motoru Baslatiliyor...")
        
        # --- 1. Sabitler ve Ayarlar ---
        self.frozen_corpus_path = str(corpus_path) if corpus_path else None
        self.model_paths = model_paths or {}
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
        self.csv_path = os.environ.get(
            "KIZILELMAI_CSV_PATH", 
            os.path.join(self.root_dir, 'data', 'processed', 'egitim_verisi_final.csv')
        )
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
        print("⏳ Vektör Arama (Embedding) modeli yükleniyor...")
        if os.path.exists(self.local_model_path):
            print(f"📂 Yerel model kullanılıyor: {self.local_model_path}")
            self.search_model = SentenceTransformer(self.local_model_path)
        else:
            self.search_model = SentenceTransformer('intfloat/multilingual-e5-small')
        self.search_model.half()
        print("✅ Vektör Arama modeli hazır (FP16)!")

        # Embeddings Hesapla (Eğer PostgreSQL bağlı değilse RAM'e yükle - Hızlı Başlangıç Önbellekli)
        if not getattr(self, 'db_connected', False) and self.texts:
            npy_path = self.csv_path.replace('.csv', '_embeddings.npy')
            if os.path.exists(npy_path):
                print(f"📂 Vektör önbelleği bulundu, RAM'e yükleniyor: {os.path.basename(npy_path)}")
                try:
                    self.text_embeddings = np.load(npy_path)
                    if len(self.text_embeddings) == len(self.texts):
                        print(f"✅ {len(self.text_embeddings)} vektör önbellekten başarıyla yüklendi (Anında açılış!).")
                    else:
                        print("⚠️ Vektör sayısı uyuşmuyor, yeniden hesaplanıyor...")
                        self.text_embeddings = []
                except Exception as cache_err:
                    print(f"⚠️ Önbellek okunamadı: {cache_err}, yeniden hesaplanıyor...")
                    self.text_embeddings = []
            
            if len(self.text_embeddings) == 0:
                print("⏳ Çevrimdışı mod için vektörler RAM'e yükleniyor (Multilingual-E5-Small)...")
                try:
                    passage_texts = ["passage: " + str(t) for t in self.texts]
                    self.text_embeddings = self.search_model.encode(passage_texts, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
                    if not self.frozen_corpus_path:
                        np.save(npy_path, self.text_embeddings)
                    print(f"✅ {len(self.text_embeddings)} vektör RAM'e başarıyla yüklendi ve önbelleğe kaydedildi.")
                except Exception as e:
                    print(f"⚠️ Çevrimdışı modda vektörler hesaplanırken hata oluştu: {e}")
                    self.text_embeddings = []
                    if self.frozen_corpus_path:
                        raise RuntimeError("Frozen-run embeddings failed; evaluation cannot fall back.") from e
        else:
            print("⏳ Vektörler veritabanından sorgulanacak, RAM'e yüklenmiyor.")
            self.text_embeddings = []

    def load_heavy_models(self):
        with self._model_lock:
            if self.nli_model is not None and self.rerank_model is not None:
                return
            print("Agir modeller yukleniyor (NLI + ReRanker)...")


        # NLI Modeli (Gerekçelendirme)
        self.nli_model = CrossEncoder(self.model_paths.get('nli', 'joeddav/xlm-roberta-large-xnli'))
        if hasattr(self.nli_model, 'model') and self.nli_model.model:
            self.nli_model.model.half()

        # --- YENI: Layer 3 Re-Ranker Modeli (Keskin Nişancı) ---
        print("⏳ Re-Ranker model yükleniyor (bge-reranker-v2-m3)...")
        self.rerank_model = CrossEncoder(self.model_paths.get('reranker', 'BAAI/bge-reranker-v2-m3'))
        if hasattr(self.rerank_model, 'model') and self.rerank_model.model:
            self.rerank_model.model.half()

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
                self.classifier_model.eval()
                print("✅ Sınıflandırma modeli hazır (FP16)!")
            except Exception as e:
                print(f"⚠️ Sınıflandırma modeli yüklenirken hata oldu: {e}")
        print("✅ Tüm Akıl Yürütme modelleri hazır!")

    def sync_db(self):
        """
        Veritabanındaki yeni kayıtları bellekle senkronize eder.
        Throttle: En fazla her 60 saniyede bir çalışır.
        """
        if self.frozen_corpus_path:
            return
        now = time.time()
        with self._sync_lock:
            if now - self._last_sync_time < self.SYNC_INTERVAL:
                return  # Cok sik cagirilmamasi icin throttle
            self._last_sync_time = now

        if getattr(self, 'db_connected', False):
            try:
                max_id = int(self.df['id'].max()) if not self.df.empty else 0
                with self.db_engine.connect() as conn:
                    sql_new = text("SELECT * FROM knowledge_base WHERE id > :max_id ORDER BY id")
                    new_rows = pd.read_sql(sql_new, conn, params={"max_id": max_id}).drop(columns=["embedding"], errors="ignore")

                if not new_rows.empty:
                    print(f"[Sync] Veritabanindan {len(new_rows)} yeni kayit belleğe yukleniyor...")
                    self.df = pd.concat([self.df, new_rows], ignore_index=True)
                    self.texts = self.df['text'].tolist()

                    # BM25 guncelle (turkish_lower ile tutarli tokenize)
                    def tokenize(t): return re.findall(r'\w+', turkish_lower(str(t)))
                    tokenized_corpus = [tokenize(doc) for doc in self.texts]
                    self.bm25 = BM25Okapi(tokenized_corpus)
                    print(f"✅ [Sync] BM25 indeksi güncellendi. Toplam kayıt: {len(self.df)}")
            except Exception as e:
                print(f"⚠️ [Sync] Veritabanı senkronizasyon hatası: {e}")
        else:
            # ÇEVRİMDIŞI MOD: Yerel CSV dosyasından yeni kayıtları senkronize et
            try:
                if os.path.exists(self.csv_path):
                    csv_df = pd.read_csv(self.csv_path)
                    if len(csv_df) > len(self.df):
                        new_rows = csv_df.iloc[len(self.df):]
                        print(f"🔄 [Sync-Offline] CSV dosyasından {len(new_rows)} yeni kayıt belleğe yükleniyor...")
                        
                        # Eksik kolonları ayarla
                        if 'id' not in new_rows.columns:
                            new_rows['id'] = range(len(self.df) + 1, len(csv_df) + 1)
                        if 'authority' not in new_rows.columns:
                            new_rows['authority'] = 0.85
                        if 'label' not in new_rows.columns:
                            new_rows['label'] = 1
                            
                        self.df = pd.concat([self.df, new_rows], ignore_index=True)
                        new_texts = new_rows['text'].astype(str).tolist()
                        self.texts.extend(new_texts)
                        
                        # BM25 güncelle
                        def tokenize(t): return re.findall(r'\w+', str(t).lower())
                        tokenized_corpus = [tokenize(doc) for doc in self.texts]
                        self.bm25 = BM25Okapi(tokenized_corpus)
                        
                        # Vektör önbelleğini (embeddings) güncelle
                        if new_texts:
                            self.load_search_model()
                            passage_texts = ["passage: " + str(t) for t in new_texts]
                            new_embs = self.search_model.encode(passage_texts, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
                            
                            if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                                self.text_embeddings = np.vstack([self.text_embeddings, new_embs])
                            else:
                                self.text_embeddings = new_embs
                                
                        print(f"✅ [Sync-Offline] BM25 ve Vektörler güncellendi. Toplam kayıt: {len(self.df)}")
            except Exception as e:
                print(f"⚠️ [Sync-Offline] CSV senkronizasyon hatası: {e}")

    def inject_knowledge(self, input_text, label, authority=0.95, *, source_url=None, publisher=None,
                         published_at=None, evidence_id=None, label_provenance="unknown"):
        """
        Katman 10: Çalışma zamanında yeni bilgi enjekte eder (PostgreSQL ve/veya CSV).
        """
        if self.frozen_corpus_path:
            raise RuntimeError("Cannot inject into a frozen evaluation corpus.")
        self.load_search_model()
        new_emb = self.search_model.encode([f"passage: {input_text}"], convert_to_numpy=True)[0].astype(np.float32)
        provenance = {"source_url": source_url or "", "publisher": publisher or "", "published_at": published_at or None,
                      "evidence_id": evidence_id or str(uuid.uuid4()), "label_provenance": label_provenance or "unknown",
                      "ingested_at": datetime.now(timezone.utc).isoformat()}
        new_id = int(self.df["id"].max()) + 1 if not self.df.empty else 1
        
        if getattr(self, 'db_connected', False):
            try:
                # Veritabanına kaydet
                with self.db_engine.connect() as conn:
                    query_emb_str = "[" + ",".join(map(str, new_emb.tolist())) + "]"
                    sql = text("INSERT INTO knowledge_base (text, label, authority, embedding, source_url, publisher, published_at, evidence_id, label_provenance, ingested_at) VALUES (:t, :l, :a, :e, :source_url, :publisher, :published_at, :evidence_id, :label_provenance, :ingested_at) RETURNING id")
                    result = conn.execute(sql, {"t": input_text, "l": int(label), "a": float(authority), "e": query_emb_str, **provenance})
                    new_id = result.scalar()
                    conn.commit()
            except Exception as e:
                print(f"⚠️ Veritabanına enjeksiyon hatası: {e}")
                
                return False

        new_data = {'id': new_id, 'text': input_text, 'label': int(label), 'authority': float(authority), **provenance}
        new_row = pd.DataFrame([new_data])
        
        # Belleği Güncelle (BM25 ve RAM embeddings için)
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.texts.append(input_text)
        
        if not getattr(self, 'db_connected', False):
            # Çevrimdışı modda CSV dosyasına yazarak kalıcı kıl
            try:
                self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                # RAM'deki embeddings dizisini güncelle
                if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                    self.text_embeddings = np.vstack([self.text_embeddings, new_emb])
                else:
                    self.text_embeddings = np.array([new_emb])
                print("💾 Çevrimdışı Mod: Yeni bilgi yerel CSV dosyasına kaydedildi.")
            except Exception as csv_err:
                print(f"⚠️ Yerel CSV güncellenirken hata oluştu: {csv_err}")
        
        def tokenize(t): return re.findall(r'\w+', str(t).lower())
        tokenized_corpus = [tokenize(doc) for doc in self.texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        print(f"💉 Katman 10 (Enjeksiyon): Yeni bilgi enjekte edildi -> {input_text[:30]}...")
        return True

    def delete_knowledge(self, record_id):
        """
        Katman 10 (Admin): Belirli bir kaydı veritabanından veya yerel CSV'den ve bellekten siler.
        """
        if self.frozen_corpus_path:
            raise RuntimeError("Cannot delete from a frozen evaluation corpus.")
        deleted_from_db = False
        if getattr(self, 'db_connected', False):
            try:
                with self.db_engine.connect() as conn:
                    result = conn.execute(text("DELETE FROM knowledge_base WHERE id = :id"), {"id": int(record_id)})
                    conn.commit()
                    if result.rowcount > 0:
                        deleted_from_db = True
            except Exception as e:
                print(f"⚠️ Veritabanından silme hatası: {e}")
            
        # Belleği (RAM) Güncelle
        try:
            if 'id' in self.df.columns:
                idx = self.df.index[self.df['id'] == int(record_id)].tolist()
                if idx:
                    deleted_text = self.df.iloc[idx[0]]['text']
                    self.df = self.df[self.df['id'] != int(record_id)].reset_index(drop=True)
                    
                    if deleted_text in self.texts:
                        idx_text = self.texts.index(deleted_text)
                        self.texts.remove(deleted_text)
                        # RAM embeddings güncelle
                        if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                            self.text_embeddings = np.delete(self.text_embeddings, idx_text, axis=0)
                            
                    # BM25 güncelle
                    def tokenize(t): return re.findall(r'\w+', str(t).lower())
                    tokenized_corpus = [tokenize(doc) for doc in self.texts]
                    if tokenized_corpus:
                        self.bm25 = BM25Okapi(tokenized_corpus)
                    else:
                        self.bm25 = None
                    
                    # Çevrimdışı modda yerel CSV'ye yaz
                    if not getattr(self, 'db_connected', False):
                        self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                        
                    print(f"🗑️ Katman 10 (Admin): {record_id} numaralı bilgi silindi.")
                    return True
        except Exception as e:
            print(f"❌ Hata (Silme): {e}")
            return False
            
        return deleted_from_db

    def update_knowledge(self, record_id, input_text, label, authority, *, source_url=None, publisher=None,
                         published_at=None, evidence_id=None, label_provenance="unknown"):
        """
        Katman 10 (Admin): Belirli bir kaydın içeriğini, etiketini ve otoritesini günceller.
        """
        if self.frozen_corpus_path:
            raise RuntimeError("Cannot update a frozen evaluation corpus.")
        self.load_search_model()
        provenance = {"source_url": source_url or "", "publisher": publisher or "", "published_at": published_at or None,
                      "evidence_id": evidence_id or str(uuid.uuid4()), "label_provenance": label_provenance or "unknown",
                      "ingested_at": datetime.now(timezone.utc).isoformat()}
        new_emb = self.search_model.encode([f"passage: {input_text}"], convert_to_numpy=True)[0]
        updated_in_db = False
        
        if getattr(self, 'db_connected', False):
            try:
                query_emb_str = "[" + ",".join(map(str, new_emb.tolist())) + "]"
                with self.db_engine.connect() as conn:
                    sql = text("UPDATE knowledge_base SET text = :t, label = :l, authority = :a, embedding = :e, source_url = :source_url, publisher = :publisher, published_at = :published_at, evidence_id = :evidence_id, label_provenance = :label_provenance, ingested_at = :ingested_at WHERE id = :id")
                    result = conn.execute(sql, {"t": input_text, "l": int(label), "a": float(authority), "e": query_emb_str, "id": int(record_id), **provenance})
                    conn.commit()
                    if result.rowcount > 0:
                        updated_in_db = True
            except Exception as e:
                print(f"⚠️ Veritabanı güncelleme hatası: {e}")
                    
        # Belleği Güncelle
        try:
            if 'id' in self.df.columns:
                idx = self.df.index[self.df['id'] == int(record_id)].tolist()
                if idx:
                    old_text = self.df.at[idx[0], 'text']
                    self.df.at[idx[0], 'text'] = input_text
                    self.df.at[idx[0], 'label'] = int(label)
                    self.df.at[idx[0], 'authority'] = float(authority)
                    for field, value in provenance.items():
                        self.df.at[idx[0], field] = value
                    
                    if old_text in self.texts:
                        idx_text = self.texts.index(old_text)
                        self.texts[idx_text] = input_text
                        # RAM embeddings güncelle
                        if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                            self.text_embeddings[idx_text] = new_emb
                    
                    def tokenize(t): return re.findall(r'\w+', str(t).lower())
                    tokenized_corpus = [tokenize(doc) for doc in self.texts]
                    self.bm25 = BM25Okapi(tokenized_corpus)
                    
                    # Çevrimdışı modda yerel CSV'ye yaz
                    if not getattr(self, 'db_connected', False):
                        self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
                        
                    print(f"🔄 Katman 10 (Admin): {record_id} numaralı bilgi güncellendi.")
                    return True
        except Exception as e:
            print(f"❌ Hata (Güncelleme): {e}")
            return False
            
        return updated_in_db
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

    def temizle_ve_normallestir(self, query):
        q = turkish_lower(query)
        # Noktalama işaretlerini kaldır (Sorgu genişletme için temiz hal lazım)
        q = re.sub(r'[^\w\s]', '', q)
        q = re.sub(r'\s+(mi|mı|mu|mü)$', '', q)
        return q.strip()

    # --- KATMAN 1: GİRİŞ VE NİYET ANALİZİ ---
    
    def intent_analyzer(self, query):
        """Kullanıcın niyetini belirler: Selamlaşma mı, Proje Tanıtımı mı yoksa İddia mı?"""
        query_norm = turkish_lower(query)
        query_ascii = to_ascii_tr(query)  # Encoding güvenliği için ASCII versiyon

        # KızılelmAI hakkında sorular (hem Türkçe hem ASCII kontrol)
        kizil_variants = ["kızılelma", "kizilelma", "kizilelmA", "kzlelma"]
        has_kizil = any(v in query_norm for v in kizil_variants) or "kizilelma" in query_ascii
        if has_kizil:
            about_keywords = {"nedir", "ne", "kim", "amac", "gelistir", "yapan", "yapmistir", "kimdir", "hakkinda", "hakkında", "anlat", "tanitim"}
            tokens_ascii = re.findall(r'\b\w+\b', query_ascii)
            tokens_norm = re.findall(r'\b\w+\b', query_norm)
            all_tokens = set(tokens_ascii) | set(tokens_norm)
            if any(token in about_keywords for token in all_tokens):
                return "ABOUT"

        # Selamlaşma kontrolü
        greetings_list = self.kb.get("greetings", [])
        tokens_norm = query_norm.split()
        for token in tokens_norm:
            if token in greetings_list:
                return "GREETING"
        return "CLAIM"

    def query_expander(self, query):
        """Sözlük tabanlı sorgu genişletme (Örn: Maraş -> Kahramanmaraş)"""
        expanded_terms = []
        tokens = turkish_lower(query).split()
        
        for token in tokens:
            expanded_terms.append(token)
            # Eğer kelime sözlüğümüzde varsa yanına ek anlamlarını ekle
            synonyms_dict = self.kb.get("synonyms", {})
            if isinstance(synonyms_dict, dict) and token in synonyms_dict:
                syns = synonyms_dict.get(token, [])
                if syns:
                    print(f"💡 NLP Genişletme: '{token}' -> {syns} eklendi.")
                    expanded_terms.extend(syns)
        
        return " ".join(list(dict.fromkeys(expanded_terms))) # Tekrar edenleri temizle

    def kelime_capasi_kontrolu(self, query, source, sim_score, sig_rerank=0.0):
        def get_keywords(text, is_query=False):
            words = re.findall(r'\w+', turkish_lower(text))
            ignored = self.STOP_WORDS
            if is_query:
                ignored = ignored.union(self.SKEPTIC_KEYWORDS)
            return set([w for w in words if w not in ignored and len(w) > 2])

        if sim_score > self.SAFE_SIMILARITY_ZONE or sig_rerank > 0.70: return True, []

        q_keys = get_keywords(query, is_query=True)
        s_keys = get_keywords(source)
        if not q_keys: return True, [] 

        # En az kaç kelime eşleşmeli? (Kısa sorgularda en az 1, uzunlarda en az 2 veya %35'i)
        required_matches = 1
        if len(q_keys) >= 3:
            required_matches = max(2, int(len(q_keys) * 0.35))

        matches = []
        for q_word in q_keys:
            for s_word in s_keys:
                if q_word in s_word or s_word in q_word:
                    matches.append(q_word)
                    break

        if len(matches) >= required_matches:
            return True, []
        else:
            missing_words = list(q_keys - set(matches))
            if not missing_words: missing_words = list(q_keys)
            return False, missing_words


    def find_matching_source_number(self, q_num, user_query, db_source, s_nums):
        """Kullanıcı sorgusundaki hatalı sayının kaynaktaki hangi sayı ile çeliştiğini bağlam penceresiyle bulur."""
        q_tokens = re.findall(r'\b\w+\b', turkish_lower(user_query))
        try:
            q_idx = q_tokens.index(q_num)
            start = max(0, q_idx - 3)
            end = min(len(q_tokens), q_idx + 4)
            q_context = set(q_tokens[start:q_idx] + q_tokens[q_idx+1:end])
        except ValueError:
            q_context = set()

        best_s_num = None
        max_overlap = -1
        
        s_tokens = re.findall(r'\b\w+\b', turkish_lower(db_source))
        
        for s_num in s_nums:
            s_indices = [i for i, x in enumerate(s_tokens) if x == str(s_num)]
            for s_idx in s_indices:
                start_s = max(0, s_idx - 3)
                end_s = min(len(s_tokens), s_idx + 4)
                s_context = set(s_tokens[start_s:s_idx] + s_tokens[s_idx+1:end_s])
                
                # Stop words ve sayıları bağlam kelimelerinden çıkaralım
                s_context_clean = s_context - self.STOP_WORDS
                q_context_clean = q_context - self.STOP_WORDS
                
                overlap = len(q_context_clean.intersection(s_context_clean))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_s_num = s_num
        return best_s_num

    def get_original_case(self, word, text):
        """Metin içerisindeki kelimenin orijinal cased (büyük/küçük harf) halini bulur."""
        pattern = r'\b' + re.escape(word) + r'\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
        return word

    def find_best_matching_word(self, q_word, user_query, db_source, s_words):
        """
        Sorgudaki bir kelimenin kaynaktaki hangi kelime ile çeliştiğini 
        hem semantik benzerlik, hem bağlam örtüşmesi, hem de göreceli pozisyon kullanarak bulur.
        """
        def share_stem_helper(w1, w2):
            w1_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w1).lower()
            w2_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w2).lower()
            min_len = min(len(w1_clean), len(w2_clean))
            if min_len < 3:
                return w1_clean == w2_clean
            common_len = 0
            for c1, c2 in zip(w1_clean, w2_clean):
                if c1 == c2:
                    common_len += 1
                else:
                    break
            required_len = min_len - 1 if min_len <= 5 else min_len - 2
            return common_len >= required_len

        # Prioritize exact character match or stem/grammatical match first to avoid semantic mismatch noise
        for s_word in s_words:
            if turkish_lower(q_word) == turkish_lower(s_word) or share_stem_helper(q_word, s_word):
                return s_word

        q_tokens = re.findall(r'\b\w+\b', turkish_lower(user_query))
        try:
            q_idx = q_tokens.index(turkish_lower(q_word))
            rel_q = q_idx / len(q_tokens) if q_tokens else 0.0
            start = max(0, q_idx - 3)
            end = min(len(q_tokens), q_idx + 4)
            q_context = set(q_tokens[start:q_idx] + q_tokens[q_idx+1:end]) - self.STOP_WORDS
        except ValueError:
            q_idx = 0
            q_context = set()
            rel_q = 0.0

        s_tokens = re.findall(r'\b\w+\b', turkish_lower(db_source))
        
        best_word = None
        best_score = -1.0
        
        # Kelimeleri semantik olarak karşılaştırmak için embedding alalım
        try:
            q_emb = self.search_model.encode([q_word], convert_to_numpy=True)[0]
            s_embs = self.search_model.encode(s_words, convert_to_numpy=True)
        except Exception:
            # Hata durumunda boş/dummy embedding kullan
            q_emb = np.zeros(384)
            s_embs = [np.zeros(384)] * len(s_words)
        
        for idx, s_word in enumerate(s_words):
            # 1. Semantik benzerlik (0 ile 1 arasında normalize edilmiş)
            norm_q = np.linalg.norm(q_emb)
            norm_s = np.linalg.norm(s_embs[idx])
            if norm_q > 0 and norm_s > 0:
                sem_sim = np.dot(q_emb, s_embs[idx]) / (norm_q * norm_s)
            else:
                sem_sim = 0.0
            sem_sim = max(0.1, float(sem_sim)) # Sıfıra bölünmeyi önlemek ve taban sağlamak için minimum 0.1
            
            # 2. Bağlam örtüşmesi ve Pozisyon analizi
            s_indices = [i for i, x in enumerate(s_tokens) if x == turkish_lower(s_word)]
            best_word_score = -1.0
            for s_idx in s_indices:
                start_s = max(0, s_idx - 3)
                end_s = min(len(s_tokens), s_idx + 4)
                s_context = set(s_tokens[start_s:s_idx] + s_tokens[s_idx+1:end_s]) - self.STOP_WORDS
                overlap = len(q_context.intersection(s_context))
                
                # Pozisyon benzerliği (relative position closeness)
                rel_s = s_idx / len(s_tokens) if s_tokens else 0.0
                pos_sim = 1.0 - abs(rel_q - rel_s)
                
                # Mutlak pozisyon yakınlığı (slot eşleşmelerini güçlendirir)
                abs_pos_sim = 1.0 / (1.0 + abs(q_idx - s_idx))
                
                combined_pos_sim = (pos_sim + abs_pos_sim) / 2.0
                score = sem_sim * (1.0 + overlap) * (combined_pos_sim ** 2)
                
                if score > best_word_score:
                    best_word_score = score
            
            if best_word_score > best_score:
                best_score = best_word_score
                best_word = s_word
                
        return best_word
                    
    def get_relevant_sentences(self, query, document, top_n=1):
        """Metin içerisinden sorgu ile en çok örtüşen cümle(leri) seçer."""
        if not document or document == '-':
            return document
            
        # Türkçe cümle sınırlarına göre böl (nokta, ünlem, soru işareti ardından boşluk)
        sentences = re.split(r'(?<=[.!?])\s+', document.strip())
        if not sentences:
            return document
            
        q_words = set(re.findall(r'\w+', turkish_lower(query)))
        scored_sentences = []
        for sent in sentences:
            sent_words = set(re.findall(r'\w+', turkish_lower(sent)))
            overlap = len(q_words.intersection(sent_words))
            scored_sentences.append((overlap, sent))
            
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        selected = [s[1] for s in scored_sentences[:top_n]]
        return " ".join(selected)

    def get_local_context_window(self, query, document):
        if not document or document == '-':
            return document
            
        sentences = re.split(r'(?<=[.!?])\s+', document.strip())
        if not sentences:
            return document
            
        q_words = set(re.findall(r'\w+', self.temizle_ve_normallestir(query)))
        best_idx = 0
        max_overlap = -1
        
        for idx, sent in enumerate(sentences):
            sent_words = set(re.findall(r'\w+', self.temizle_ve_normallestir(sent)))
            overlap = len(q_words.intersection(sent_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_idx = idx
                
        start_idx = max(0, best_idx - 1)
        end_idx = min(len(sentences), best_idx + 2)
        
        selected_sentences = sentences[start_idx:end_idx]
        return " ".join(selected_sentences)

    def akilli_fark_analizi(self, user_query, db_source):
        """
        Kişi, Yer, Tarih, Sayı, Unvan ve Olay farklarını yakalar.
        6 Kritik Problem Odaklı Analiz.
        Returns: (diff_user, diff_source, score, category)
        """
        # [Kaynak: ...] önekini analizden önce temizle
        db_source = re.sub(r'^\[Kaynak:[^\]]+\]\s*', '', db_source)

        # local context window (3 sentences around best match) to avoid false matches on far sentences
        db_source = self.get_local_context_window(user_query, db_source)

        # Sayı-harf bitişik yazımlarını düzelt (örn: 25saatte -> 25 saatte)
        user_query = split_numbers_letters(user_query)
        db_source = split_numbers_letters(db_source)

        # 1. TARİH ANALİZİ (Zaman Aşımı / Güncel Değil)
        date_pattern = r'\b\d{1,4}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{4}\b'
        q_dates = set(re.findall(date_pattern, user_query))
        s_dates = set(re.findall(date_pattern, db_source))
        
        # Eğer sayısal bir tarih (özellikle yıl) değişmişse: Zaman Aşımı
        if q_dates - s_dates:
            return list(q_dates - s_dates)[0], list(s_dates - q_dates)[0] if s_dates else "KAYIT", 0.05, "ZAMAN AŞIMI"

        # 2. SAYISAL FARK KONTROLÜ (Sayı Problemi)
        q_nums = set(re.findall(r'\b\d+\b', user_query))
        s_nums = set(re.findall(r'\b\d+\b', db_source))
        # Tarihleri sayısal farktan ayır
        q_nums = q_nums - q_dates
        s_nums = s_nums - s_dates

        if q_nums - s_nums:
            mismatched_q_num = list(q_nums - s_nums)[0]
            s_val = self.find_matching_source_number(mismatched_q_num, user_query, db_source, s_nums)
            if not s_val:
                s_val = list(s_nums)[0] if s_nums else "DEĞER"
            return str(mismatched_q_num), str(s_val), 0.1, "SAYI" # type: ignore

        # 3. KELİME VE ÖZEL İSİM FARK KONTROLÜ
        # Gürültüyü engellemek için her şeyi lowercase yapıyoruz
        def get_words_lower(text):
            words = re.findall(r'\b\w+\b', self.temizle_ve_normallestir(text))
            return set([w for w in words if w not in self.STOP_WORDS and len(w) > 1])

        q_words = get_words_lower(user_query) - q_nums - q_dates
        s_words = get_words_lower(db_source) - s_nums - s_dates

        user_diff = list(q_words - s_words)
        source_diff = list(s_words - q_words)

        if not user_diff or not source_diff: return None, None, 1.0, "GENEL"

        # Kritik kırmızı liste unvan kontrolü (case-insensitive)
        found_red_titles = [t for t in self.RED_LIST_TITLES if re.search(r'\b' + t + r'\b', turkish_lower(user_query))]
        source_red_titles = [t for t in self.RED_LIST_TITLES if re.search(r'\b' + t + r'\b', turkish_lower(db_source))]
        
        # Eğer kullanıcının girdiği unvanlardan biri kaynakta yoksa:
        missing_titles = set(found_red_titles) - set(source_red_titles)
        if missing_titles:
            diff_t = list(missing_titles)[0]
            src_t = source_red_titles[0] if source_red_titles else "BİLİNMİYOR"
            return diff_t.upper(), src_t.upper(), 0.01, "KRİTİK UNVAN"

        # Tüm user_diff kelimelerini analiz edip, eşanlamlı veya ek farkı (suffix) olanları eleyelim
        filtered_user_diff = []
        mismatch_details = {}  # q_word -> (s_word, score)
        
        # Helper to check if two words share a prefix/suffix relation (Turkish stem matching)
        def share_stem(w1, w2):
            w1_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w1).lower()
            w2_clean = re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', w2).lower()
            min_len = min(len(w1_clean), len(w2_clean))
            if min_len < 3:
                return w1_clean == w2_clean
            common_len = 0
            for c1, c2 in zip(w1_clean, w2_clean):
                if c1 == c2:
                    common_len += 1
                else:
                    break
            
            # Suffix/stem threshold based on length to prevent tarım/tarih matching
            required_len = min_len - 1 if min_len <= 5 else min_len - 2
            return common_len >= required_len

        # Helper to check if two words are explicitly declared synonyms
        def is_explicit_synonym(w1, w2):
            syns = self.kb.get("synonyms", {})
            # Check direct lists
            if w1 in syns and w2 in syns[w1]:
                return True
            if w2 in syns and w1 in syns[w2]:
                return True
            # Check cross-lookup
            for key, val_list in syns.items():
                if w1 == key or w1 in val_list:
                    if w2 == key or w2 in val_list:
                        return True
            return False

        for q_word in user_diff:
            s_word = self.find_best_matching_word(q_word, user_query, db_source, source_diff)
            if not s_word:
                s_word = source_diff[0] if source_diff else "DEĞER"

            # 1. Stem / Grammatical variation matching (e.g. 'şoför' vs 'şoförü', 'kayseri' vs 'kayseride')
            if share_stem(q_word, s_word):
                continue

            # 2. Explicit synonyms matching
            if is_explicit_synonym(q_word, s_word):
                continue

            # 3. Herhangi bir eşleşme bulunamazsa bu bir çelişki/fark olarak kabul edilir.
            # Denetimsiz tekil kelime gömmesi (embedding) benzerliği kullanılmaz; çünkü tarım/orman, kedi/köpek gibi aynı kategorideki farklı kelimeleri eşanlamlı sanıp karıştırabilmektedir.
            filtered_user_diff.append(q_word)
            mismatch_details[q_word] = (s_word, 0.0)
            
        if not filtered_user_diff:
            return None, None, 1.0, "GENEL"
            
        # Kalan gerçek çelişkilerden en belirgin olanı seçelim (en düşük benzerlik skoruna sahip olan)
        filtered_user_diff.sort(key=lambda w: mismatch_details[w][1])
        mismatched_q_lower = filtered_user_diff[0]
        mismatched_s_lower, score = mismatch_details[mismatched_q_lower]

        # Orijinal harf büyüklüklerini (cased) geri yükleyelim
        diff_user = self.get_original_case(mismatched_q_lower, user_query)
        diff_source = self.get_original_case(mismatched_s_lower, db_source)

        def is_originally_capitalized(word, text):
            pattern = r'\b' + re.escape(word) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if m and m[0].isupper():
                    return True
            return False

        is_entity = is_originally_capitalized(mismatched_q_lower, user_query) or is_originally_capitalized(mismatched_s_lower, db_source)

        if is_entity:
            # Kategori tespiti
            cat = "KİŞİ/YER/UNVAN"
            if any(w in user_query.upper() for w in ['ŞEHİR', 'ÜLKE', 'YER', 'KÖY', 'İL', 'GAZZE', 'İSRAİL', 'ABD']): cat = "YER"
            elif any(w in user_query.upper() for w in ['KİM', 'KİŞİ', 'ADAM', 'KADIN', 'CUMHURBAŞKANI', 'BAKAN']): cat = "KİŞİ"
            return diff_user, diff_source, 0.2, cat

        if score < self.IRRELEVANT_THRESHOLD:
            # Tamamen alakasız bir kelime ise
            return diff_user, diff_source, score, "OLAY"
            
        return diff_user, diff_source, score, "DETAY"

    def detect_negation(self, text):
        """Metindeki Türkçe olumsuzluk yapılarını tespit eder."""
        text_lower = re.sub(r'[^\w\s]', '', turkish_lower(text))
        
        # Word boundaries for exact negation words
        neg_words = {'değil', 'yok', 'asla', 'hiçbir'}
        for word in neg_words:
            if re.search(r'\b' + word + r'\b', text_lower):
                return True
                
        # Suffix-based negations
        neg_patterns = [
            r'\w+ma(?:dı|dılar|dığı|dık|mış|yacak|makta|malı)\b',
            r'\w+me(?:di|diler|diği|dik|miş|yecek|mekte|meli)\b',
            r'\w+ma(?:z|zlar)\b',
            r'\w+me(?:z|zler)\b',
            r'\w+m(?:ı|i|u|ü)yor\b'
        ]
        for pat in neg_patterns:
            matches = re.findall(pat, text_lower)
            for match in matches:
                # Filter out false positives
                false_positives = {
                    'malzeme', 'mama', 'maliyet', 'mavi', 'maya', 'mayıs', 'memnun', 'mermer', 
                    'memur', 'merkez', 'mesaj', 'metal', 'meyve', 'mezun', 'memleket', 'medya', 
                    'medeni', 'melodi', 'melek', 'merak', 'mezarlık'
                }
                if not any(fp in match for fp in false_positives):
                    return True
        return False

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
                # RET (Bulunamadı) durumunda, eğer K-6 çok yüksek güvenle yalan/şüpheli diyorsa ve hafif benzerlik varsa
                elif status == "RET" and k6_label == 0 and k6_conf >= 0.90 and sim_score > 0.40:
                    status = "UYARI"
                    res["msg"] = "⚠️ **ŞÜPHELİ METİN YAPISI (K-6)**"
                    desc = "Doğrudan kanıt kaydı yetersiz olmakla birlikte, metin yapısı teyit edilmiş yalan haber kalıplarıyla yüksek örtüşme göstermektedir."
                    conf = round(k6_conf * 100, 1)
                    risk = 75.0

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

        # 3. NLI ANALİZİ
        score_contra, score_neutral, score_entail = nli_probs[0], nli_probs[1], nli_probs[2] # type: ignore
        confidence = max(score_contra, score_neutral, score_entail) * 100
        
        # NLI modeli Nötr (Alakasız) diyorsa reddet
        # AMA eğer akıllı fark analizinde net bir YER, KİŞİ, SAYI veya KRİTİK UNVAN mismatch'i varsa Nötr kontrolünü atla (Çünkü bu doğrudan bir bilgi yanlışlığıdır, alakasızlık değildir!)
        has_critical_mismatch = diff_user is not None and diff_source is not None and diff_cat in ["YER", "KİŞİ", "SAYI", "KRİTİK UNVAN", "KİŞİ/YER/UNVAN"]

        neutral_threshold = 0.75
        if sig_rerank > 0.70 or sim_score > 0.65:
            neutral_threshold = 0.92  # Güvenli eşleşmelerde eşiği esnetiyoruz
            
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

            # B. Hiçbir fark bulunamadıysa doğrudan doğrula!
            if not diff_user and not diff_source:
                return {
                    "status": "ONAY", "msg": "✅ **DOĞRULANDI**",
                    "desc": "Doğrulandı, bilgi güvenilir kaynaklarla uyuşuyor.",
                    "conf": max(int(sim_score * 100), 95), "risk": 5, "cat": "GENEL"
                }

            # C. Kritik Fark Kontrolleri (NLI entailment'ını veto eder)
            if diff_user and diff_source:
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
            if score_entail > 0.45:
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

    def ask(self, raw_query, *, include_trace=False, independent=False):
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
            result = self._ask(raw_query)
            if include_trace:
                trace["latency_ms"] = (time.perf_counter() - start) * 1000
                trace["raw_status"] = result.get("status")
                result["trace"] = trace
            return result
        finally:
            _evaluation_trace.reset(token)

    def _ask(self, raw_query):
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
        else:
            if hasattr(self, 'text_embeddings') and len(self.text_embeddings) > 0:
                dense_sims = cosine_similarity([query_emb], self.text_embeddings)[0]
        
        # 2. SPARSE RETRIEVAL (Keyword - BM25 Arama)
        tokenized_query = re.findall(r'\w+', turkish_lower(search_query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # 3. RECIPROCAL RANK FUSION (Hibrit Harmanlama)
        dense_order = np.argsort(dense_sims)[::-1]
        dense_rank = {idx: rank for rank, idx in enumerate(dense_order)}
        
        sparse_order = np.argsort(bm25_scores)[::-1]
        sparse_rank = {idx: rank for rank, idx in enumerate(sparse_order)}
        
        k = 60
        fused_scores = {}
        for idx in range(len(self.texts)):
            score = (1 / (k + dense_rank[idx])) + (1 / (k + sparse_rank[idx]))
            fused_scores[idx] = score
            
        # Hibrid skoruna göre en iyi belgelerin indeksini al (GPU varsa 20 aday, CPU ise 5 aday)
        candidate_limit = 20 if torch.cuda.is_available() else 5
        top_indices = sorted(list(fused_scores.keys()), key=lambda x: fused_scores[x], reverse=True)[:candidate_limit] # type: ignore
        
        # --- KATMAN 3: RE-RANKING (The Sniper) ---
        trace_elapsed("K2_retrieval", stage_start)
        trace = _evaluation_trace.get()
        if trace is not None:
            trace["retrieved_source_ids"] = [int(self.df.iloc[idx]["id"]) for idx in top_indices]
        stage_start = time.perf_counter()
        rerank_pairs = [[search_query, self.texts[idx]] for idx in top_indices]
        rerank_output = self.rerank_model.predict(rerank_pairs) if self.rerank_model else None # type: ignore
        rerank_scores = list(rerank_output) if rerank_output is not None else [0.0] * len(top_indices)
        trace_elapsed("K3_reranker", stage_start)
        if trace is not None:
            trace["rerank_scores"] = [float(v) for v in rerank_scores]
        stage_start = time.perf_counter()
        
        # Yeni skorlarla adayları tekrar eşleştir ve sırala
        ranked_candidates = []
        for i, idx in enumerate(top_indices):
            # Katman 8: Otorite Ağırlıklandırması (Normalizasyon ve Dinamik Kaynak Otoritesi ile)
            auth = self.resolve_source_authority(self.df.iloc[idx])
            
            # Sigmoid Normalizasyonu: Rerank skorunu [0,1] arasına çeker
            raw_rerank = float(rerank_scores[i])
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
        # Re-ranker veto eşiği: Sigmoid sonrası 0.50 altı "Alakasız" kabul edelim (Daha esnek semantik eşleşme için 0.50'ye çekildi)
        RERANK_VETO_THRESHOLD = 0.50 

        for cand in ranked_candidates:
            idx = cand['idx']
            s_score = cand['sig_rerank']
            
            if s_score > RERANK_VETO_THRESHOLD:
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
        if trace is not None:
            trace["accepted_source_ids"] = [c["id"] for c in candidates]
        if not candidates:
            return self.local_response_engine(raw_query, {'text': '-'}, {
                "status": "RET", "msg": "📭 KAYIT BULUNAMADI", 
                "desc": "Veri tabanımda bu konuyla örtüşen bir bilgiye ulaşılamadı.", 
                "conf": 0, "risk": 0, "cat": "YOK"
            })
            
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
        # Eğer fark analizinde hiçbir fark bulunamazsa, NLI modelinin kararı yoksayılır ve karar motoru doğrudan ONAY/UYARI döner.
        # Bu durumda NLI modelini çalıştırmayarak 1-2 saniye zaman kazanabiliriz.
        diff_user, diff_source, diff_match_score, diff_cat = self.akilli_fark_analizi(raw_query, best_cand['text'])
        
        # Fark yoksa ve semantik uyuşma yüksekse, NLI çalışmasını bypass et (entailment olasılığını %100 yap)
        if diff_user is None and diff_source is None and (best_cand['sim'] > 0.60 or best_cand.get('sig_rerank', 0.0) > 0.70):
            print("⚡ NLP Mantıksal Bypass: Eşleşmede fark tespit edilmedi, NLI modeli atlandı (Bypass).")
            probs = np.array([0.0, 0.0, 1.0])  # [contradiction=0, neutral=0, entailment=1]
            if trace is not None:
                trace["nli_bypassed"] = True
        else:
            # NLI Tahmini: Her zaman [Kaynak, Gelen Soru] sırasıyla çalışmalıdır (Asimetrik).
            input_pair = [best_cand['text'], clean_query]
            logits = self.nli_model.predict([input_pair])[0] # type: ignore
            probs = torch.nn.functional.softmax(torch.tensor(logits, dtype=torch.float32), dim=0).numpy()
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
            inputs = self.classifier_tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)
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

    def detect_source_channel(self, text):
        """Metin içerisinden haber kaynağını/kanalını tespit etmeye çalışır."""
        if not text or text == '-':
            return "Belirlenemedi"
            
        text_lower = text.lower()
        
        # Check explicit prefix we inject (e.g. "[Kaynak: TRT Haber] ...")
        match = re.match(r'^\[Kaynak:\s*([^\]]+)\]', text)
        if match:
            return match.group(1).strip()
            
        # Agency and website keywords mapping
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
            
        # Domain name extraction from URLs if present in text
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
        
        # Haber kanalını/kaynağını tespit et
        source_channel = cand.get('publisher') if cand.get('source_url') and cand.get('publisher') else "Kaynak kaydı eksik"
        
        # Kaynak metinden [Kaynak: ...] önekini temizleyerek daha temiz gösterelim
        display_source = source
        if display_source.startswith(f"[Kaynak: {source_channel}]"):
            display_source = display_source[len(f"[Kaynak: {source_channel}]"):].strip()
        else:
            display_source = re.sub(r'^\[Kaynak:[^\]]+\]\s*', '', display_source)

        # Katman 9 Bilgisi
        cons = res.get('consensus', {})
        cons_text = ""
        if cons.get('is_consensus'):
            cons_text = f" (Konsensüs: {cons.get('agreement_count')}/{cons.get('total_sources')} kaynak uyumlu)"
        else:
            cons_text = " (⚠️ Dikkat: Kaynaklar arasında çelişki tespit edildi!)"

        # Tipik bir chatbot baloncuğu için formatlanmış metin
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

        # YAPILANDIRILMIŞ ÇIKTI (Dashboard İçin)
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

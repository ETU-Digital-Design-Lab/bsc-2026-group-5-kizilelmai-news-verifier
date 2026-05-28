import os
import sys
import re
import json
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

class KizilelmaEngine:
    """
    KızılelmAI'nin tüm zekasını barındıran sınıf.
    Veriyi yükler, modelleri hazırlar ve sorulara cevap üretir.
    """
    def __init__(self):
        print("[System] KizilElma Motoru Baslatiliyor...")
        
        # --- 1. Sabitler ve Ayarlar ---
        self.root_dir = "" # type: Any
        self.csv_path = "" # type: Any
        self.local_model_path = "" # type: Any
        self.kb_path = "" # type: Any
        self.RETRIEVAL_THRESHOLD = 0.40
        self.SAFE_SIMILARITY_ZONE = 0.65
        self.SYNONYM_THRESHOLD = 0.85
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
        self.db_engine = create_engine("postgresql://kizilelmai_user:kizilelmai_pass@localhost:5433/kizilelmai")
        self.kb = {} # type: Any
        self.search_model = None # type: Any
        self.nli_model = None # type: Any
        self.rerank_model = None # type: Any
        self.context_buffer = [] # type: List[Dict[str, Any]]
        self.MAX_CONTEXT = 3

        # --- 3. Başlatma Sırası ---
        self.setup_paths()
        self.load_data()
        self.load_models()
        print("🚀 Motor Hazır!")

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



    def load_data(self):
        print("📂 PostgreSQL Veritabanına Bağlanılıyor...")
        self.db_connected = False
        try:
            with self.db_engine.connect() as conn:
                self.df = pd.read_sql("SELECT id, text, label, authority FROM knowledge_base ORDER BY id", conn)
            
            print(f"✅ Veri seti yüklendi: {len(self.df)} kayıt (PostgreSQL).")
            self.texts = self.df['text'].tolist()
            self.db_connected = True
            
        except Exception as e:
            print(f"❌ Hata: Veritabanına bağlanılamadı veya tablo yok! {e}")
            print("⚠️ ÇEVRİMDIŞI MOD: Yerel CSV dosyasından veri yükleniyor...")
            
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
        if self.texts:
            def tokenize(text):
                return re.findall(r'\w+', str(text).lower())
            
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
        except:
            print("⚠️ Uyarı: knowledge_base.json bulunamadı, varsayılan boş ayarlar kullanılacak.")
            self.kb = {"greetings": [], "synonyms": {}, "responses": {}} # type: ignore

    def load_models(self):
        print("⏳ Modeller yükleniyor (v2.1)...")
        # Embedding Modeli
        if os.path.exists(self.local_model_path):
            print(f"📂 Yerel model kullanılıyor: {self.local_model_path}")
            self.search_model = SentenceTransformer(self.local_model_path)
        else:
            self.search_model = SentenceTransformer('intfloat/multilingual-e5-small')
        
        # NLI Modeli (Gerekçelendirme)
        self.nli_model = CrossEncoder('joeddav/xlm-roberta-large-xnli')

        # --- YENI: Layer 3 Re-Ranker Modeli (Keskin Nişancı) ---
        print("⏳ Re-Ranker model yükleniyor (bge-reranker-v2-m3)...")
        self.rerank_model = CrossEncoder('BAAI/bge-reranker-v2-m3')

        # --- YENI: Sınıflandırma Modeli Yükleme ---
        self.classifier_model = None
        self.classifier_tokenizer = None
        if os.path.exists(self.classifier_model_path):
            print(f"📂 Yerel sınıflandırma modeli yükleniyor: {self.classifier_model_path}")
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            try:
                self.classifier_tokenizer = AutoTokenizer.from_pretrained(self.classifier_model_path)
                self.classifier_model = AutoModelForSequenceClassification.from_pretrained(self.classifier_model_path)
                self.classifier_model.eval()
                print("✅ Sınıflandırma modeli hazır!")
            except Exception as e:
                print(f"⚠️ Sınıflandırma modeli yüklenirken hata oldu: {e}")

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
                    self.text_embeddings = self.search_model.encode(passage_texts, convert_to_numpy=True, show_progress_bar=False)
                    np.save(npy_path, self.text_embeddings)
                    print(f"✅ {len(self.text_embeddings)} vektör RAM'e başarıyla yüklendi ve önbelleğe kaydedildi.")
                except Exception as e:
                    print(f"⚠️ Çevrimdışı modda vektörler hesaplanırken hata oluştu: {e}")
                    self.text_embeddings = []
        else:
            print("⏳ Vektörler veritabanından sorgulanacak, RAM'e yüklenmiyor.")
            self.text_embeddings = []

    def inject_knowledge(self, input_text, label, authority=0.95):
        """
        Katman 10: Çalışma zamanında yeni bilgi enjekte eder (PostgreSQL ve/veya CSV).
        """
        new_emb = self.search_model.encode([f"passage: {input_text}"], convert_to_numpy=True)[0]
        
        new_id = len(self.df) + 1
        
        if getattr(self, 'db_connected', False):
            try:
                # Veritabanına kaydet
                with self.db_engine.connect() as conn:
                    query_emb_str = "[" + ",".join(map(str, new_emb.tolist())) + "]"
                    sql = text("INSERT INTO knowledge_base (text, label, authority, embedding) VALUES (:t, :l, :a, :e) RETURNING id")
                    result = conn.execute(sql, {"t": input_text, "l": int(label), "a": float(authority), "e": query_emb_str})
                    new_id = result.scalar()
                    conn.commit()
            except Exception as e:
                print(f"⚠️ Veritabanına enjeksiyon hatası: {e}")
                
        new_data = {'id': new_id, 'text': input_text, 'label': int(label), 'authority': float(authority)}
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

    def update_knowledge(self, record_id, input_text, label, authority):
        """
        Katman 10 (Admin): Belirli bir kaydın içeriğini, etiketini ve otoritesini günceller.
        """
        new_emb = self.search_model.encode([f"passage: {input_text}"], convert_to_numpy=True)[0]
        updated_in_db = False
        
        if getattr(self, 'db_connected', False):
            try:
                query_emb_str = "[" + ",".join(map(str, new_emb.tolist())) + "]"
                with self.db_engine.connect() as conn:
                    sql = text("UPDATE knowledge_base SET text = :t, label = :l, authority = :a, embedding = :e WHERE id = :id")
                    result = conn.execute(sql, {"t": input_text, "l": int(label), "a": float(authority), "e": query_emb_str, "id": int(record_id)})
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

        q_clean = current_query.lower().strip()
        tokens = q_clean.split()
        
        # Takip sorusu tetikleyicileri
        follow_up_triggers = {'peki', 'ya', 've', 'kim', 'nerede', 'ne', 'nasıl', 'neden'}
        
        # Eğer sorgu çok kısaysa veya tetikleyici ile başlıyorsa bağlam ara
        if len(tokens) <= 3 or (tokens and tokens[0] in follow_up_triggers):
            last_query = self.context_buffer[-1]['query']
            # Önceki sorgudan önemli anahtar kelimeleri (isimleri) çekmeye çalış
            # (NLP Heuristic: Büyük harfle başlayanlar veya stop-word olmayanlar)
            merged = f"{last_query} {current_query}"
            print(f"🔗 NLP Katman 7 (Konsept Birleştirme): '{current_query}' -> '{merged}'")
            return merged

        return current_query

    def temizle_ve_normallestir(self, query):
        q = query.lower()
        # Noktalama işaretlerini kaldır (Sorgu genişletme için temiz hal lazım)
        q = re.sub(r'[^\w\s]', '', q)
        q = re.sub(r'\s+(mi|mı|mu|mü)$', '', q)
        return q.strip()

    # --- KATMAN 1: GİRİŞ VE NİYET ANALİZİ ---
    
    def intent_analyzer(self, query):
        """Kullanıcın niyetini belirler: Selamlaşma mı yoksa İddia mı?"""
        tokens = query.lower().split()
        for token in tokens:
            if token in self.kb.get("greetings", []):
                return "GREETING"
        return "CLAIM"

    def query_expander(self, query):
        """Sözlük tabanlı sorgu genişletme (Örn: Maraş -> Kahramanmaraş)"""
        expanded_terms = []
        tokens = query.lower().split()
        
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

    def kelime_capasi_kontrolu(self, query, source, sim_score):
        def get_keywords(text):
            words = re.findall(r'\w+', text.lower())
            return set([w for w in words if w not in self.STOP_WORDS and len(w) > 2])

        if sim_score > self.SAFE_SIMILARITY_ZONE: return True, []

        q_keys = get_keywords(query)
        s_keys = get_keywords(source)
        if not q_keys: return True, [] 

        match_found = False
        for q_word in q_keys:
            for s_word in s_keys:
                if q_word in s_word or s_word in q_word:
                    match_found = True; break
            if match_found: break
        
        if match_found: return True, []
        else:
            missing_words = list(q_keys - s_keys)
            if not missing_words: missing_words = list(q_keys)
            return False, missing_words

    def akilli_fark_analizi(self, user_query, db_source):
        """
        Kişi, Yer, Tarih, Sayı, Unvan ve Olay farklarını yakalar.
        6 Kritik Problem Odaklı Analiz.
        Returns: (diff_user, diff_source, score, category)
        """
        def get_tokens(text):
            # Büyük harfle başlayan kelimeleri (Entities) ve sayıları koru
            words = re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]*\b|\b\d+\b|\b\w+\b', text)
            return set([w for w in words if w.lower() not in self.STOP_WORDS and len(w) > 1])

        q_tokens = get_tokens(user_query)
        s_tokens = get_tokens(db_source)

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
            return str(list(q_nums - s_nums)[0]), "DEĞER", 0.1, "SAYI" # type: ignore

        user_diff = list(q_tokens - s_tokens)
        source_diff = list(s_tokens - q_tokens)

        if not user_diff or not source_diff: return None, None, 0, "GENEL"

        # 3. KIRMIZI LİSTE (KRİTİK UNVAN) VE ÖZEL İSİM KONTROLÜ
        q_entities = [w for w in user_diff if w[0].isupper()]
        s_entities = [w for w in source_diff if w[0].isupper()]
        
        # Özel durum: Kullanıcı sorgusunda Kırmızı Liste unvanı geçiyorsa hassas davran
        found_red_titles = [t for t in self.RED_LIST_TITLES if t in user_query.lower()]
        source_red_titles = [t for t in self.RED_LIST_TITLES if t in db_source.lower()]
        
        if set(found_red_titles) != set(source_red_titles):
            # Unvan doğrudan değişmiş!
            diff_t = found_red_titles[0] if found_red_titles else "BELİRSİZ"
            src_t = source_red_titles[0] if source_red_titles else "BİLİNMİYOR"
            return diff_t.upper(), src_t.upper(), 0.01, "KRİTİK UNVAN"

        if q_entities and s_entities:
             # Kategori tespiti
             cat = "KİŞİ/YER/UNVAN"
             if any(w in user_query.upper() for w in ['ŞEHİR', 'ÜLKE', 'YER', 'KÖY', 'İL']): cat = "YER"
             elif any(w in user_query.upper() for w in ['KİM', 'KİŞİ', 'ADAM', 'KADIN']): cat = "KİŞİ"
             return q_entities[0], s_entities[0], 0.2, cat

        # 3. GENEL ANLAMSAL FARK (Embedding)
        q_emb = self.search_model.encode(user_diff, convert_to_tensor=True) # type: ignore
        s_emb = self.search_model.encode(source_diff, convert_to_tensor=True) # type: ignore
        cosine_scores = util.cos_sim(q_emb, s_emb)
        
        best_pair_user = ""
        best_pair_source = ""
        best_score = -1.0
        scores_list = cosine_scores.tolist()

        for i in range(len(user_diff)):
            for j in range(len(source_diff)):
                score = scores_list[i][j]
                if score > self.SYNONYM_THRESHOLD: continue     # Eşanlamlı
                if score < self.IRRELEVANT_THRESHOLD: continue  # Alakasız
                if score > best_score:
                    best_score = float(score)
                    best_pair_user = str(user_diff[i]) # type: ignore
                    best_pair_source = str(source_diff[j]) # type: ignore

        if best_score < 0: return None, None, 1.0, "OLAY" 
        return best_pair_user, best_pair_source, best_score, "DETAY"

    def karar_motoru(self, user_query, db_record, nli_probs, sim_score):
        db_text = db_record['text']
        db_label = db_record['label']
        
        # 1. KELİME ÇAPASI
        is_relevant, missing_words = self.kelime_capasi_kontrolu(user_query, db_text, sim_score)
        if not is_relevant:
            missing_str = ", ".join([w.upper() for w in missing_words])
            return {
                "status": "RET", "msg": "ℹ️ **BULUNAMADI / ALAKASIZ**",
                "desc": f"Veri tabanımda **'{missing_str}'** ile ilgili kayıt yok.", "conf": 0, "risk": 0, "cat": "YOK"
            }

        # 2. NLI VE FARK ANALİZİ
        score_contra, score_neutral, score_entail = nli_probs[0], nli_probs[1], nli_probs[2] # type: ignore
        confidence = max(score_contra, score_neutral, score_entail) * 100
        
        # YENİ EKLENEN KONTROL: Eğer NLI modeli Nötr (Alakasız) diyorsa reddet (Halüsinasyon Engelleme için daha katı hale getirildi)
        if score_neutral > 0.75:
            return {
                "status": "RET", "msg": "ℹ️ **BULUNAMADI / ALAKASIZ**",
                "desc": "Veri tabanımda bu iddiayı doğrulayacak veya yalanlayacak mantıksal bir kayıt yok.", "conf": 0, "risk": 0, "cat": "GENEL"
            }
        
        diff_user, diff_source, diff_match_score, diff_cat = self.akilli_fark_analizi(user_query, db_text)
        diff_msg = ""
        if diff_user and diff_source:
            diff_msg = f"\n⚠️ **Farklı Detay:** Siz **'{diff_user.upper()}'** dediniz, kaynakta **'{diff_source.upper()}'** geçiyor."

        # --- LABEL 1: DOĞRU HABERLER ---
        if db_label == 1:
            if score_contra > 0.50:
                 return { "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**", "desc": "İddianız kaynaklarla çelişiyor.", "conf": max(confidence, 85), "risk": 60, "cat": diff_cat }
            if score_entail > 0.45:
                # DENGELİ RİSK: Onaylandığında risk düşük olmalı
                return { "status": "ONAY", "msg": "✅ **DOĞRULANDI**", "desc": "Bilgi güvenilir kaynaklarla uyuşuyor.", "conf": confidence, "risk": max(10, 100 - confidence), "cat": diff_cat }
            elif sim_score > 0.60:
                # ÖZEL MESAJ OVERRIDE (Katman 6.5)
                msg = "⚠️ **KISMİ DOĞRU / DETAY HATASI**"
                desc = f"Olay doğru fakat detaylarda hata var.{diff_msg}"
                
                if diff_cat == "ZAMAN AŞIMI":
                    msg = "⏳ **GÜNCEL DEĞİL / ZAMAN AŞIMI**"
                    desc = f"Bu bilgi artık geçerliliğini yitirmiş olabilir. {diff_msg}"
                elif diff_cat == "KRİTİK UNVAN":
                    msg = "🚨 **KRİTİK UNVAN HATASI**"
                    desc = f"Kırmızı liste kapsamında olan bir unvanda fark tespit edildi! {diff_msg}"

                if diff_match_score > self.SEMANTIC_SHIFT_THRESHOLD:
                    return { "status": "KISMI", "msg": msg, "desc": desc, "conf": sim_score * 100, "risk": 45, "cat": diff_cat }
                else:
                     return { "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**", "desc": "Detaylar uyuşmuyor.", "conf": 80, "risk": 65, "cat": diff_cat }
            else:
                 return { "status": "RET", "msg": "ℹ️ **BULUNAMADI**", "desc": "Olay tam örtüşmüyor.", "conf": 0, "risk": 0, "cat": "BELİRSİZ" }

        # --- LABEL 0: YALAN HABERLER ---
        else:
            user_is_skeptic = any(w in user_query.lower() for w in self.SKEPTIC_KEYWORDS)
            if user_is_skeptic and score_entail > 0.40:
                 return { "status": "ONAY", "msg": "✅ **DOĞRU TESPİT**", "desc": "Evet, şüpheleriniz haklı. Bu deryandaki haberin **YALAN** olduğu kayıtlıdır.", "conf": 95, "risk": 15, "cat": diff_cat }
            
            if score_entail > 0.45:
                return { "status": "UYARI", "msg": "❌ **HAYIR / ASILSIZ İDDİA**", "desc": "Hayır, bu durum gerçeği yansıtmamaktadır. Bu iddia **YALAN HABER** olarak işaretlenmiştir.", "conf": 99, "risk": 90, "cat": diff_cat }
            
            if score_contra > 0.45:
                return { "status": "ONAY", "msg": "✅ **DOĞRU TESPİT**", "desc": "Tebrikler. Savunduğunuz tez doğru. Karşı çıktığınız iddia zaten **YALAN HABER** olarak işaretlenmiştir.", "conf": 99, "risk": 10, "cat": diff_cat }
            
            return { "status": "RET", "msg": "ℹ️ **YETERLİ VERİ YOK**", "desc": "Net doğrulama yapılamadı.", "conf": 50, "risk": 40, "cat": "YOK" }

    def ask(self, raw_query):
        """Dış dünyadan gelen soruya cevap veren ana fonksiyon"""
        
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
        contextual_query = self.context_merger(raw_query)
        clean_query = self.temizle_ve_normallestir(contextual_query)
        print(f"\n📩 Gelen: {raw_query} | Analitik Bağlam: {contextual_query}")

        # Yerel sınıflandırma modelini çalıştır (varsa)
        self.classifier_score_str = ""
        if self.classifier_model and self.classifier_tokenizer:
            try:
                import torch.nn.functional as F
                inputs = self.classifier_tokenizer(contextual_query, return_tensors="pt", truncation=True, padding=True, max_length=128)
                with torch.no_grad():
                    outputs = self.classifier_model(**inputs)
                    logits = outputs.logits
                probs = F.softmax(logits, dim=1)
                yalan_olasilik = probs[0][0].item()
                gercek_olasilik = probs[0][1].item()
                pred_label = "GERÇEK" if gercek_olasilik > 0.5 else "YALAN"
                pred_score = max(gercek_olasilik, yalan_olasilik) * 100
                self.classifier_score_str = f"• **AI Sınıflandırıcı Tahmini:** % {pred_score:.1f} {pred_label}\n"
            except Exception as e:
                print(f"⚠️ Sınıflandırma tahmini hatası: {e}")

        # 1. Niyet Analizi
        intent = self.intent_analyzer(clean_query)
        if intent == "GREETING":
            greet_text = self.kb["responses"].get("greeting", "Merhaba! Size nasıl yardımcı olabilirim?")
            return {
                "result": greet_text,
                "status": "ONAY", "msg": "👋 MERHABA", 
                "description": "KızılelmAI hazır bekliyor.", 
                "confidence": 100, "risk": 0, "category": "GREETING", "source": "-"
            }

        # 2. Sorgu Genişletme (Öğretilen kelimeleri kullan)
        search_query = self.query_expander(clean_query)
        print(f"🔍 Arama Sorgusu (Genişletilmiş): {search_query}")

        # 1. DENSE RETRIEVAL (Semantic - Vektör Arama PostgreSQL veya in-memory)
        query_text = f"query: {search_query}"
        query_emb = self.search_model.encode([query_text])[0] # type: ignore
        
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
        tokenized_query = re.findall(r'\w+', search_query.lower())
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
            
        # Hibrid skoruna göre en iyi 3 belgenin indeksini al (Re-ranking yükünü azaltmak için)
        top_indices = sorted(list(fused_scores.keys()), key=lambda x: fused_scores[x], reverse=True)[:3] # type: ignore
        
        # --- KATMAN 3: RE-RANKING (The Sniper) ---
        rerank_pairs = [[search_query, self.texts[idx]] for idx in top_indices]
        rerank_output = self.rerank_model.predict(rerank_pairs) if self.rerank_model else None # type: ignore
        rerank_scores = list(rerank_output) if rerank_output is not None else [0.0] * len(top_indices)
        
        # Yeni skorlarla adayları tekrar eşleştir ve sırala
        ranked_candidates = []
        for i, idx in enumerate(top_indices):
            # Katman 8: Otorite Ağırlıklandırması (Normalizasyon ile)
            auth = self.df.iloc[idx].get('authority', 0.85)
            
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
        
        candidates = []
        # Re-ranker veto eşiği: Sigmoid sonrası 0.55 altı "Alakasız" kabul edelim (Halüsinasyon Engelleme için 0.40'tan 0.55'e çekildi)
        RERANK_VETO_THRESHOLD = 0.55 

        for cand in ranked_candidates:
            idx = cand['idx']
            s_score = cand['sig_rerank']
            
            if s_score > RERANK_VETO_THRESHOLD:
                if cand['dense_sim'] > self.RETRIEVAL_THRESHOLD or cand['bm25_score'] > 1.5:
                    candidates.append({
                        'text': self.df.iloc[idx]['text'], 
                        'label': int(self.df.iloc[idx]['label']), 
                        'sim': cand['dense_sim'],
                        'rerank_score': cand['rerank_score'],
                        'authority': cand['authority'],
                        'sig_rerank': cand['sig_rerank']
                    })

        if not candidates:
            return self.local_response_engine(raw_query, {'text': '-'}, {
                "status": "RET", "msg": "📭 KAYIT BULUNAMADI", 
                "desc": "Veri tabanımda bu konuyla örtüşen bir bilgiye ulaşılamadı.", 
                "conf": 0, "risk": 0, "cat": "YOK"
            })
            
        # Katman 9: Multi-Source Consensus (Konsensüs Analizi)
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
        
        print(f"🎯 Sniper Seçimi (Ağırlıklı): {best_cand['text'][:50]}... | Otorite: {best_cand['authority']}")
        
        # NLI Tahmini: Her zaman [Kaynak, Gelen Soru] sırasıyla çalışmalıdır (Asimetrik).
        input_pair = [best_cand['text'], clean_query]
        logits = self.nli_model.predict([input_pair])[0] # type: ignore
        probs = torch.nn.functional.softmax(torch.tensor(logits), dim=0).numpy()
        
        print(f"🔍 Kaynak: {best_cand['text']} | Sim: {best_cand['sim']:.2f} | NLI: {probs}")

        # Karar
        res = self.karar_motoru(raw_query, best_cand, probs, best_cand['sim'])
        res['consensus'] = consensus_info # Konsensüs verisini ekle
        
        # Katman 7: Context Güncelleme (Sadece geçerli iddiaları sakla)
        if res.get('status') != 'RET':
            self.context_buffer.append({"query": raw_query, "category": res.get('cat')})
            if len(self.context_buffer) > self.MAX_CONTEXT:
                self.context_buffer.pop(0)

        # Artık yapılandırılmış bir sözlük (dict) dönüyoruz
        return self.local_response_engine(raw_query, best_cand, res)

    def local_response_engine(self, query, cand, res):
        """Dış API olmadan profesyonel Türkçe yanıt üretir ve detaylı metadata döner."""
        status_msg = res['msg']
        detail = res['desc']
        trust = int(res.get('conf', 0))
        risk = int(res.get('risk', 0))
        cat = res.get('cat', 'GENEL')
        source = cand.get('text', '-')
        
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
        if hasattr(self, 'classifier_score_str') and self.classifier_score_str:
            classifier_line = self.classifier_score_str

        formatted_text = f"{header}\n\n🔍 **DERİN ANALİZ RAPORU (v3.0):**\n• **Hata Kategorisi:** {cat}\n{classifier_line}• **Otorite Puanı:** % {int(cand.get('authority', 0.85)*100)}\n• **Tespit Türü:** {'Doğrudan Çelişki' if risk > 50 else 'Semantik Örtüşme'}{cons_text}\n{extra}\n🛡️ **Doğruluk:** %{trust} | 📉 **Risk:** %{risk}\n-----------------------------\n📄 **Kaynak:** {source}"

        # YAPILANDIRILMIŞ ÇIKTI (Dashboard İçin)
        return {
            "result": formatted_text,
            "status": res.get('status'),
            "msg": status_msg,
            "description": detail,
            "confidence": trust,
            "risk": risk,
            "category": cat,
            "source": source
        }
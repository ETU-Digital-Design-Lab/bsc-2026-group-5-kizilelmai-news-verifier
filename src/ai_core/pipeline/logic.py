import os
import sys
import re
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder, util
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings("ignore")

class KizilelmaEngine:
    """
    KızılelmAI'nin tüm zekasını barındıran sınıf.
    Veriyi yükler, modelleri hazırlar ve sorulara cevap üretir.
    """
    def __init__(self):
        print("⚙️  KızılElma Motoru Başlatılıyor...")
        self.setup_paths()
        self.setup_constants()
        self.load_data()
        self.load_models()
        print("🚀 Motor Hazır ve Çalışıyor!")

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

    def setup_constants(self):
        # Eşik Değerleri (Sweet Spot)
        self.RETRIEVAL_THRESHOLD = 0.35      
        self.SAFE_SIMILARITY_ZONE = 0.65     
        self.SYNONYM_THRESHOLD = 0.85        
        self.IRRELEVANT_THRESHOLD = 0.25     
        self.SEMANTIC_SHIFT_THRESHOLD = 0.55 
        
        # Kelime Listeleri
        self.STOP_WORDS = {
            'mi', 'mı', 'mu', 'mü', 'nin', 'nın', 'nun', 'nün', 'de', 'da', 'te', 'ta', 'den', 'dan',
            'ile', 've', 'veya', 'ki', 'bu', 'şu', 'o', 'bir', 'olan', 'eden', 'olarak',
            'için', 'diye', 'kadar', 'sonra', 'önce', 'daha', 'en', 'ise', 'nedir', 'kimdir', 'nasil',
            'neden', 'niçin', 'miydi', 'miyim', 'mıyım'
        }
        self.SKEPTIC_KEYWORDS = {'yalan', 'uydurma', 'kurgu', 'montaj', 'fake', 'palavra', 'efsane', 'iftira', 'yanlış'}

    def load_data(self):
        print(f"📂 Veri Yolu: {self.csv_path}")
        try:
            self.df = pd.read_csv(self.csv_path)
            print(f"✅ Veri seti yüklendi: {len(self.df)} kayıt.")
            self.texts = self.df['text'].tolist()
        except Exception as e:
            print(f"❌ Hata: CSV dosyası bulunamadı! {e}")
            self.df = pd.DataFrame(columns=['text', 'label'])
            self.texts = []

    def load_models(self):
        print("⏳ Modeller yükleniyor (v2.1)...")
        # Embedding Modeli
        if os.path.exists(self.local_model_path):
            print(f"📂 Yerel model kullanılıyor: {self.local_model_path}")
            self.search_model = SentenceTransformer(self.local_model_path)
        else:
            self.search_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # NLI Modeli
        self.nli_model = CrossEncoder('joeddav/xlm-roberta-large-xnli')

        # Embeddings Hesapla
        if self.texts:
            print("⏳ Vektörler oluşturuluyor...")
            self.text_embeddings = self.search_model.encode(self.texts, convert_to_numpy=True, show_progress_bar=False)
        else:
            self.text_embeddings = []

    # --- MANTIK FONKSİYONLARI ---

    def temizle_ve_normallestir(self, query):
        q = query.lower()
        q = q.replace("?", "")
        q = re.sub(r'\s+(mi|mı|mu|mü)$', '', q)
        return q.strip()

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
        def get_tokens(text):
            words = re.findall(r'\w+', text.lower())
            return set([w for w in words if w not in self.STOP_WORDS and len(w) > 2])

        q_tokens = get_tokens(user_query)
        s_tokens = get_tokens(db_source)
        user_diff = list(q_tokens - s_tokens)
        source_diff = list(s_tokens - q_tokens)

        if not user_diff or not source_diff: return None, None, 0

        q_emb = self.search_model.encode(user_diff, convert_to_tensor=True)
        s_emb = self.search_model.encode(source_diff, convert_to_tensor=True)
        cosine_scores = util.cos_sim(q_emb, s_emb)
        
        best_pair = (None, None); best_score = -1
        scores_list = cosine_scores.tolist()

        for i in range(len(user_diff)):
            for j in range(len(source_diff)):
                score = scores_list[i][j]
                if score > self.SYNONYM_THRESHOLD: continue     # Eşanlamlı
                if score < self.IRRELEVANT_THRESHOLD: continue  # Alakasız
                if score > best_score:
                    best_score = score
                    best_pair = (user_diff[i], source_diff[j])

        if best_score == -1: return None, None, 1.0 
        return best_pair[0], best_pair[1], best_score

    def karar_motoru(self, user_query, db_record, nli_probs, sim_score):
        db_text = db_record['text']
        db_label = db_record['label']
        
        # 1. KELİME ÇAPASI
        is_relevant, missing_words = self.kelime_capasi_kontrolu(user_query, db_text, sim_score)
        if not is_relevant:
            missing_str = ", ".join([w.upper() for w in missing_words])
            return {
                "status": "RET", "msg": "ℹ️ **BULUNAMADI / ALAKASIZ**",
                "desc": f"Veri tabanımda **'{missing_str}'** ile ilgili kayıt yok.", "conf": 0, "risk": 0
            }

        # 2. NLI VE FARK ANALİZİ
        score_contra, score_neutral, score_entail = nli_probs[0], nli_probs[1], nli_probs[2]
        confidence = max(score_contra, score_neutral, score_entail) * 100
        
        diff_user, diff_source, diff_match_score = self.akilli_fark_analizi(user_query, db_text)
        diff_msg = ""
        if diff_user and diff_source:
            diff_msg = f"\n⚠️ **Farklı Detay:** Siz **'{diff_user.upper()}'** dediniz, kaynakta **'{diff_source.upper()}'** geçiyor."

        # --- LABEL 1: DOĞRU HABERLER ---
        if db_label == 1:
            if score_contra > 0.50:
                 return { "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**", "desc": "İddianız kaynaklarla çelişiyor.", "conf": max(confidence, 85), "risk": 75 }
            if score_entail > 0.50:
                return { "status": "ONAY", "msg": "✅ **DOĞRULANDI**", "desc": "Bilgi güvenilir kaynaklarla uyuşuyor.", "conf": confidence, "risk": 100 - confidence }
            elif sim_score > 0.50:
                if diff_match_score > self.SEMANTIC_SHIFT_THRESHOLD:
                    return { "status": "KISMI", "msg": "⚠️ **KISMİ DOĞRU / DETAY HATASI**", "desc": f"Olay doğru fakat detaylarda hata var.{diff_msg}", "conf": sim_score * 100, "risk": 40 }
                else:
                     return { "status": "RED", "msg": "❌ **BİLGİ YANLIŞLIĞI**", "desc": "Detaylar uyuşmuyor.", "conf": 80, "risk": 70 }
            else:
                 return { "status": "RET", "msg": "ℹ️ **BULUNAMADI**", "desc": "Olay örtüşmüyor.", "conf": 0, "risk": 0 }

        # --- LABEL 0: YALAN HABERLER ---
        else:
            user_is_skeptic = any(w in user_query.lower() for w in self.SKEPTIC_KEYWORDS)
            if user_is_skeptic and sim_score > 0.50:
                 return { "status": "ONAY", "msg": "✅ **DOĞRU TESPİT**", "desc": "Evet, şüpheleriniz haklı. Bu haberin **YALAN** olduğu kayıtlıdır.", "conf": 95, "risk": 0 }
            if score_entail > 0.50 or sim_score > 0.60:
                return { "status": "UYARI", "msg": "❌ **HAYIR / ASILSIZ İDDİA**", "desc": "Hayır, bu durum gerçeği yansıtmamaktadır. Bu iddia **YALAN HABER** olarak işaretlenmiştir.", "conf": 99, "risk": 95 }
            else:
                 return { "status": "RET", "msg": "ℹ️ **YETERLİ VERİ YOK**", "desc": "Net doğrulama yapılamadı.", "conf": 50, "risk": 50 }

    def ask(self, raw_query):
        """Dış dünyadan gelen soruya cevap veren ana fonksiyon"""
        clean_query = self.temizle_ve_normallestir(raw_query)
        print(f"\n📩 Gelen: {raw_query}")

        # Retrieval
        query_emb = self.search_model.encode([clean_query])
        similarities = cosine_similarity(query_emb, self.text_embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][:3]
        
        candidates = []
        for idx in top_indices:
            sim = similarities[idx]
            if sim > self.RETRIEVAL_THRESHOLD:
                candidates.append({
                    'text': self.df.iloc[idx]['text'], 'label': int(self.df.iloc[idx]['label']), 'sim': sim
                })

        if not candidates:
            return "📭 Veri tabanımda bu konuyla ilgili yeterli bilgi bulunamadı."

        best_cand = candidates[0]
        
        # NLI Tahmini
        input_pair = [clean_query, best_cand['text']]
        logits = self.nli_model.predict([input_pair])[0]
        probs = torch.nn.functional.softmax(torch.tensor(logits), dim=0).numpy()
        
        print(f"🔍 Kaynak: {best_cand['text']} | Sim: {best_cand['sim']:.2f} | NLI: {probs}")

        # Karar
        res = self.karar_motoru(raw_query, best_cand, probs, best_cand['sim'])
        
        if res['status'] == 'RET' and "BULUNAMADI" in res['msg']:
            return f"{res['msg']}\n{res['desc']}"
        else:
            return (
                f"{res['msg']}\n"
                f"{res['desc']}\n\n"
                f"🛡️ **Güvenilirlik:** %{int(res['conf'])}\n"
                f"📉 **Manipülasyon Riski:** %{int(res['risk'])}\n"
                f"-----------------------------\n"
                f"📄 **Kaynak:** {best_cand['text']}"
            )
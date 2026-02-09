from flask import Flask, jsonify, make_response, request
import pandas as pd
from flask_cors import CORS
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder, util
from sklearn.metrics.pairwise import cosine_similarity
import torch
import re
import warnings

# Gereksiz uyarıları kapat
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ---------------------------------------------------------
# 1. AYARLAR VE MODELLER
# ---------------------------------------------------------

RETRIEVAL_THRESHOLD = 0.35      # Aday havuzuna giriş barajı
SAFE_SIMILARITY_ZONE = 0.65     # Bu skorun üstündeyse kelime aramaya gerek yok

# --- YENİ EŞİK DEĞERLERİ (SWEET SPOT STRATEJİSİ) ---
# Eşanlamlılık Filtresi: %80'den fazla benzeyen kelimeleri (Şampiyon/Kazandı) fark sayma.
SYNONYM_THRESHOLD = 0.80
# Anlamsızlık Filtresi: %30'dan az benzeyen kelimeleri (THY/Araba) fark sayma.
IRRELEVANT_THRESHOLD = 0.30
# Semantik Kayma Sınırı: Detay hatası mı yoksa tamamen yanlış mı ayrımı.
SEMANTIC_SHIFT_THRESHOLD = 0.55 

try:
    df = pd.read_csv('egitim_verisi_final.csv')
    print("✅ Veri seti yüklendi.")
except Exception as e:
    print(f"❌ Hata: CSV dosyası bulunamadı! {e}")
    df = pd.DataFrame(columns=['text', 'label'])

print("⏳ Modeller yükleniyor...")
search_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
nli_model = CrossEncoder('joeddav/xlm-roberta-large-xnli')
print("🚀 Sistem Hazır!")

texts = df['text'].tolist()
if texts:
    text_embeddings = search_model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
else:
    text_embeddings = []

STOP_WORDS = {
    'mi', 'mı', 'mu', 'mü', 'nin', 'nın', 'nun', 'nün', 'de', 'da', 'te', 'ta', 'den', 'dan',
    'ile', 've', 'veya', 'ki', 'bu', 'şu', 'o', 'bir', 'olan', 'eden', 'olarak',
    'için', 'diye', 'kadar', 'sonra', 'önce', 'daha', 'en', 'ise', 'nedir', 'kimdir', 'nasil',
    'neden', 'niçin', 'miydi', 'mu', 'mü', 'yalan', 'gerçek', 'mi', 'mu'
}

# ---------------------------------------------------------
# 2. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def temizle_ve_normallestir(query):
    q = query.lower()
    q = q.replace("?", "")
    q = re.sub(r'\s+(mi|mı|mu|mü)$', '', q)
    return q.strip()

def kelime_capasi_kontrolu(query, source, sim_score):
    """
    Kullanıcının aradığı ama kaynakta BULUNAMAYAN kelimeleri döndürür.
    """
    def get_keywords(text):
        words = re.findall(r'\w+', text.lower())
        return set([w for w in words if w not in STOP_WORDS and len(w) > 2])

    if sim_score > SAFE_SIMILARITY_ZONE:
        return True, []

    q_keys = get_keywords(query)
    s_keys = get_keywords(source)

    if not q_keys: return True, [] 

    match_found = False
    for q_word in q_keys:
        for s_word in s_keys:
            if q_word in s_word or s_word in q_word:
                match_found = True
                break
        if match_found: break
    
    if match_found:
        return True, []
    else:
        # DÜZELTME: Sadece eksik olanları bul (Küme farkı)
        missing_words = list(q_keys - s_keys)
        # Eğer hepsi eksik çıkarsa (hiç eşleşme yoksa) hepsini dön
        if not missing_words: missing_words = list(q_keys)
        return False, missing_words

def akilli_fark_analizi(user_query, db_source):
    """
    SWEET SPOT MANTIĞI:
    Çok benzeyenleri (Synonym) ele -> Şampiyon/Kazandı (~0.85) -> İGNORLANIR
    Çok alakasızları ele -> Uçak/Araba (~0.15) -> İGNORLANIR
    Arada kalanları bul -> Dünya/Avrupa (~0.60) -> HEDEF!
    """
    def get_tokens(text):
        words = re.findall(r'\w+', text.lower())
        return set([w for w in words if w not in STOP_WORDS and len(w) > 2])

    q_tokens = get_tokens(user_query)
    s_tokens = get_tokens(db_source)
    
    user_diff = list(q_tokens - s_tokens)
    source_diff = list(s_tokens - q_tokens)

    if not user_diff or not source_diff:
        return None, None, 0

    q_emb = search_model.encode(user_diff, convert_to_tensor=True)
    s_emb = search_model.encode(source_diff, convert_to_tensor=True)
    cosine_scores = util.cos_sim(q_emb, s_emb)

    best_pair = (None, None)
    best_score = -1
    scores_list = cosine_scores.tolist()

    for i in range(len(user_diff)):
        for j in range(len(source_diff)):
            score = scores_list[i][j]
            
            # 1. EŞANLAMLI FİLTRESİ: Çok benziyorsa (Şampiyon/Kazandı) fark değildir.
            if score > SYNONYM_THRESHOLD:
                continue
                
            # 2. GÜRÜLTÜ FİLTRESİ: Hiç benzemiyorsa dikkate alma.
            if score < IRRELEVANT_THRESHOLD:
                continue

            # 3. EN İYİ ADAYI SEÇ
            if score > best_score:
                best_score = score
                best_pair = (user_diff[i], source_diff[j])

    if best_score == -1: 
        # Eğer hiç uygun aday bulamazsak, 
        # demek ki farklar ya çok alakasız ya da eşanlamlı.
        # Bu durumda en yüksek skoru (eşanlamlı olsa bile) "Aynılar" varsayarak dönmemiz daha güvenli.
        return None, None, 1.0 
        
    return best_pair[0], best_pair[1], best_score

def karar_motoru(user_query, db_record, nli_probs, sim_score):
    db_text = db_record['text']
    db_label = db_record['label']
    
    # 1. KELİME ÇAPASI
    is_relevant, missing_words = kelime_capasi_kontrolu(user_query, db_text, sim_score)
    if not is_relevant:
        missing_str = ", ".join([w.upper() for w in missing_words])
        return {
            "status": "RET",
            "msg": "ℹ️ **BULUNAMADI / ALAKASIZ**",
            "desc": f"Veri tabanımda **'{missing_str}'** ile ilgili/alakalı bir kayıt bulunmamaktadır.",
            "conf": 0, "risk": 0
        }

    # 2. NLI VE FARK ANALİZİ
    score_contra, score_neutral, score_entail = nli_probs[0], nli_probs[1], nli_probs[2]
    confidence = max(score_contra, score_neutral, score_entail) * 100
    
    diff_user, diff_source, diff_match_score = akilli_fark_analizi(user_query, db_text)
    diff_msg = ""
    if diff_user and diff_source:
        diff_msg = f"\n⚠️ **Farklı Detay:** Siz **'{diff_user.upper()}'** dediniz, kaynakta **'{diff_source.upper()}'** geçiyor."

    # --- LABEL 1: DOĞRU HABERLER ---
    if db_label == 1:
        # ÖNCELİK 1: ÇELİŞKİ (Erdoğan vakasını çözer)
        # Benzerlik yüksek olsa bile, NLI "Çelişki" diyorsa YANLIŞTIR.
        if score_contra > 0.50:
             return {
                "status": "RED",
                "msg": "❌ **BİLGİ YANLIŞLIĞI**",
                "desc": "Bahsettiğiniz konu doğru olsa da, iddia ettiğiniz eylem/durum kaynaklarla çelişiyor.",
                "conf": max(confidence, 85), 
                "risk": 75
            }

        # ÖNCELİK 2: TAM ONAY
        if score_entail > 0.50:
            return {
                "status": "ONAY",
                "msg": "✅ **DOĞRULANDI**",
                "desc": "Bu bilgi güvenilir kaynaklarla uyuşuyor.",
                "conf": confidence, "risk": 100 - confidence
            }
        
        # ÖNCELİK 3: DETAY HATASI (Mete Gazoz vakası)
        elif sim_score > 0.50:
            if diff_match_score > SEMANTIC_SHIFT_THRESHOLD:
                # Fark anlamlı (Dünya/Avrupa) -> Kısmi Doğru
                return {
                    "status": "KISMI",
                    "msg": "⚠️ **KISMİ DOĞRU / DETAY HATASI**",
                    "desc": f"Bahsettiğiniz olay sistemde mevcut fakat detaylarda hata var.{diff_msg}",
                    "conf": sim_score * 100, "risk": 40
                }
            else:
                # Fark anlamsız veya çok düşük -> Yanlış Bilgiye düşür
                 return {
                    "status": "RED",
                    "msg": "❌ **BİLGİ YANLIŞLIĞI**",
                    "desc": "İddianızın detayları kaynaklarla uyuşmuyor.",
                    "conf": 80, "risk": 70
                }
        
        # Hiçbiri değilse
        else:
             return { "status": "RET", "msg": "ℹ️ **BULUNAMADI**", "desc": "Benzer kelimeler var ama olay örtüşmüyor.", "conf": 0, "risk": 0 }

    # --- LABEL 0: YALAN HABERLER ---
    else:
        # Kullanıcı yalan haberi GERÇEKMİŞ GİBİ soruyor
        if score_entail > 0.50 or (sim_score > 0.60 and score_contra < 0.50):
            return {
                "status": "UYARI",
                "msg": "🚨 **UYARI: YANILTICI İÇERİK!**",
                "desc": "Sorduğunuz iddia sistemimizde **YALAN HABER** olarak işaretlenmiştir.",
                "conf": 99, "risk": 95
            }
        
        # Kullanıcı "YALAN MI?" diye soruyor (Gökten balık yağdı vakası)
        # Sim yüksek ama Entailment düşükse veya Contra yüksekse -> Kullanıcı şüpheleniyor.
        else:
             return { 
                 "status": "ONAY", 
                 "msg": "✅ **DOĞRU TESPİT**", 
                 "desc": "Evet, bu haberin yalan olduğu/gerçeği yansıtmadığı kayıtlarımızda mevcuttur.", 
                 "conf": max(confidence, 90), # NLI emin olamasa bile biz eminiz
                 "risk": 0 
            }

    return { "status": "BOS", "msg": "ℹ️ **YETERLİ VERİ YOK**", "desc": "Net bir doğrulama yapamıyorum.", "conf": 50, "risk": 50 }

# ---------------------------------------------------------
# 3. API ENDPOINTLERİ
# ---------------------------------------------------------

@app.route('/api/veri', methods=['GET'])
def getir_veri():
    try:
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': 'Veri okunamadı.'}), 500

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp
    
    data = request.json
    raw_query = data.get('query', '').strip()
    clean_query = temizle_ve_normallestir(raw_query)

    if not raw_query: return jsonify({'result': 'Lütfen bir soru girin.'})
    print(f"\n📩 Gelen: {raw_query}")

    query_emb = search_model.encode([clean_query])
    similarities = cosine_similarity(query_emb, text_embeddings)[0]
    top_indices = np.argsort(similarities)[::-1][:3]
    
    candidates = []
    for idx in top_indices:
        sim = similarities[idx]
        if sim > RETRIEVAL_THRESHOLD:
            candidates.append({
                'text': df.iloc[idx]['text'], 'label': int(df.iloc[idx]['label']), 'sim': sim
            })

    if not candidates:
        return jsonify({'result': "📭 Veri tabanımda bu konuyla ilgili yeterli bilgi bulunamadı."})

    best_cand = candidates[0]
    
    input_pair = [clean_query, best_cand['text']]
    logits = nli_model.predict([input_pair])[0]
    probs = torch.nn.functional.softmax(torch.tensor(logits), dim=0).numpy()
    
    print(f"🔍 Kaynak: {best_cand['text']} | Sim: {best_cand['sim']:.2f} | NLI: {probs}")

    res = karar_motoru(clean_query, best_cand, probs, best_cand['sim'])
    
    if res['status'] == 'RET' and "BULUNAMADI / ALAKASIZ" in res['msg']:
        final_output = f"{res['msg']}\n{res['desc']}"
    else:
        final_output = (
            f"{res['msg']}\n"
            f"{res['desc']}\n\n"
            f"🛡️ **Güvenilirlik:** %{int(res['conf'])}\n"
            f"📉 **Manipülasyon Riski:** %{int(res['risk'])}\n"
            f"-----------------------------\n"
            f"📄 **Kaynak:** {best_cand['text']}"
        )

    return jsonify({'result': final_output})

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)

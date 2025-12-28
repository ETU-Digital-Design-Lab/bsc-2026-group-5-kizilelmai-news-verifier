from flask import Flask, jsonify, make_response, request
import pandas as pd
from flask_cors import CORS
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
# CORS tamamen serbest, tüm yollar ve metodlar için ayarlandı
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# CSV'yi yükle
df = pd.read_csv('egitim_verisi_final.csv')

# BERT modelini yükle (Türkçe destekleyen multilingual model)
print("BERT modeli yükleniyor... Bu ilk seferde biraz zaman alabilir.")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("BERT modeli hazır!")

# Tüm cümleleri embedding'e çevir ve bellekte tut
print("Veri setindeki cümleler embedding'e çevriliyor...")
texts = df['text'].tolist()
text_embeddings = model.encode(texts, show_progress_bar=True)
print(f"{len(texts)} cümle embedding'e çevrildi. Sistem hazır!")

@app.route('/api/veri')
def getir_veri():
    try:
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        app.logger.error(f'CSV okunamadı: {e}')
        return make_response(jsonify({'error': 'Veri okunamadı.'}), 500)

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp
    
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'result': 'Lütfen bir soru girin.'})
    
    # Kullanıcı sorgusunu embedding'e çevir
    query_embedding = model.encode([query], show_progress_bar=False)
    
    # Cosine similarity ile en yakın eşleşmeleri bul
    similarities = cosine_similarity(query_embedding, text_embeddings)[0]
    
    # En yüksek similarity skorlarına göre sırala (eşik: 0.5 - daha sıkı filtreleme)
    threshold = 0.5
    top_indices = np.where(similarities >= threshold)[0]
    
    if len(top_indices) == 0:
        return jsonify({'result': 'Bu konuda veri setinde bir bilgi bulunamadı.'})
    
    # En yüksek skorlu sonuçları al (sadece en iyi 2 sonuç - daha odaklı)
    top_scores = similarities[top_indices]
    sorted_indices = top_indices[np.argsort(top_scores)[::-1]][:2]
    
    # En yüksek skorlu sonucun diğerlerinden çok daha yüksek olması durumunda sadece onu göster
    if len(sorted_indices) > 1:
        best_score = similarities[sorted_indices[0]]
        second_score = similarities[sorted_indices[1]]
        # Eğer en iyi sonuç ikinciden %20 daha iyiyse, sadece en iyisini göster
        if best_score > second_score * 1.2:
            sorted_indices = [sorted_indices[0]]
    
    # Sonuçları formatla
    cevaplar = []
    for idx in sorted_indices:
        rec = df.iloc[idx]
        label = int(rec['label'])
        score = similarities[idx]
        
        if label == 1:
            sonuc = f"✅ Evet, bu haber doğru. (Benzerlik: {score:.2%})\nKaynak: {rec['text']}"
        else:
            sonuc = f"❌ Hayır, bu haber yanlış. (Benzerlik: {score:.2%})\nYanıltıcı cümle: {rec['text']}"
        cevaplar.append(sonuc)
    
    return jsonify({'result': '\n\n'.join(cevaplar)})

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)

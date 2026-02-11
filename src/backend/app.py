"""
KızılelmAI Backend API (App Layer)
Yapay zeka mantığı 'src/ai_core/pipeline/logic.py' dosyasındadır.
Burası sadece sunucudur.
"""
import os
import sys
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS

# ---------------------------------------------------------
# PATH AYARLAMALARI (Engine'i bulmak için)
# ---------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # src/backend
SRC_DIR = os.path.dirname(CURRENT_DIR)                   # src/
sys.path.append(SRC_DIR)

# Engine'i İçe Aktar (Beyni Çağır)
try:
    from ai_core.pipeline.logic import KizilelmaEngine
except ImportError as e:
    print(f"❌ Kritik Hata: Logic modülü bulunamadı! {e}")
    sys.exit(1)

# ---------------------------------------------------------
# UYGULAMA BAŞLATMA
# ---------------------------------------------------------
app = Flask(__name__)

# CORS Ayarları
CORS_ORIGINS = os.environ.get("KIZILELMAI_CORS_ORIGINS", "*").split(",")
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Motoru Başlat (Belleğe yükler - 10sn sürebilir)
engine = KizilelmaEngine()

# ---------------------------------------------------------
# API ENDPOINTLERİ
# ---------------------------------------------------------

@app.route('/api/veri', methods=['GET'])
def getir_veri():
    """Tüm veri setini JSON olarak döndürür"""
    try:
        return jsonify(engine.df.to_dict(orient='records'))
    except Exception:
        return jsonify({'error': 'Veri okunamadı.'}), 500

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Sohbet Endpoint'i"""
    # Preflight Request (CORS)
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp
    
    # Gelen isteği al
    data = request.json
    raw_query = data.get('query', '').strip()

    if not raw_query:
        return jsonify({'result': 'Lütfen bir soru girin.'})

    # MOTORU ÇALIŞTIR (Tek satır!)
    result_text = engine.ask(raw_query)

    return jsonify({'result': result_text})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
"""
KızılelmAI Backend API (FastAPI Layer)
Yapay zeka mantığı 'src/ai_core/engine/engine.py' dosyasındadır.
Burası asenkron, yüksek performanslı API sunucusudur.
"""
import os
import sys
import uvicorn # type: ignore
from fastapi import FastAPI, HTTPException, Request # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
from typing import List, Dict, Any

# ---------------------------------------------------------
# PATH AYARLAMALARI (Engine'i bulmak için)
# ---------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # src/backend
SRC_DIR = os.path.dirname(CURRENT_DIR)                   # src/
sys.path.append(SRC_DIR)

# Engine'i İçe Aktar (Beyni Çağır)
try:
    from ai_core.engine.engine import KizilelmaEngine # type: ignore
except ImportError as e:
    print(f"❌ Kritik Hata: Logic modülü bulunamadı! {e}")
    sys.exit(1)

# ---------------------------------------------------------
# UYGULAMA YAPILANDIRMASI
# ---------------------------------------------------------
app = FastAPI(
    title="KızılelmAI API",
    description="Yerel Haber Doğrulama ve Analiz Motoru API",
    version="2.0.0"
)

# CORS Ayarları (Frontend Erişimi İçin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Güvenlik için gerçek ortamda kısıtlanmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Motoru Başlat (Belleğe yükler - 10-15sn sürebilir)
engine = KizilelmaEngine()

# ---------------------------------------------------------
# VERI MODELLERI (Pydantic)
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    result: str
    status: str
    msg: str
    description: str
    confidence: int
    risk: int
    category: str
    source: str

# ---------------------------------------------------------
# API ENDPOINTLERI
# ---------------------------------------------------------

@app.get("/api/veri", response_model=List[Dict[str, Any]])
async def getir_veri():
    """Tüm veri setini JSON olarak döndürür"""
    try:
        return engine.df.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri okunamadı: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Sohbet Endpoint'i (Asenkron)"""
    raw_query = request.query.strip()

    if not raw_query:
        return { 
            "result": "Lütfen geçerli bir iddia veya soru girin.",
            "status": "RET", "msg": "⚠️ GEÇERSİZ GİRDİ", "description": "Boş sorgu.",
            "confidence": 0, "risk": 0, "category": "YOK", "source": "-"
        } # type: ignore

    try:
        # Motoru Çalıştır (Sözlük Döner)
        res = engine.ask(raw_query)
        # Linter'ın hatalarını tamamen yok etmek için model yerine sözlük dönüyoruz.
        # FastAPI 'response_model' sayesinde bu sözlüğü otomatik olarak doğrular.
        return { 
            "result": res['result'],
            "status": res['status'],
            "msg": res['msg'],
            "description": res['description'],
            "confidence": res['confidence'],
            "risk": res['risk'],
            "category": res['category'],
            "source": res['source']
        } # type: ignore
    except Exception as e:
        print(f"❌ Sunucu Hatası: {e}")
        raise HTTPException(status_code=500, detail="İşlem sırasında bir hata oluştu.")

@app.get("/")
async def root():
    return {"status": "online", "info": "KızılelmAI API Aktif. /docs adresine gidin."}

if __name__ == '__main__':
    # Frontend uyumluluğu için 5000 portunda başlatıyoruz
    uvicorn.run(app, host='127.0.0.1', port=5000)
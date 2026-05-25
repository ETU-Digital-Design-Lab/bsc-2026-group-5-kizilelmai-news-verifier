"""
KızılelmAI Backend API (FastAPI Layer)
Yapay zeka mantığı 'src/ai_core/engine/engine.py' dosyasındadır.
Burası asenkron, yüksek performanslı API sunucusudur.
"""
import os
import sys
import uvicorn # type: ignore
import redis
import json
import hashlib
from fastapi import FastAPI, HTTPException, Request # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
from typing import List, Dict, Any, Optional
from starlette.concurrency import run_in_threadpool # type: ignore
import time

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

# Redis Bağlantısı (Önbellek Katmanı)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("⚡ Redis Önbellek Katmanı: Aktif!")
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False
    print("⚠️  Redis bulunamadı, önbelleksiz devam ediliyor.")

CACHE_TTL = 86400  # 24 saat (saniye cinsinden)

# ---------------------------------------------------------
# VERI MODELLERI (Pydantic)
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    query: str

class InjectRequest(BaseModel):
    text: str
    label: int
    authority: float = 0.95

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

@app.get("/api/veri", response_model=Dict[str, Any])
async def getir_veri(page: int = 1, limit: int = 50):
    """Veri setini sayfalı (paginated) olarak döndürür"""
    try:
        total_records = len(engine.df)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated_data = engine.df.iloc[start_idx:end_idx].to_dict(orient='records')
        
        return {
            "total": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + limit - 1) // limit,
            "data": paginated_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri okunamadı: {str(e)}")

@app.delete("/api/admin/veri/{record_id}")
async def delete_record(record_id: int):
    """Belirli bir kaydı siler (Admin)"""
    try:
        success = engine.delete_knowledge(record_id)
        if success:
            return {"status": "success", "message": f"{record_id} numaralı kayıt başarıyla silindi."}
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@app.put("/api/admin/veri/{record_id}")
async def update_record(record_id: int, request: InjectRequest):
    """Belirli bir kaydı günceller (Admin)"""
    try:
        success = engine.update_knowledge(record_id, request.text, request.label, request.authority)
        if success:
            return {"status": "success", "message": f"{record_id} numaralı kayıt başarıyla güncellendi."}
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@app.get("/api/status")
async def get_status():
    """Sistem kaynaklarını ve veri tabanı durumunu döner"""
    return {
        "status": "online",
        "records": len(engine.df),
        "engine_version": "3.0.0-Elite",
        "uptime": "active",
        "context_depth": len(engine.context_buffer),
        "cache_status": "active" if REDIS_AVAILABLE else "disabled",
        "dynamic_records": len(engine.df) - 251
    }

@app.post("/api/inject")
async def inject_data(request: InjectRequest):
    """Sisteme canlı bilgi enjekte eder (Katman 10)"""
    try:
        success = engine.inject_knowledge(request.text, request.label, request.authority)
        if success:
            return {"status": "success", "message": "Bilgi başarıyla enjekte edildi."}
        return {"status": "error", "message": "Enjeksiyon başarısız."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Sohbet Endpoint'i - Redis Önbellekli (Asenkron)"""
    raw_query = request.query.strip()

    if not raw_query:
        return {
            "result": "Lütfen geçerli bir iddia veya soru girin.",
            "status": "RET", "msg": "⚠️ GEÇERSİZ GİRDİ", "description": "Boş sorgu.",
            "confidence": 0, "risk": 0, "category": "YOK", "source": "-"
        } # type: ignore

    # --- Redis Önbellek Kontrolü ---
    cache_key = "chat:" + hashlib.sha256(raw_query.lower().strip().encode()).hexdigest()
    if REDIS_AVAILABLE and redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                print(f"⚡ Önbellekten Yanıt: '{raw_query[:40]}...'")
                return json.loads(cached)  # type: ignore
        except Exception as e:
            print(f"⚠️ Redis okuma hatası: {e}")

    try:
        # Motoru Çalıştır (Asenkron Thread Pool içinde) - Bloklamayı önler
        res = await run_in_threadpool(engine.ask, raw_query)

        response = {
            "result": res['result'],
            "status": res['status'],
            "msg": res['msg'],
            "description": res['description'],
            "confidence": res['confidence'],
            "risk": res['risk'],
            "category": res['category'],
            "source": res['source']
        }

        # --- Redis Önbelleğe Yaz ---
        if REDIS_AVAILABLE and redis_client:
            try:
                redis_client.setex(cache_key, CACHE_TTL, json.dumps(response, ensure_ascii=False))
                print(f"💾 Önbelleğe Kaydedildi (24s): '{raw_query[:40]}...'")
            except Exception as e:
                print(f"⚠️ Redis yazma hatası: {e}")

        return response  # type: ignore
    except Exception as e:
        print(f"❌ Sunucu Hatası: {e}")
        raise HTTPException(status_code=500, detail="İşlem sırasında bir hata oluştu.")

@app.get("/")
async def root():
    return {"status": "online", "info": "KızılelmAI API Aktif. /docs adresine gidin."}

if __name__ == '__main__':
    # Frontend uyumluluğu için 5000 portunda başlatıyoruz
    uvicorn.run(app, host='127.0.0.1', port=5000)
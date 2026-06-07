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

import subprocess
from contextlib import asynccontextmanager

# ---------------------------------------------------------
# UYGULAMA YAPILANDIRMASI
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlarken arka plan scraper servisini başlat
    print("🚀 Otomatik Haber Scraper servisi arka planda başlatılıyor...")
    scraper_process = subprocess.Popen(
        [sys.executable, os.path.join(SRC_DIR, "ai_core", "ingest", "auto_scraper.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    yield
    # Uygulama kapanırken scraper servisini de kapat
    print("🛑 Kapanış: Otomatik Haber Scraper servisi durduruluyor...")
    scraper_process.terminate()

app = FastAPI(
    title="KızılelmAI API",
    description="Yerel Haber Doğrulama ve Analiz Motoru API",
    version="2.0.0",
    lifespan=lifespan
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
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
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
    force_refresh: Optional[bool] = False

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
    source_channel: Optional[str] = "Belirlenemedi"

# ---------------------------------------------------------
# KIMLIK DOGRULAMA (AUTH) BAGLANTILARI
# ---------------------------------------------------------
import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.backend.auth import (
    get_db_connection, get_password_hash, verify_password,
    create_access_token, generate_verification_code, send_verification_email,
    SECRET_KEY, ALGORITHM
)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        first_name: str = payload.get("first_name", "")
        last_name: str = payload.get("last_name", "")
        if email is None:
            raise HTTPException(status_code=401, detail="Geçersiz token")
        return {"email": email, "role": role, "first_name": first_name, "last_name": last_name}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token süresi dolmuş")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz token")

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Yalnızca admin yetkisine sahip kullanıcılar erişebilir")
    return current_user

class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

class VerifyRequest(BaseModel):
    email: str
    code: str

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register_user(request: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (request.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
        
    code = generate_verification_code()
    hashed_pw = get_password_hash(request.password)
    
    cursor.execute('''
        INSERT INTO users (email, password_hash, is_verified, verify_code, first_name, last_name)
        VALUES (%s, %s, False, %s, %s, %s)
    ''', (request.email, hashed_pw, code, request.first_name, request.last_name))
    conn.commit()
    conn.close()
    
    # Send email
    send_verification_email(request.email, code)
    return {"status": "success", "message": "Kayıt başarılı. Lütfen email adresinize gelen kodu girin."}

@app.post("/api/auth/verify")
async def verify_user(request: VerifyRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s AND verify_code = %s", (request.email, request.code))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Geçersiz doğrulama kodu veya email.")
        
    cursor.execute("UPDATE users SET is_verified = True, verify_code = NULL WHERE email = %s", (request.email,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Hesabınız başarıyla doğrulandı. Giriş yapabilirsiniz."}

@app.post("/api/auth/login")
async def login_user(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (request.email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(request.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Geçersiz email veya şifre.")
        
    if not user['is_verified']:
        raise HTTPException(status_code=403, detail="Lütfen önce email adresinizi doğrulayın.")
        
    access_token = create_access_token(data={
        "sub": user['email'], 
        "role": user['role'],
        "first_name": user['first_name'],
        "last_name": user['last_name']
    })
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user['role'],
        "first_name": user['first_name'],
        "last_name": user['last_name']
    }

# ---------------------------------------------------------
# API ENDPOINTLERI
# ---------------------------------------------------------

@app.get("/api/veri", response_model=Dict[str, Any])
async def getir_veri(page: int = 1, limit: int = 50, sort: str = "oldest", user: dict = Depends(require_admin)):
    """Veri setini sayfalı (paginated) olarak döndürür"""
    try:
        engine.sync_db()
        total_records = len(engine.df)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        # Sıralama
        if sort == "newest":
            df_sorted = engine.df.iloc[::-1]
        else:
            df_sorted = engine.df
            
        paginated_data = df_sorted.iloc[start_idx:end_idx].to_dict(orient='records')
        
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
async def delete_record(record_id: int, user: dict = Depends(require_admin)):
    """Belirli bir kaydı siler (Admin)"""
    try:
        success = engine.delete_knowledge(record_id)
        if success:
            return {"status": "success", "message": f"{record_id} numaralı kayıt başarıyla silindi."}
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@app.put("/api/admin/veri/{record_id}")
async def update_record(record_id: int, request: InjectRequest, user: dict = Depends(require_admin)):
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
    try:
        engine.sync_db()
    except Exception:
        pass
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
async def inject_data(request: InjectRequest, user: dict = Depends(require_admin)):
    """Sisteme canlı bilgi enjekte eder (Katman 10)"""
    try:
        success = engine.inject_knowledge(request.text, request.label, request.authority)
        if success:
            return {"status": "success", "message": "Bilgi başarıyla enjekte edildi."}
        return {"status": "error", "message": "Enjeksiyon başarısız."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Sohbet Endpoint'i - Redis Önbellekli (Asenkron)"""
    raw_query = request.query.strip()
    
    # Kullanıcı kimliğini (opsiyonel) al
    user_email = "anonim"
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_email = payload.get("sub", "anonim")
        except Exception:
            pass
            
    # --- BASİT SOHBET KONTROLÜ (HIZLI YANIT) ---
    import string
    lower_query = raw_query.lower()
    clean_query = lower_query.translate(str.maketrans('', '', string.punctuation))
    greetings = ["merhaba", "selam", "naber", "nasılsın", "hello", "hi", "iyi misin", "selamlar"]
    
    if clean_query in greetings or clean_query.startswith("merhaba"):
        return {
            "result": "Merhaba! Ben KızılelmAI Doğrulama Asistanıyım. Size bir haberi veya iddiayı analiz etme konusunda yardımcı olabilirim. Lütfen doğrulamak istediğiniz metni yazın.",
            "status": "SYS", "msg": "💬 SOHBET", "description": "Sistem Mesajı",
            "confidence": 100, "risk": 0, "category": "GENEL", "source": "Sistem"
        }

    if not raw_query:
        return {
            "result": "Lütfen geçerli bir iddia veya soru girin.",
            "status": "RET", "msg": "⚠️ GEÇERSİZ GİRDİ", "description": "Boş sorgu.",
            "confidence": 0, "risk": 0, "category": "YOK", "source": "-"
        } # type: ignore

    # --- Redis Önbellek Kontrolü ---
    cache_key = "chat:" + hashlib.sha256(raw_query.lower().strip().encode()).hexdigest()
    
    # Check headers and body for force-refresh / no-cache requests
    bypass_cache = False
    cache_control = req.headers.get("Cache-Control", "").lower()
    pragma = req.headers.get("Pragma", "").lower()
    if "no-cache" in cache_control or "no-cache" in pragma or request.force_refresh:
        bypass_cache = True
        print(f"🔄 Cache Bypass tetiklendi (Header/Parametre): '{raw_query[:40]}...'")

    if REDIS_AVAILABLE and redis_client and not bypass_cache:
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
            "source": res['source'],
            "source_channel": res.get('source_channel', 'Belirlenemedi')
        }

        # --- Redis Önbelleğe Yaz ---
        if REDIS_AVAILABLE and redis_client:
            try:
                redis_client.setex(cache_key, CACHE_TTL, json.dumps(response, ensure_ascii=False))
                print(f"💾 Önbelleğe Kaydedildi (24s): '{raw_query[:40]}...'")
            except Exception as e:
                print(f"⚠️ Redis yazma hatası: {e}")

        # --- Veritabanına (PostgreSQL) Logla ---
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_logs (user_email, query, response_status)
                VALUES (%s, %s, %s)
            ''', (user_email, raw_query, response['status']))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ PostgreSQL Log kaydı hatası: {e}")

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
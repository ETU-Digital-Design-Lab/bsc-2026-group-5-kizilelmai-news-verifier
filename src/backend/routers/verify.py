"""
Verify Router — Sohbet ve doğrulama endpoint'leri.
/api/chat, /api/inject, /api/status, /api/veri
"""
import string
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
import jwt

from src.backend.auth import get_db_connection, SECRET_KEY, ALGORITHM
from src.backend.routers.auth import get_current_user, require_admin
from src.backend.middleware.cache import build_cache_key, get_cached, set_cached

router = APIRouter(tags=["verify"])


# ---- Pydantic Modeller ----

class ChatRequest(BaseModel):
    query: str
    force_refresh: Optional[bool] = False


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
    source_id: Optional[int] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    source_attribution_basis: str = "unknown"
    evidence_metadata: Optional[Dict[str, Any]] = None
    classifier: Optional[Dict[str, Any]] = None


class InjectRequest(BaseModel):
    text: str
    label: int
    authority: float = 0.95
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    evidence_id: Optional[str] = None
    label_provenance: str = "unknown"


def _extract_user_email(req: Request) -> str:
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("sub", "anonim")
        except Exception:
            pass
    return "anonim"


def make_router(engine, redis_client, redis_available: bool):
    """Engine ve Redis bağımlılıklarını inject ederek router'ı döndürür."""

    @router.get("/")
    async def root():
        return {"status": "online", "info": "KızılelmAI API Aktif. /docs adresine gidin."}

    @router.get("/api/status")
    async def get_status():
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
            "cache_status": "active" if redis_available else "disabled",
            "dynamic_records": max(0, len(engine.df) - engine.baseline_records),
        }

    @router.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest, req: Request):
        raw_query = request.query.strip()
        if not raw_query:
            return {
                "result": "Lütfen geçerli bir iddia veya soru girin.",
                "status": "RET", "msg": "⚠️ GEÇERSİZ GİRDİ", "description": "Boş sorgu.",
                "confidence": 0, "risk": 0, "category": "YOK", "source": "-",
            }  # type: ignore

        user_email = _extract_user_email(req)

        # Hızlı selamlama cevabı
        clean_query = raw_query.lower().translate(str.maketrans("", "", string.punctuation))
        greetings = ["merhaba", "selam", "naber", "nasılsın", "hello", "hi", "iyi misin", "selamlar"]
        if clean_query in greetings or clean_query.startswith("merhaba"):
            return {
                "result": "Merhaba! Ben KızılelmAI, nasıl yardımcı olabilirim?",
                "status": "SYS", "msg": "💬 SOHBET", "description": "Sistem Mesajı",
                "confidence": 100, "risk": 0, "category": "GENEL", "source": "Sistem",
            }

        # Cache kontrol
        cache_key = build_cache_key(raw_query)
        bypass_cache = (
            "no-cache" in req.headers.get("Cache-Control", "").lower()
            or "no-cache" in req.headers.get("Pragma", "").lower()
            or request.force_refresh
        )

        if redis_available and not bypass_cache:
            cached = get_cached(redis_client, cache_key)
            if cached:
                print(f"⚡ Önbellekten Yanıt: '{raw_query[:40]}...'")
                return cached  # type: ignore

        try:
            res = await run_in_threadpool(engine.ask, raw_query)
            response = {
                "result": res["result"], "status": res["status"], "msg": res["msg"],
                "description": res["description"], "confidence": res["confidence"],
                "risk": res["risk"], "category": res["category"], "source": res["source"],
                "source_channel": res.get("source_channel", "Belirlenemedi"),
                "source_id": res.get("source_id"),
            }

            if redis_available:
                set_cached(redis_client, cache_key, response, response["status"])

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO user_logs (user_email, query, response_status) VALUES (%s, %s, %s)",
                    (user_email, raw_query, response["status"]),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"⚠️ PostgreSQL Log kaydı hatası: {e}")

            return response  # type: ignore
        except Exception as e:
            print(f"❌ Sunucu Hatası: {e}")
            raise HTTPException(status_code=500, detail="İşlem sırasında bir hata oluştu.")

    @router.post("/api/chat/clear")
    async def clear_chat():
        try:
            engine.context_buffer = []
            return {"status": "success", "message": "Sohbet bağlamı başarıyla temizlendi."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Temizleme hatası: {str(e)}")

    @router.post("/api/inject")
    async def inject_data(request: InjectRequest, user: dict = Depends(require_admin)):
        try:
            metadata = request.dict(exclude={"text", "label", "authority"})
            success = engine.inject_knowledge(request.text, request.label, request.authority, **metadata)
            if success:
                return {"status": "success", "message": "Bilgi başarıyla enjekte edildi."}
            return {"status": "error", "message": "Enjeksiyon başarısız."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

    @router.get("/api/veri", response_model=Dict[str, Any])
    async def getir_veri(page: int = 1, limit: int = 50, sort: str = "oldest", user: dict = Depends(require_admin)):
        try:
            engine.sync_db()
            total_records = len(engine.df)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            df_sorted = engine.df.iloc[::-1] if sort == "newest" else engine.df
            paginated_data = df_sorted.iloc[start_idx:end_idx].to_dict(orient="records")
            return {
                "total": total_records, "page": page, "limit": limit,
                "total_pages": (total_records + limit - 1) // limit,
                "data": paginated_data,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Veri okunamadı: {str(e)}")

    @router.get("/api/veri/{record_id}")
    async def get_record(record_id: int, user: dict = Depends(require_admin)):
        try:
            engine.sync_db()
            row = engine.df[engine.df["id"] == record_id]
            if not row.empty:
                record = row.iloc[0].to_dict()
                return {
                    "id": int(record["id"]), "text": str(record["text"]),
                    "label": int(record["label"]), "authority": float(record["authority"]),
                    **{k: str(record[k]) if record.get(k) is not None else None
                       for k in ("source_url", "publisher", "published_at", "evidence_id", "label_provenance", "ingested_at")},
                }
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

    @router.delete("/api/admin/veri/{record_id}")
    async def delete_record(record_id: int, user: dict = Depends(require_admin)):
        try:
            success = engine.delete_knowledge(record_id)
            if success:
                return {"status": "success", "message": f"{record_id} numaralı kayıt başarıyla silindi."}
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

    @router.put("/api/admin/veri/{record_id}")
    async def update_record(record_id: int, request: InjectRequest, user: dict = Depends(require_admin)):
        try:
            metadata = request.dict(exclude={"text", "label", "authority"})
            success = engine.update_knowledge(record_id, request.text, request.label, request.authority, **metadata)
            if success:
                return {"status": "success", "message": f"{record_id} numaralı kayıt başarıyla güncellendi."}
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

    return router

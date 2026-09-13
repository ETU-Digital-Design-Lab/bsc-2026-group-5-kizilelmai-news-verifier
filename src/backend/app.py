"""
KızılelmAI Backend API — FastAPI giriş noktası.
Yapay zeka mantığı : src/ai_core/engine/engine.py
Router katmanları  : src/backend/routers/
Önbellek katmanı   : src/backend/middleware/cache.py
"""
import os
import sys
import subprocess
import uvicorn  # type: ignore
from contextlib import asynccontextmanager
from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

# ---- PATH AYARLAMALARI ----
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))   # src/backend
SRC_DIR = os.path.dirname(CURRENT_DIR)                     # src/
ROOT_DIR = os.path.dirname(SRC_DIR)                        # proje kökü
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, ROOT_DIR)

# ---- ENGINE ----
try:
    from ai_core.engine.engine import KizilelmaEngine  # type: ignore
except ImportError as e:
    print(f"❌ Kritik Hata: Logic modülü bulunamadı! {e}")
    sys.exit(1)

# ---- CACHE ----
from src.backend.middleware.cache import init_redis  # noqa: E402
from src.backend.routers import auth, admin  # noqa: E402
from src.backend.routers.verify import make_router  # noqa: E402

# ---- GLOBAL ----
engine = KizilelmaEngine()
redis_client, REDIS_AVAILABLE = init_redis()


# ---- YAŞAM DÖNGÜSÜ ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    enable_scraper = os.getenv("ENABLE_AUTO_SCRAPER", "0").lower() in ("1", "true")
    scraper_process = None
    if enable_scraper:
        print("🚀 Otomatik Haber Scraper servisi arka planda başlatılıyor...")
        scraper_process = subprocess.Popen(
            [sys.executable, os.path.join(SRC_DIR, "ai_core", "ingest", "auto_scraper.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        print("🔒 Dondurulmuş Değerlendirme Modu: Arka plan kazıyıcı devre dışı (Korpus sabit tutuluyor).")
    yield
    if scraper_process:
        print("🛑 Kapanış: Otomatik Haber Scraper servisi durduruluyor...")
        scraper_process.terminate()


# ---- UYGULAMA ----
app = FastAPI(
    title="KızılelmAI API",
    description="Yerel Haber Doğrulama ve Analiz Motoru API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- ROUTER'LARI BAĞ ----
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(make_router(engine, redis_client, REDIS_AVAILABLE))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)

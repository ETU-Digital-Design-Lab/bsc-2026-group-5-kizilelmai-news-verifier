"""
Cache Middleware — Süreç-içi bellek ve Redis önbellek yönetimi.
"""
import hashlib
import json
import os
import redis

CACHE_TTL = 86400  # 24 saat


def build_cache_key(query: str) -> str:
    return "chat:" + hashlib.sha256(query.lower().strip().encode()).hexdigest()


def init_redis():
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
        client.ping()
        print("⚡ Redis Önbellek Katmanı: Aktif!")
        return client, True
    except Exception:
        print("⚠️  Redis bulunamadı, önbelleksiz devam ediliyor.")
        return None, False


def get_cached(client, key: str):
    if client is None:
        return None
    try:
        cached = client.get(key)
        return json.loads(cached) if cached else None
    except Exception as e:
        print(f"⚠️ Redis okuma hatası: {e}")
        return None


def set_cached(client, key: str, value: dict, status: str):
    if client is None:
        return
    try:
        ttl = 30 if status == "RET" else CACHE_TTL
        label = "kısa süreli (30sn)" if status == "RET" else "24s"
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        print(f"💾 Önbelleğe Kaydedildi ({label})")
    except Exception as e:
        print(f"⚠️ Redis yazma hatası: {e}")

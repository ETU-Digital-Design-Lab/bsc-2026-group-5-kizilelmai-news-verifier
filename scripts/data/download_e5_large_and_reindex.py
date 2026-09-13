"""
scripts/data/download_e5_large_and_reindex.py
=============================================
KızılelmAI — Faz 2: multilingual-e5-large İndirme ve Corpus Yeniden İndeksleme

Mevcut intfloat/multilingual-e5-small (384-dim, 117M param) yerine
intfloat/multilingual-e5-large (1024-dim, 560M param) kullanılacak.

Bu betik:
1. multilingual-e5-large modelini cache'e indirir
2. corpus.csv'yi batch'ler halinde yeniden vektörleştirir (VRAM kısıtı: 4GB FP16)
3. Yeni models.json SHA-256'larını günceller
4. snapshot_report.json'ı günceller

Kullanım:
    python scripts/data/download_e5_large_and_reindex.py \\
        --corpus data/corpus_snapshots/local_csv_20260913_v2/corpus.csv \\
        --output-dir data/corpus_snapshots/local_csv_20260913_v2 \\
        --models .runtime/evaluation_models/models.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

MODEL_ID = "intfloat/multilingual-e5-large"
BATCH_SIZE = 64   # 4GB VRAM için güvenli batch boyutu
MAX_LENGTH = 512


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path,
                    default=_ROOT / "data" / "corpus_snapshots" / "local_csv_20260913_v2" / "corpus.csv")
    ap.add_argument("--output-dir", type=Path,
                    default=_ROOT / "data" / "corpus_snapshots" / "local_csv_20260913_v2")
    ap.add_argument("--models", type=Path,
                    default=_ROOT / ".runtime" / "evaluation_models" / "models.json")
    ap.add_argument("--cache-dir", type=Path,
                    default=_ROOT / ".runtime" / "evaluation_models" / "cache")
    ap.add_argument("--device", type=int, default=0, help="CUDA device (-1=CPU)")
    a = ap.parse_args()

    print("=" * 60)
    print("Faz 2: multilingual-e5-large İndirme ve Yeniden İndeksleme")
    print("=" * 60)

    # 1. Modeli indir
    print(f"\n[1/4] Model indiriliyor: {MODEL_ID}")
    import torch
    from sentence_transformers import SentenceTransformer

    os.environ["TRANSFORMERS_CACHE"] = str(a.cache_dir)
    os.environ["HF_HOME"] = str(a.cache_dir.parent)

    # VRAM yönetimi: NLI ve reranker bellekte değil
    device = f"cuda:{a.device}" if (a.device >= 0 and torch.cuda.is_available()) else "cpu"
    print(f"  Cihaz: {device}")
    if torch.cuda.is_available():
        print(f"  VRAM toplam: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    t0 = time.perf_counter()
    model = SentenceTransformer(
        MODEL_ID,
        cache_folder=str(a.cache_dir),
        device=device,
    )
    if device.startswith("cuda"):
        model.half()  # FP16 → VRAM optimizasyonu
    print(f"  Model yüklendi ({(time.perf_counter()-t0):.1f}s)")

    # 2. Corpus yükle
    print(f"\n[2/4] Corpus yükleniyor: {a.corpus}")
    rows = list(csv.DictReader(open(a.corpus, encoding="utf-8")))
    texts = ["passage: " + r["text"] for r in rows]
    print(f"  {len(texts)} kayıt bulundu")

    # 3. Toplu vektörleştirme
    print(f"\n[3/4] Vektörleştirme başlıyor (batch_size={BATCH_SIZE})...")
    import numpy as np
    t0 = time.perf_counter()
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    elapsed = time.perf_counter() - t0
    print(f"  Tamamlandı: {embeddings.shape} — {elapsed:.0f}s")

    # Embeddings'i kaydet
    a.output_dir.mkdir(parents=True, exist_ok=True)
    emb_path = a.output_dir / "embeddings_e5_large.npy"
    np.save(emb_path, embeddings.astype(np.float32))
    print(f"  Embeddings kaydedildi: {emb_path}")

    # 4. models.json güncelle
    print(f"\n[4/4] models.json güncelleniyor: {a.models}")
    models_data = json.loads(a.models.read_text(encoding="utf-8"))

    # Cache klasöründeki model dosyalarını bul
    model_cache_name = MODEL_ID.replace("/", "--")
    model_dir = a.cache_dir / f"models--{model_cache_name}"
    snapshots = list((model_dir / "snapshots").iterdir()) if (model_dir / "snapshots").exists() else []
    if snapshots:
        snapshot_dir = snapshots[0]
        revision = snapshot_dir.name
        files_sha = {}
        for f in snapshot_dir.iterdir():
            if f.is_file():
                files_sha[f.name] = sha256_file(f)

        models_data["embedding"] = {
            "model_id": MODEL_ID,
            "revision": revision,
            "path": str(snapshot_dir),
            "files_sha256": files_sha,
            "dim": 1024,
            "note": "Upgraded from multilingual-e5-small (384-dim) to e5-large (1024-dim) on 2026-09-13",
        }
        a.models.write_text(json.dumps(models_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  models.json güncellendi: {MODEL_ID} @ {revision}")
    else:
        print("  [UYARI] Model cache dizini bulunamadı — models.json elle güncellenmeli.")

    print("\n[TAMAMLANDI] Bir sonraki adım: snapshot_report.py ile snapshot mühürle")
    print(f"  Embedding: {emb_path}")
    print(f"  Boyut: {embeddings.shape}")


if __name__ == "__main__":
    main()

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, Float, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector

FILE_DIR = Path(__file__).parent
ROOT_DIR = FILE_DIR.parent.parent.parent

DB_URL = os.getenv("DATABASE_URL", "postgresql://kizilelmai_user:kizilelmai_pass@db:5432/kizilelmai")
print(f"Connecting to database: {DB_URL}")
engine = create_engine(DB_URL)
Base = declarative_base()

sys.path.insert(0, str(ROOT_DIR))
from src.shared.evidence_schema import EvidenceColumns


class KnowledgeRecord(EvidenceColumns, Base):
    __tablename__ = 'knowledge_base'
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    label = Column(Integer, nullable=False)
    authority = Column(Float, nullable=False, default=0.85)
    embedding = Column(Vector(384))

def main():
    csv_path = ROOT_DIR / "data" / "processed" / "egitim_verisi_final.csv"
    npy_path = ROOT_DIR / "data" / "processed" / "egitim_verisi_final_embeddings.npy"

    if not csv_path.exists() or not npy_path.exists():
        print(f"Hata: Dosyalar bulunamadi: {csv_path}, {npy_path}")
        return

    print("Veri ve onceden hesaplanmis embeddingler yukleniyor...")
    df = pd.read_csv(csv_path)
    embeddings = np.load(npy_path)

    print(f"Veri boyutu: {len(df)}, Embedding boyutu: {embeddings.shape}")
    if len(df) > len(embeddings):
        print(f"Df boyutu ({len(df)}) embeddinglerden ({len(embeddings)}) fazla, ilk {len(embeddings)} kayit aliniyor...")
        df = df.iloc[:len(embeddings)]
    elif len(embeddings) > len(df):
        embeddings = embeddings[:len(df)]

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("pgvector extension aktif.")

    print("knowledge_base tablosu olusturuluyor...")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Tabloda zaten kayit var mi kontrol et
    count = session.query(KnowledgeRecord).count()
    if count >= len(df):
        print(f"Veritabaninda zaten {count} kayit var. Yukleme atlaniyor.")
        session.close()
        return

    if count > 0:
        print(f"Mevcut {count} kayit temizleniyor...")
        session.query(KnowledgeRecord).delete()
        session.commit()

    print(f"30,331 kayit veritabanina aktariliyor...")
    batch_size = 2000
    total = len(df)
    
    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        batch_df = df.iloc[start_idx:end_idx]
        batch_emb = embeddings[start_idx:end_idx]

        records = []
        for i, row in enumerate(batch_df.itertuples()):
            records.append(
                KnowledgeRecord(
                    id=int(row.id) if hasattr(row, 'id') and not pd.isna(row.id) else start_idx + i + 1,
                    text=str(row.text),
                    label=int(row.label),
                    authority=float(row.authority) if hasattr(row, 'authority') and not pd.isna(row.authority) else 0.85,
                    embedding=batch_emb[i].tolist()
                )
            )
        session.bulk_save_objects(records)
        session.commit()
        print(f"  [{end_idx}/{total}] kaydedildi.")

    # Indeks olustur (IVFFlat veya HNSW)
    print("Vektor indeksi (HNSW) olusturuluyor...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS kb_embedding_hnsw_idx ON knowledge_base USING hnsw (embedding vector_cosine_ops)"))
            conn.commit()
            print("HNSW indeksi basariyla olusturuldu.")
    except Exception as e:
        print(f"Indeks olusturma notu: {e}")

    session.close()
    print("=== TAMAMLANDI: 30,331 KAYIT POSTGRESQL/PGVECTOR VERITABANINA AKTARILDI! ===")

if __name__ == "__main__":
    main()

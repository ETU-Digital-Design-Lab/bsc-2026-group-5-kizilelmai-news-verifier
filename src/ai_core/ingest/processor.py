import os
import pandas as pd # type: ignore
import sys
from pathlib import Path
import numpy as np # type: ignore
from sqlalchemy import create_engine, Column, Integer, Float, Text # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker # type: ignore
from pgvector.sqlalchemy import Vector # type: ignore
from sentence_transformers import SentenceTransformer # type: ignore

# Proje kök dizini ayarı
FILE_DIR = Path(__file__).parent
ROOT_DIR = FILE_DIR.parent.parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from src.shared.preprocess import preprocess # type: ignore
except ImportError:
    try:
        from shared.preprocess import preprocess # type: ignore
    except:
        def preprocess(text, **kwargs): return text # Fallback

# openpyxl kontrolü
try:
    import openpyxl # type: ignore
except ImportError:
    print("❌ HATA: openpyxl kütüphanesi eksik.")
    print("Lütfen şu komutu çalıştırın: pip install openpyxl")
    print("Veya tüm kütüphaneler için: pip install -r requirements.txt")
    exit(1)

# --- Veritabanı Yapılandırması ---
DB_URL = "postgresql://kizilelmai_user:kizilelmai_pass@localhost:5433/kizilelmai"
engine = create_engine(DB_URL)
Base = declarative_base()

class KnowledgeRecord(Base):
    __tablename__ = 'knowledge_base'
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    label = Column(Integer, nullable=False)
    authority = Column(Float, nullable=False, default=0.85)
    embedding = Column(Vector(384))  # multilingual-e5-small boyutu

def veri_hazirla():
    print("--- 1. ADIM: Veriler Okunuyor ---")
    gercek_yol = ROOT_DIR / "data" / "raw" / "gercekler.xlsx"
    yalan_yol = ROOT_DIR / "data" / "raw" / "yalanlar.csv"

    if not gercek_yol.exists() or not yalan_yol.exists():
        print(f"❌ HATA: {gercek_yol} veya {yalan_yol} bulunamadı.")
        return

    print("Dosyalar okunuyor...")
    try:
        df_gercek = pd.read_excel(gercek_yol)
        try:
            df_yalan = pd.read_csv(yalan_yol, encoding='utf-8', on_bad_lines='skip')
        except UnicodeDecodeError:
            try:
                df_yalan = pd.read_csv(yalan_yol, encoding='windows-1254', sep=';', on_bad_lines='skip')
            except UnicodeDecodeError:
                df_yalan = pd.read_csv(yalan_yol, encoding='iso-8859-9', sep=';', on_bad_lines='skip')
    except Exception as e:
        print(f"❌ HATA: Dosyalar okunurken hata oluştu: {e}")
        return

    df_gercek = df_gercek.rename(columns={"Haber Metni": "text"})
    if 'text' not in df_yalan.columns:
        df_yalan.columns = ['text']

    df_gercek['label'] = 1
    df_yalan['label'] = 0

    df_final = pd.concat([df_gercek[["text", "label"]], df_yalan[["text", "label"]]])

    print("Metinler temizleniyor...")
    df_final["text"] = df_final["text"].apply(
        lambda t: preprocess(
            str(t) if pd.notna(t) else "",
            strip_html_tags=True,
            normalize_ws=True,
            remove_stopwords_flag=False,
        )
    )
    df_final = df_final[df_final["text"].str.len() > 0].reset_index(drop=True)
    df_final = df_final.sample(frac=1).reset_index(drop=True)

    print("--- 2. ADIM: Vektörler Hesaplanıyor (Sentence-Transformers) ---")
    local_model_path = ROOT_DIR / "src" / "ai_core" / "models" / "kizilelma_model_v1"
    if local_model_path.exists():
        model = SentenceTransformer(str(local_model_path))
    else:
        model = SentenceTransformer('intfloat/multilingual-e5-small')

    passage_texts = ["passage: " + str(t) for t in df_final["text"].tolist()]
    embeddings = model.encode(passage_texts, convert_to_numpy=True, show_progress_bar=True)

    print("--- 3. ADIM: PostgreSQL'e Kaydediliyor ---")
    try:
        # pgvector extension'ını aktifleştir
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        print(f"Uyarı: pgvector extension oluşturulamadı (zaten var olabilir): {e}")

    from sqlalchemy import text # type: ignore
    
    # Tabloyu oluştur (Varsa sil ve yeniden oluştur)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    records = []
    for i, row in df_final.iterrows():
        rec = KnowledgeRecord(
            text=row["text"],
            label=row["label"],
            authority=0.85,  # Varsayılan otorite
            embedding=embeddings[i]
        )
        records.append(rec)

    session.add_all(records)
    session.commit()
    session.close()

    print(f"\n✅ BAŞARILI: Toplam {len(df_final)} satır veri ve vektör PostgreSQL'e kaydedildi.")

if __name__ == "__main__":
    veri_hazirla()


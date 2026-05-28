import os
import sys
import pandas as pd
import requests
import io
import re
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, Float, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer

# Proje koek dizini ayari
FILE_DIR = Path(__file__).parent
ROOT_DIR = FILE_DIR.parent.parent.parent
sys.path.append(str(ROOT_DIR))

# Preprocess import
try:
    from src.shared.preprocess import preprocess
except ImportError:
    try:
        from shared.preprocess import preprocess
    except:
        def preprocess(text, **kwargs):
            return text

# Veritabani Yapilandirmasi
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

def clean_and_normalize(text_str):
    if not isinstance(text_str, str):
        return ""
    # URL'leri temizle
    text_str = re.sub(r'https?://\S+|www\.\S+', '', text_str)
    # E-posta adreslerini temizle
    text_str = re.sub(r'\S+@\S+', '', text_str)
    # Twitter kullanici adlarini temizle (@user)
    text_str = re.sub(r'@\S+', '', text_str)
    # Cift bosluklari ve satir baslarini temizle
    text_str = re.sub(r'\s+', ' ', text_str)
    return text_str.strip()

def download_file(url, filepath):
    if os.path.exists(filepath):
        print(f"  - {os.path.basename(filepath)} zaten mevcut, indirme atlaniyor.")
        return True
    print(f"  - Indiriliyor: {url} -> {filepath}")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            print("    Indirme basarili!")
            return True
        else:
            print(f"    Hata: Durum kodu {response.status_code}")
            return False
    except Exception as e:
        print(f"    Baglanti hatasi: {e}")
        return False

def main():
    print("=== KIZILELMAI 30K VERI HAZIRLAMA VE ENJEKSIYON HATTI ===")
    
    # Dizinleri olustur
    raw_dir = ROOT_DIR / "data" / "raw"
    processed_dir = ROOT_DIR / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Kaynak Dosyalari Indir
    urls = {
        "isakulaksiz_dataset.csv": "https://huggingface.co/datasets/isakulaksiz/turkish-fake-news-detection/resolve/main/dataset.csv",
        "ogozcelik_dataset.tsv": "https://huggingface.co/datasets/ogozcelik/turkish-fake-news-detection/resolve/main/mide22_all_tr.tsv",
        "diken_non-clickbait.csv": "https://raw.githubusercontent.com/clickbaittr/turkish-clickbait-dataset/master/dataset/diken_non-clickbait.csv",
        "evrensel_non-clickbait.csv": "https://raw.githubusercontent.com/clickbaittr/turkish-clickbait-dataset/master/dataset/evrensel_non-clickbait.csv",
        "limon_clickbait.csv": "https://raw.githubusercontent.com/clickbaittr/turkish-clickbait-dataset/master/dataset/limon_clickbait.csv"
    }

    print("\n--- 1. ADIM: Kaynak Dosyalar Kontrol Ediliyor/Indiriliyor ---")
    for filename, url in urls.items():
        filepath = raw_dir / filename
        download_file(url, str(filepath))

    # 2. Dosyalari Oku ve Yukle
    print("\n--- 2. ADIM: Dosyalar Bellege Yukleniyor ve Hazirlaniyor ---")
    
    # A. Isakulaksiz (0 = Fake, 1 = Real)
    try:
        df_isa = pd.read_csv(raw_dir / "isakulaksiz_dataset.csv")
        df_isa_clean = pd.DataFrame()
        df_isa_clean['text'] = df_isa['description'].fillna(df_isa['title']).apply(clean_and_normalize)
        df_isa_clean['label'] = df_isa['status']
        print(f"  * Isakulaksiz yuklendi: {len(df_isa_clean)} satir")
    except Exception as e:
        print("  * Isakulaksiz yuklenirken hata:", e)
        df_isa_clean = pd.DataFrame(columns=['text', 'label'])

    # B. Ogozcelik (label: 'False' = 0, 'True' = 1, 'Other' = Drop)
    try:
        df_ogo = pd.read_csv(raw_dir / "ogozcelik_dataset.tsv", sep='\t')
        df_ogo = df_ogo[df_ogo['label'].isin(['False', 'True'])].copy()
        df_ogo['label'] = df_ogo['label'].map({'False': 0, 'True': 1})
        df_ogo_clean = pd.DataFrame()
        df_ogo_clean['text'] = df_ogo['tweet'].apply(clean_and_normalize)
        df_ogo_clean['label'] = df_ogo['label']
        print(f"  * Ogozcelik yuklendi: {len(df_ogo_clean)} satir")
    except Exception as e:
        print("  * Ogozcelik yuklenirken hata:", e)
        df_ogo_clean = pd.DataFrame(columns=['text', 'label'])

    # C. Clickbait - Real (non-clickbait)
    try:
        df_diken = pd.read_csv(raw_dir / "diken_non-clickbait.csv")
        df_evrensel = pd.read_csv(raw_dir / "evrensel_non-clickbait.csv")
        df_real_cb = pd.concat([df_diken, df_evrensel], ignore_index=True)
        df_real_cb_clean = pd.DataFrame()
        df_real_cb_clean['text'] = df_real_cb['full_text'].apply(clean_and_normalize)
        df_real_cb_clean['label'] = 1 # Real
        print(f"  * Clickbait-Real (diken + evrensel) yuklendi: {len(df_real_cb_clean)} satir")
    except Exception as e:
        print("  * Clickbait-Real yuklenirken hata:", e)
        df_real_cb_clean = pd.DataFrame(columns=['text', 'label'])

    # D. Clickbait - Fake (clickbait)
    try:
        df_limon = pd.read_csv(raw_dir / "limon_clickbait.csv")
        df_fake_cb_clean = pd.DataFrame()
        df_fake_cb_clean['text'] = df_limon['full_text'].apply(clean_and_normalize)
        df_fake_cb_clean['label'] = 0 # Fake / Clickbait
        print(f"  * Clickbait-Fake (limon) yuklendi: {len(df_fake_cb_clean)} satir")
    except Exception as e:
        print("  * Clickbait-Fake yuklenirken hata:", e)
        df_fake_cb_clean = pd.DataFrame(columns=['text', 'label'])

    # 3. Birlestir ve Filtrele
    print("\n--- 3. ADIM: Veriler Birlestiriliyor ve Filtreleniyor ---")
    
    # Real Haberler
    df_all_real = pd.concat([
        df_isa_clean[df_isa_clean['label'] == 1],
        df_ogo_clean[df_ogo_clean['label'] == 1],
        df_real_cb_clean
    ], ignore_index=True)
    
    # Fake Haberler
    df_all_fake = pd.concat([
        df_isa_clean[df_isa_clean['label'] == 0],
        df_ogo_clean[df_ogo_clean['label'] == 0],
        df_fake_cb_clean
    ], ignore_index=True)

    # Temizlik ve Filtreler
    # Minimum karakter uzunlugu 30
    df_all_real = df_all_real[df_all_real['text'].str.len() > 30].drop_duplicates(subset=['text'])
    df_all_fake = df_all_fake[df_all_fake['text'].str.len() > 30].drop_duplicates(subset=['text'])

    print(f"  * Toplam Benzersiz REAL kayit sayisi: {len(df_all_real)}")
    print(f"  * Toplam Benzersiz FAKE kayit sayisi: {len(df_all_fake)}")

    if len(df_all_real) < 15000 or len(df_all_fake) < 15000:
        print("  * UYARI: Hedeflenen 15.000 satir icin yeterli kaynak yok! Mevcut maksimum dengeli boyuta cekiliyor.")
        min_size = min(len(df_all_real), len(df_all_fake))
        target_size = min_size
    else:
        target_size = 15000

    print(f"  * Esitleme Yapiliyor: Her sinif icin {target_size} satir seciliyor...")
    df_real_sampled = df_all_real.sample(n=target_size, random_state=42)
    df_fake_sampled = df_all_fake.sample(n=target_size, random_state=42)

    df_30k = pd.concat([df_real_sampled, df_fake_sampled], ignore_index=True)
    # Karistir
    df_30k = df_30k.sample(frac=1, random_state=42).reset_index(drop=True)
    
    output_path = processed_dir / "egitim_verisi_30k.csv"
    df_30k.to_csv(output_path, index=False, encoding='utf-8')
    print(f"  * Dengeli 30k veri seti basariyla olusturuldu ve kaydedildi: {output_path}")
    print(f"  * Sinif Dagilimi:\n{df_30k['label'].value_counts()}")

    # 4. Vektorlestir ve PostgreSQL'e Yaz
    print("\n--- 4. ADIM: Vektorlestirme (E5-Small) ve PostgreSQL Enjeksiyonu ---")
    
    # Test DB Connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  * PostgreSQL veritabanı baglantisi basarili!")
    except Exception as e:
        print("  * PostgreSQL veritabanına baglanilamadi! Lutfen PostgreSQL'in 5433 portunda acik oldugundan emin olun.")
        print("  Hata detayi:", e)
        print("  (Vektor veritabanı adimi atlanıyor, CSV ile devam edilecek)")
        return

    # Load Model
    local_model_path = ROOT_DIR / "src" / "ai_core" / "models" / "kizilelma_model_v1"
    if local_model_path.exists():
        print(f"  * Yerel embedding modeli yukleniyor: {local_model_path}")
        model = SentenceTransformer(str(local_model_path))
    else:
        print("  * 'intfloat/multilingual-e5-small' embedding modeli indiriliyor/yukleniyor...")
        model = SentenceTransformer('intfloat/multilingual-e5-small')

    # Vector Extension'ı aktiflestir
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("  * pgvector extension kontrol edildi/aktiflestirildi.")
    except Exception as e:
        print("  * pgvector extension uyarisi:", e)

    # Tabloyu sifirla
    print("  * knowledge_base tablosu sifirlaniyor...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    # Vektorleri hesapla ve kaydet (Batch olarak islem bellek sorunlarini onler)
    print("  * Cumleler vektorlestiriliyor ve veritabanina ekleniyor...")
    Session = sessionmaker(bind=engine)
    session = Session()

    batch_size = 500
    total_len = len(df_30k)
    
    for start_idx in range(0, total_len, batch_size):
        end_idx = min(start_idx + batch_size, total_len)
        batch_df = df_30k.iloc[start_idx:end_idx]
        
        # Passage prefix'i E5 modelleri icin arama dogrulugunu artirir
        passage_texts = ["passage: " + str(t) for t in batch_df["text"].tolist()]
        embeddings = model.encode(passage_texts, convert_to_numpy=True, show_progress_bar=False)
        
        records = []
        for i, row in enumerate(batch_df.itertuples()):
            rec = KnowledgeRecord(
                text=row.text,
                label=row.label,
                authority=0.85,
                embedding=embeddings[i]
            )
            records.append(rec)
            
        session.add_all(records)
        session.commit()
        print(f"    [{end_idx}/{total_len}] kayit basariyla eklendi.")

    session.close()
    print("=== BAŞARILI: VERİ HAZIRLAMA VE POSTGRESQL AKTARIMI TAMAMLANDI! ===")

if __name__ == "__main__":
    main()

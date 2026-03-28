import os
import pandas as pd # type: ignore
import sys
from pathlib import Path

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

def veri_hazirla():
    print("--- 1. ADIM: Veriler Okunuyor ---")
    # Dosya yolları (Pathlib ile güvenli)
    gercek_yol = ROOT_DIR / "data" / "raw" / "gercekler.xlsx"
    yalan_yol = ROOT_DIR / "data" / "raw" / "yalanlar.csv"

    # Dosyalar yerinde mi kontrol et
    if not gercek_yol.exists() or not yalan_yol.exists():
        print(f"❌ HATA: {gercek_yol} veya {yalan_yol} bulunamadı.")
        return

    # 1. Dosyaları Oku
    print("Dosyalar okunuyor...")
    try:
        # Gerçek haberler Excel formatında
        df_gercek = pd.read_excel(gercek_yol)
        # Yalan haberler CSV formatında
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

    # 2. Sütun İsimlerini Düzelt ('text' yapacağız)
    df_gercek = df_gercek.rename(columns={"Haber Metni": "text"})
    
    if 'text' not in df_yalan.columns:
        df_yalan.columns = ['text']

    # 3. Etiketle (1: Gerçek, 0: Yalan)
    df_gercek['label'] = 1
    df_yalan['label'] = 0

    # 4. Birleştir
    df_final = pd.concat([df_gercek[["text", "label"]], df_yalan[["text", "label"]]])

    # 4b. Ön işleme
    df_final["text"] = df_final["text"].apply(
        lambda t: preprocess(
            str(t) if pd.notna(t) else "",
            strip_html_tags=True,
            normalize_ws=True,
            remove_stopwords_flag=False,
        )
    )
    df_final = df_final[df_final["text"].str.len() > 0].reset_index(drop=True)

    # 5. Karıştır (Shuffle)
    df_final = df_final.sample(frac=1).reset_index(drop=True)

    # 6. Kaydet
    processed_dir = ROOT_DIR / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    cikis_yolu = processed_dir / "egitim_verisi_final.csv"

    try:
        df_final.to_csv(cikis_yolu, index=False, encoding='utf-8-sig')
        print(f"\n✅ BAŞARILI: Toplam {len(df_final)} satır veri birleştirildi.")
        print(f"'{cikis_yolu}' dosyası oluşturuldu.")
    except Exception as e:
        print(f"❌ HATA: Dosya kaydedilirken hata oluştu: {e}")
        return

if __name__ == "__main__":
    veri_hazirla()

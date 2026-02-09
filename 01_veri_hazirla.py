import os
import pandas as pd

from preprocess import preprocess

# openpyxl kontrolü
try:
    import openpyxl
except ImportError:
    print("❌ HATA: openpyxl kütüphanesi eksik.")
    print("Lütfen şu komutu çalıştırın: pip install openpyxl")
    print("Veya tüm kütüphaneler için: pip install -r requirements.txt")
    exit(1)

def veri_hazirla():
    print("--- 1. ADIM: Veriler Okunuyor ---")
    
    # Dosya yolları (00_veri_uydur.py ile oluşturduğumuz dosyalar)
    gercek_yol = "veriler/gercekler.xlsx"
    yalan_yol = "veriler/yalanlar.csv"

    # Dosyalar yerinde mi kontrol et
    if not os.path.exists(gercek_yol) or not os.path.exists(yalan_yol):
        print("HATA: 'veriler' klasöründe dosyalar bulunamadı.")
        print("Lütfen önce '00_veri_uydur.py' kodunu çalıştır.")
        return

    # 1. Dosyaları Oku
    print("Dosyalar okunuyor...")
    try:
        # Gerçek haberler Excel formatında
        df_gercek = pd.read_excel(gercek_yol)
        # Yalan haberler CSV formatında
        df_yalan = pd.read_csv(yalan_yol)
    except Exception as e:
        print(f"❌ HATA: Dosyalar okunurken hata oluştu: {e}")
        return

    # 2. Sütun İsimlerini Düzelt ('text' yapacağız)
    # 00_veri_uydur.py kodunda Excel sütununa 'Haber Metni' demiştik:
    df_gercek = df_gercek.rename(columns={"Haber Metni": "text"})
    
    # Yalan haber dosyasında zaten 'text' var ama garanti olsun:
    if 'text' not in df_yalan.columns:
        df_yalan.columns = ['text']

    # 3. Etiketle (1: Gerçek, 0: Yalan)
    df_gercek['label'] = 1
    df_yalan['label'] = 0

    # 4. Birleştir
    df_final = pd.concat([df_gercek[["text", "label"]], df_yalan[["text", "label"]]])

    # 4b. Ön işleme (HTML temizleme, boşluk normalleştirme; stopword opsiyonel)
    df_final["text"] = df_final["text"].apply(
        lambda t: preprocess(
            str(t) if pd.notna(t) else "",
            strip_html_tags=True,
            normalize_ws=True,
            remove_stopwords_flag=False,
        )
    )
    df_final = df_final[df_final["text"].str.len() > 0].reset_index(drop=True)

    # 5. Karıştır (Shuffle) - Çok önemli, yoksa model ezber yapar
    df_final = df_final.sample(frac=1).reset_index(drop=True)

    # 6. Kaydet
    try:
        df_final.to_csv("egitim_verisi_final.csv", index=False)
        print(f"\n✅ BAŞARILI: Toplam {len(df_final)} satır veri birleştirildi.")
        print("'egitim_verisi_final.csv' dosyası oluşturuldu.")
    except Exception as e:
        print(f"❌ HATA: Dosya kaydedilirken hata oluştu: {e}")
        return

if __name__ == "__main__":
    veri_hazirla()

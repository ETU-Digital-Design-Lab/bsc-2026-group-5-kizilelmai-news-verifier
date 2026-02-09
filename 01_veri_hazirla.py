import pandas as pd
import re
import string

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Küçük harfe çevir
    text = text.lower()
    # Noktalama işaretlerini kaldır
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text).strip()
    return text

print("Veriler birleştiriliyor ve temizleniyor...")

try:
    # CSV dosyalarını oku
    df_gercek = pd.read_csv("veriler/gercekler.csv", encoding='utf-8')
    df_yalan = pd.read_csv("veriler/yalanlar.csv", encoding='utf-8')

    # Etiketle (1: Gerçek, 0: Yalan)
    df_gercek['label'] = 1
    df_yalan['label'] = 0

    # Sütun isimlerini standartlaştır (Her ikisinde de 'text' olduğundan emin olalım)
    # Eğer 00_veri_uydur.py düzgün çalıştıysa zaten 'text' olarak gelecektir.
    
    # Birleştir
    df_final = pd.concat([df_gercek, df_yalan], ignore_index=True)

    # Temizle
    df_final['text'] = df_final['text'].apply(clean_text)

    # Karıştır (Shuffle)
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    # Sonucu kaydet
    df_final.to_csv("egitim_verisi_final.csv", index=False, encoding='utf-8')
    print(f"✅ 'egitim_verisi_final.csv' başarıyla oluşturuldu! Toplam veri: {len(df_final)}")
    print(df_final.head())

except Exception as e:
    print(f"❌ HATA: {e}")

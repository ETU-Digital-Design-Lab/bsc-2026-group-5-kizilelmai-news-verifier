from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import os

# Eğittiğimiz modelin klasörü
MODEL_YOLU = "./kizilelma_model_v1"

def test_uygulamasi():
    print("--- 🧠 MODEL YÜKLENİYOR ---")
    
    # Klasör kontrolü
    if not os.path.exists(MODEL_YOLU):
        print(f"HATA: '{MODEL_YOLU}' klasörü yok! Eğitim (02_model_egit.py) tamamlanmamış.")
        return

    try:
        # Modeli ve Tokenizer'ı kaydettiğimiz yerden geri çağırıyoruz
        tokenizer = AutoTokenizer.from_pretrained(MODEL_YOLU)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_YOLU)
    except Exception as e:
        print(f"Model yüklenirken hata oldu: {e}")
        return

    print("\n✅ MODEL HAZIR! (Çıkmak için 'q' yazıp Enter'a bas)")
    print("--------------------------------------------------")

    while True:
        # Kullanıcıdan haber metni al
        text = input("\n🔎 Haber metnini yapıştır (veya q): ")
        
        if text.lower() == 'q':
            print("Çıkış yapılıyor...")
            break
        
        if len(text) < 5:
            print("⚠️ Lütfen daha uzun bir cümle girin.")
            continue

        # 1. Metni Matematiğe Çevir (Tokenization)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        
        # 2. Tahmin Yap
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
        
        # 3. Sonucu Yüzdeye Çevir (Softmax)
        probs = F.softmax(logits, dim=1)
        
        # Eğitimde: Label 1 -> Gerçek, Label 0 -> Yalan demiştik
        yalan_olasilik = probs[0][0].item()
        gercek_olasilik = probs[0][1].item()
        
        # Ekrana Yazdır
        print(f"\n📊 SONUÇ ANALİZİ:")
        if gercek_olasilik > 0.5:
            guven = gercek_olasilik * 100
            print(f"🟢 SINIF: GERÇEK HABER")
            print(f"📈 Güven Skoru: %{guven:.2f}")
        else:
            guven = yalan_olasilik * 100
            print(f"🔴 SINIF: YALAN / MANİPÜLATİF")
            print(f"📉 Güven Skoru: %{guven:.2f}")
        print("--------------------------------------------------")

if __name__ == "__main__":
    test_uygulamasi()
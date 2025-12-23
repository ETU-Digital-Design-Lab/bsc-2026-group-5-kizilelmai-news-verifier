import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from torch.utils.data import Dataset
import os

# --- AYARLAR ---
MODEL_ISMI = "dbmdz/bert-base-turkish-cased" # En iyi Türkçe model
CIKIS_KLASORU = "./kizilelma_model_v1"       # Model buraya kaydedilecek

# --- DATASET SINIFI (Modelin anlayacağı format) ---
class HaberDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

# --- ANA EĞİTİM FONKSİYONU ---
def egitimi_baslat():
    print(f"--- 2. ADIM: {MODEL_ISMI} Modeli Eğitiliyor ---")

    # 1. Veriyi Yükle
    if not os.path.exists("egitim_verisi_final.csv"):
        print("HATA: 'egitim_verisi_final.csv' bulunamadı. Önce 01 kodunu çalıştır.")
        return
    
    try:
        df = pd.read_csv("egitim_verisi_final.csv")
    except Exception as e:
        print(f"❌ HATA: CSV dosyası okunurken hata oluştu: {e}")
        return
    
    # Veriyi Böl (Eğitim ve Test)
    # Veri az olduğu için test oranını %20 yapıyoruz
    X_train, X_val, y_train, y_val = train_test_split(df['text'].tolist(), df['label'].tolist(), test_size=0.2, random_state=42)

    print("1. Model indiriliyor (Bu işlem internet hızına göre sürebilir)...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ISMI)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_ISMI, num_labels=2)
    except Exception as e:
        print(f"❌ HATA: Model indirilirken hata oluştu: {e}")
        print("İnternet bağlantınızı kontrol edin.")
        return

    print("2. Veriler işleniyor (Tokenization)...")
    train_encodings = tokenizer(X_train, truncation=True, padding=True, max_length=64)
    val_encodings = tokenizer(X_val, truncation=True, padding=True, max_length=64)

    train_dataset = HaberDataset(train_encodings, y_train)
    val_dataset = HaberDataset(val_encodings, y_val)

    # Eğitim Ayarları
    training_args = TrainingArguments(
        output_dir='./sonuclar',
        num_train_epochs=3,              # Veri seti üzerinden 3 tur geçecek
        per_device_train_batch_size=4,   # Bilgisayar kasmasın diye düşük tuttum
        per_device_eval_batch_size=4,
        logging_dir='./logs',
        save_strategy="no",              # Disk dolmasın diye ara kayıt yapma
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )

    print("3. EĞİTİM BAŞLIYOR...")
    try:
        trainer.train()
    except Exception as e:
        print(f"❌ HATA: Eğitim sırasında hata oluştu: {e}")
        return

    print(f"4. Model kaydediliyor: {CIKIS_KLASORU} ...")
    try:
        model.save_pretrained(CIKIS_KLASORU)
        tokenizer.save_pretrained(CIKIS_KLASORU)
    except Exception as e:
        print(f"❌ HATA: Model kaydedilirken hata oluştu: {e}")
        return
    
    print("\n✅ TEBRİKLER! Model başarıyla eğitildi.")
    print(f"'{CIKIS_KLASORU}' klasörü artık kullanıma hazır.")

if __name__ == "__main__":
    egitimi_baslat()
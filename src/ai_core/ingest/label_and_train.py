import os
import sys
import re
import argparse
import pandas as pd
import numpy as np
import torch
from pathlib import Path
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    TrainerCallback
)

# Windows terminal UTF-8 encoding support
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Proje kök dizinini ekle
FILE_DIR = Path(__file__).parent
ROOT_DIR = FILE_DIR.parent.parent.parent
sys.path.append(str(ROOT_DIR))

# Kızılelma modüllerini yükle
try:
    from src.ai_core.engine.engine import KizilelmaEngine
    from src.shared.preprocess import preprocess
except ImportError:
    try:
        from ai_core.engine.engine import KizilelmaEngine
        from shared.preprocess import preprocess
    except Exception as e:
        print(f"❌ Kritik Hata: Gerekli Kızılelma modülleri yüklenemedi: {e}")
        sys.exit(1)


class InteractiveCallback(TrainerCallback):
    """Eğitim adımlarını konsola güzel bir şekilde yazdıran callback."""
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            loss = logs.get("loss", "N/A")
            eval_loss = logs.get("eval_loss", "N/A")
            eval_accuracy = logs.get("eval_accuracy", "N/A")
            epoch = state.epoch if state.epoch is not None else 0.0
            print(f"   [Adım {state.global_step}] Epoch: {epoch:.2f} | Eğitim Kaybı: {loss} | Doğrulama Kaybı: {eval_loss} | Doğruluk (Acc): {eval_accuracy}")


class PyTorchDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)


def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    preds = predictions.argmax(axis=1)
    acc = (preds == labels).mean()
    return {"accuracy": acc}


def detect_and_read_csv(filepath):
    """Farklı Türkçe kodlamaları ve ayrışma formatlarını deneyerek CSV okur."""
    encodings = ['utf-8', 'cp1254', 'iso-8859-9', 'latin-1']
    delimiters = ['\t', ';', ',']
    
    print(f"🔍 Haber dosyası okunuyor: {os.path.basename(filepath)}")
    
    for encoding in encodings:
        for sep in delimiters:
            try:
                # Skip bad lines ve dropna ile temiz bir deneme yapalım
                df = pd.read_csv(filepath, sep=sep, encoding=encoding, on_bad_lines='skip')
                
                # Eğer tek kolon geldiyse ve kolon adı 'text' veya 'text\t' gibi bir şeyse temizle
                if df.shape[1] >= 1:
                    # Sütun isimlerindeki boşlukları ve tabları temizle
                    df.columns = [c.strip() for c in df.columns]
                    
                    # 'text' veya ilk geçerli kolonu metin olarak kabul et
                    text_col = None
                    for col in ['text', 'Haber Metni', 'haber', 'tweet', 'description', 'title']:
                        if col in df.columns:
                            text_col = col
                            break
                    if not text_col:
                        text_col = df.columns[0]
                        
                    # Boş satırları ve NaN olanları temizle
                    df = df.rename(columns={text_col: 'text'})
                    df = df.dropna(subset=['text'])
                    # Boşlukları kırpılmış halde satırların uzunluğunu kontrol et
                    df = df[df['text'].astype(str).str.strip().str.len() > 5].reset_index(drop=True)
                    
                    # Eğer anlamlı sayıda satır okunduysa başarılı sayalım
                    if len(df) > 0:
                        print(f"   ✅ Başarılı: Kodlama={encoding}, Ayrıcı={repr(sep)}, Sütun='{text_col}', Satır Sayısı={len(df)}")
                        return df[['text']]
            except Exception:
                continue
                
    # Excel denemesi
    if filepath.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(filepath)
            df.columns = [c.strip() for c in df.columns]
            text_col = 'text' if 'text' in df.columns else df.columns[0]
            df = df.rename(columns={text_col: 'text'}).dropna(subset=['text'])
            df = df[df['text'].astype(str).str.strip().str.len() > 5].reset_index(drop=True)
            print(f"   ✅ Başarılı: Excel dosyası okundu. Satır Sayısı={len(df)}")
            return df[['text']]
        except Exception as e:
            print(f"❌ Excel okuma hatası: {e}")

    raise ValueError("❌ HATA: Haber dosyası hiçbir kodlama veya ayrıcı ile okunamadı!")


def label_news_with_engine(df, engine):
    """Haberleri 10 katmanlı Kızılelma motorundan geçirip etiketler."""
    print("\n=== 🧠 10 KATMANLI KIZILELMA ANALİZİ VE ETİKETLEME BAŞLIYOR ===")
    
    labeled_data = []
    total = len(df)
    
    for idx, row in df.iterrows():
        text_content = str(row['text']).strip()
        sys.stdout.write(f"\r⏳ Haber Analiz Ediliyor: [{idx+1}/{total}] ...")
        sys.stdout.flush()
        
        try:
            # 10 katmanlı analizi çağır
            res = engine.ask(text_content)
            
            # Dezenformasyon skoru (risk) ve Güvenilirlik skoru (confidence) al
            risk = res.get('risk', 0)
            confidence = res.get('confidence', 0)
            status = res.get('status', 'RET')
            category = res.get('category', 'GENEL')
            description = res.get('description', '-')
            source = res.get('source', '-')
            
            # Binary etiket belirle: Risk %50 üzeriyse YALAN (0), değilse GERÇEK (1)
            predicted_label = 0 if risk > 50 else 1
            
            labeled_data.append({
                'text': text_content,
                'clean_text': preprocess(text_content),
                'label': predicted_label,
                'label_provenance': 'engine_silver_risk_threshold_50',
                'label_generator': 'KizilelmaEngine',
                'label_threshold': 50,
                'confidence': confidence,
                'risk': risk,
                'status': status,
                'category': category,
                'description': description,
                'source': source
            })
        except Exception as e:
            print(f"\n⚠️ Haber analiz edilirken hata oluştu (Atlanıyor): {e}")
            
    print(f"\n✅ Etiketleme tamamlandı: {len(labeled_data)} haber işlendi.")
    return pd.DataFrame(labeled_data)


def main():
    parser = argparse.ArgumentParser(description="KizilelmAI Haber Etiketleme ve Eğitim Hattı")
    parser.add_argument("--input", type=str, default="data/raw/yalanlar.csv", help="İşlenecek ham haber CSV/Excel dosyası")
    parser.add_argument("--model", type=str, default="dbmdz/bert-base-turkish-cased", help="İnce ayar yapılacak HuggingFace modeli (varsayılan: BERTurk — kizilelma_classifier_v1 mimarisiyle uyumlu)")
    parser.add_argument("--epochs", type=int, default=1, help="Model eğitim epoch sayısı")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch boyutu")
    parser.add_argument("--subset", type=int, default=1000, help="Eğitim veri seti alt kümesi boyutu (CPU hızı için)")
    parser.add_argument("--allow-silver-training", action="store_true", help="Explicitly allow training on engine-generated silver labels")
    parser.add_argument("--allow-silver-injection", action="store_true", help="Explicitly allow injecting engine-generated silver labels into the knowledge base")
    args = parser.parse_args()

    # Dosya yolları
    input_path = os.path.join(ROOT_DIR, args.input)
    processed_dir = os.path.join(ROOT_DIR, "data", "processed")
    output_csv_path = os.path.join(processed_dir, "etiketlenmis_haberler.csv")
    final_train_csv_path = os.path.join(processed_dir, "egitim_verisi_30k.csv")
    output_model_path = os.path.join(ROOT_DIR, "src", "ai_core", "models", "kizilelma_classifier_v1")

    print("=================================================================")
    print("🛡️  KIZILELMAI HABER ETİKETLEME VE EĞİTİM ENTEGRASYON HATTI v3.0")
    print("=================================================================")

    # 1. Dosya Yükleme ve Etiketleme Kontrolü
    skip_labeling = False
    df_labeled = None
    engine = None
    
    if os.path.exists(output_csv_path):
        use_existing = input(f"\n📂 Bulundu: Daha önceden etiketlenmiş {os.path.basename(output_csv_path)} dosyası mevcut.\nYeniden etiketleme yapmadan bu dosyayı kullanmak ister misiniz? (55 dakika tasarruf sağlar) [E/h]: ").strip().lower()
        if use_existing in ['', 'e', 'evet', 'y', 'yes']:
            print(f"⏳ Mevcut etiketlenmiş haberler yükleniyor: {output_csv_path}")
            df_labeled = pd.read_csv(output_csv_path)
            skip_labeling = True

    if not skip_labeling:
        if not os.path.exists(input_path):
            print(f"❌ Hata: Girdi dosyası bulunamadı: {input_path}")
            sys.exit(1)
            
        df_raw = detect_and_read_csv(input_path)

        # 2. Kızılelma Motorunu Başlat
        engine = KizilelmaEngine()

        # 3. Etiketleme Döngüsü
        df_labeled = label_news_with_engine(df_raw, engine)

        # Sonuçları Kaydet
        os.makedirs(processed_dir, exist_ok=True)
        df_labeled.to_csv(output_csv_path, index=False, encoding='utf-8')
        print(f"💾 Etiketlenmiş veriler başarıyla kaydedildi: {output_csv_path}")

    # Sınıf Dağılımını Göster
    labels_counts = df_labeled['label'].value_counts()
    real_count = labels_counts.get(1, 0)
    fake_count = labels_counts.get(0, 0)
    print(f"📊 Dağılım -> 🟢 GERÇEK Haberler: {real_count} | 🔴 YALAN/MANİPÜLATİF Haberler: {fake_count}")

    # 3.5. Veri Birleştirme (Unification) Seçeneği
    unify_ans = input("\n🔗 Tüm veri kaynaklarını (251 orijinal, 30.000 eski ve yeni etiketlenen 133 haber) tek bir dosyada birleştirmek ister misiniz? [E/h]: ").strip().lower()
    if unify_ans in ['', 'e', 'evet', 'y', 'yes']:
        print("⏳ Veri birleştirme ve temizleme işlemi başlatılıyor...")
        dfs_to_merge = []
        
        # 1. Yeni etiketlenen veriler (sadece text ve label kolonları)
        dfs_to_merge.append(df_labeled[['text', 'label']])
        
        # 2. Orijinal final veri seti (251 satır)
        original_final_path = os.path.join(processed_dir, "egitim_verisi_final.csv")
        if os.path.exists(original_final_path):
            try:
                # Orijinal dosyayı yedekleyelim (egitim_verisi_final_backup.csv)
                backup_path = os.path.join(processed_dir, "egitim_verisi_final_backup.csv")
                if not os.path.exists(backup_path):
                    pd.read_csv(original_final_path).to_csv(backup_path, index=False, encoding='utf-8')
                    print(f"   * Orijinal veritabanı yedeği alındı: {backup_path}")
                
                df_orig = pd.read_csv(original_final_path)
                dfs_to_merge.append(df_orig[['text', 'label']])
            except Exception as orig_err:
                print(f"   ⚠️ Orijinal final veri seti okunurken hata oluştu (Atlanıyor): {orig_err}")
                
        # 3. 30k veri seti
        if os.path.exists(final_train_csv_path):
            try:
                df_30k = pd.read_csv(final_train_csv_path)
                dfs_to_merge.append(df_30k[['text', 'label']])
            except Exception as train_err:
                print(f"   ⚠️ 30k veri seti okunurken hata oluştu (Atlanıyor): {train_err}")
                
        # Birleştir, temizle ve yinelenenleri kaldır
        df_unified = pd.concat(dfs_to_merge, ignore_index=True)
        df_unified['text'] = df_unified['text'].astype(str).str.strip()
        df_unified = df_unified.drop_duplicates(subset=['text']).reset_index(drop=True)
        
        # Tek bir dosya olarak kaydet: egitim_verisi_final.csv
        df_unified.to_csv(original_final_path, index=False, encoding='utf-8')
        
        # Önbellek (.npy) dosyasını temizle ki motor ilk açılışta güncel npy dosyasını sıfırdan oluştursun!
        npy_path = original_final_path.replace('.csv', '_embeddings.npy')
        if os.path.exists(npy_path):
            try:
                os.remove(npy_path)
                print(f"   * Eski vektör önbelleği silindi: {os.path.basename(npy_path)}")
            except Exception as npy_err:
                print(f"   ⚠️ Önbellek silinemedi: {npy_err}")
                
        print(f"✅ BAŞARILI: Tüm veriler tek bir dosyada birleştirildi! Toplam satır sayısı: {len(df_unified)} -> Hedef: {original_final_path}")

    # 4. Bilgi Tabanına Canlı Enjeksiyon Seçeneği
    inject_ans = input("\n💉 Etiketlenen yeni haberleri Kızılelma Bilgi Bankasına (Knowledge Base) enjekte etmek ister misiniz? [E/h]: ").strip().lower()
    if inject_ans in ['', 'e', 'evet', 'y', 'yes'] and not args.allow_silver_injection:
        print("WARNING: Engine-generated silver labels are not injected by default. Re-run with --allow-silver-injection only for an explicitly documented weak-supervision experiment.")
    elif inject_ans in ['', 'e', 'evet', 'y', 'yes']:
        print("⏳ Bilgi enjeksiyonu başlatılıyor...")
        if engine is None:
            engine = KizilelmaEngine()
        injected_count = 0
        for idx, row in df_labeled.iterrows():
            # Otorite skoru olarak güvenilirlik oranını normalize et (0.50 ile 1.00 arası)
            auth_val = max(0.50, float(row['confidence']) / 100.0)
            success = engine.inject_knowledge(row['text'], label=int(row['label']), authority=auth_val)
            if success:
                injected_count += 1
        print(f"✅ Başarılı: {injected_count} yeni haber bilgi bankasına aşılandı!")

    # 5. Model Eğitimi (Fine-Tuning) Seçeneği
    train_ans = input("\n🧠 Yapay zeka sınıflandırma modelini (kizilelma_classifier_v1) bu yeni verilerle eğitmek ister misiniz? [E/h]: ").strip().lower()
    if train_ans in ['', 'e', 'evet', 'y', 'yes'] and not args.allow_silver_training:
        print("WARNING: This workflow derives labels from the engine risk score. Training is blocked to prevent circular measurement. Use --allow-silver-training only for a documented silver-label/distillation experiment, never for human-gold evaluation.")
        return
    if train_ans not in ['', 'e', 'evet', 'y', 'yes']:
        print("👋 Model eğitimi atlandı. Program sonlandırılıyor.")
        sys.exit(0)

    # Kızılelma motorunu bellekten (VRAM/RAM) tamamen temizle
    if 'engine' in locals() and engine is not None:
        print("\n🧹 GPU/RAM belleği boşaltılıyor...")
        del engine
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("✅ Bellek temizlendi!")

    print("\n--- 🧠 MODEL İNCE AYAR (FINE-TUNING) AŞAMASI ---")
    
    # Cihaz kontrolü
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️  Eğitim Cihazı: {device.upper()}")
    if device == "cpu":
        print("⚠️  UYARI: GPU (CUDA) bulunamadı. CPU üzerinde eğitim yapılacağı için '--subset' boyutu sınırlandırıldı.")

    # Birleştirilmiş tek veri kaynağını yükle
    train_texts = []
    train_labels = []
    
    unified_train_file = os.path.join(processed_dir, "egitim_verisi_final.csv")
    if os.path.exists(unified_train_file):
        print(f"📂 Birleştirilmiş tek veri kaynağı yükleniyor: {unified_train_file}")
        df_train = pd.read_csv(unified_train_file)
        
        # CPU hızı için dengeli alt küme seçimi
        if device == "cpu" and args.subset > 0:
            print(f"   * CPU Hızlandırması: Birleştirilmiş veri setinden rastgele {args.subset} kayıt seçiliyor...")
            df_train = df_train.sample(n=min(args.subset, len(df_train)), random_state=42)
            
        train_texts = df_train['text'].tolist()
        train_labels = df_train['label'].tolist()
    else:
        print("⚠️  Birleştirilmiş egitim_verisi_final.csv bulunamadı, sadece yeni etiketlenen verilerle eğitim yapılacak.")
        train_texts.extend(df_labeled['text'].tolist())
        train_labels.extend(df_labeled['label'].tolist())

    # Eğitim ve Doğrulama setlerine ayır
    print(f"📚 Toplam Eğitim Havuzu: {len(train_texts)} kayıt.")
    train_t, val_t, train_l, val_l = train_test_split(
        train_texts, train_labels, test_size=0.15, random_state=42, stratify=train_labels
    )
    print(f"   -> Eğitim Seti: {len(train_t)} | Doğrulama Seti: {len(val_t)}")

    # Tokenizer yükle
    print(f"⏳ Tokenizer yükleniyor ({args.model})...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    # Tokenize et
    print("⏳ Metinler sayısallaştırılıyor (max_length=128)...")
    train_encodings = tokenizer(train_t, truncation=True, padding=True, max_length=128)
    val_encodings = tokenizer(val_t, truncation=True, padding=True, max_length=128)

    # Datasets
    train_dataset = PyTorchDataset(train_encodings, train_l)
    val_dataset = PyTorchDataset(val_encodings, val_l)

    # Model yükle
    print(f"⏳ Ön eğitimli model yükleniyor ({args.model})...")
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)
    model.to(device)

    # Custom PyTorch Training Loop
    from torch.utils.data import DataLoader
    from torch.optim import AdamW

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

    optimizer = AdamW(model.parameters(), lr=5e-5, weight_decay=0.01)

    # AMP (FP16) setup
    use_amp = (device == "cuda")
    scaler = torch.cuda.amp.GradScaler() if use_amp else None

    print("\n🚀 Model ince ayarı (Custom PyTorch Loop) başlatıldı...")
    if use_amp:
        print("⚡ Karma Hassasiyet (AMP - FP16) aktif! Tensor Cores devrede.")
    sys.stdout.flush()
    
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        correct = 0
        total_samples = 0
        
        for step, batch in enumerate(train_loader):
            optimizer.zero_grad()
            
            # Move to device
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            # Forward pass with autocast
            if use_amp:
                with torch.cuda.amp.autocast():
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                    loss = outputs.loss
                    logits = outputs.logits
            else:
                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs.loss
                logits = outputs.logits
            
            # Backward pass
            if use_amp and scaler is not None:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
            
            total_loss += loss.item()
            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total_samples += labels.size(0)
            
            if (step + 1) % 5 == 0 or (step + 1) == len(train_loader):
                acc = (correct / total_samples) * 100
                avg_loss = total_loss / (step + 1)
                print(f"   [Epoch {epoch+1}/{args.epochs}] Adım {step+1}/{len(train_loader)} | Eğitim Kaybı: {avg_loss:.4f} | Eğitim Doğruluğu: %{acc:.2f}")
                sys.stdout.flush()

        # Validation loop
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                
                if use_amp:
                    with torch.cuda.amp.autocast():
                        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                        loss = outputs.loss
                        logits = outputs.logits
                else:
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                    loss = outputs.loss
                    logits = outputs.logits
                
                val_loss += loss.item()
                preds = logits.argmax(dim=1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)
                
        val_acc = (val_correct / val_total) * 100
        val_avg_loss = val_loss / len(val_loader)
        print(f"🌟 Epoch {epoch+1} Bitti | Doğrulama Kaybı: {val_avg_loss:.4f} | Doğrulama Doğruluğu: %{val_acc:.2f}")
        sys.stdout.flush()

    print("🎉 Model eğitimi başarıyla tamamlandı!")
    sys.stdout.flush()

    # Modeli Kaydet
    print(f"💾 Model kaydediliyor: {output_model_path}")
    os.makedirs(output_model_path, exist_ok=True)
    model.save_pretrained(output_model_path)
    tokenizer.save_pretrained(output_model_path)

    print("\n=================================================================")
    print("✅ BAŞARILI: Model eğitildi, kaydedildi ve kullanıma hazır!")
    print("=================================================================")


if __name__ == "__main__":
    main()

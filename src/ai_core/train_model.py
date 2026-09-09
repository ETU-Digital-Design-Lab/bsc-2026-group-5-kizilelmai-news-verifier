import os
import sys
import argparse
import hashlib
import json
from datetime import datetime, timezone
import pandas as pd
import torch
import transformers
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    TrainerCallback
)

class CustomCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            loss = logs.get("loss", "N/A")
            eval_loss = logs.get("eval_loss", "N/A")
            eval_accuracy = logs.get("eval_accuracy", "N/A")
            print(f"Epoch {state.epoch:.2f} | Loss: {loss} | Eval Loss: {eval_loss} | Eval Acc: {eval_accuracy}")

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

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="KizilelmAI Model Fine-Tuning Script")
    parser.add_argument("--model", type=str, default="dbmdz/bert-base-turkish-cased", help="Pretrained model name (default: BERTurk — matches kizilelma_classifier_v1 architecture)")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size per device")
    parser.add_argument("--subset", type=int, default=0, help="Train on a subset of data (0 for all)")
    args = parser.parse_args()

    # Path settings
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    dataset_path = os.path.join(root_dir, "data", "processed", "egitim_verisi_30k.csv")
    output_model_path = os.path.join(root_dir, "src", "ai_core", "models", "kizilelma_classifier_v1")

    print("=== KIZILELMAI MODEL INCE AYAR (FINE-TUNING) BASLIYOR ===")
    print(f"Model: {args.model}")
    print(f"Veri Seti: {dataset_path}")
    print(f"Cikti Dizini: {output_model_path}")

    # Check CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Cihaz: {device.upper()}")
    if device == "cpu":
        print("  * UYARI: GPU (CUDA) bulunamadi! CPU uzerinde egitim yavas surecektir.")

    # Load dataset
    if not os.path.exists(dataset_path):
        print(f"  * HATA: Egitim veri seti bulunamadi: {dataset_path}")
        print("Lütfen once 'prep_30k_data.py' scriptini calistirarak veri setini hazirlayin.")
        sys.exit(1)

    print("Veri yukleniyor...")
    df = pd.read_csv(dataset_path)
    print(f"Toplam kayit: {len(df)}")

    if args.subset > 0:
        print(f"Subset modu aktif! Yalnizca {args.subset} kayit kullanilacak.")
        df = df.sample(n=args.subset, random_state=42).reset_index(drop=True)

    # Train / Val Split
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        df['text'].tolist(), 
        df['label'].tolist(), 
        test_size=0.15, 
        random_state=42, 
        stratify=df['label'].tolist()
    )
    print(f"Egitim boyutu: {len(train_texts)} | Dogrulama boyutu: {len(val_texts)}")

    # Load Tokenizer
    print("Tokenizer indiriliyor/yukleniyor...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    # Tokenize
    print("Metinler tokenize ediliyor (max_length=128)...")
    train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=128)
    val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=128)

    # Datasets
    train_dataset = PyTorchDataset(train_encodings, train_labels)
    val_dataset = PyTorchDataset(val_encodings, val_labels)

    # Load Model
    print("Model indiriliyor/yukleniyor...")
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)
    model.to(device)

    # Training Arguments
    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=50,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to="none"
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[CustomCallback()]
    )

    print("\n--- Egitim Basliyor ---")
    import time
    train_start_time = time.perf_counter()
    trainer.train()
    train_duration_sec = time.perf_counter() - train_start_time
    throughput = (len(train_texts) * args.epochs) / max(train_duration_sec, 0.001)
    print(f"Egitim Tamamlandi! Sure: {train_duration_sec:.2f} saniye ({train_duration_sec / 60:.1f} dakika) | Throughput: {throughput:.2f} ornek/sn")

    # Save Model & Tokenizer
    print(f"Model kaydediliyor: {output_model_path}")
    os.makedirs(output_model_path, exist_ok=True)
    model.save_pretrained(output_model_path)
    tokenizer.save_pretrained(output_model_path)

    # Hardware profile
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    hardware_info = {
        "device": device,
        "gpu_model": gpu_name if device == "cuda" else None,
        "cuda_available": torch.cuda.is_available(),
        "cpu_count": os.cpu_count(),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
    }

    # The checkpoint config alone does not reliably preserve its upstream
    # checkpoint name. Store the training provenance beside every new artifact.
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_model": args.model,
        "training_data": os.path.relpath(dataset_path, root_dir),
        "training_data_sha256": sha256_file(dataset_path),
        "records_loaded": len(df),
        "split": {"test_size": 0.15, "random_state": 42, "stratified": True},
        "hyperparameters": {"epochs": args.epochs, "batch_size": args.batch_size},
        "training_duration_seconds": round(train_duration_sec, 2),
        "training_duration_minutes": round(train_duration_sec / 60, 2),
        "throughput_samples_per_sec": round(throughput, 2),
        "hardware": hardware_info,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "label_provenance": "See the source dataset card; do not describe unknown labels as human gold.",
    }
    with open(os.path.join(output_model_path, "training_manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    print("=== BAŞARILI: Model egitim ve kaydetme islemleri tamamlandi! ===")

if __name__ == "__main__":
    main()

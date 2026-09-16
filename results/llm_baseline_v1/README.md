# LLM Baseline Veri ve Çıktı Dizini

> [!WARNING]
> **DİKKAT: BU DİZİNDEKİ TAHMİNLER TEST AMAÇLI SENTETİK (MOCK) VERİDİR.**  
> `MOCK_llm_predictions.csv` ve `MOCK_metrics.json` dosyaları boru hattı kodlarının doğrulanması amacıyla simülasyon bayrağı (`--mock`) ile üretilmiştir.  
> Bu sayılar kesinlikle gerçek LLM performansı değildir ve makale tablolarına dahil edilemez.

## 📋 Mevcut Dosyalar
- `llm_payloads_500.jsonl`: FACTurk-500 test iddialarından türetilmiş resmi sıfır-atış (zero-shot) JSON istem yükleri (Gerçek ve kullanıma hazır).
- `MOCK_llm_predictions.csv`: Simülasyon çıktıları (MOCK).
- `MOCK_metrics.json`: Simülasyon metrikleri (MOCK).

## 🔑 Gerçek Koşum İçin Talimat (Danışman Tarafından Yapılacak)
Resmi API anahtarı sağlandığında şu komut ile gerçek koşum başlatılır:
```bash
python scripts/evaluation/llm_baseline/run_llm_baseline.py --model gpt-4o-mini
python scripts/evaluation/llm_baseline/score_llm_baseline.py
```
Bu işlem tamamlandığında gerçek `llm_predictions.csv` ve `metrics.json` dosyaları oluşacaktır.

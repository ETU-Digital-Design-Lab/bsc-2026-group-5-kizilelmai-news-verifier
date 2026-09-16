# LLM Baseline Karşılaştırma Paketi (B Paketi)

Bu paket, hakemlerin 2026 yılı beklentileri doğrultusunda güncel Büyük Dil Modellerinin (LLM) FACTurk-500 üzerindeki sıfır-atış (zero-shot) doğrulama başarımını ölçmek ve KızılelmAI mimarisiyle karşılaştırmak için tasarlanmıştır.

## 🚀 Çalıştırma (3 Adım)

### 1. Adım: İstem Yüklerini (Payloads) Oluşturma
```bash
python scripts/evaluation/llm_baseline/build_llm_payloads.py
```
*Çıktı:* `results/llm_baseline_v1/llm_payloads_500.jsonl`

### 2. Adım: LLM Çıkarımını Koşma
```bash
# Canlı API (OPENAI_API_KEY tanımlı ise):
python scripts/evaluation/llm_baseline/run_llm_baseline.py --model gpt-4o-mini

# Test / Simülasyon modu (API anahtarsız):
python scripts/evaluation/llm_baseline/run_llm_baseline.py --mock
```
*Çıktı:* `results/llm_baseline_v1/llm_predictions.csv`

### 3. Adım: Skorlama ve Wilson Güven Aralığı Hesaplama
```bash
python scripts/evaluation/llm_baseline/score_llm_baseline.py
```
*Çıktı:* `results/llm_baseline_v1/metrics.json`

# 📊 KızılelmAI Deney Sonuçları ve Benchmark İndeksi

Bu dizin, KızılelmAI sisteminin bağımsız **FACTurk-500** benchmark veri seti üzerindeki tüm değerlendirme koşumlarını, ablasyon çalışmalarını ve doğrulama artefaktlarını içerir.

Her koşum dizininde tekrarlanabilirlik (reproducibility) ilkesi gereğince **`metrics.json`**, **`predictions.csv`**, **`responses.jsonl`** ve çalıştırma ortamını belgeleyen **`run_manifest.json`** bulunmaktadır.

---

## 🏆 Temel Benchmark Koşumları Karşılaştırması

| Koşum Dizini | Açıklama | Embedding Modeli | NLI Durumu | Kapsama (Coverage) | Doğruluk (Selective Acc.) | Macro-F1 | Durum |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **[`facturk_full_v8/`](facturk_full_v8/)** | **Resmi Final Sistem** | `multilingual-e5-large` (1024d) | Düzeltilmiş (K-4) | **%80.4** (402/500) | **%56.72** | **0.5647** | 🏆 **Şampiyon / Final** |
| **[`facturk_full_v6/`](facturk_full_v6/)** | K-4 Düzeltme Doğrulaması | `multilingual-e5-small` (384d) | Düzeltilmiş (K-4) | %54.6 (273/500) | %54.21 | 0.5275 | Tamamlandı |
| **[`facturk_full_v7/`](facturk_full_v7/)** | Büyük Model Geçiş Koşumu | `multilingual-e5-large` (1024d) | Eski Mantık (dirty) | %53.8 (269/500) | %53.53 | 0.5074 | Belgelendi (Regresyon) |
| **[`facturk_full_v5/`](facturk_full_v5/)** | Eski Temel Sistem (Baseline) | `multilingual-e5-small` (384d) | Eski Mantık | %53.2 (266/500) | %54.14 | 0.5098 | Arşiv / Temel |

---

## 🔬 Özel Analiz ve Doğrulama Dizinleri

* **[`facturk_ablation_v1/`](facturk_ablation_v1/):** Bileşen izolasyon ablasyonları (Re-ranker etkisi, Embedding etkisi, NLI etkisi).
* **[`k4_fix_v1/`](k4_fix_v1/):** K-4 NLI ters etiket hatasının matematiksel doğrulama raporu ve iki kapılı (Gate 1 & Gate 2) test JSON'ı.
* **[`corrections_v1/`](corrections_v1/):** Altı temel mimari iyileştirmenin (otorite, bağlam, konsensüs, vb.) kayıtları.
* **[`selective_v1/`](selective_v1/):** Seçici tahmin (Selective Prediction), çekimserlik (abstain) ve hata taksonomisi raporu.
* **[`temporal_coverage_v1/`](temporal_coverage_v1/):** Zamansal analiz ve yayıncı seviyesinde kaynak (publisher-level provenance) doğrulamaları.
* **[`latency_v1/`](latency_v1/):** Donanım (NVIDIA RTX 3050 Ti GPU) üzerinde katman bazlı çıkarım ve gecikme ölçümleri.
* **[`provenance_v4/`](provenance_v4/):** Kaynak atıf ve doğrulama denetim sonuçları.

---

## 📌 Akademik Makale ve Raporlar

Tüm bu sonuçların detaylı akademik analizi için:
👉 **[`docs/reports/2026-09-13_kizilelmai_tum_duzeltmeler_ve_sistem_iyilestirme_raporu.md`](../docs/reports/2026-09-13_kizilelmai_tum_duzeltmeler_ve_sistem_iyilestirme_raporu.md)**

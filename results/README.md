# 📊 KızılelmAI Deney Sonuçları ve Benchmark İndeksi

Bu dizin, KızılelmAI sisteminin bağımsız **FACTurk-500** benchmark veri seti üzerindeki tüm değerlendirme koşumlarını, ablasyon çalışmalarını ve doğrulama artefaktlarını içerir.

Her koşum dizininde tekrarlanabilirlik (reproducibility) ilkesi gereğince **`metrics.json`**, **`predictions.csv`**, **`responses.jsonl`** ve çalıştırma ortamını belgeleyen **`run_manifest.json`** bulunmaktadır.

---

## 🏆 Temel Benchmark Koşumları Karşılaştırması

| Koşum Dizini | Açıklama | Embedding / Getirim | NLI & Karar Durumu | Kapsama (Coverage) | Doğruluk (Selective Acc.) | Macro-F1 | Durum |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **[`facturk_full_v17/`](facturk_full_v17/)** | **Gelişmiş Varlık & Framing Temizlemeli Sistem** | `e5-large` + Hibrit Web | K-4 Doğrulanmış + Yalanlama Tespiti | **%46.00** (230/500) | **%70.87** | **0.7078** | 🏆 **Resmi Altın Oran (Final)** |
| **[`facturk_full_v16/`](facturk_full_v16/)** | Esnek Web Fallback Koşumu | `e5-large` + Hibrit Web | K-4 Doğrulanmış + Dengeli Eşikler | %43.40 (217/500) | %72.35 | 0.7235 | Doğrulandı |
| **[`facturk_full_v15/`](facturk_full_v15/)** | Kesin Filtreli Yüksek Doğruluk Koşumu | `e5-large` + Hibrit Web | K-4 Doğrulanmış + Katı Eşik | %33.60 (168/500) | %75.00 | 0.7487 | Maksimum Doğruluk |
| **[`facturk_full_v14/`](facturk_full_v14/)** | Aday Sınırı 40 + Karar Modeli | `e5-large` + Web | Hatalı ML Karar Ezmesi | %57.00 (285/500) | %62.11 | 0.6197 | Analiz Edildi |
| **[`facturk_full_v13/`](facturk_full_v13/)** | Zamana Duyarlı Hibrit Sistem (Web Fallback) | `e5-large` + Web | K-4 Doğrulanmış | %51.60 (258/500) | %65.12 | 0.6476 | Arşiv |
| **[`facturk_full_v12/`](facturk_full_v12/)** | Kapalı Korpus Temiz Sistem (Kapalı RAG) | `e5-large` (1024d) | K-4 Gerçek NLI (premise/hyp) | %40.20 (201/500) | %67.66 | 0.6750 | Arşiv |
| **[`facturk_full_v11/`](facturk_full_v11/)** | Tarihsiz Web Entegrasyon Denemesi | `e5-large` + Web (tarihsiz) | K-4 Doğrulanmış | — | — | — | İptal (Zaman sızıntısı riski nedeniyle erken durduruldu) |
| **[`facturk_full_v10/`](facturk_full_v10/)** | Web Getirim Prototip / Chunking Denemesi | `e5-large` + Web | K-4 Doğrulanmış | — | — | — | İptal (RSS gecikmesi/chunking revizyonu nedeniyle durduruldu) |
| **[`facturk_full_v8/`](facturk_full_v8/)** | Yüksek Kapsama Zorlama | `e5-large` (1024d) | Gevşek Eşikler | %80.40 (402/500) | %56.72 | 0.5647 | Arşiv |
| **[`facturk_full_v6/`](facturk_full_v6/)** | K-4 Düzeltme Doğrulaması | `e5-small` (384d) | K-4 Düzeltilmiş | %54.60 (273/500) | %54.21 | 0.5275 | Arşiv |
| **[`facturk_full_v5/`](facturk_full_v5/)** | Eski Temel Sistem (Baseline) | `e5-small` (384d) | Eski Sıfır-atış Mantık | %53.20 (266/500) | %55.26 | 0.5382 | Arşiv / Temel |

---

## 🔬 Özel Analiz ve Doğrulama Dizinleri

* **[`debunk_audit_v1/`](debunk_audit_v1/):** D1 Denetimi — Yalanlama filtresi 2x2 çapraz kırılımı ve anahtar kelime analizi.
* **[`temporal_leakage_audit_v1/`](temporal_leakage_audit_v1/):** D2 Denetimi — Zamansal sızıntı, tarihli pencere vs. tarihsiz arama doğruluk karşılaştırması.
* **[`k6_influence_audit_v1/`](k6_influence_audit_v1/):** K-6 Sınıflandırıcı Etki Denetimi (+k6_override ve +k6_rescue sıfır etki kanıtı).
* **[`paired_comparison_v12_v17/`](paired_comparison_v12_v17/):** v12 vs v17 McNemar eşleştirilmiş istatistiksel karşılaştırma testi.
* **[`nearest_neighbors_percentile_v1/`](nearest_neighbors_percentile_v1/):** e5-large yüzdelik tabanlı en yakın komşu analizi (p99 eşiği).
* **[`facturk_ablation_v1/`](facturk_ablation_v1/):** Bileşen izolasyon ablasyonları (Re-ranker etkisi, Embedding etkisi, NLI etkisi).
* **[`k4_fix_v1/`](k4_fix_v1/):** K-4 NLI ters etiket hatasının matematiksel doğrulama raporu ve iki kapılı (Gate 1 & Gate 2) test JSON'ı.
* **[`corrections_v1/`](corrections_v1/):** Altı temel mimari iyileştirmenin (otorite, bağlam, konsensüs, vb.) kayıtları.
* **[`selective_v1/`](selective_v1/):** Seçici tahmin (Selective Prediction), sabit %40 kapsama karşılaştırması ve risk-kapsama eğrisi.
* **[`temporal_coverage_v1/`](temporal_coverage_v1/):** Zamansal analiz ve yayıncı seviyesinde kaynak (publisher-level provenance) doğrulamaları.
* **[`latency_v1/`](latency_v1/):** Donanım (NVIDIA RTX 3050 Ti GPU) üzerinde katman bazlı çıkarım ve gecikme ölçümleri.
* **[`provenance_v4/`](provenance_v4/):** Kaynak atıf ve doğrulama denetim sonuçları.

---

## 📌 Akademik Makale ve Raporlar

Tüm bu sonuçların detaylı akademik analizi için:
👉 **[`docs/reports/2026-09-13_kizilelmai_tum_duzeltmeler_ve_sistem_iyilestirme_raporu.md`](../docs/reports/2026-09-13_kizilelmai_tum_duzeltmeler_ve_sistem_iyilestirme_raporu.md)**

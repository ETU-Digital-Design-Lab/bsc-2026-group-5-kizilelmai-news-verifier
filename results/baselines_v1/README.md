# FACTurk Baseline Karşılaştırma ve B2 Ablasyon Paketi (v1)

Bu dizin, FACTurk 500 ikili iddia doğrulama kümesi üzerinde yürütülen temel karşılaştırma (baseline) ve mimari ablasyon analizlerinin tam artefaktlarını içerir.

## Dosya İçeriği
- `baseline_results.json`: B0 (Çoğunluk Sınıfı), B1 (Yalnızca İddia Metni / K-6 Sınıflandırıcı), B2 (En Yakın Korpus Kaydı Etiketi Kopyalama / 1-NN Getirim Ablasyonu) ve KızılelmAI (v12 ve v17) sistem sonuçları, eşlenmiş kapsama noktaları, McNemar eşleştirilmiş anlamlılık testleri ve bootstrap %95 güven aralıkları.

## Yürütme Komutu
```bash
python baselines.py \
  --k6 results/facturk_baseline_k6/k6_predictions.csv \
  --system results/facturk_full_v17/predictions.csv \
  --corpus data/corpus_snapshots/local_csv_20260913_v2/corpus.csv \
  --cov-points 0.402,0.460 \
  --out results/baselines_v1/baseline_results.json
```

## Özet Karşılaştırma Tablosu

| Sistem / Model | Kapsama | n | Doğruluk (%) | Makro-F1 |
| :--- | :---: | :---: | :---: | :---: |
| B0 — Çoğunluk sınıfı | %100.0 | 500 | %50.00 | 0.3333 |
| B1 — Yalnızca iddia metni (getirim yok) | %100.0 | 500 | %55.20 | 0.5515 |
| B1 — aynı, eşlenmiş kapsama %40.2 | %40.2 | 201 | %64.18 | 0.6416 |
| B1 — aynı, eşlenmiş kapsama %46.0 | %46.0 | 230 | %64.78 | 0.6473 |
| KızılelmAI — kapalı korpus (v12) | %40.2 | 201 | %67.66 | 0.6750 |
| KızılelmAI — web destekli (v17) | %46.0 | 230 | %70.87 | 0.7078 |
| B2 — En yakın korpus kaydı (100% kapsama) | %100.0 | 500 | %61.40 | 0.5955 |
| B2 — aynı, sistem eşlenmiş kapsama (230 iddia) | %46.0 | 230 | %62.61 | 0.6258 |
| B2 — kendi seçtiği en güvenli %40.2 | %40.2 | 201 | %81.59 | 0.8123 |
| B2 — kendi seçtiği en güvenli %46.0 | %46.0 | 230 | %78.26 | 0.7765 |

## Eşleştirilmiş İstatistiksel Testler (n = 230 iddia)

1. **Sistem vs B1 (K-6 İddia Metni Yalnızca):**
   - Sistem Doğru: 163/230, B1 Doğru: 123/230
   - McNemar $\chi^2$ (süreklilik düzeltmeli) = 14.08, $p = 0.00017$
   - $\Delta$ Makro-F1 = +0.2012, Eşleştirilmiş Bootstrap %95 GA: [+0.115, +0.287]

2. **Sistem vs B2 (En Yakın Korpus Kaydı Etiket Kopyalama):**
   - Sistem Doğru: 163/230, B2 Doğru: 144/230
   - McNemar $\chi^2$ (süreklilik düzeltmeli) = 3.21, $p = 0.0733$ ($\chi^2$ düzeltmesiz = 3.57, $p = 0.0587$)
   - $\Delta$ Makro-F1 = +0.0819 (+8.19 puan)
   - Eşleştirilmiş Bootstrap %95 GA: [-0.002, +0.167]
   - `b2_claims_without_resolvable_record`: 0 (Tüm kayıtlar donmuş korpus üzerinde başarıyla çözümlenmiştir)

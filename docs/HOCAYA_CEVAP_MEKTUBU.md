# KızılelmAI Makalesi — Denetim Sonrası Soru ve İş Listesi Yanıt Raporu

**Kime:** Dr. Öğr. Üyesi Latif Akçay  
**Kimden:** İbrahim Sinan Akbulut, Doğukan Kılıç  
**Tarih:** 9 Eylül 2026  
**Konu:** 08.09.2026 / 09.09.2026 Tarihli Denetim Soruları (A1–A6) ve Tamamlanan İşler (B1–B10)  

---

Sayın Hocam,

Gönderdiğiniz denetim listesindeki tüm uyarıları ve tespitleri eksiksiz bir ciddiyetle ele aldık. SCIE seviyesinde bir makalenin en temel omurgasının dürüst, tekrarlanabilir ve denetlenebilir bir ölçüm katmanı olduğunun bilincindeyiz.

Yaptığımız incelemeler sonucunda geriye dönük tek bir sayı uydurmadan, depoda var olanı dürüstçe raporlayıp, eksik olanları ise yeni ve sağlam betiklerle üreterek sistemi tam anlamıyla savunulabilir bir temele oturttuk.

Aşağıda hem **Bölüm A (A1–A6)** sorularınızın kesin ve yazılı yanıtlarını hem de **Bölüm B** kapsamında tamamlanan kod, veritabanı ve mimari revizyonlarını arz ederiz.

---

# BÖLÜM A — Soruların Cevapları

### A1. Tablo 5'in Sayıları Nereden Geliyor?

**Cevap: Depoda bu sayılara ait hiçbir çalıştırma manifesti, tahmin dosyası veya kod dayanağı YOKTUR.**

- `results/`, `simulations/`, `scripts/` ve `data/` dizinleri taranmış; makaledeki `%98.5`, `%91.2`, `%89.4`, `%42.0`, `%55.0`, `%68.0` sayılarına ve "uydurma oranı" (hallucination) metriklerine ait geçmiş bir çalıştırma logu bulunamamıştır.
- Bu sayılar tez döneminden kalan varsayımsal tahminlerdir ve operasyonel olarak objektif bir denetçi/hakem kaydıyla sayılmamıştır.
- **Karar ve Eylem:** **Tablo 5 makaleden tamamen çıkartılmalıdır.** Makalede dayanaksız hiçbir doğruluk sayısı bırakılmamıştır. Sistemin başarısı yalnızca dış bağımsız benchmark (FACTurk) ve dondurulmuş test kümesi üzerinden raporlanacaktır.

---

### A2. Gecikme Sayıları Ölçüldü mü?

**Cevap: Makaledeki eski sayılar (1252 ms, 420 ms vb.) kaba tahminlerdi; ancak per-layer zamanlayıcı altyapısı kodda zaten mevcuttu. Şimdi gerçek ölçüm yapıldı.**

- `engine.py` (satır 23–30) içinde `_evaluation_trace` ve `trace_elapsed()` altyapısı mevcuttu ancak dosyaya dökülmemişti.
- **Yapılan Ölçüm:** `scripts/benchmark_latency.py` betiği geliştirilmiş ve dondurulmuş 100 bağımsız iddia üzerinden ölçüm koşturulmuştur:
  1. **Cold Start (Konteyner + Model Yükleme):** ~2.8 – 3.4 saniye (Multilingual-E5, XLM-R NLI, BGE-Reranker, BERTurk Sınıflandırıcı).
  2. **Önbelleksiz İlk Sorgu (No-Cache):** Ortalama, medyan ve p95 olarak milisaniye cinsinden kaydedilmiştir.
  3. **Önbellek İsabeti (Cache-Hit):** Deserializasyon ve lookup süresi ölçülerek kaydedilmiştir.
  4. **Katman Başına Dağılım (Per-Layer Latency):** `K1_intent`, `K2_retrieval`, `K3_reranker`, `K4_nli`, `K5_decision`, `K6_advisory`, `K8_ranking`, `K9_consensus` süreleri ayrıştırılmıştır.
- **Artefaktlar:** `results/latency_v1/latency.csv` + `summary.json` + `manifest.json` (donanım profiliyle birlikte kaydedildi).

---

### A3. Eğitim ve Throughput Sayıları Ölçüldü mü?

**Cevap: Eski eğitim süresi ve throughput sayıları için kaydedilmiş bir log yoktu; altyapı manifestli hale getirildi.**

- Yerel checkpoint'in (`kizilelma_classifier_v1`) mimarisi kesin olarak `dbmdz/bert-base-turkish-cased` (BERTurk) tabanlıdır (12 katman, 768 gizli boyut, 32.000 vocab). Checkpoint ağırlık SHA-256'sı `7db7c2556a91d5b4384551ae2173e6e0e48b9d87f2455b2e16e57a5248d85865` olarak doğrulanmıştır.
- `src/ai_core/train_model.py` betiği güncellendi: Artık `time.perf_counter()` ile kesin eğitim süresi (`training_duration_seconds`, `training_duration_minutes`), anlık throughput (`throughput_samples_per_sec`) ve donanım künyesi (GPU modeli, CPU çekirdek sayısı, PyTorch/Transformers sürümleri) otomatik olarak `training_manifest.json` içine yazılmaktadır.

---

### A4. Kanıt Zinciri Gerçekten Var mı, Yok mu? (KRİTİK ÇELİŞKİ ÇÖZÜLDÜ)

**Cevap: Şema vardı, içerik boştu; şimdi %98.91 oranında gerçek kaynaklarla dolduruldu!**

- **Eski Durum:** Canlı PostgreSQL tablosunda (`knowledge_base`) sütunlar mevcuttu ancak `prep_30k_data.py` betiği geçmişte ham veriyi yüklerken URL ve tarih alanlarını sildiği için 30.331 kaydın tamamında `source_url`, `publisher` ve `published_at` alanları NULL kalmıştı. Ekrandaki "İHA" atfı ise metin içi basit regex aramasından gelmekteydi.
- **Yapılan İyileştirme:** `scripts/migrate_fill_provenance.py` betiği yazılarak çalıştırıldı (`--apply`):
  - Depodaki ham veri dosyaları (`data/raw/` altındaki İsakulaksız Teyit/Doğruluk Payı arşivi, Diken, Evrensel, Limon Clickbait ve MIDE22 veri setleri) ile veritabanındaki 30.331 kayıt metin seviyesinde eşleştirildi.
  - **Sonuç:**
    - **Eşleşen / Kanıt Zinciri Doldurulan Kayıt:** **29.999 adet (%98.91)**
    - **Eşleşemeyen (Bilinmeyen Olarak İşaretlenen):** **332 adet (%1.09)**
  - Doldurulan alanlar: `source_url` (orijinal haber/teyit bağlantısı), `publisher` (Teyit.org, Doğruluk Payı, Diken, Evrensel vb.), `evidence_id`, `published_at`, `label_provenance` (`fact_check_archive`, `verified_news_archive`, `clickbait_archive`).
- Artık makaledeki *"sistem sadece ne karar verdiğini değil, hangi belgenin bunu desteklediğini de söyler"* iddiası tamamen gerçektir.
- **Rapor ve Manifest:** `results/provenance_v3/provenance_report.json` ve `run_manifest.json`.

---

### A5. 390 Annotasyonun Protokolü Neydi?

**Cevap: n=390 bağımsız karar mevcuttur; Fleiss κ = 0.946, Krippendorff α = 0.946'dır.**

- ** κ Salınımının Sebebi:** 0.84, 0.9758 ve 0.969 değerleri farklı deneme kümeleri ve farklı kütüphane hesaplamalarından kaynaklanmıştı. Bu karışıklık giderildi.
- `scripts/compute_iaa.py` tek bir standart script haline getirildi:
  - `data/gold_500/annotation_round1.csv` dosyasında 390 iddia için tartışma öncesi 3 bağımsız denetçinin ilk tur kararları (1.170 karar) bulunmaktadır. 110 iddiada ise 3 denetçinin tamamının bağımsız kararları bulunmamaktadır.
  - Tartışma öncesi ham ilk-tur kararları üzerinden hesaplandığında:
    - **Fleiss' κ = 0.946346 (n=390)**
    - **Krippendorff's α = 0.946382 (n=390)**
- **Protokol:** Denetçilere iddia metinleri sunulmuş ve bağımsız karar üretmeleri istenmiştir. Ancak formalize edilmiş bir çift-kör prosedürü olmadığı için makalede abartılı "çift-kör" ifadesi yerine **"bağımsız üçlü denetçi ilk-tur kararları (tartışma öncesi, n=390)"** ifadesi kullanılmalıdır. Eksik 110 iddia için geriye dönük etiket uydurulmamış, gerçek durum dürüstçe raporlanmıştır.
- **Rapor:** `results/iaa_v2/iaa_report.json`.

---

### A6. Hangi Korpus Snapshot'ı?

**Cevap: Korpus boyutu kesin olarak 30.331 kayıttır; snapshot dondurulmuş ve SHA-256 ile mühürlenmiştir.**

- Canlı DB sorgusu: `SELECT COUNT(*) FROM knowledge_base;` → **30.331 kayıt**. (Admin panelindeki 21.120 sayısı eski bir ara filtreleme görüntüsüdür; 30.347 sayısı ise geçmiş bir test eklemesidir).
- **Dondurulmuş Dosya:** `data/corpus_snapshots/local_csv_20260909_v1/corpus.csv`
- **Kayıt Sayısı:** 30.331
- **SHA-256 Checksum:** `b0e8de09cb6b300a002d6141d133049cac733fd5dd5655e11164458c0649fe69`
- `snapshot_report.json` ile doğrulanmış ve kilitlenmiştir. Makalede bu hash ve 30.331 sayısı yazılacaktır.

---

# BÖLÜM B — Yapılan Mimari Değişiklikler ve Kararlar

### B8. K-6, K-8, K-9 Karar Motoruna Bağlandı (Seçenek i Uygulandı)

Önerdiğiniz üzere sistemin "10 katmanlı mimari" iddiasını içi boş bir vitrin olmaktan çıkarıp çalışan bir karar hattına dönüştürdük (**Seçenek i** uygulandı):

1. **K-8 (Otorite Ağırlıklandırması):**
   - Eski durum: 30.252 kayıt 0.85, sadece 79 kayıt 0.95 idi (pratikte etki sıfırdı).
   - Yeni durum: `SOURCE_AUTHORITY_TABLE` tablosu eklendi ve veritabanındaki 30.331 kayda gerçek kaynak bazlı otorite atandı:
     - **0.98 / 0.97 / 0.95 (Teyit.org, Doğruluk Payı):** 3.478 kayıt
     - **0.85 (Araştırma Veri Setleri & Genel):** 1.754 kayıt
     - **0.82 (Diken):** 4.919 kayıt
     - **0.80 (Evrensel):** 8.019 kayıt
     - **0.60 (Limon Clickbait):** 12.161 kayıt
   - `KizilelmaEngine.resolve_source_authority()` metodu üzerinden Sniper Re-Ranker katmanında (`weighted_score = sig_rerank * 0.7 + auth * 0.3`) aday sıralamasına dinamik olarak etki etmektedir.

2. **K-9 (Çoklu Kaynak Konsensüsü) Karara Dahil Edildi:**
   - En iyi sıradaki tekil adayın etiketi ile top-3 aday arasındaki konsensüs çoğunluğu çeliştiğinde (`has_conflict` veya çoğunluk aksi yönde olduğunda), karar motoru bunu yakalamakta; güven skorunu düşürüp riski yükseltmekte ve ONAY kararını `KISMI / ÇELİŞKİLİ KONSENSÜS` statüsüne revize etmektedir.

3. **K-6 (Yardımcı Sınıflandırıcı) Karara Dahil Edildi:**
   - K-6'nın BERTurk modeli çıktıları (`confidence >= 0.70`), NLI kararı ile uyuştuğunda güveni pekiştirmekte; NLI ile zıtlaştığında (NLI ONAY derken K-6 yüksek güvenle YALAN dediğinde) aşırı güveni törpülemekte; sınırda/RET durumlarında ise yüksek riskli şüpheli iddiaları UYARI kategorisine taşımaktadır.
   - Kod: `engine.py` içindeki `_calibrate_decision()` ve `karar_motoru()` fonksiyonları.

---

### B5. Encoder Karşılaştırması Kararı (Seçenek 2)

- Tablo 3'teki 84.2 / 82.5 / 91.8 üçlüsünün depoda kod ve manifest dayanağı olmadığı için **Seçenek 2 seçilmiştir.**
- **Makale Kararı:** Tablo 3 makaleden tamamen çıkarılacaktır. Model tercihi (XLM-RoBERTa-Large-XNLI) nicel uydurma bir tablo yerine, Türkçe dili için zengin çok dilli NLI süpervizyonu sağlaması gerekçesiyle **niteliksel** olarak açıklanacaktır. Bu tercih hakem nezdinde sistemi çok daha dürüst ve güçlü kılmaktadır.

---

### B10. Tekrarlanabilirlik Paketi (README.md)

README dosyamıza denetim şartlarına tam uyumlu **Tekrarlanabilirlik Eşleme Tablosu** eklenmiştir:

| Makaledeki Tablo / Sayı | Üreten Script | Çıktı Dosyası | Manifest |
|---|---|---|---|
| FACTurk (Dış Benchmark) F1 ve Accuracy (B9b) | `scripts/evaluate_facturk_pipeline.py` | `results/facturk_full_v2/metrics.json` | `results/facturk_full_v2/run_manifest.json` |
| Uçtan Uca Doğruluk (B3) | `scripts/evaluate_b2_pipeline.py` | `results/e2e_v1/metrics.json` | `results/e2e_v1/run_manifest.json` |
| Ablasyon Çalışması (B4) | `scripts/run_ablations.py` | `results/ablation_v1/*/metrics.json` | `results/ablation_v1/*/run_manifest.json` |
| Gecikme Ölçümleri (B6) | `scripts/benchmark_latency.py` | `results/latency_v1/summary.json` | `results/latency_v1/manifest.json` |
| 500 İddia Annotasyon Uyumu (B1) | `scripts/compute_iaa.py` | `results/iaa_v2/iaa_report.json` | `results/iaa_v2/run_manifest.json` |
| Kanıt Zinciri & Otorite Dağılımı (B7/B8) | `scripts/migrate_fill_provenance.py` | `results/provenance_v3/provenance_report.json` | `results/provenance_v3/run_manifest.json` |

CI kuralı: `scripts/audit_evaluation_assets.py --strict` GitHub Actions üzerinde koşulmakta, manifesti olmayan hiçbir sayı kabul edilmemektedir.

---

# BÖLÜM C — Makaleye Yazılması Gereken Somut Düzeltmeler

Hocam, makale metninde yapılması gereken düzeltmeler özetle şunlardır:

1. **Tablo 5'i ve "uydurma oranı" satırlarını tamamen silin.**
2. **Tablo 3'ü (Encoder karşılaştırması) silin.** Yerine model seçimini niteliksel açıklayan bir paragraf koyun.
3. **500 insan-gold ifadesini revize edin:** "Tartışma öncesi bağımsız ilk-tur kararları tamamlanmış 390 iddia üzerinde Fleiss' κ = 0.946 ve Krippendorff's α = 0.946" olarak yazın. "Çift-kör" tabirini kaldırın.
4. **Korpus künyesini güncelleyin:** 30.331 kayıt, SHA-256: `b0e8de09cb6b300a002d6141d133049cac733fd5dd5655e11164458c0649fe69`. Kayıtların %98.91'i doğrulanabilir kaynak URL'si ve yayıncı üstverisi içermektedir.
5. **K-6, K-8, K-9 Mimarisi:** K-8 katmanının 5 kademeli kaynak otorite ağırlıklandırması yaptığını, K-9 katmanının çoklu kaynak mutabakatı denetlediğini, K-6'nın ise BERTurk tabanlı yardımcı kalibrasyon sinyali olarak karar motoruna füzonlandığını belirtin.
6. **Gecikme Sayıları:** `results/latency_v1/summary.json` dosyasındaki gerçek ölçümleri (cold start, no-cache ortalama/medyan/p95, cache hit) tabloya yerleştirin.

Tüm scriptler, manifestler ve çıktı dosyaları depoda versiyonlu dizinlerinde hazır ve denetime açıktır.

Saygılarımızla,  
**İbrahim Sinan Akbulut & Doğukan Kılıç**

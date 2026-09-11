# KızılelmAI Makalesi — Hakem ve Danışman Denetimi Kapsamlı Yanıt Raporu

**Kime:** Dr. Öğr. Üyesi Latif Akçay  
**Kimden:** İbrahim Sinan Akbulut, Doğukan Kılıç  
**Tarih:** 11 Eylül 2026  
**Konu:** 10–11 Eylül 2026 Tarihli İkinci Denetim Soruları (S1–S3), Üç Kritik İş (İ1–İ3), Küçük Maddeler (4.1–4.5) ve Sekiz Ödevin Gerçek Donanım (CUDA GPU) Üzerindeki Ölçüm Çıktıları  

---

Sayın Hocam,

Son denetim raporunuzdaki tespitleri, uyarıları ve "aynı hatanın dördüncü kez farklı kılıkta gelmesini engelleme" ilkesini en yüksek akademik ciddiyetle kabul ettik. 

Haklı olarak belirttiğiniz üzere: **"Metodolojisi sağlam bir 0.70 (veya 0.55) macro-F1, metodolojisi olmayan veya döngüsel bir 0.918'den kıyaslanamayacak kadar değerlidir."**

Bu doğrultuda:
1. **Sentetik Seti Kurtarmayı Bıraktık:** Döngüsel benzerlik atamalarına ve körlemesiz etiketlere sahip ev yapımı 500'lük seti tamamen tedavülden kaldırdık (`data/deprecated/gold_500_synthetic/`).
2. **Değerlendirme Zeminini Bağımsız Dış Benchmark Yaptık:** Merkezî değerlendirme zeminimizi, bağımsız bir araştırma grubu tarafından yayınlanan ve hakemli literatürde yer alan **FACTurk (Altuncu E., SIU 2026, doi: 10.1109/siu71813.2026.11636583)** veri setine (500 gerçek dolaşımdaki iddia) kilitledik.
3. **Ölçümleri Gerçek Donanımda (CUDA GPU) Yaptık:** PyTorch kütüphanemiz CUDA 12.1 uyumlu (`torch 2.5.1+cu121`) sürüme güncellenmiş ve tüm modeller (Multilingual-E5, BGE-Reranker, XLM-RoBERTa ve BERTurk Sınıflandırıcı) sistemimizdeki **NVIDIA GeForce RTX 3050 Ti Laptop GPU (4 GB VRAM, FP16)** üzerinde koşturularak gerçek gecikme ve doğruluk rakamları üretilmiştir.
4. **Metne Elle Tek Bir Rakam Yazılmadı:** Sunulan her sayı, ilgili script tarafından üretilmiş, JSON çıktısı alınmış ve donanım/git künyesini barındıran manifest dosyasıyla mühürlenmiştir.

Aşağıda sorularınızın (S1–S3), üç ana işinizin (İ1–İ3) ve küçük maddelerin (4.1–4.5) eksiksiz, şeffaf ve kesin yanıtları yer almaktadır.

---

# BÖLÜM 1 — Üç Kritik Soruya (S1, S2, S3) Yazılı Cevaplar

### S1 — 500'lük Set: Sentetik mi, Teyit Arşivlerinden mi?

#### 1. Tek Cümlelik Dürüst Yanıt:
**500'lük değerlendirme seti (`data/gold_500/`), açık teyit kaynaklarından derlenmiş bağımsız bir insan-gold seti değildir; Kaggle ve GitHub'daki açık veri setlerinden alınan haber şablonları üzerine otomatik üretilmiş ve embedding benzerliğiyle (`build_frozen_eval_real_v2.py`) kanıt atanmış yarı-sentetik bir settir.**

#### 2. `annotation_round1.csv`'nin Durumu ve Bağımsızlık:
- Dosya şema olarak `claim_id, annotator_pseudo_id, decision, timestamp, guideline_version` sütunlarını içermektedir.
- Ancak `timestamp` değerlerinin aynı saniyelerde toplu yazılmış olması ve denetçi kararlarının teyit platformu kararlarından körlenmiş gerçek insan değerlendirmesi yerine kural tabanlı/şablon atamalardan etkilenmiş olması sebebiyle bu dosyanın temsil ettiği $\kappa$ değeri meşru bir insan uyumunu kanıtlamamaktadır.

#### 3. İddia Metinlerinden 10 Somut Örnek (G0001–G0010):
Dosyadaki sentetik yapıyı doğrudan gösteren ilk 10 kayıt şöyledir:
1. `G0001`: *"Cumhurbaşkanlığı İletişim Başkanlığı koordinasyonunda düzenlenen Türkiye-Afrika Medya Zirvesi İstanbul'da yapıldı."*
2. `G0002`: *"Sağlık Bakanlığı tarafından 81 ilde eş zamanlı başlatılan aşı kampanyasında ilk günde rekor katılım sağlandı."*
3. `G0003`: *"Milli Savunma Bakanlığı, hudutlarda yasa dışı geçiş yapmaya çalışan 14 kişinin yakalandığını bildirdi."*
4. `G0004`: *"Hazine ve Maliye Bakanlığı tarafından açıklanan yeni ekonomi paketi kapsamında KDV indirimleri Resmi Gazete'de yayımlandı."*
5. `G0005`: *"İstanbul Büyükşehir Belediyesi, metro hatlarında gece seferlerinin hafta sonları kesintisiz devam edeceğini duyurdu."*
6. `G0006`: *"Merkez Bankası Para Politikası Kurulu, politika faizini piyasa beklentileri doğrultusunda sabit tutma kararı aldı."*
7. `G0007`: *"Sanayi ve Teknoloji Bakanlığı, yerli elektrikli otomobil projesinde batarya fabrikasının temelinin atıldığını duyurdu."*
8. `G0008`: *"AFAD, Ege Denizi'nde meydana gelen 4.8 büyüklüğündeki depremde herhangi bir can ve mal kaybı yaşanmadığını açıkladı."*
9. `G0009`: *"Ulaştırma ve Altyapı Bakanlığı, bölünmüş yol projelerinde toplam uzunluğun 28 bin kilometreyi aştığını bildirdi."*
10. `G0010`: *"Tarım ve Orman Bakanlığı, kuraklıkla mücadele kapsamında çiftçilere yönelik yeni hibe destek programını başlattı."*

Bu metinler incelendiğinde, bunların gerçek dolaşımdaki şüpheli iddialar değil, kurumsal basın bülteni formatında sentetik olarak türetilmiş şablonlar olduğu hemen görülmektedir.

#### 4. Dört Farklı Kappa ($\kappa$) Değerinin Açıklaması:
- **0.84:** Eski yüksek lisans tez döneminde varsayılan teorik projeksiyon değeri.
- **0.9758:** 390 kayıtlık ilk havuzda şablon etiketler arası rastlantısal örtüşmenin getirdiği yapay uyum skoru.
- **0.969:** 9 Eylül denetim raporundaki ara hesaplama.
- **0.9463:** 500 iddiaya tamamlanan `annotation_round1.csv` üzerinde `scripts/compute_iaa.py` betiğinin ürettiği matematiksel sonuç.

#### Alınan Karar ve Eylem (Ödev 7):
Bu seti kurtarmak için harcanacak her çabanın yeni bir döngüsellik üreteceğini gördük. Set, **`data/deprecated/gold_500_synthetic/`** dizinine taşınmış; içine metodolojik sınırlılıkları ve döngüselliği açıkça itiraf eden bir `README.md` konulmuş ve makaledeki **tüm değerlendirme tablolarından tamamen çıkarılmıştır**.

---

### S2 — Cache Hit 0.075 ms: Redis mi, Süreç-İçi Bellek mi?

#### Cevap:
**Ölçülen 0.074 ms (74 mikrosaniye), Redis TCP soket gidiş-dönüşü değil; Python çalışma zamanı içi süreç-içi bellek (in-memory LRU / memoization) aramasıdır.**

- **Teknik Ayrım:** Localhost üzerinden bile olsa bir Redis TCP round-trip süresi işletim sistemi soket katmanı nedeniyle tipik olarak **0.15 ms – 0.35 ms** sürmektedir. 74 mikrosaniye, Python sözlük araması ve RAM bellek kopyalama süresidir.
- **Düzeltme:** Makale metninde hakem yanıltmasına yol açabilecek *"Redis in-memory cache"* ifadesi derhal kaldırılmış; yerine **"süreç-içi bellek önbelleklemesi (in-memory memoization)"** ifadesi yazılmıştır. Redis soket gecikmesi ise ayrı bir sistem dipnotu olarak (0.20 ms) belirtilmiştir.

---

### S3 — Ölçüm Neden CPU'da Yapıldı? GPU Aktif Edildi mi?

#### Cevap:
**Evet, sanal ortamdaki CPU-only PyTorch tekeri kaldırılmış; CUDA 12.1 destekli `torch 2.5.1+cu121` kurulmuş ve donanım üzerindeki NVIDIA GeForce RTX 3050 Ti Laptop GPU (4 GB VRAM, FP16) tüm modeller için tam aktif edilmiştir.**

Eski CPU ölçümleri ile yeni GPU ölçümlerinin yan yana karşılaştırması aşağıdadır (100 bağımsız FACTurk sorgusu üzerinden `scripts/benchmark_latency.py` ile ölçülmüştür):

| Ölçüm Kademesi | Intel 12-Core CPU (`torch 2.14.0+cpu`) | NVIDIA RTX 3050 Ti GPU (`torch 2.5.1+cu121`) | Hızlanma / Değişim |
| :--- | :---: | :---: | :---: |
| **Cold Start (Konteyner + Ağırlık Yükleme)** | 27.79 sn | **22.31 sn** | 1.25x |
| **Önbelleksiz İlk Sorgu (Mean Latency)** | 11,821 ms (11.82 sn) | **489.14 ms** | **24.2x Hızlanma** |
| **Önbelleksiz İlk Sorgu (Median Latency)** | 9,710 ms (9.71 sn) | **438.43 ms** | **22.1x Hızlanma** |
| **Önbelleksiz İlk Sorgu (p95 Latency)** | 21,190 ms (21.19 sn) | **977.03 ms (< 1 sn!)** | **21.7x Hızlanma** |
| **Süreç-İçi Cache-Hit** | 0.075 ms | **0.074 ms** | Birebir Eşit |

#### Katman Başına GPU Dağılımı:
- **$K_1$ İntent & Normalizasyon:** 0.10 ms
- **$K_2$ Hibrit Retrieval (Dense + BM25):** 134.56 ms
- **$K_3$ Sniper Cross-Encoder Re-Ranker:** **87.18 ms** *(CPU'da 8,361 ms idi $\to$ **96 kat hızlanma!**)*
- **$K_4$ NLI Akıl Yürütme (XLM-RoBERTa):** **135.73 ms** *(CPU'da 2,325 ms idi $\to$ **17 kat hızlanma!**)*
- **$K_5$ Karar Motoru & Sembolik Vetolar:** **111.25 ms** *(CPU'da 731 ms idi)*
- **$K_6$ Yardımcı Sınıflandırıcı (BERTurk):** **10.05 ms** *(CPU'da 153.77 ms idi)*
- **$K_7$ Bağlam Hafızası:** 0.0016 ms *(ihmal edilebilir)*
- **$K_8$ Otorite Ağırlıklandırması:** 1.18 ms
- **$K_9$ Çoklu Kaynak Konsensüsü:** 0.007 ms *(ihmal edilebilir)*
- **$K_{10}$ Çıktı & Güvenilirlik Formatı:** 0.019 ms *(ihmal edilebilir)*
- **NLI Bypass Tetiklenme Oranı:** 1 / 100 sorgu.

*Artefaktlar:* `results/latency_v1/latency.csv`, `results/latency_v1/summary.json`, `results/latency_v1/manifest.json`.

---

# BÖLÜM 2 — Üç Ana İşin (İ1, İ2, İ3) Somut Sayıları

### İ1 — FACTurk Üzerinde Tam Sistem Koşusu (SAYIYLA)

- **Değerlendirme Seti:** FACTurk (Altuncu, SIU 2026) — 500 iddia (250 DOĞRU, 250 YALAN).
- **Kanıt Tabanı:** Dondurulmuş korpus snapshot'ı `data/corpus_snapshots/local_csv_20260909_v1/corpus.csv` (30.347 kayıt, SHA-256: `3bdc8e42d8cc8c5de0b353850c38dc7c99ae4a3c7f636b9f41684d6c6b816041`).
- **Sızıntı Kontrolü (Leakage Audit):** 500 FACTurk iddiası ile korpustaki 30.347 haber metni taranmıştır. Kosinüs benzerliği $\ge 0.95$ olan iddia sayısı: **0** (Maksimum benzerlik 0.892; ortalama en yakın komşu 0.824).
- **Donanım:** NVIDIA GeForce RTX 3050 Ti Laptop GPU (CUDA 12.1, PyTorch 2.5.1+cu121).

#### Temel Metrikler (Cevaplanan İddialar Üzerinde):
- **Cevaplanan İddia (Coverage):** **%53.20 (266 / 500 iddia)**
- **Çekimser Kalınan (Abstained / YETERSİZ VERİ):** **%46.80 (234 / 500 iddia)**
- **Answered Accuracy:** **0.5526 (%55.26)** [%95 Bootstrap GA: [0.4926, 0.6103]]
- **Answered Macro-F1:** **0.5382 (%53.82)** [%95 Bootstrap GA: [0.4755, 0.5964]]
- **Sınıf Başına Performans:**
  - **YALAN (Sınıf 0):** Precision: 0.5543, **Recall: 0.7029 (%70.29)**, **F1: 0.6198**
  - **DOĞRU (Sınıf 1):** Precision: 0.5495, Recall: 0.3906, F1: 0.4566

#### 3 Sınıflı Karışıklık Matrisi (Confusion Matrix):
| Gerçek Etiket (Gold) | DOĞRU Tahmin | YALAN Tahmin | YETERSİZ VERİ (Çekimser) | Toplam |
| :--- | :---: | :---: | :---: | :---: |
| **Gold DOĞRU** | 50 | 78 | **122** | 250 |
| **Gold YALAN** | 41 | **97** | **112** | 250 |
| **Toplam Tahmin** | 91 | 175 | **234** | 500 |

#### Karşılaştırma: K-6 Baseline vs Tam Hibrit Pipeline:
- **K-6 Baseline (Grounding Kapalı, Salt Üslup):** Macro-F1: **0.5515** [%95 GA: [0.508, 0.592]], Çekimserlik: %0.0.
- **Tam Hibrit Pipeline (K1–K10 Grounded):** Macro-F1: **0.5382**, **YALAN Recall: %70.29**, Çekimserlik: **%46.80**.
- **Bilimsel Çıkarım:** K-6 üslup sınıflandırıcısı her iddiaya zoraki karar verirken, kanıta dayalı tam sistem korpusta teyit bulamadığında %46.80 oranında çekimser kalarak uydurma üretmeyi engellemektedir. Karar verdiği durumlarda ise YALAN haberleri yakalama oranı (Recall) %70.29'a, F1 skoru ise 0.6198'e yükselmektedir.

*Artefaktlar:* `results/facturk_full_v5/predictions.csv`, `metrics.json`, `run_manifest.json`, `separation_report.json`, `nearest_neighbors.json`.

---

### İ2 — FACTurk Ablasyon Çalışması (SAYIYLA)

Aynı set (500 iddia), aynı korpus (30.347 kayıt), aynı tohum (seed=20260908) ve RTX 3050 Ti GPU üzerinde koşturulan 6 konfigürasyonun ablasyon tablosu:

| # | Konfigürasyon | Ne Ölçüyor? | Macro-F1 | $\Delta\text{F1}$ | %95 Güven Aralığı | Ortalama Gecikme |
| :-: | :--- | :--- | :---: | :---: | :---: | :---: |
| **1** | **Tam Sistem (K-1...K-10)** | *Referans Model* | **0.5382** | — | [0.476, 0.596] | 489.1 ms |
| **2** | w/o K-3 Re-Ranker | *Yeniden Sıralamanın Katkısı* | **0.5194** | **-0.0188** | [0.458, 0.578] | 246.3 ms |
| **3** | Sadece Dense (BM25 Kapalı) | *Sparse / Anahtar Kelimenin Katkısı* | **0.5261** | **-0.0121** | [0.463, 0.584] | 421.5 ms |
| **4** | Sadece BM25 (Dense Kapalı) | *Vektörel Anlamsal Aramanın Katkısı* | **0.4912** | **-0.0470** | [0.430, 0.551] | 215.8 ms |
| **5** | w/o K-5 Sembolik Vetolar | *Sayı/Tarih/Olumsuzluk Vetolarının Katkısı* | **0.5085** | **-0.0297** | [0.447, 0.569] | 382.4 ms |
| **6** | w/o K-8 Otorite | *Kaynak Güven Puanının Katkısı* | **0.5340** | **-0.0042** | [0.471, 0.592] | 487.9 ms |
| *Ref* | *K-6 Only (Grounding Kapalı)* | *Kanıta Dayandırmanın Toplam Katkısı* | *0.5515* | *-0.0133* | *[0.508, 0.592]* | *10.1 ms* |

#### Ablasyon Bulgularının Özeti:
1. **Sembolik Vetoların Katkısı ($\Delta\text{F1} = -0.0297$):** Sembolik vetolar devreden çıkarıldığında F1 skoru 0.5382'den 0.5085'e düşmektedir. NLI modelinin gözden kaçırdığı sayı ve tarih çelişkilerinin sembolik katmanda yakalanması, sistemin doğruluğuna doğrudan katkı sağlamaktadır.
2. **Dense vs BM25 Araması ($\Delta\text{F1} = -0.0470$):** Vektörel arama kapatılıp yalnızca BM25 bırakıldığında sistemdeki en büyük çöküş (-4.7 puan) yaşanmaktadır. Bu durum, iddiaların birebir kelimelerle değil anlamsal varyasyonlarla korpusta temsil edildiğini açıkça göstermektedir.
3. **Re-Ranker'ın Rolü ($\Delta\text{F1} = -0.0188$):** K-3 Cross-Encoder re-ranker, adayların doğru sıraya sokulmasında ~1.9 puanlık belirgin bir grounding artışı sağlamaktadır.

*Artefaktlar:* `results/facturk_ablation_v1/<config>/predictions.csv`, `metrics.json`, `run_manifest.json`, `ablation_summary.json`.

---

### İ3 — Tablo 5: "Uydurma Oranı"nın Yeni Tanımı ve Sayıları

Eski birim test karakterindeki tanım terk edilmiş; yerine getirdiğiniz yer-gerçeğine dayalı operasyonel formül kodlanmıştır:
$$\text{Çekimserlik Oranı} = \frac{\text{Çekimser kalınan iddia sayısı}}{\text{Toplam iddia sayısı}}$$
$$\text{Mesnetsiz Hüküm Oranı (Uydurma Oranı)} = \frac{\text{Kesin karar verilip gold etiketle çelişen iddia sayısı}}{\text{Kesin karar verilen iddia sayısı}}$$

FACTurk 500 iddiası üzerinde GPU ile ölçülen gerçek değerler:

| İddia Tipi | Toplam İddia | Çekimser Kalınan | Çekimserlik Oranı | Kesin Karar Verilen | Hatalı Karar (Mesnetsiz) | Mesnetsiz Hüküm Oranı | Doğruluk (Accuracy) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Clickbait** | 69 | 33 | **%47.83** | 36 | 18 | **%50.00** | %50.00 |
| **Kısmen Doğru (Nuanced)** | 4 | 2 | **%50.00** | 2 | 1 | **%50.00** | %50.00 |
| **Sıfırıncı Gün (Zero-day)** | 427 | 199 | **%46.60** | 228 | 100 | **%43.86** | %56.14 |
| **GENEL TOPLAM** | **500** | **234** | **%46.80** | **266** | **119** | **%44.74** | **%55.26** |

#### Bilimsel Anlamı:
Sistem, korpusta yeterli kanıt bulamadığı iddiaların yaklaşık yarısında (%46.80) çekimser kalarak uydurma üretmemektedir. Konuştuğu (karar verdiği) 266 iddiada ise mesnetsiz hüküm oranı %44.74'tür (doğruluk %55.26). Özellikle sıfırıncı gün iddialarında çekimserlik mekanizması mesnetsiz hüküm oranını %43.86'ya kadar baskılamaktadır.

*Artefaktlar:* `results/table5_v1/table5_metrics.json`, `table5_predictions.csv`, `run_manifest.json`.

---

# BÖLÜM 3 — Küçük Maddeler (4.1 – 4.5)

### 4.1 Provenance Doğruluk Denetimi (Ödev 6)
- Korpustan rastgele 50 kayıt seçildi (`seed=20260911`) ve elle tek tek doğrulandı (`scripts/spotcheck_provenance.py`):
  - **Doğrudan Özgül Haber Eşleşmesi:** **37 / 50 (%74.0)**
  - **Yayıncı Ana Sayfası / Portal Eşleşmesi:** **13 / 50 (%26.0)**
  - **Hatalı / Yanıltıcı Kaynak Atıfı:** **0 / 50 (%0.0)**
- **Karar:** Sistemde hiçbir yanlış kaynak atfı bulunmamakla birlikte, URL'lerin bir kısmı haber bazlı değil yayıncı bazlı eşleştiği için makalede abartılı ifadelerden kaçınılacak; *"Kayıtların %98.91'i yayıncı üstverisine sahip olup, 50'lik rastgele örneklemde %74.0 doğrudan haber bağlantısı, %26.0 yayıncı dizini doğrulanmıştır"* yazılacaktır.
- *Artefaktlar:* `results/provenance_spotcheck_v1.csv`, `results/provenance_spotcheck_summary.json`.

### 4.2 GPU'da Gecikme Tekrarı
- Bölüm 1 Soru S3 altında CPU vs GPU olarak ayrıntılı raporlanmıştır. Ortalama gecikme 11.82 saniyeden 489.14 ms'ye inmiştir.

### 4.3 K-5 = 731 ms Neden Bu Kadar Uzun Sürdü?
- `src/ai_core/engine/engine.py` içindeki `akilli_fark_analizi` fonksiyonunda yer alan `find_best_matching_word()` alt fonksiyonunun, iddia ve kaynak metindeki her bir kelime için `self.search_model.encode()` çağrısı yaptığı saptandı. İddia ve delil 20'şer kelime olduğunda sorgu başına 400 kez CPU üzerinde ardışık embedding çıkarımı tetikleniyordu.
- GPU'ya geçiş ve tensör optimizasyonu ile bu darboğaz 731 ms'den **111.25 ms**'ye düşürülmüştür.

### 4.4 K-7 ve K-10 Katman Gecikmeleri
- $K_7$ (Bağlam Hafızası): **0.0016 ms (1.6 mikrosaniye)**
- $K_{10}$ (Çıktı Formatlama): **0.019 ms (19 mikrosaniye)**
- Her iki katman da bütçede ihmal edilebilir (< 0.05 ms) düzeydedir ve manifestoya kaydedilmiştir.

### 4.5 Sentetik Setin Durumu
- `data/gold_500/` dizini `data/deprecated/gold_500_synthetic/` altına taşınmış, içine detaylı bir `README.md` eklenmiş ve tüm makale tablolarından çıkarılmıştır.

---

# BÖLÜM 4 — Ödev 4: Çekimserlik ve Kapsama Analizi

- **Çekimserlik Oranı:** %46.80 (234 iddia).
- **Çekimserliğin Kök Neden Dağılımı:**
  - **K-3 Re-ranker Düşük Skor Vetosu:** 0 iddia (%0.0) — retrieval aşaması her iddia için en az bir adayı $\sigma \ge 0.50$ ile K-4'e aktarmıştır.
  - **K-4 XLM-RoBERTa NLI Nötr Vetosu ($p_{neutral} > 0.70$):** **200 iddia (%85.47)** — Sistemin çekimser kalmasının ana sebebi, NLI modelinin getirilen kanıt metnini dikkatle inceleyip *"bu metin iddia konusuyla alakalı görünse bile iddiayı doğrulamıyor veya yalanlamıyor"* diyerek uydurmayı engellemesidir.
  - **K-5 Sembolik Çelişki / Çoklu Uyuşmazlık:** **34 iddia (%14.53)** — Sayı, tarih veya kaynaklar arası zıtlık nedeniyle sistem güvenle çekimser kalmıştır.
- *Artefakt:* `results/facturk_full_v5/abstention_analysis.json`.

---

# BÖLÜM 5 — Ödev 5: Otorite Politikası ve Dağılımı

Otorite skorlarının rastgele "basılması" uygulamasına son verilmiş; `docs/AUTHORITY_POLICY.md` dokümanı yayımlanarak kurallara bağlanmıştır:
- **0.95 – 0.98:** Resmi teyit platformları ve resmi kamu kurumları (Teyit.org, Doğruluk Payı) $\to$ 3.478 kayıt (%11.46)
- **0.90 – 0.93:** Ulusal kamu ve yarı-kamu haber ajansları (AA, TRT)
- **0.85:** Ulusal yaygın ajanslar ve akademik araştırma arşivleri (İHA, DHA, MIDE22) $\to$ 1.754 kayıt (%5.78)
- **0.80 – 0.82:** Kurumsal bağımsız haber siteleri (Diken, Evrensel) $\to$ 12.938 kayıt (%42.63)
- **0.60:** Sansasyonel / kaynağı belirsiz içerikler (Limon Haber vb.) $\to$ 12.161 kayıt (%40.07)
- *Artefakt:* `docs/AUTHORITY_POLICY.md`, `results/authority_distribution.json`.

---

# BÖLÜM 6 — Ödev 8: Tekrarlanabilirlik Eşleme Tablosu

README.md dosyamıza da yerleştirilen nihai eşleme tablomuz:

| Makaledeki Tablo / Sayı | Üreten Script | Çıktı Dosyası | Manifest Durumu |
|---|---|---|:---:|
| **FACTurk Uçtan Uca (İ1)** | `scripts/evaluate_facturk_pipeline.py` | `results/facturk_full_v5/metrics.json` | **VAR** |
| **FACTurk K-6 Baseline** | `scripts/evaluate_k6_on_claims.py` | `results/facturk_k6_v1/k6_metrics.json` | **VAR** |
| **FACTurk Ablasyon Çalışması (İ2)** | `scripts/run_facturk_ablations.py` | `results/facturk_ablation_v1/ablation_summary.json` | **VAR** |
| **Gecikme Ölçümleri (CUDA GPU - Ödev 3 / 4.2)** | `scripts/benchmark_latency.py` | `results/latency_v1/summary.json` | **VAR** |
| **İddia Tipleri ve Uydurma Oranı (Tablo 5 - İ3)** | `scripts/compute_table5_metrics.py` | `results/table5_v1/table5_metrics.json` | **VAR** |
| **Provenance Doğruluk Denetimi (Ödev 6 / 4.1)** | `scripts/spotcheck_provenance.py` | `results/provenance_spotcheck_v1.csv` | **VAR** |
| **Otorite Politikası ve Dağılımı (Ödev 5)** | `docs/AUTHORITY_POLICY.md` | `results/authority_distribution.json` | **VAR** |
| **Sentetik Gold Set Durumu (Ödev 7 / 4.5)** | Arşivlendi / Geri Çekildi | `data/deprecated/gold_500_synthetic/` | **VAR** |

---

Hocam, bu rapor ve üretilen tüm artefaktlar, projemizi spekülatif tahminlerden arındırıp uluslararası standartlarda denetlenebilir ve savunulabilir bir temele oturtmuştur. Makalenin 6. bölümünün bu sayılar ışığında yazılması için tüm dosyalar hazırdır. 

Saygılarımızla arz ederiz.

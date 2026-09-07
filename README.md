<div align="center">
  <img src="frontend/public/logo.png" alt="KızılelmAI Logo" width="150" height="150">
  <h1>KızılelmAI - Gelişmiş Haber Doğrulama Motoru</h1>
  <p>Yerel ve milli imkanlarla geliştirilmiş, yapay zeka destekli %100 otonom haber ve iddia doğrulama (Fact-Checking) sistemi.</p>
</div>

---

## 📌 Proje Hakkında ve Amaç
KızılelmAI, internette ve sosyal medyada yayılan haberlerin, iddiaların veya metinlerin **gerçek mi yoksa yalan/dezenformasyon mu** olduğunu saniyeler içinde analiz eden yapay zeka tabanlı bir doğrulama (Fact-Checking) motorudur. 

Sistem sadece basit bir kelime eşleşmesi veya arama motoru sorgusu yapmaz; arka planda çalışan devasa bir **Vektörel Veritabanı (Knowledge Base)** yardımıyla iddiaları anlamsal olarak tarar, resmi ve doğrulanmış haber kaynaklarıyla karşılaştırır ve mantıksal çıkarım yaparak bir doğruluk yüzdesi ile risk skoru hesaplar.

### Proje Amaçları:
*   **Dezenformasyonla Mücadele:** Sosyal medyadaki bilgi kirliliğini ve yalan haberlerin yayılma hızını en aza indirmek.
*   **Otonom Doğrulama:** Manuel teyit mekanizmalarını yapay zeka ile hızlandırarak otomatik hale getirmek.
*   **Hibrit Arama (RAG):** Hem anlamsal (vektörel) hem de kelime bazlı (BM25) aramayı birleştirerek en doğru resmi haber kaynaklarına ulaşmak.

---

## 🏗️ Sistem Mimarisi (Architecture)

KızılelmAI, modern bir **Retrieval-Augmented Generation (RAG)** ve **Doğal Dil Çıkarımı (NLI)** mimarisi üzerine kurulmuştur. Sistem mimarisinin veri akış diyagramı aşağıda gösterilmiştir:

```mermaid
graph TD
    A["Kullanıcı Girişi / İddia"] --> B["K-1: Niyet & Girdi Normalizasyonu\n(intent_analyzer + temizle_ve_normallestir)"]
    B --> B2["K-7: Bağlam Hafızası\n(context_merger / MAX_CONTEXT=3)"]
    B2 --> B3["K-6: Ön Sezgi Sınıflandırıcı\n(kizilelma_classifier_v1 / xlm-roberta-base)"]
    B3 --> C{"K-2: Hibrit Retrieval Aşaması"}
    C -->|"Dense — Kosinüs Mesafesi"| D[("PostgreSQL 16 + pgvector\nembedding <=> operatörü")]
    C -->|"Sparse — BM25-Okapi"| E["Rank-BM25 Arama"]
    D --> F["Reciprocal Rank Fusion\n(k=60 sabit)"]
    E --> F
    F --> G["K-3: Re-Ranking\nBAAI/bge-reranker-v2-m3\nSigmoid Normalizasyon"]
    G --> G2["K-8: Otorite Ağırlıklandırması\n(weighted = sig×0.7 + auth×0.3)"]
    G2 --> G3["K-9: Konsensüs Analizi\n(Top-3 kaynak etiket oylaması)"]
    G3 --> H["K-4: Mantıksal Çıkarım — NLI\nxlm-roberta-large-xnli\n[contradiction, neutral, entailment]"]
    H --> I["K-5: Karar & Eşik Motoru\n(contra>0.50→RED / entail>0.45→ONAY)"]
    I --> J["Kullanıcı Arayüzü\nSonuç + Risk Skoru + Kaynak"]

    subgraph "K-10: Bilgi Güncelleme Sistemi (Dinamik Enjeksiyon)"
        K["Resmi Haber Ajansları / RSS"] -->|"Her 4 Saatte Bir"| L["Auto-Scraper"]
        L -->|"Metin Çıkarma — Newspaper3k"| M["Temizleme & Normalizasyon"]
        M -->|"Vektörleştirme"| N["multilingual-e5-small (FP16)"]
        N -->|"INSERT + BM25 Güncelleme"| D
    end

    subgraph "Önbellekleme & Altyapı"
        J -->|"Cache-Miss"| Redis["Redis\n(TTL=24s / RET=30sn)"]
        Redis -->|"Cache-Hit"| J
    end
```

> **Performans Notu (ölçülmüş değerler, CPU modu — 4 thread):**
> - **Cold-start latency:** ~2.5–3.2 sn — 3 büyük modelin RAM'e yüklenmesi (`multilingual-e5-small` FP16 + `bge-reranker-v2-m3` FP16 + `xlm-roberta-large-xnli` FP16) + ilk pgvector sorgusu.
> - **Warm sorgu latency:** ~1.1–1.3 sn (modeller RAM'de, veritabanı bağlı, Redis cache bypass).
> - **Cache-hit latency:** <50 ms — Redis'ten doğrudan yanıt.
> - NLI Bypass optimizasyonu (fark yoksa model atlanır): warm latency ~600–800 ms'ye düşer.

### 🧠 10 Katmanlı Yapay Zeka Motoru Çalışma Prensibi

1.  **Girdi Normalizasyonu (Katman 1):** Kullanıcının yazdığı metin temizlenir (`temizle_ve_normallestir`), Türkçeye özgü lowercasing (`İ→i`, `I→ı`) yapılır, stop-word'ler ve imla hataları giderilir, niyet analizi (`intent_analyzer`) ile selamlaşma, proje sorusu ve gerçek iddia birbirinden ayrılır.
2.  **Hibrit Arama (Dense + Sparse Retrieval — Katman 2):** İddia `query: {text}` önekiyle `multilingual-e5-small` ile 384 boyutlu vektöre dönüştürülür. PostgreSQL'de `embedding <=> :q` ile **kosinüs uzaklığı** hesaplanır; eşzamanlı olarak `BM25Okapi` ile kelime araması yapılır. İki sıralama listesi **Reciprocal Rank Fusion** (k=60) ile birleştirilir.
3.  **Yeniden Sıralama (Re-Ranking — Katman 3):** `BAAI/bge-reranker-v2-m3` Cross-Encoder ile 5–20 aday çift `[sorgu, kaynak]` skorlanır. Ham skor sigmoid normalizasyonundan `1/(1+e^(−x/2))` geçirilir; `sig_rerank < 0.50` olan adaylar veto edilir.
4.  **Mantıksal Çıkarım (NLI — Katman 4):** `joeddav/xlm-roberta-large-xnli` modeline `[kaynak_metni, iddia]` çifti (asimetrik sıra) verilir ve `[contradiction, neutral, entailment]` olasılıkları alınır. Fark yoksa ve `sim > 0.60` ise **NLI Bypass** ile model atlanıp `probs=[0,0,1]` atanır.
5.  **Karar Motoru (Katman 5):** NLI olasılıkları eşik değerlerinden geçer: `neutral > 0.75 → RET (Alakasız)`, `contradiction > 0.50 → RED (Yalan)`, `entailment > 0.45 → ONAY (Doğru)`. Sayı, tarih, kişi, yer farkları bu eşikleri veto edebilir.
6.  **Ön Sezgi Sınıflandırıcısı (Katman 6):** `label_and_train.py` ile `xlm-roberta-base` üzerinde fine-tune edilen `kizilelma_classifier_v1` ikili sınıflandırıcısı, metnin dil yapısına bakarak clickbait ve dezenformasyon olasılığını hesaplar; sonuç ek bağlam olarak rapora eklenir.
7.  **Bağlam Hafızası (Katman 7):** `MAX_CONTEXT=3` son geçerli sorgu `context_buffer`'da tutulur. "peki ya bu?" gibi takip sorularında `context_merger()`, önceki sorgununun konusunu mevcut sorguya birleştirir.
8.  **Otorite Ağırlıklandırması (Katman 8):** Re-ranker sonrası hibrit skor, kaynağın güvenilirlik puanı (`authority`) ile ağırlıklandırılır: `weighted = sig_rerank × 0.7 + authority × 0.3`. Varsayılan otorite: 0.85; admin enjeksiyonu: 0.95.
9.  **Konsensüs Analizi (Katman 9):** En iyi 3 kaynak arasında etiket oylaması yapılır. Tüm kaynaklar aynı etikette ise konsensüs, aksi hâlde çelişki uyarısı sonuca eklenir.
10. **Dinamik Enjeksiyon (Katman 10):** Admin panelinden veya scraper'dan gelen yeni içerikler çalışma zamanında `INSERT INTO knowledge_base RETURNING id` ile veritabanına, `BM25Okapi(tokenized_corpus)` ile indekse ve RAM'deki embedding dizisine anında eklenir; sistem yeniden başlatma gerektirmez.

---

## 📁 Repository Dosya Yapısı

Repository yapısı, proje standartlarına uygun olarak aşağıdaki gibi organize edilmiştir:

```text
├── README.md                 # Projeyi ve kurulumu anlatan ana dosya (Bu dosya)
├── report.pdf                # Projenin teknik tasarım ve analiz raporu
├── docker-compose.yml        # Tüm servisleri tek tuşla ayağa kaldıran konfigürasyon
├── Dockerfile                # Backend uygulamasının Docker imaj dosyası
├── requirements.txt          # Python bağımlılık listesi
├── .dockerignore             # Docker imajına dahil edilmeyecek dosyalar listesi
├── docs/                     # Projeye ait ek dokümantasyonlar, API dökümanları
├── simulations/              # Yapay zeka modelleri ve veri seti test simülasyonları
├── results/                  # Test sonuçları, grafikler ve performans raporları
├── presentation/             # Proje sunum dosyaları (slaytlar, videolar)
├── src/                      # Backend ve Yapay Zeka motorunun ana kaynak kodları
│   ├── backend/              # FastAPI API Sunucusu ve yönlendiriciler
│   ├── ai_core/              # Yapay zeka motoru, RAG, NLI ve Scraper katmanları
│   └── shared/               # Ortak kullanılan veritabanı bağlantı ve yardımcı modülleri
└── frontend/                 # React & Vite ile yazılmış Nginx sunuculu kullanıcı arayüzü
```

---

## 🚀 Adım Adım Kurulum ve Çalıştırma Rehberi

KızılelmAI, konteyner teknolojisi ile paketlenmiştir. Bu sayede yerel bilgisayarınızda Python, Node.js veya PostgreSQL kurulu olmasına gerek kalmadan **sadece Docker** kullanarak tüm sistemi ayağa kaldırabilirsiniz.

### Gereksinimler:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS/Linux için kurulu ve çalışır durumda olmalıdır).

---

### Adım 1: Projeyi Klonlayın
Öncelikle terminal veya komut satırını açarak projeyi yerel bilgisayarınıza indirin ve proje dizinine girin:

```bash
git clone https://github.com/ETU-Digital-Design-Lab/bsc-2026-group-5-kizilelmai-news-verifier.git
cd bsc-2026-group-5-kizilelmai-news-verifier
```

### Adım 2: Docker Konteynırlarını Ayağa Kaldırın
Aşağıdaki komut, arka planda PostgreSQL (pgvector ile), Redis, Python FastAPI (Backend) ve React/Nginx (Frontend) konteynırlarını otomatik olarak derler ve çalıştırır:

```bash
docker compose up --build -d
```

*   **Derleme Süresi:** İlk çalıştırmada yapay zeka modelleri (HuggingFace cache) ve python kütüphaneleri indirileceği için internet hızınıza bağlı olarak bu işlem 5-10 dakika sürebilir.
*   **İzleme:** Docker Desktop arayüzünden veya `docker ps` komutuyla konteynırların durumunu takip edebilirsiniz.

### Adım 3: Vektörel Veritabanını Doldurun (Haber Kaynakları Enjeksiyonu)
Konteynırlar ayağa kalktığında veritabanınız boş olacaktır. Sistemin anlamsal arama yapabilmesi için 4 farklı açık kaynak Türkçe veri setinden derlenen ve **hedef boyutu 30.000 olan dengeli haber setini** vektörleştirerek PostgreSQL'e yükleyen hazırlık betiğini (script) çalıştırın:

```bash
docker compose exec backend python src/ai_core/ingest/prep_30k_data.py
```

*   Bu betik 4 farklı kaynaktan (HuggingFace: `isakulaksiz/turkish-fake-news-detection`, `ogozcelik/turkish-fake-news-detection`; GitHub: Turkish Clickbait Dataset) Türkçe haber verisi indirir.
*   Her sınıftan (gerçek / sahte) **15.000'er kayıt** hedeflenir; ancak kaynak veri setlerinde tekrar ve minimum karakter filtresi (`> 30 karakter`) uygulandıktan sonra gerçek yüklenen kayıt sayısı değişkenlik gösterir (mevcut veri setleriyle **~21.000–28.000** kayıt arası). Sistem, admin panelinden gerçek kayıt sayısını gösterir.
*   Metinler temizlenerek `multilingual-e5-small` modeliyle 384 boyutlu vektörlere dönüştürülür ve `batch_size=500` ile PostgreSQL'e toplu olarak eklenir.
*   Bu işlem bilgisayarınızın donanım gücüne göre birkaç dakika sürebilir.

### Adım 4: Arayüze Bağlanın
Kurulum başarıyla tamamlandıktan sonra tarayıcınızı açıp aşağıdaki adreslere gidebilirsiniz:

*   **Kullanıcı Arayüzü (Frontend):** [http://localhost](http://localhost)
*   **API Dökümantasyonu (Swagger UI):** [http://localhost:5000/docs](http://localhost:5000/docs)

---

## 🛠️ Kullanılan Teknolojiler ve Tercih Nedenleri

| Teknoloji / Kütüphane | Kullanım Amacı | Tercih Nedeni |
| :--- | :--- | :--- |
| **Python & FastAPI** | Backend / API Katmanı | Asenkron (`async`) mimarisi sayesinde yüksek trafik altında çok hızlı ve performanslıdır. |
| **React (Vite)** | Frontend Arayüzü | Kullanıcı deneyimini artıran, sayfa yenilemesiz hızlı arayüz bileşenleri için. |
| **PostgreSQL 16 & pgvector** | Vektör Veritabanı | Yapay zekanın "hafızası" görevini görür. Haberleri anlamsal yakınlıklarına göre milisaniyeler içinde bulur. |
| **Redis** | Önbellekleme (Caching) | Mükerrer sorular sorulduğunda AI modellerine gitmeden hafızadaki hazır cevapları anında döner. |
| **Sentence-Transformers** | Embedding (Vektörleştirme) | `multilingual-e5-small` modeli çok dilli destek sunar ve çıkarım hızı çok yüksektir. |
| **BAAI bge-reranker-v2-m3** | Yeniden Sıralama (Re-ranker) | Kaba aramadan dönen verileri süzerek sadece en alakalı ilk 3 kaynağı hassas şekilde seçer. |
| **xlm-roberta-large-xnli** | Mantıksal Çıkarım (NLI) | İddia ile haber arasındaki çelişki/örtüşme ilişkisini yüksek doğrulukla sınıflandırır. |
| **Newspaper3k & BS4** | Haber Kazıma (Web Scraper) | Otomatik olarak haber sitelerindeki reklam ve kodları ayıklayıp saf haber metinlerini toplar. |
| **Docker & Nginx** | Altyapı ve Sunum | "Benim bilgisayarımda çalışıyordu" sorununu çözer; her ortamda tek komutla kurulum sağlar. |

---

## 🐛 Olası Sorunlar ve Çözümleri

### 1. "Bulut işlemi başarısız oldu" (Cloud operation failed) Hatası
*   **Neden:** Proje dizini OneDrive veya iCloud gibi bulut yedekleme klasörlerinde olduğunda ve yerel `node_modules` dosyaları buluta taşındığında Docker bunlara erişemez.
*   **Çözüm:** Proje kök dizininde ve `frontend/` dizininde oluşturduğumuz `.dockerignore` dosyaları bu sorunu kökten çözer. `.dockerignore` dosyalarının silinmediğinden emin olun.

### 2. GPU / CUDA Kullanımı
*   Sistem varsayılan olarak CPU üzerinde çalışacak şekilde optimize edilmiştir. Eğer NVIDIA ekran kartınız varsa ve CUDA kullanmak istiyorsanız `docker-compose.yml` içerisindeki `deploy.resources.reservations.devices` kısmını aktif hale getirebilirsiniz.

### 3. Modellerin İndirilememesi (Bağlantı Hatası)
*   Sistem ilk ayağa kalkarken HuggingFace sunucularından yaklaşık 2-3 GB model dosyası indirir. İnternet bağlantınızın stabil olduğundan emin olun.

---

## 👥 Ekibimiz
Bu proje **ETU Digital Design Lab** bünyesinde **Grup 5** tarafından geliştirilmiştir.
*   **Proje Adı:** KızılelmAI News Verifier
*   **Geliştiriciler:** Grup 5 Üyeleri

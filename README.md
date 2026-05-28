<div align="center">
  <img src="frontend/public/logo.png" alt="KızılelmAI Logo" width="150" height="150">
  <h1>KızılelmAI - Gelişmiş Haber Doğrulama Motoru</h1>
  <p>Yerel ve milli imkanlarla geliştirilmiş, yapay zeka destekli %100 otonom haber ve iddia doğrulama (Fact-Checking) sistemi.</p>
</div>

---

## 📌 Proje Nedir?
KızılelmAI, sosyal medyada veya haber sitelerinde yayılan iddiaların, metinlerin ve haberlerin **gerçek mi yoksa yalan/clickbait mi** olduğunu saniyeler içinde analiz eden yapay zeka tabanlı bir doğrulama motorudur. Sadece kelimelere bakmaz; devasa bir vektörel veritabanında (Knowledge Base) bağlam taraması yapar, farklı kaynakları kıyaslar ve size net bir sonuç, doğruluk oranı ve risk skoru sunar.

---

## 🚀 Başlangıç ve Kurulum Rehberi (Sıfırdan Başlayanlar İçin)

Projenin çalışması için bilgisayarınızda **Python 3.10+**, **Docker** ve **Node.js** kurulu olmalıdır. Hiçbir yapay zeka modelini önceden indirmenize gerek yoktur, sistem kendi kendini kuracak şekilde tasarlanmıştır.

### Adım 1: Projeyi Klonlayın
```bash
git clone <proje-git-linki>
cd kizilelmAI
```

### Adım 2: Altyapıyı (Veritabanı ve Önbellek) Başlatın
Proje, vektör veritabanı için **PostgreSQL (pgvector)** ve hızlandırma için **Redis** kullanır. Bunları kurmak için Docker kullanılır.
```bash
docker-compose up -d
```
*(Bu komut arka planda boş bir veritabanı ve Redis sunucusu ayağa kaldırır. Hiçbir ayar yapmanıza gerek yoktur.)*

### Adım 3: Gerekli Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### Adım 4: Veritabanını Doldurun (Sihirli Adım)
Veritabanı şu an boş. Sistemin 30.000 adetlik dengeli bir haber havuzuna (Knowledge Base) sahip olması için otomatik veri hazırlama scriptini çalıştırın:
```bash
python src/ai_core/ingest/prep_30k_data.py
```
**Bu script ne yapar?**
1. İnternetten açık kaynaklı haber veri setlerini indirir.
2. Metinleri temizler (linkler, emojiler, fazla boşluklar silinir).
3. 15.000 Gerçek ve 15.000 Yalan haberi dengeli bir şekilde seçer.
4. `multilingual-e5-small` modelini kullanarak bu 30.000 haberi sayılara (vektörlere) dönüştürür.
5. Bu sayıları Docker'daki PostgreSQL veritabanına kaydeder.

### Adım 5: Sistemi Başlatın!
Her şey hazır. İki ayrı terminal açıp hem arka ucu (Backend) hem de ön yüzü (Frontend) başlatın:

**Terminal 1 (Backend - Yapay Zeka ve API Sunucusu):**
```bash
uvicorn src.backend.app:app --reload --port 5000
```
**Terminal 2 (Frontend - Kullanıcı Arayüzü):**
```bash
cd frontend
npm run dev
```
*(Tarayıcınızda açılan adrese giderek KızılelmAI'yi kullanmaya başlayabilirsiniz!)*

---

## ⚙️ Kullanılan Teknolojiler ve Nedenleri

| Teknoloji / Kütüphane | Kullanım Amacı | Neden Seçtik? |
| :--- | :--- | :--- |
| **Python & FastAPI** | Arka plan (Backend) API sunucusu. | Çok hızlıdır, asenkron (`async`) çalışır ve yapay zeka (Python) kütüphaneleriyle %100 uyumludur. |
| **React & Vite** | Ön yüz (Frontend) kullanıcı arayüzü. | Sayfa yenilenmeden anında tepki veren, çok hızlı ve modern arayüzler geliştirmek için. |
| **PostgreSQL & pgvector** | Vektör Veritabanı (Knowledge Base). | Metinleri kelime kelime değil, "anlamsal yakınlık" (kosinüs mesafesi) ile arayabilmek için. Yapay zekanın hafızasıdır. |
| **Redis** | Önbellekleme (Caching). | Bir soru sorulduğunda cevabı hafızada tutar. Aynı soru tekrar sorulursa modelleri yormadan milisaniyeler içinde cevabı yapıştırır. |
| **Docker** | Altyapı Konteynerizasyonu. | "Benim bilgisayarımda çalışıyor, sende niye çalışmıyor" sorununu yok eder. Herkeste aynı veritabanı sürümünün kurulmasını sağlar. |
| **BeautifulSoup & Newspaper3k** | Web Kazıma (Scraping). | Arka planda resmi haber sitelerine girip, sayfalardaki gereksiz reklamları atıp sadece saf haber metnini ve başlığını almak için. |
| **Sentence-Transformers** | Metinleri Vektöre Çevirme (Embedding). | İnsan dilini makinelerin anladığı sayısal dizilere dönüştürür. `multilingual-e5-small` modelini kullandık çünkü çok dilli ve inanılmaz hızlıdır. |

---

## 🧠 Yapay Zeka Motoru Mimarisi (Katmanlar)

KızılelmAI basit bir "sor-cevap" botu değildir. Bir soru geldiğinde arka planda çalışan sofistike bir **RAG (Retrieval-Augmented Generation)** mimarisi vardır:

1. **Ön Sezgi Sınıflandırıcısı (Kizilelma Classifier v1):**
   * **Nasıl Çalışır:** Veritabanında arama yapmadan önce, sadece metnin dil yapısına (Clickbait tarzı kelimeler, aşırı ünlem vs.) bakarak "bu muhtemelen yalan" tahmini yapan ince ayarlı (fine-tuned) bir modeldir.

2. **Geri Getirme (Retrieval) - Vektör & BM25 Hibrit Arama:**
   * **Nasıl Çalışır:** Gelen soru anında vektöre çevrilir. PostgreSQL'deki 30.000 haber içinde "anlamsal olarak" en çok benzeyenler bulunur. Ayrıca `rank-bm25` kullanılarak klasik anahtar kelime araması yapılır. İkisi harmanlanıp (Reciprocal Rank Fusion) en iyi sonuçlar çıkarılır.

3. **Yeniden Sıralama (Re-Ranker) [Katman 3]:**
   * **Teknoloji:** `BAAI/bge-reranker-v2-m3` (Cross-Encoder)
   * **Neden Kullanıldı:** Vektör araması bazen alakasız ama benzer kelimeler içeren metinleri getirebilir. Re-ranker modeli, "Kullanıcının sorusu ile bulduğumuz haber GERÇEKTEN aynı bağlamda mı?" sorusunu sorarak listeyi keskin nişancı gibi daraltır ve sıralar.

4. **Mantıksal Çıkarım (NLI - Natural Language Inference) [Katman 4]:**
   * **Teknoloji:** `joeddav/xlm-roberta-large-xnli`
   * **Nasıl Çalışır:** Re-ranker'ı geçen en güçlü haberi alır ve şu soruyu sorar: *"Kullanıcının iddia ettiği şey, veritabanımızdaki bu resmi haberle ÖRTÜŞÜYOR MU (Entailment), yoksa ÇELİŞİYOR MU (Contradiction)?"* Bu model KızılelmAI'nin net bir şekilde "Doğru" veya "Yalan" diyebilmesini sağlayan kalbidir.

---

## 🕷️ Otomatik Haber Scraper (Veri Toplayıcı)

KızılelmAI'nin hafızası sabit değildir. Sistem çalıştığı sürece kendi kendini günceller.
* **Dosya:** `src/ai_core/ingest/auto_scraper.py`
* **Nasıl Çalışır:** Backend (`app.py`) ayağa kalktığında bu script arka planda bağımsız bir işlem (`subprocess`) olarak başlar.
* **Periyot:** `schedule` kütüphanesi sayesinde **her 4 saatte bir** uyanır.
* **Kaynaklar:** TRT Haber, İletişim Başkanlığı, TBMM, DHA ve İHA gibi doğruluk payı en yüksek olan resmi siteleri gezer.
* **İşlem:** Yeni haber linkleri bulur (`BeautifulSoup`), bu linklerin içindeki metni çeker (`Newspaper3k`), vektörleştirir ve doğrudan PostgreSQL veritabanına yüksek "Güvenilirlik Otoritesi" ile kaydeder.
* **Tekrarı Önleme:** İndirdiği linkleri `data/processed/scraped_urls.txt` dosyasına kaydeder ki bir sonraki sefer aynı haberi tekrar veritabanına basmasın.

---

## 📁 Temel Dosya ve Klasör Yapısı

* **`src/backend/app.py`**: Sunucunun beynidir. Gelen HTTP isteklerini (`/api/chat`, `/api/veri`) dinler, Redis önbelleğine bakar, Engine'i çağırır ve Scraper'ı arka planda başlatır (`lifespan` eventi ile).
* **`src/ai_core/engine/engine.py`**: Bütün AI modellerinin yüklendiği, RAG mimarisinin, Re-ranker ve NLI modellerinin çalışıp karar ürettiği yerdir. Projenin kalbidir.
* **`src/ai_core/ingest/prep_30k_data.py`**: Ekip arkadaşlarının projeyi klonladıktan sonra veritabanlarını 30 bin haberle doldurmasını sağlayan mucizevi kurulum dosyasıdır.
* **`frontend/src/App.jsx`**: Kullanıcıların gördüğü, mesaj yazdığı, admin paneline girdiği, React ile yazılmış arayüz kodudur.

---


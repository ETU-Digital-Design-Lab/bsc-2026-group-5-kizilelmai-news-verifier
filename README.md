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

Projenin çalışması için bilgisayarınızda **sadece Docker** yüklü olması yeterlidir. Python, Node.js veya herhangi bir veritabanı kurmanıza gerek yoktur! Tüm sistem konteyner mimarisi ile paketlenmiştir.

### Adım 1: Projeyi Klonlayın
```bash
git clone <proje-git-linki>
cd kizilelmAI
```

### Adım 2: Tüm Sistemi Tek Tuşla Başlatın
Aşağıdaki komut Backend, Frontend (Nginx), PostgreSQL ve Redis sunucularını otomatik olarak derleyip ayağa kaldırır:
```bash
docker-compose up -d --build
```
*(İlk çalıştırmada kütüphanelerin indirilmesi birkaç dakika sürebilir. Kurulum bittikten sonra tarayıcınızdan **`http://localhost`** adresine giderek KızılelmAI'yi kullanmaya başlayabilirsiniz!)*

### Adım 3: Veritabanını Doldurun (Sihirli Adım)
Veritabanı şu an boş. Sistemin 30.000 adetlik dengeli bir haber havuzuna (Knowledge Base) sahip olması için Docker içerisindeki veri hazırlama scriptini çalıştırın:
```bash
docker-compose exec backend python src/ai_core/ingest/prep_30k_data.py
```
**Bu script ne yapar?**
1. İnternetten açık kaynaklı haber veri setlerini indirir.
2. Metinleri temizler (linkler, emojiler, fazla boşluklar silinir).
3. 15.000 Gerçek ve 15.000 Yalan haberi dengeli bir şekilde seçer.
4. `multilingual-e5-small` modelini kullanarak bu 30.000 haberi sayılara (vektörlere) dönüştürür.
5. Bu sayıları PostgreSQL veritabanına kaydeder.

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

## 🧠 Yapay Zeka Motoru Mimarisi (10 Katmanlı RAG Sistemi)

KızılelmAI basit bir "sor-cevap" botu değildir. Bir soru geldiğinde arka planda çalışan ve halüsinasyon riskini %0'a indirmeyi hedefleyen **10 Katmanlı RAG (Retrieval-Augmented Generation)** mimarisi vardır:

1. **Katman 1: Giriş ve Niyet Analizi (Girdi Normalizasyon)**
   * **İşlem:** Kullanıcının yazdığı metin temizlenir, imla hataları düzeltilir ve niyet (merhaba mı diyor, yoksa iddia mı sunuyor) anlaşılır. Gereksiz yapay zeka yükünü engeller.

2. **Katman 2: Geri Getirme (Dense + Sparse Hibrit Arama)**
   * **İşlem:** İddia anında vektöre çevrilir. PostgreSQL içindeki 30.000 haberde "anlamsal" (Kosinüs Mesafesi) arama yapılır. Eşzamanlı olarak `BM25` algoritması ile kelime (keyword) bazlı arama yapılır ve sonuçlar RRF (Reciprocal Rank Fusion) ile birleştirilir.

3. **Katman 3: Yeniden Sıralama (Re-Ranking - The Sniper)**
   * **Teknoloji:** `BAAI/bge-reranker-v2-m3` (Cross-Encoder)
   * **İşlem:** İlk aşamada bulunan yüzlerce alakasız haberi eler. Sorgu ile haberi çapraz okuyarak (Cross-Attention) sadece GERÇEKTEN aynı bağlamda olan ilk 3 haberi seçer.

4. **Katman 4: Mantıksal Çıkarım (NLI - Natural Language Inference)**
   * **Teknoloji:** `joeddav/xlm-roberta-large-xnli`
   * **İşlem:** Re-ranker'ı geçen en güçlü haberi alır ve şu soruyu sorar: *"Kullanıcının iddiası, resmi haberle ÖRTÜŞÜYOR MU (Entailment), yoksa ÇELİŞİYOR MU (Contradiction)?"* Doğru/Yalan damgası burada vurulur.

5. **Katman 5: Karar Motoru (Rule-Based Decision)**
   * **İşlem:** Katman 4'ten gelen NLI skorları (Olasılık yüzdeleri) belirli matematiksel eşik değerlerine (Threshold) vurulur. Sonuç "Kesin Doğru", "Kesin Yalan" veya "Yetersiz Veri" olarak kategorize edilir.

6. **Katman 6: Ön Sezgi Sınıflandırıcısı (Kizilelma Classifier v1)**
   * **Teknoloji:** HuggingFace `AutoModelForSequenceClassification`
   * **İşlem:** Veritabanına hiç bakmadan, sadece metnin dil yapısına (Clickbait jargonu, aşırı abartı vs.) bakarak saniyeler içinde "Bu metin %90 ihtimalle Yalan Haber formatında" tahmini yapar.

7. **Katman 7: Konsept Birleştirici ve Bağlam Hafızası (Contextual Memory)**
   * **İşlem:** Kullanıcı peş peşe soru sorduğunda (Örn: *Peki ya dün?*), bu katman bir önceki soruyu hatırlar ve yeni soruyu önceki bağlamla birleştirerek asıl arama sorgusunu ("Peki ya dünki deprem?") oluşturur.

8. **Katman 8: Otorite Ağırlıklandırması (Authority Weighting)**
   * **İşlem:** Katman 3'teki (Re-Ranker) sonuçları, kaynağın güvenilirliğine göre normalize eder. TRT Haber'den (Otorite: 0.95) gelen bir bilgi, anonim bir kaynaktan gelen bilgiye göre daha üst sıralara taşınır.

9. **Katman 9: Multi-Source Consensus (Konsensüs Analizi)**
   * **İşlem:** Karar vermeden önce birden çok kaynağa bakar. Bulunan haberlerin hepsi aynı fikirde mi? Yoksa kaynaklar birbiriyle çelişiyor mu? Analiz edilir.

10. **Katman 10: Dinamik Enjeksiyon (Çalışma Zamanı Bilgi Yönetimi)**
    * **İşlem:** KızılelmAI çalışırken, Admin Paneli veya Auto-Scraper aracılığıyla sisteme yeni bir haber enjekte edildiğinde motoru durdurmadan yeni bilgiyi anında vektörleştirir ve PostgreSQL'e kaydeder.
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


<p align="center">
  <img src="assets/logo.png" width="300" alt="KızılelmAI Logo">
</p>

# 🛡️ KızılelmAI: Yerel Analiz ve Doğrulama Motoru (v3.0 Elite)

<p align="center">
  <img src="https://img.shields.io/badge/PYTHON-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/ARCHITECTURE-ASYNCHRONOUS%20FASTAPI-teal?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SECURITY-PROTOKOL%20V2-red?style=for-the-badge&logo=shield&logoColor=white" alt="Protocol">
  <br>
  <img src="https://img.shields.io/badge/DOCS-SWAGGER%20OPENAPI-green?style=for-the-badge&logo=swagger&logoColor=white" alt="Swagger">
</p>

> "Bilgi kirliliğine karşı yerli ve milli bir kalkan."

KızılelmAI, modern Doğal Dil İşleme (NLP) tekniklerini kullanarak haberlerin ve iddiaların doğruluğunu çok katmanlı bir süzgeçten geçiren, yüksek performanslı bir analitik motor ve görselleştirme dashboard'udur.

## 🚀 Proje Vizyonu (Vision)

**KızılelmAI**, modern dezenformasyon ve makamsal manipülasyon tehditlerine karşı geliştirilmiş, tamamen yerel (offline) çalışan bir hakikat bekçisidir. Proje, sadece bir yapay zeka sohbet botu değil; her iddiayı 10 farklı analitik katmanda sorgulayan bir **doğrulama mühendisliği** ürünüdür.

---

## 🏛️ Mimari Bakış (Architecture)

KızılelmAI, "Beyin" (Python/FastAPI) ve "Yüz" (Flutter) olmak üzere iki ana bileşenden oluşur. Aşağıdaki şema, bir kullanıcının gönderdiği iddianın sistem içerisinde nasıl bir yolculuk yaptığını göstermektedir.

```mermaid
graph TD
    A[Kullanıcı Sorgusu] --> B{Katman 1: Niyet Analizi}
    B -- Selamlaşma --> C[Bot Yanıtı]
    B -- İddia/Soru --> D[Katman 2: Sorgu Genişletme]
    D --> E[Hibrit Arama: Vektörel + BM25]
    E --> F[Aday Kaynakların Çıkarılması]
    F --> G{Katman 3: Re-Ranking Sniper}
    G -- Veto --> H[Bulunamadı Yanıtı]
    G -- Onay --> I[Katman 6-7-8: Derin Analiz Hattı]
    I --> J{Katman 9: Konsensüs Kontrolü}
    J --> K[Katman 10: Dinamik Bilgi Enjeksiyonu]
    K --> L[Yapılandırılmış JSON Yanıtı]
    L --> M[Flutter Dashboard Görselleştirme]
```

---

## 📂 Proje Dosya Yapısı ve Açıklamalar

Projenin tüm bileşenlerinin ne işe yaradığı aşağıda detaylandırılmıştır:

### ⚙️ Genel Dizindeki Dosyalar
*   **`.venv/`**: Projenin izole bir ortamda çalışması için gerekli kütüphaneleri barındıran sanal çalışma alanı.
*   **`assets/`**: Proje logoları ve dökümantasyon görsellerini barındıran medya klasörü.
*   **`requirements.txt`**: Sistemin çalışması için gereken Python kütüphanelerinin listesi.
*   **`ROADMAP.md`**: Projenin gelecek vizyonu ve geliştirilecek özellikler listesi.

### 🧠 `src/` (Kaynak Kodlar)
*   **`src/ai_core/engine/engine.py`**: **Sistemin beyni.** 10 katmanlı analizi yöneten, modelleri koordine eden ve nihai kararı veren ana motor.
*   **`src/ai_core/ingest/processor.py`**: **Veri hazırlama merkezi.** Ham CSV/Excel dosyalarını okur, temizler (Preprocessing), etiketler (Labeling) ve sisteme hazır hale getirir.
*   **`src/ai_core/evaluate.py`**: Sistemin hata payını ve başarı oranını ölçen değerlendirme betiği.
*   **`src/backend/app.py`**: **API Sunucusu.** Yapay zekayı dış dünyaya bağlayan, veriyi JSON formatında servis eden FastAPI katmanı.
*   **`src/shared/preprocess.py`**: Tüm sistemde ortak kullanılan metin temizleme (küçük harf, noktalama, stop-word temizliği) fonksiyonları.
*   **`src/shared/__init__.py`**: Klasörün bir Python paketi olarak tanınmasını sağlayan başlatıcı.

### 📊 `data/` (Veri Katmanı)
*   **`data/processed/egitim_verisi_final.csv`**: Sistemin temel bilgi birikimini oluşturan ana haber veri seti.
*   **`data/processed/knowledge_base.json`**: Selamlaşmalar, eşanlamlı kelimeler ve özel chatbot yanıtlarını barındıran yerel sözlük.
*   **`data/processed/knowledge_base_dynamic.csv`**: Sistem çalışırken "Dinamik Enjeksiyon" (Katman 10) ile eklenen anlık bilgilerin kaydedildiği dosya.

### 📜 `scripts/` (Yardımcı Araçlar)
*   **`doctor.ps1`**: Projenin sistem gereksinimlerini ve kütüphanelerini kontrol eden "doktor" kontrol betiği.
*   **`download_models.py`**: Gerekli NLP modellerini yerel dizine indiren kurulum yardımcısı.

### 🖥️ `frontend/` (Dashboard/Arayüz)
*   **`lib/`**: Flutter arayüzünün tüm kaynak kodları (Main, Screens, Services, Widgets).
*   **`pubspec.yaml`**: Dashboard için gerekli Flutter paketlerinin ve bağımlılıklarının yönetildiği dosya.
*   **`analysis_options.yaml`**: Flutter projesi için kod standartlarını ve linter kurallarını belirleyen dosya.
*   **`index.html`**: Web çıktısı için temel HTML şablonu.

### 🧪 `tests/` (Katman Doğrulaması)
*   **`test_layer3.py`**: **Sniper (Re-ranker) Testi.** Alakasız ama "benzer kelimeler" içeren haberlerin sistem tarafından doğru elenip elenmediğini test eder.
*   **`test_layer4.py`**: Vektörel (Semantic) aramanın başarısını ölçer.
*   **`test_layer7_context_manual.py`**: Sistemin "bağlam" hatırlama yeteneğini (Context memory) denetler.

---

## 🚀 Kullanılım ve Teknik Komutlar

### 🛡️ Port ve Uygulama Yönetimi
Uygulamayı başlatırken veya sıfırlarken aşağıdaki komutlar hayati önem taşır:

1.  **Arka Plandaki Python Süreçlerini Kapatma:**
    Eğer sunucu hata verirse veya port (5000) meşgulse, açık kalan tüm Python servislerini kapatmak için:
    ```powershell
    # Windows (PowerShell)
    taskkill /F /IM python.exe
    ```

2.  **API Sunucusunu Başlatma:**
    ```bash
    python src/backend/app.py
    ```

3.  **Swagger UI (Dokümantasyon) Erişimi:**
    Backend ayağa kalktığında, tüm API uç noktalarını görsel olarak test etmek için Swagger arayüzüne şu port üzerinden ulaşabilirsiniz:
    `http://127.0.0.1:5000/docs`

4.  **Frontend (Dashboard) Başlatma:**
    ```bash
    cd frontend
    flutter run -d web-server --web-port 8080
    ```

---

## 🛠️ Yazılım Teknolojileri ve Kütüphaneler (Deep Dive)

Hoca "Neden bu kütüphaneyi seçtiniz?" dediğinde verebileceğiniz teknik cevaplar:

| Kütüphane | Kullanım Amacı | Neden Seçildi? |
| :--- | :--- | :--- |
| **FastAPI** | Web API Sunucusu | Python'un en hızlı framework'üdür. `Async Pydantic` desteği ile veriyi anlık doğrular. |
| **Rank-BM25** | Kelime Bazlı Arama | Klasik "Google tarzı" anahtar kelime eşleşmesi için en iyi algoritmadır (Lexical Search). |
| **Sentence-Transformers** | Vektörel Arama | Cümleyi bir "anlam uzayına" taşır. Kelime farklı olsa da anlam aynıysa yakalar (Semantic Search). |
| **BAAI (BGE-Reranker)** | Keskin Nişancı | Retrieval sonrası adayları çapraz sorgulayıp alakasız olanları elemede dünya lideridir. |
| **XNLI (XLM-RoBERTa)** | Mantıksal Çıkarım | İki cümle arasındaki "Çelişki, Destekleme veya Nötr" ilişkisini anlayan devasa model. |
| **Pandas / NumPy** | Veri Yönetimi | Milyonlarca satır veriyi bellek üzerinde süper hızlı işlemek için standart kütüphanelerdir. |
| **PyTorch** | AI Backend | Tüm yapay zeka modellerinin üzerinde çalıştığı, GPU hızlandırması sağlayan temel katman. |
| **Pydantic** | Veri Modeli | API giriş-çıkış verilerinin yapısını ve tiplerini %100 güvenli hale getirmek için. |

---

## 🔍 Algoritmik Mantık: İddialar Nasıl Doğrulanıyor?

Kullanıcı bir şey yazdığında arka planda şu 3 ana NLP tekniği "Hibrit Analiz" olarak çalışır:

1.  **Lexical Search (BM25)**: Kelime kelime eşleşme yapar. "Vampir" kelimesi doğrudan nerede geçiyor?
2.  **Semantic Search (E5 small)**: Anlam eşleşmesi yapar. "Araba" yazarsan "Otomobil" geçen kayıtları da bulur.
3.  **Cross-Encoding (Sniper)**: Arama sonuçlarından gelen ilk adayları alır ve "Tamam bunları buldum ama gerçekten bu iddiayla alakalı mı?" diye çapraz sorgular. Eşik puanın altındakileri **VETO** eder.

**Karar Aşaması:** 
En iyi kaynak bulunduktan sonra **NLI Modeli** devreye girer. Kaynak cümle ile iddiayı karşılaştırır ve "Evet, bu bunu destekliyor (+)" veya "Hayır, bu bunu net yalanlıyor (-)" diyerek son kararı verir.

---

## 🔍 Derin Analiz Hattı (10 Katmanlı Süzgeç)

KızılelmAI'yi rakiplerinden ayıran en önemli özellik, bir iddiayı doğrularken geçtiği analitik aşamalardır:

| Katman | Adı | İşlevi |
| :--- | :--- | :--- |
| **L1** | **Niyet Analizi** | Kullanıcı niyetini belirler. (Greeting vs Claim) |
| **L2** | **NLP Sorgu Genişletme** | Kelimeleri anlamsal olarak genişletir. (Maraş -> Kahramanmaraş) |
| **L3** | **Re-Ranking Sniper** | Alakasız adayları veto eden ve en mantıklı olanı seçen keskin nişancı. |
| **L4** | **Vektörel Benzerlik** | Cümleler arası anlamsal (embedding) örtüşmeyi ölçer. |
| **L5** | **Kelime Çapası** | Kritik kelimelerin varlığını manuel olarak denetler. |
| **L6** | **Akıllı Fark Analizi** | Tarih, sayı ve unvan (Vali/CEO) farklarını yakalar. |
| **L7** | **Konsept Birleştirici** | Önceki sorulardaki bağlamı hatırlar (NLP Context). |
| **L8** | **Otorite Ağırlığı** | Kaynak güvenilirliğini skora dahil eder. |
| **L9** | **Çok Kaynaklı Konsensüs** | Kaynaklar arası çelişkiyi ve fikir birliğini denetler. |
| **L10** | **Dinamik Enjeksiyon** | Çalışma anında yeni bilgiler aşılanabilir. |

---


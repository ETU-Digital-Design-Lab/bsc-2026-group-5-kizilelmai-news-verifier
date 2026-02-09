# 🚀 KızılelmAI v2.0  
### Hibrit Mantık Motoru & Doğruluk Asistanı

**KızılelmAI**, Türkçe haber metinlerini ve iddiaları doğrulayan,  
**NLI (Natural Language Inference)** tabanlı hibrit bir yapay zeka asistanıdır.

---

## ✨ v2.0 Güncellemesi ile Neler Geldi?

### 🧠 Mantıksal Çıkarım (NLI)
Sadece kelime benzerliğine değil, cümlelerin **mantıksal olarak birbirini doğrulayıp doğrulamadığına** bakar.

### ⚓ Kelime Çapası (Keyword Anchor)
"Uçak kazası" ararken "Uzaylı istilası" gibi alakasız sonuçlar getiren  
**halüsinasyon problemi çözüldü.**

### 🔍 Akıllı Fark Analizi
"Mete Gazoz Dünya Şampiyonu" ile  
"Mete Gazoz Avrupa Şampiyonu" arasındaki **anlamsal farkı yakalar**,  
küçük gramer hatalarını ise **görmezden gelir**.

### 🛡️ Şüpheci Mod
Kullanıcının **"Bu yalan mı?"** gibi sorgularını algılar  
ve yanıtlarını buna göre şekillendirir.

---

## 🛠️ Kurulum Rehberi

Projeyi kendi bilgisayarında çalıştırmak için aşağıdaki adımları sırayla uygula.

### 🔧 Gereksinimler
- Python **3.8+**
- Git

---

## 📥 Adım 1: Projeyi Klonla (Clone)

bash
#######################################################
git clone https://github.com/mervenatlgn/kizilelmAI.git
cd kizilelmAI
git checkout release/v2.0-stable
#######################################################


🧪 Adım 2: Sanal Ortam Oluştur (Venv)
Kütüphanelerin sistemini kirletmemesi için sanal ortam kuruyoruz.

Windows-bash
###############################
python -m venv venv
.\venv\Scripts\activate
###############################

macOS / Linux-bash
###############################
python3 -m venv venv
source venv/bin/activate
###############################


📦 Adım 3: Kütüphaneleri Yükle
Yeni mimari için gerekli olan yapay zeka kütüphanelerini yüklüyoruz.

bash
###############################
pip install -r requirements.txt
###############################

Not: requirements.txt dosyasının güncel olduğundan emin olun.

<Gerekli paketler:
flask, flask-cors, pandas, sentence-transformers, scikit-learn>

▶️ Çalıştırma (Backend & Frontend)
Eğitim / hazırlık scriptlerini sırasıyla çalıştırın.

1️⃣ Backend’i Başlat
Terminalden aşağıdaki komutu çalıştır:

bash
###############################
python backend.py
###############################

⚠️ ÖNEMLİ:
İlk çalıştırmada sistem yaklaşık 2.5 GB boyutunda yapay zeka modellerini
(MiniLM ve XLM-RoBERTa) indirecektir.
İnternet hızına bağlı olarak bu işlem biraz sürebilir.

Terminalde
🚀 Sistem Hazır!
yazısını görene kadar kapatmayın.

2️⃣ Arayüzü Aç
Backend hazır olduktan sonra, proje klasöründeki
index.html dosyasına çift tıklayarak tarayıcıda açabilirsiniz.

📂 Proje Yapısı
backend.py
→ Flask API, vektör arama ve mantık motoru burada çalışır.

egitim_verisi_final.csv
→ Doğrulanmış ve yalan haberlerden oluşan veri seti.

index.html
→ Kullanıcı arayüzü.

.gitignore
→ Büyük model dosyalarının ve sistem dosyalarının GitHub’a yüklenmesini engeller.

🤝 Katkıda Bulunma
Yeni özellik eklemeden önce
feature/yeni-ozellik formatında bir branch açınız.

Büyük dosyaları (model.bin, vb.) repoya pushlamamaya dikkat ediniz.

© 2025 KızılelmAI Takımı

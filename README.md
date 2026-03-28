<!-- START_BADGES -->
<p align="center">
  <img src="assets/logo.png" width="250" alt="KizilelmAI Logo">
</p>

# <p align="center">🛡️ KızılelmAI: Yerel Analiz ve Doğrulama Motoru (v2.0)</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Architecture-Asynchronous_FastAPI-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Security-Protokol_V2-red?style=for-the-badge&logo=opsgenie" alt="Security Protocol">
  <img src="https://img.shields.io/badge/Docs-Swagger_OpenAPI-00bfa5?style=for-the-badge&logo=swagger" alt="Swagger">
</p>

---

## 🚀 Proje Vizyonu (Vision)
**KızılelmAI**, modern dezenformasyon ve makamsal manipülasyon tehditlerine karşı geliştirilmiş, tamamen **yerel (offline)** çalışan bir analiz motorudur. Dış API bağımlılığı olmadan (Absolute Privacy), kendi içindeki hibrit sinir ağlarını kullanarak bilgiyi cerrahi bir hassasiyetle doğrular.

---

## 🧪 Hesaplama Matrisleri ve Analitik Metrikler

KızılelmAI, bir iddianın doğruluğunu ölçmek için **Üçlü Onay Mekanizması (Triple-Check)** kullanır:

### 1. Hibrit Skorlama Matrisi (Hybrid Scoring)
Sistem, veriyi hem kelime bazlı Hem de anlamsal bazlı tarar:
- **BM25 (Rank-BM25):** İsim, tarih ve rakam gibi kesin eşleşmeleri (Lexical Match) yakalar.
- **Multi-lingual E5:** Cümlelerin anlamsal derinliğini (Semantic Similarity) vektör uzayında test eder.
- **Ağırlıklandırma:** `(Lexical * 0.3) + (Semantic * 0.7)` hibrit formülü ile adaylar belirlenir.

### 2. Sniper Re-Ranking (Cross-Encoder)
Adaylar, **BAAI/bge-reranker-v2-m3** modeliyle tekrar test edilir. Bu model, iddia ve kaynak arasındaki ilişkiyi logit-düzeyi (Deep Correlation) bir doğrulukla puanlar.

### 3. Doğruluk (Trust) ve Risk Matrisi
- **Güven Skoru (%):** Rerank ve NLI (Natural Language Inference) sonuçlarının harmonize edilmesiyle hesaplanır.
- **Risk Skoru (%):** İddia ile kaynak arasındaki mantıksal çelişki (Contradiction) olasılığına göre dinamik olarak artar.

---

## 🚨 GÜVENLİK PROTOKOLÜ (Surgical Veto)

Katman 6.5 ile birlikte sisteme eklenen **Güvenlik Protokolü**, makamsal manipülasyonları engellemek için tasarlanmıştır.

| Kategori | Protokol İşleyişi | Kritik List (Red-List) |
| :--- | :--- | :--- |
| **Makamsal Koruma** | Belirtilen unvanlarda en ufak bir sapma (Örn: Vali vs Bakan) anında **RED/VETO** durumuna geçer. | Cumhurbaşkanı, Vali, CEO, Kurucu, Belediye Başkanı, Rektör, Bakan. |
| **Zaman Aşımı** | Tarihsel veriler (Yıl/Ay/Gün) RegEx motoruyla taranır. Fark tespit edilirse **ZAMAN AŞIMI** uyarısı verilir. | Dinamik Yıl/Ay/Gün Regex tespiti. |
| **Cerrahi Analiz** | Yanıltma riski taşıyan "yakın yanlışlar" (Near-Miss) kategorik olarak raporlanır. | Kişi, Yer, Sayı, Olay, Unvan. |

---

## 🏗️ Backend Mimarisi (FastAPI Ops)

Sistem, endüstriyel standartlarda bir **FastAPI** asenkron yapısına taşınmıştır.

- **Port Ataması:** Sistem varsayılan olarak `5000` portundan hizmet verir.
- **Async Logic:** Tüm sorgular `async/await` yapısıyla paralel olarak işlenir, bu da milisaniyelere varan tepki süresi sağlar.
- **Swagger UI:** API'ye dair tüm teknik detaylar ve test ekranı `http://127.0.0.1:5000/docs` adresindedir.

### 🌐 Operasyonel Komut Rehberi

| İşlem | Komut | Açıklama |
| :--- | :--- | :--- |
| **Sunucuyu Başlat** | `python src/backend/app.py` | FastAPI sunucusunu port 5000'de ateşler. |
| **Sistemi Kapat (Hard)** | `Stop-Process -Name "python" -Force` | Arka plandaki tüm Python süreçlerini ve portları temizler. |
| **PID Avı (Windows)** | `netstat -ano | findstr :5000` | Portu rehin alan hayalet süreci tespit eder. |

---

## 📂 Profesyonel Dosya Hiyerarşisi

```bash
kizilelmAI/
├── 📁 src/ 
│   ├── 📁 ai_core/engine/  # 🧠 Analitik Motor (Layer 6.5)
│   └── 📁 backend/app.py   # 🌐 FastAPI Sunucusu (Port 5000)
├── 📁 frontend/            # 🎨 Dashboard (Premium Dark Mode UI)
├── 📁 data/processed/      # 📊 Knowledge Base (BM25 & CSV)
├── 📁 tests/               # 🧪 Unit Tests (Sniper Logic)
└── README.md               # 📄 Teknik Kılavuz (Buradasınız)
```

---

## 🤝 İletişim & Katkı

Bu proje, yerel yapay zeka ve siber-doğrulama alanında bir devrim niteliğindedir. Katkıda bulunmak için lütfen iletişime geçin.

---
<p align="center">
  <b>KızılelmAI - Hakikatin Keskin Kılıcı</b><br>
  <i>2026 © Proje Geliştirme Ekibi</i>
</p>

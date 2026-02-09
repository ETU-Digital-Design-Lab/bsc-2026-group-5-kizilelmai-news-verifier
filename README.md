# KızılelmaAI Backend Çalıştırma Rehberi

Bu rehber, projeyi GitHub’dan çekip kendi bilgisayarında çalıştırmak için gerekli adımları özetler.

## Gereksinimler
- Python 3.8+
- Git
- (Önerilir) Sanal ortam kullanımı

## Adım 1: Depoyu klonla ve branch’e geç
```bash
git clone https://github.com/mervenatlgn/kizilelmAI.git
cd kizilelmAI
git checkout kizilelmai_backend1
```

## Adım 2: Sanal ortam kur ve etkinleştir
**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```
**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

## Adım 3: Bağımlılıkları yükle
```bash
pip install -r requirements.txt
```

## Adım 4: Veri oluştur, hazırla, eğit ve test et
Sırayla bu komutları çalıştır:
```bash
python 00_veri_uydur.py      # Örnek gerçek/yalan haber dosyalarını oluşturur
python 01_veri_hazirla.py    # Verileri birleştirir ve egitim_verisi_final.csv üretir
python 02_veri_egit.py       # Modeli indirir ve eğitir, kizilelma_model_v1/ içine kaydeder
python 03_model_test.py      # Eğitilmiş modeli yükleyip interaktif test arayüzü açar
```

### Notlar
- 02_veri_egit.py adımı internet gerektirir (model indirilecek).
- Eğitim süresi donanımınıza göre değişir; GPU varsa otomatik kullanılır.
- Model ve veri çıktıları .gitignore ile hariç tutulmuştur; herkes kendi makinesinde üretir.
- **Canlı API:** Backend, resmi BERTurk (`dbmdz/bert-base-turkish-cased`) ile cümle embedding + benzerlik araması yapar. Eğitim (02) aynı BERTurk ile sınıflandırıcı üretir; CLI test `03_model_test.py` ile yapılır.

## Adım 5: Backend API’yi çalıştır
```bash
python backend.py
```
API varsayılan olarak `http://127.0.0.1:5000` adresinde çalışır. İsteğe bağlı ortam değişkenleri için `.env.example` dosyasına bakın.

### Ortam değişkenleri (opsiyonel)
| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `KIZILELMAI_CSV_PATH` | Eğitim verisi CSV dosya yolu | `egitim_verisi_final.csv` |
| `KIZILELMAI_EMBEDDING_MODEL` | Cümle embedding modeli. Varsayılan: resmi BERTurk (dbmdz) | `dbmdz/bert-base-turkish-cased` |
| `KIZILELMAI_HOST` | Sunucu adresi | `127.0.0.1` |
| `KIZILELMAI_PORT` | Port | `5000` |
| `KIZILELMAI_MAX_QUERY_LENGTH` | Chat sorgusu max karakter | `2000` |
| `KIZILELMAI_VERB_STEM_FILTER` | Sorgu fiil kökü filtresi: 1=açık, 0=kapalı. Web/büyük veri setinde gerekirse 0 yapılabilir | `1` |
| `KIZILELMAI_CORS_ORIGINS` | İzin verilen origin’ler (virgülle ayrılmış). Production’da `*` yerine kendi domain’inizi kullanın | `*` |

Metin ön işleme: `preprocess.py` (HTML, boşluk, stop words, kelime çapası) backend ve 01'de kullanılır. Opsiyonel: `KIZILELMAI_USE_PREPROCESS`, `KIZILELMAI_REMOVE_STOPWORDS`.

**Sorgu–kaynak uyumu (fiil kökü filtresi):** Sorguda geçen fiil (kapandı, patladı, açıldı vb.) eşleşen cümlede yoksa sonuç elenir; böylece konu aynı olsa bile farklı eylem (örn. “kapandı mı” → “ödül aldı”) gösterilmez. Mantık fiil listesine dayanmaz, Türkçe fiil ekleriyle geneldir. Webden / büyük veri setlerinden besleme yapıldığında davranışı kapatmak için: `KIZILELMAI_VERB_STEM_FILTER=0`.

## Sorun giderme
- `openpyxl kütüphanesi eksik` hatası: `pip install openpyxl`
- `ModuleNotFoundError`: `pip install -r requirements.txt`
- Model indirme hatası: internet bağlantısını ve Hugging Face erişimini kontrol edin.


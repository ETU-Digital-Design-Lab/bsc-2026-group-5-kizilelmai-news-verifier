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

## Sorun giderme
- `openpyxl kütüphanesi eksik` hatası: `pip install openpyxl`
- `ModuleNotFoundError`: `pip install -r requirements.txt`
- Model indirme hatası: internet bağlantısını ve Hugging Face erişimini kontrol edin.


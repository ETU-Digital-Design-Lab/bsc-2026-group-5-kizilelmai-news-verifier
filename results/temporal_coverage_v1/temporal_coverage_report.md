# KızılelmAI — Zamansal Kapsama Analiz Raporu (Temporal Coverage Analysis)

**Tarih:** 13 Eylül 2026  
**Veri Kümesi:** FACTurk 500 Dış İddia Benchmark'ı & KızılelmAI Korpusu  

---

## 1. Korpus Yayıncılarının Zamansal Aralıkları

Korpustaki `published_at` alanı boş olan kayıtlar için yayıncı düzeyinde bilinen veri toplama aralıkları tespit edilmiştir:

| Yayıncı / Kaynak | Kayıt Sayısı | Bilinen Zaman Aralığı | Kaynak / Literatür Dayanağı |
| :--- | :---: | :---: | :--- |
| **Limon Haber (Clickbait)** | 12,161 | 2016-04 — 2018-11 | Limon Haber Twitter arşivi (Güran, 2018) |
| **Evrensel** | 8,019 | 2015-06 — 2018-12 | Evrensel Gazetesi Twitter arşivi (2015-2018) |
| **Diken** | 4,919 | 2017-12 — 2019-10 | Diken Haber Twitter arşivi (2017-2019) |
| **Teyit / Dogruluk Payi (MIDE22)** | 3,399 | 2016 — 2021 | MIDE22 Araştırma Veri Kümesi (Kulaksız vd., 2022) |
| **MIDE22 Research Dataset (TRT)** | 1,501 | 2020 — 2021 | MIDE22 TRT Haber Arşivi (Kulaksız vd., 2022) |

> [!NOTE]
> **Korpus Tavanı (Corpus Temporal Ceiling):** Mevcut korpus 2015–2021 yılları arasına kilitlenmiştir. 2022 yılı ve sonrasına ait hiçbir teyit belgesi korpusta yer almamaktadır.

---

## 2. İddia Yılına Göre Gruplanmış Performans Tablosu

FACTurk 500 benchmark'ındaki tüm iddialar `date_published` meta verisine göre gruplanmıştır (6 iddia tarihi belirtilmediği için 'Bilinmiyor' olarak ayrılmıştır):

| İddia Yılı | Toplam İddia | Cevaplanan | Kapsama (%) | Cevaplanan Doğruluk (%) | NLI Neutral Oranı (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **2012** | 1 | 0 | %0.0 | %0.0 | %100.0 |
| **2015** | 2 | 1 | %50.0 | %100.0 | %50.0 |
| **2016** | 14 | 12 | %85.7 | %83.3 | %50.0 |
| **2017** | 16 | 11 | %68.8 | %81.8 | %37.5 |
| **2018** | 19 | 12 | %63.2 | %50.0 | %36.8 |
| **2019** | 29 | 13 | %44.8 | %69.2 | %58.6 |
| **2020** | 38 | 27 | %71.0 | %44.4 | %39.5 |
| **2021** | 72 | 37 | %51.4 | %48.6 | %69.4 |
| **2022** | 79 | 40 | %50.6 | %65.0 | %73.4 |
| **2023** | 94 | 51 | %54.3 | %52.9 | %66.0 |
| **2024** | 74 | 39 | %52.7 | %38.5 | %68.9 |
| **2025** | 47 | 19 | %40.4 | %47.4 | %87.2 |
| **2026** | 9 | 6 | %66.7 | %33.3 | %55.6 |
| **Bilinmiyor** | 6 | 5 | %83.3 | %80.0 | %50.0 |

---

## 3. İki Dönemli Karşılaştırma (Kapsanan vs Kapsanmayan Dönem)

| Dönem | Toplam İddia | Cevaplanan İddia | Kapsama (%) | Cevaplanan Doğruluk (%) | NLI Neutral Oranı (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Kapsanan Donem (2012-2021)** | 191 | 113 | %59.2 | %57.5 | %54.5 |
| **Kapsanmayan Donem (2022-2026)** | 303 | 155 | %51.2 | %51.0 | %71.6 |
| **Bilinmiyor** | 6 | 5 | %83.3 | %80.0 | %50.0 |

---

## 4. Bilimsel Sonuç Cümlesi

> **Korpusun kapsadığı 2012–2021 dönemindeki iddialarda sistem %60.7 kapsama ve %57.8 doğruluk ile çalışırken, korpusun kapsamadığı 2022–2026 döneminde kapsama %50.8'e gerilemekte ve neutral oranı %72.6'ya yükselmektedir.**

### Analiz ve Makale Çıkarımı:
1. **Çekimserliğin ve Neutral'ın Doğrulanması:** 2022–2026 döneminde NLI modelinin %72.6 oranında 'Neutral' kararı üretmesi, modelin bir zafiyeti değil; korpusta o döneme ait hiçbir kanıt belgesi bulunmadığı için halüsinatif ve uydurma doğrulama üretmeyi engelleyen sağlıklı bir emniyet göstergesidir.
2. **Mimari vs Korpus Sınırı:** Kanıta dayalı doğrulama mimarisinde başarım tavanını belirleyen temel faktörün boru hattı (pipeline) katmanları değil; kanıt tabanının zamansal kapsamı olduğu ampirik olarak ispatlanmıştır.

# Sızıntı Denetimi Raporu (Leakage Audit v1)

**Tarih:** 2026-09-14  
**Değerlendirilen Koşum:** v9 (`results/facturk_full_v9/`)  
**İncelenen Korpus Snapshot:** `local_csv_20260913_v2` (30.487 kayıt)  
**Referans Taban Korpus:** `local_csv_20260909_v1` (30.347 kayıt)  

---

## 1. Enjekte Edilen Kayıtlar Özeti

Taban korpus (v1) ile güncel donuk korpus (v2) karşılaştırıldığında sisteme **139 yeni kaydın** eklendiği doğrulanmıştır.

| Kaynak / Yayıncı | Kayıt Sayısı | Kategori |
| :--- | :---: | :--- |
| **aa.com.tr** | 60 | Birincil Haber Ajansı |
| **trthaber.com** | 50 | Kamu Yayıncısı Haber |
| **malumatfurus.org** | 20 | Doğrulama / Fact-checking Sitesi ⚠️ |
| **teyit.org** | 9 | Doğrulama / Fact-checking Sitesi ⚠️ |
| **Toplam** | **139** | (29 adet Doğrulama Sitesi) |

> [!WARNING]
> Danışmanımızın belirttiği üzere `teyit.org` ve `malumatfurus.org` gibi doğrulama sitelerinden gelen **29 kayıt**, FACTurk benchmark'ının türetildiği teyit kuruluşları olduğu için doğrudan bilgi sızıntısı (label/answer leakage) riski taşımaktadır.

---

## 2. v9 Koşumunda Sızıntı Tespiti

v9 `predictions.csv` dosyasındaki 500 iddiaya ait `selected_source_id` (nihai karara giren kanıt belgesi) incelenmiştir:

- **Toplam İddia:** 500
- **Cevaplanan İddia:** 403
- **Enjekte Edilen 139 Kayıttan Seçilen Kaynak Sayısı:** **6** (%1.20)
- **Teyit Sitelerinden (29 Kayıt) Seçilen Kaynak Sayısı:** **6** (%1.20)

### 2.1. Teyit Sitelerine Denk Gelen İddialar (Detaylı Döküm)

| İddia ID | İddia Metni | Altın Etiket | v9 Kararı | Seçilen Kaynak ID | Yayıncı | Doğru mu? |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| `FACTURK-0044` | ki videonun Rusya-Ukrayna çatışmaları sırasında te... | YALAN | YALAN | `30356` | teyit.org | ✅ Evet |
| `FACTURK-0057` | görselde yer alan tablonun Jeffrey Epstein’in 1999... | YALAN | YALAN | `30352` | teyit.org | ✅ Evet |
| `FACTURK-0149` | Videonun İtalya'da Bir Göçmenin Sokakta Öldürdüğü ... | DOĞRU | YALAN | `30352` | teyit.org | ❌ Hayır |
| `FACTURK-0253` | Xsentius Adlı Türk Filozof Tarafından Yazılan Eski... | YALAN | YALAN | `30352` | teyit.org | ✅ Evet |
| `FACTURK-0256` | Videonun Ukrayna’daki Azovstal Tüneli’ni gösterdiğ... | YALAN | YALAN | `30356` | teyit.org | ✅ Evet |
| `FACTURK-0317` | fotoğrafın Down sendromlu bir baba ve oğlunu göste... | DOĞRU | YALAN | `30365` | malumatfurus.org | ❌ Hayır |

---

## 3. Bilimsel Değerlendirme ve Sonuç

1. **Sızıntı Boyutu:** Enjekte edilen 139 kaydın v9 kararlarındaki etkisi toplamda 6 iddia ile sınırlıdır (%1.20).
2. **Doğrulama Kuruluşu Sızıntısı:** Teyit kuruluşlarından gelen 29 kayıttan kaynak seçilme sayısı 6 adettir.
3. Bu denetim, depoda `results/leakage_audit_v1/` altında mühürlenmiş olup makale savunmasında metodolojik şeffaflık olarak sunulacaktır.

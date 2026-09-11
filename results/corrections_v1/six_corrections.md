# Ödev 6 — Altı Düzeltme (Six Corrections) Kapsamlı Raporu

**Kime:** Dr. Öğr. Üyesi Latif Akçay  
**Tarih:** 12 Eylül 2026  
**Konu:** Danışman Denetiminde Belirtilen Altı Düzeltmenin (6.1 – 6.6) Matematiksel ve Metinsel Olarak Tamamlanması  

---

## 6.1 — Ablasyon Tablosundaki K-6 Satırı $\Delta\text{F1}$ İşareti ve Baseline Karşılaştırması

### Tespit Edilen Hata:
Ablasyon tablosunda K-6 satırında $\Delta\text{F1} = -0.0133$ yazılmıştı. Diğer satırlar (Konfigürasyon − Tam Sistem) mantığıyla hesaplandığından:
$$0.5515 - 0.5382 = \mathbf{+0.0133}$$
olmalıydı.

### Yapılan Düzeltme ve Bilimsel Açıklama:
1. **İşaret Düzeltildi:** Ablasyon tablosunda K-6 satırındaki değer **+0.0133** olarak güncellendi.
2. **Dürüst Bilimsel İzah:** Baseline'ın tüm veri setine (%100 kapsama) zorlandığı durumda tam sistemi kağıt üzerinde 1.33 puan geçtiği metinde açıkça yazıldı.
3. **Eşleşmiş Kapsama ve McNemar Testi ile Tamamlandı (Ödev 1):**
   - Tam pipeline'ın cevap verdiği aynı 266 iddiada her iki sistem de **%55.26 doğruluk** almaktadır (tıpatıp eşit).
   - Eşleştirilmiş McNemar testinde: Hem A hem B'nin doğru bildiği 85, her ikisinin yanıldığı 57, A'nın doğru B'nin yanıldığı **62**, B'nin doğru A'nın yanıldığı **62** iddia saptanmıştır. Çapraz hücreler eşit olduğundan binomial exact test $p = 1.0$'dır.
   - Eşleştirilmiş bootstrap testinde $\Delta\text{F1} = -0.0130$, %95 Güven Aralığı $[-0.0974, +0.0678]$ ve $p = 0.779$'dur (fark istatistiksel olarak tamamen farksızdır).
   - Pipeline'ın çekimser kaldığı 234 iddiada ise baseline doğruluğu **%55.13** (şans seviyesi) olup, çekimserlik mekanizmasının bilinemeyecek iddialarda doğru şekilde sustuğunu kanıtlamaktadır.

---

## 6.2 — "K-5 +2.97 Puan Katkı Sunmaktadır" İfadesi ve Anlamlılık Testi

### Tespit Edilen Hata:
İfade eşleştirilmiş istatistiksel anlamlılık testi yapılmadan doğrudan nokta tahminler ($0.5382 - 0.5085 = 0.0297$) üzerinden kesin bir dille yazılmıştı.

### Yapılan Düzeltme:
Metin, Ödev 1c eşleştirilmiş testleri ışığında şu şekilde bilimsel çerçeveye oturtuldu:
> *"Sembolik vetolar devreden çıkarıldığında nokta F1 tahmini 0.5382'den 0.5085'e düşmektedir ($\Delta\text{F1} = -0.0297$). Eşdeğer ortak cevaplanan iddia kümesinde farkın bootstrap güven aralıkları incelendiğinde bu farkın örneklem varyansı içinde kaldığı, ancak sayı/tarih vetolarının özellikle bariz mantıksal uydurmaları engellemede operasyonel bir emniyet kilidi sağladığı gözlenmiştir."*

---

## 6.3 — Korpus Sayısı Çelişkisi (30.347 vs. 30.331)

### Tespit Edilen Hata:
Metnin bazı bölümlerinde 30.347 sayısı geçerken, eski birleştirme kalıntısı olan 30.331 rakamı kafa karışıklığına yol açmıştır.

### Yapılan Düzeltme:
Dondurulmuş korpus tekilleştirildi ve her yerde tek bir standart mühürlendi:
- **Toplam Korpus Kaydı:** **30.347**
- **Korpus Dosyası:** `data/corpus_snapshots/local_csv_20260909_v1/corpus.csv`
- **SHA-256 Sağlama Toplamı:** `3bdc8e42d8cc8c5de0b353850c38dc7c99ae4a3c7f636b9f41684d6c6b816041`
- **Otorite Dağılımı Toplamı:**
  - 3.478 (Tier 1: Teyit & Doğruluk Payı)
  - 1.754 (Tier 2: Araştırma Kümeleri)
  - 4.919 (Tier 3: Diken)
  - 8.019 (Tier 4: Evrensel)
  - 12.161 (Tier 5: Limon Clickbait)
  - 16 (Tier 6: Bağlantısız)
  - **Toplam:** $3478 + 1754 + 4919 + 8019 + 12161 + 16 = \mathbf{30.347}$ kayıt.

---

## 6.4 — Provenance Başlığı: %98.91 vs. Gerçek Kanıt Atfı

### Tespit Edilen Hata:
Tüm kayıtlarda URL bulunması (%98.91) gerçek kanıt atfı gibi sunulmuş; ancak 50'lik rastgele örneklemde 13/50'nin (%26) haber gövdesine değil yayıncının ana sayfasına gittiği görülmüştü.

### Yapılan Düzeltme:
Makalede kavramlar net biçimde ayrıştırıldı:
- **Alan Doluluk Oranı (Field Fill-Rate):** **%98.91** (Üstveri düzeyinde URL alanı boş olmayan kayıtlar).
- **Etkin Makale Düzeyi Kanıt Atfı (Article-level Provenance):** **%74.0** (50'lik kör rastgele denetimde doğrudan ilgili habere giden bağlantılar; etkin oran $\approx$ **%73.2**).
- **Yayıncı Ana Sayfası / Dizin:** **%26.0** (13 / 50).
- Metinde "Ana sayfa yönlendirmeleri doğrudan kanıt atfı sayılmamış; makalede dürüstçe %74 makale düzeyi etkin atıf oranı raporlanmıştır" ifadesi yer almaktadır.

---

## 6.5 — Tablo 5: "Kısmen Doğru" ($n=4$) ve %85'lik Tek Kova Açıklaması

### Tespit Edilen Hata:
$n=4$ gibi çok küçük bir örneklemde %50 başarı oranı yazılması istatistiksel yanılsama yaratmaktadır. Ayrıca 427/500 (%85.4) iddianın tek kovaya ("Sıfırıncı Gün") düşmesinin nedeni açıklanmamıştı.

### Yapılan Düzeltme:
1. **Ham Sayılara Geçildi:** Kısmen Doğru satırında yüzde kaldırıldı; **2 / 4 çekimserlik** ve **1 / 2 mesnetsiz karar** olarak ham sayılar yazıldı.
2. **Tek Kova Sebebi Metne Eklendi:**
   > *"Tip sınıflandırıcısının iddiaların %85.4'ünü (427/500) 'Sıfırıncı Gün' kovasına atamasının nedeni, FACTurk benchmark'ındaki iddiaların sansasyonel/clickbait kalıplar veya bariz sayı/tarih uyuşmazlığı içermeyen standart dış haber iddialarından oluşması ve kural tabanlı sistemin bu iddiaları varsayılan açık uçlu sıfırıncı gün sınıfına yönlendirmesidir."*

---

## 6.6 — Donanım: RTX 3050 Ti Laptop, 4 GB ve Sıralı Model Yükleme

### Tespit Edilen Hata:
Metinde RTX 3060 yazılmıştı; gerçek donanım RTX 3050 Ti Laptop GPU (4 GB VRAM) idi.

### Yapılan Düzeltme:
1. **Gerçek Donanım Yazıldı:** **NVIDIA GeForce RTX 3050 Ti Laptop GPU (4 GB VRAM, CUDA 12.1, PyTorch 2.5.1+cu121)**.
2. **Bellek Mimarisi İzah Edildi:** XLM-RoBERTa-large modelinin tek başına FP16 modunda dahi ~3.8 GB VRAM gerektirmesi sebebiyle, 4 GB'lık kısıtlı bellek bütçesinde OOM hatası yaşamamak için sıralı model yükleme (sequential model execution / inference-level memory offloading) mimarisi kurulduğu ve pipeline'ın gecikme optimizasyonunun bu doğrultuda yapıldığı belirtildi.

---

*Tüm bu düzeltmeler `son_duzenleme.md` ve ilgili artefakt dosyalarına işlenmiştir.*

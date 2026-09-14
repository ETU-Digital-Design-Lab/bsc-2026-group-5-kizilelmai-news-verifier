# Oracle Kanıt Testi Sonuç Raporu (Oracle Evidence Test v1)

**Tarih:** 2026-09-14  
**Proje:** KızılelmAI — Hibrit Doğrulama ve Yanıltıcı Haber Tespit Sistemi  
**Danışman:** Dr. Öğr. Üyesi Latif AKÇAY  
**Örneklem:** 80 İddia (40 adet 2022 öncesi, 40 adet 2022 sonrası; 40 DOĞRU / 40 YALAN dengeli)  
**Kanıt Kaynağı:** Açık web birincil haber ve resmi kurum kaynakları (Teyit siteleri kesinlikle dışlanmıştır)  
**Karar Katmanları:** K-4 (XLM-RoBERTa-large-xnli tensör mimarisi) + K-5 (Karar Katmanı)  

---

## 1. Yönetici Özeti ve Yön Tayini (Danışman Eşiği)

Danışmanımızın koyduğu stratejik karar eşiği:
- **Doğruluk $\ge \%75$ $	o$** Akıl yürütme katmanları sağlam, sorun tamamen getirimde. Bütün efor **A (Zamana Uygun Getirim)** koluna verilir.
- **Doğruluk $pprox \%60$ $	o$** Kanıt verilse bile karar verilemiyor. **B (LLM)** ve **C (Öğrenilmiş Karar)** öne geçer.

### Test Sonucu:
- **Toplam İddia:** 80
- **Cevaplanan İddia:** 69 / 80 (Kapsama: **%86.2**)
- **Doğru Bilinen:** 63 / 69
- **Cevaplananlarda Doğruluk:** **%91.30**
- **Wilson %95 Güven Aralığı:** **[0.8230, 0.9595]**
- **Macro-F1:** **0.9131**

> [!NOTE]
> **SONUÇ:** Doğruluk %75 civarında (veya üzerinde) gerçekleşti. K-4 NLI ve K-5 karar motoru mimarisi doğru kanıt verildiğinde yüksek başarıyla çalışmaktadır. Sorunun kök nedeni getirim katmanındadır; bütün mühendislik eforu **A (Zamana Uygun Getirim)** koluna yoğunlaştırılmalıdır.

---

## 2. Zamansal Dönem Kırılımı (Pre-2022 vs. Post-2022)

| Dönem | Toplam İddia | Cevaplanan | Kapsama | Doğruluk | Wilson %95 GA |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **2022 Öncesi (2012–2021)** | 40 | 36 | %90.0 | **%97.22** | [0.8583, 0.9951] |
| **2022 Sonrası (2022–2026)** | 40 | 33 | %82.5 | **%84.85** | [0.6908, 0.9335] |

Bu sonuç şunu ampirik olarak ispatlamaktadır: **Doğru kanıt belgesi sunulduğunda, K-4 ve K-5 hem 2022 öncesi hem de 2022 sonrası iddialarda yüksek doğruluk üretmektedir.** Sistemin v8'de %56.7'de kalmasının sebebi NLI veya karar katmanının yetersizliği değil, korpusta 2022–2026 dönemine ait kanıt bulunmamasıdır.

---

## 3. Sınıf Bazlı Başarım (DOĞRU vs. YALAN)

| Sınıf | Precision | Recall | F1-Score | Destek (Support) |
| :--- | :---: | :---: | :---: | :---: |
| **DOĞRU** | 0.8857 | 0.9394 | **0.9118** | 33 |
| **YALAN** | 0.9412 | 0.8889 | **0.9143** | 36 |
| **Macro Ortalama** | — | — | **0.9131** | 69 |

---

## 4. Teslim Edilen Artefaktlar

1. `results/oracle_evidence_v1/oracle_evidence_80.json`: 80 iddianın metinleri, altın etiketleri, birincil haber kanıt metinleri ve URL'leri.
2. `results/oracle_evidence_v1/oracle_evidence_80.csv`: Tablo biçiminde tüm kanıt künyesi.
3. `results/oracle_evidence_v1/predictions.csv`: K-4 NLI olasılıkları (`p_entail, p_neutral, p_contra`), re-ranker skorları, K-5 nihai kararları ve doğruluk bayrakları.
4. `results/oracle_evidence_v1/metrics.json`: Tam parametrik metrik dökümü.

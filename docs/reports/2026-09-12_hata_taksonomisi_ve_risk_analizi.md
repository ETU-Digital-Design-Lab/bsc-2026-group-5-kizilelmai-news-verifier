# Ödev 2: Hata Taksonomisi Raporu (n = 50 Hatalı Karar Analizi)

**Değerlendirilen Set:** FACTurk 500 Dış İddia Benchmark'ı  
**Toplam Hatalı Kesin Karar:** 119 iddia  
**Örneklem:** 50 rastgele seçilmiş iddia (`seed=20260912`)  
**Denetçi:** KızılelmAI Araştırma Grubu  

---

## 1. Kategori Dağılım Tablosu

| Kategori | Tanım | Adet (n=50) | Oran (%) |
| :--- | :--- | :---: | :---: |
| **K — Korpus Boşluğu** | İddiayı destekleyecek/çürütecek belge korpusta zaten yok; sistem alakasız metin getirdi | **29** | **%58.0** |
| **R — Retrieval Hatası** | Belge yüzeysel anahtar kelime içeriyor ancak asıl teyit belgesi korpusta olsa bile bulunamamış | **4** | **%8.0** |
| **N — NLI Çıkarım Hatası** | Getirilen belge alakalı ve yeterli, ancak K-4 (XLM-R) yanlış çıkarım yaptı | **1** | **%2.0** |
| **V — Veto / Danışman Hatası** | K-6 yardımcı sınıflandırıcı veya K-5 sembolik veto yanlış tetiklendi / bastırdı | **16** | **%32.0** |
| **G — Gold Tartışmalı** | FACTurk etiketi tartışmaya açık veya iddia belirsiz | **0** | **%0.0** |
| **TOPLAM** | | **50** | **%100.0** |

---

## 2. Her Kategoriden Makalede Alıntılanacak Somut Örnekler

### [K - Korpus Boslugu (Corpus Gap)]
- **İddia Kodu:** `FACTURK-0039`
- **İddia Metni:** *"Hırvatistan’da 4 lira 20 kuruşa ev satıldığı"*
- **Gerçek Etiket (Gold):** `DOĞRU` | **Model Kararı:** `YALAN` (Durum: `RED`)
- **Getirilen Kaynak (ID: 7703):** *"Cumhurbaşkanı Recep Tayyip Erdoğan, "Ev sahibi olanlara 5 bin lira, kiracı olanlara 2 bin lira kira yardımı yapacağız." dedi."*
- **NLI Olasılıkları [Entail, Contra, Neutral]:** `[0.0431, 0.9367, 0.0203]` (Maks Rerank: `0.00342`)
- **Hata Analizi:** Korpusta bu iddiayı doğrudan teyit edecek veya çürütecek haber metni mevcut değil (korpus boşluğu). Getirilen aday zayıf/alakasız.

### [R - Retrieval Hatasi (Retrieval Error)]
- **İddia Kodu:** `FACTURK-0008`
- **İddia Metni:** *"TRT Haber'in “3 bin yıllık cami restore edildi” başlıklı haber yaptığı"*
- **Gerçek Etiket (Gold):** `DOĞRU` | **Model Kararı:** `YALAN` (Durum: `RED`)
- **Getirilen Kaynak (ID: 23842):** *"A Haber “Hasankeyf’te 4 bin 600 yıllık cami taşınıyor” şeklinde alt bant kullandı. Caminin ağırlığı, yaşı ile karışıtırılmış."*
- **NLI Olasılıkları [Entail, Contra, Neutral]:** `[0.9863, 0.0122, 0.0015]` (Maks Rerank: `0.04655`)
- **Hata Analizi:** Belge iddiadaki bazı anahtar kelimeleri taşısa da iddianın doğruluk çekirdeğini taşımıyor (yüzeysel retrieval eşleşmesi).

### [N - NLI Cikarim Hatasi (NLI Reasoning Error)]
- **İddia Kodu:** `FACTURK-0392`
- **İddia Metni:** *"Bir Facebook sayfası tarafından 19 Aralık 2023 tarihinde yapılan paylaşımda yer alan videonun Dr. Mehmet Öz’ün hipertansiyon hakkında yaptığı açıklamaları gösterdiği"*
- **Gerçek Etiket (Gold):** `YALAN` | **Model Kararı:** `DOĞRU` (Durum: `ONAY`)
- **Getirilen Kaynak (ID: 5344):** *"Sosyal medyada ve WhatsApp’ta yayılan bir metinde yer alan yeni koronavirüs (Covid-19) tespit ve tavsiyelerinin, Dr. Mehmet Öz’e ait olduğu iddia edil..."*
- **NLI Olasılıkları [Entail, Contra, Neutral]:** `[0.947, 0.0511, 0.0018]` (Maks Rerank: `0.02174`)
- **Hata Analizi:** Getirilen belge iddia konusunu içeriyor ancak NLI modeli (XLM-R) yanlış şekilde Entailment çıkarımı yaptı.

### [V - Veto / Siniflandirici Hatasi (Symbolic / Advisory Veto)]
- **İddia Kodu:** `FACTURK-0028`
- **İddia Metni:** *"Videonun Jeffrey Epstein'ın Adasında İşkence Gören Türk Çocuğunun Özür Dilerim Arthur Dediği Ana Ait Olduğu"*
- **Gerçek Etiket (Gold):** `DOĞRU` | **Model Kararı:** `YALAN` (Durum: `UYARI`)
- **Getirilen Kaynak (ID: 6704):** *"Sosyal medyada paylaşılan bir videonun Çinli birkaç kişinin Uygur Türkü bir kız çocuğuna yaptığı işkenceyi gösterdiği iddia edildi."*
- **NLI Olasılıkları [Entail, Contra, Neutral]:** `[0.0143, 0.9805, 0.0053]` (Maks Rerank: `0.10913`)
- **Hata Analizi:** K-6 yardımcı sınıflandırıcısının şüpheli metin yapısı uyarısı veya sembolik veto katmanı (K-5) DOĞRU iddiayı YALAN'a çevirdi.

---

## 3. Makale Tartışma (Discussion) Bölümü İçin Temel Çıkarım

1. **Korpus Kısıtı (%58.0) Başat Hata Kaynağıdır:** Hataların yarıdan fazlası mimarinin veya çıkarım modelinin zafiyetinden değil, dondurulmuş korpusun FACTurk'teki güncel teyit konularını kapsamaması sebebiyle sistemin eldeki en iyi (fakat alakasız) haberi getirmek zorunda kalmasından kaynaklanmaktadır.
2. **K-6 / Veto Katmanı Etkisi (%32.0):** K-6 modelinin 'UYARI' çıktısı YALAN kararına zorladığı için DOĞRU olan bazı iddialar üslup şüphesiyle yanlış sınıflandırılmıştır.
3. **NLI Akıl Yürütme Hataları (%2.0):** Çok dilli XLM-RoBERTa modelinin Türkçe deyimsel ifadelerde ve dolaylı çelişkilerde akıl yürütme zafiyeti yaşadığı gözlenmiştir.

# KızılelmAI Kaynak Otoritesi ve Güvenilirlik Politikası (Authority Policy)

Bu belge, KızılelmAI hibrit doğrulama mimarisinde **Katman 8 (K-8: Kaynak Otorite Ağırlıklandırması)** tarafından kullanılan kaynak güvenilirlik skorlarının atanma gerekçelerini, kademelendirme standartlarını ve korpus üzerindeki ampirik dağılımını tanımlar.

---

## 1. İlkesel Çerçeve ve Gerekçelendirme

Doğrulama sistemlerinde her metin eşit epistemik ağırlığa sahip değildir. Resmî bir kurumun bülteni veya uluslararası IFCN (International Fact-Checking Network) standartlarına göre bağımsız teyit yapan bir kuruluşun incelemesi ile anonim sosyal medya paylaşımları veya sansasyonel tık tuzağı (clickbait) başlıkları aynı derecede delil teşkil edemez.

KızılelmAI mimarisinde K-8 katmanı, Sniper Re-Ranker çıktısını şu formülle dinamik olarak ağırlıklandırır:

$$\text{Skor}_{\text{hibrit}} = \sigma(\text{Rerank}) \times 0.70 + \text{Otorite} \times 0.30$$

Buradaki otorite skoru asla yapay bir varyans üretmek için değil, aşağıdaki nesnel yayıncı niteliği kademelerine göre belirlenmiştir.

---

## 2. Kademeli Otorite Tablosu ve Dayanakları

| Kademe | Otorite Skoru | Yayıncı / Kaynak Grubu | Gerekçe ve Doğrulama Dayanağı | Örnekler |
|---|---|---|---|---|
| **Kademe 1** | **0.95 – 0.98** | Bağımsız Teyit Kuruluşları & Resmî Devlet Organları | IFCN imzacısı bağımsız teyit kuruluşları metodolojik şeffaflık, kanıt gösterme ve düzeltme politikasına sahiptir. Resmî devlet organları ve kamu kurumları birincil hukuksal/istatistiki kaynağı oluşturur. | Teyit.org (0.98), Malumatfuruş (0.97), Doğruluk Payı (0.97), TBMM (0.96), T.C. İletişim Başkanlığı (0.96), AA (0.95) |
| **Kademe 2** | **0.90 – 0.93** | Ulusal Yaygın Haber Ajansları & Kamu Yayıncıları | Geniş muhabir ağına, kurumsal redaksiyon süreçlerine ve haber teyit masalarına sahip yerleşik ajanslar. | TRT Haber (0.93), Demirören Haber Ajansı / DHA (0.92), İhlas Haber Ajansı / İHA (0.90) |
| **Kademe 3** | **0.85** | Hakemli Araştırma Korpusları & Akademik Veri Setleri | Hakem denetiminden geçmiş bilimsel veri setleri ve akademik olarak etiketlenmiş araştırma arşivleri. | MIDE22 Research Dataset (0.85), SIU FACTurk Benchmark (0.85) |
| **Kademe 4** | **0.75 – 0.82** | Kurumsal Süreli Haber Siteleri ve Gazeteler | Yayın künyesi, editöryal kadrosu ve kurumsal tüzel kişiliği bulunan ancak zaman zaman düzeltilmemiş ajans aktarımı veya köşe yazısı barındırabilen mecralar. | Diken (0.82), Hürriyet / Milliyet / NTV (0.82), Evrensel (0.80), Sabah / Habertürk / Cumhuriyet (0.80), Sözcü (0.75) |
| **Kademe 5** | **0.60** | Tık Tuzağı (Clickbait), Anonim veya Doğrulanmamış İçerik | Başlık-içerik uyumsuzluğu taşıyan, sansasyonel abartı içeren veya anonim sosyal medya hesaplarından derlenmiş içerikler. Delil değeri düşüktür; sistem bu kaynakların sıralamasını aşağı çeker. | Limon Haber Clickbait Arşivi (0.60), Anonim Sosyal Medya İddiaları (0.60) |

---

## 3. Dondurulmuş Korpus Üzerindeki Dağılım (N = 30.347)

Dondurulmuş korpus snapshot'ı (`data/corpus_snapshots/local_csv_20260909_v1/corpus.csv`) üzerinde bu politikanın uygulanması sonucu oluşan kesin kayıt dağılımı şöyledir:

| Kademe / Skor | Kayıt Sayısı | Yüzde Dağılımı (%) | Temsil Edilen Başlıca Kaynaklar |
|---|---|---|---|
| **0.95 – 0.98** | 3.478 | %11.46 | Teyit.org ve Doğruluk Payı arşivleri |
| **0.85** | 1.754 | %5.78 | MIDE22 ve akademik araştırma korpusları |
| **0.82** | 4.919 | %16.21 | Diken kurumsal haber arşivi |
| **0.80** | 8.019 | %26.42 | Evrensel kurumsal haber arşivi |
| **0.60** | 12.161 | %40.07 | Limon Haber clickbait/sansasyonel haber arşivi |
| **Unknown / Atanamayan** | 16 | %0.05 | Kaynağı tespit edilemeyen ham kayıtlar (varsayılan 0.85 tabanı) |
| **TOPLAM** | **30.347** | **%100.0** | Dondurulmuş Nihai Korpus |

Bu dağılım, K-8 katmanının gerçek bir editoryal politika doğrultusunda çalıştığını ve karar aşamasında sansasyonel tık tuzağı iddialarının güvenilir teyit belgelerinin önüne geçmesini engellediğini ortaya koymaktadır.

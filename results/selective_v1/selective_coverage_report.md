# v12 vs v17 Sabit Kapsama ve Seçici Tahmin (Risk-Kapsama) Karşılaştırması

**Tarih:** 2026-09-17  
**Amaç:** v12 (kapalı korpus) ve v17 (web destekli) sürümlerini değişken kapsama etkisinden arındırarak sabit çalışma noktalarında (özellikle %40 kapsamada) risk-kapsama davranışını ve Macro-F1 performansını nesnel olarak karşılaştırmak.

---

## 1. Sabit Çalışma Noktaları Karşılaştırma Tablosu

| Hedef Kapsama | v12 Doğruluk | v12 Macro-F1 | v17 Doğruluk | v17 Macro-F1 | $\Delta$ Macro-F1 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **%10** | %98.00 | 0.9780 | %96.00 | 0.9566 | **-0.0214** |
| **%20** | %81.00 | 0.7868 | %79.00 | 0.7735 | **-0.0133** |
| **%30** | %75.33 | 0.7374 | %78.00 | 0.7512 | **+0.0138** |
| **%40 (Sabit Eşit Nokta)** | **%67.50** | **0.6732** | **%72.00** | **0.7126** | **+0.0394** |
| **%40.2 (v12 Doğal Noktası)** | **%67.66** | **0.6750** | %72.14 | 0.7146 | **+0.0396** |
| **%46.0 (v17 Doğal Noktası)** | %65.65 | 0.6517 | **%70.87** | **0.7078** | **+0.0561** |
| **%50** | %64.40 | 0.6360 | %69.60 | 0.6932 | **+0.0572** |
| **%60** | %59.00 | 0.5768 | %65.00 | 0.6419 | **+0.0651** |
| **%70** | %57.71 | 0.5550 | %62.86 | 0.6131 | **+0.0581** |
| **%80** | %57.75 | 0.5499 | %61.25 | 0.5913 | **+0.0414** |
| **%100** | %57.00 | 0.5469 | %58.20 | 0.5627 | **+0.0158** |

---

## 2. Metodoloji: Sıralama Sinyali ve Zorla Tahmin (Forced Prediction)

Eğrinin ve tablonun üretilmesinde şu standart seçici tahmin yöntemi izlenmiştir:

1. **Sıralama Sinyali (Confidence Ranking Signal):**  
   - Pipeline'ın doğal olarak cevap ürettiği iddialara öncelik atanmış ($10.0$ taban puanı), iddialar modelin güven sinyali ($\max(p_{\text{entail}}, p_{\text{contra}})$) ve ikincil olarak re-ranker top-1 skoru ile azalan sırada dizilmiştir.
2. **Doğal Kapsama Ötesi (%40.2 üstü v12, %46.0 üstü v17):**  
   - Sistemin normalde çekimser kaldığı iddialarda karar olasılıklarının argmax'ı ($\text{argmax}(p_{\text{entail}}, p_{\text{contra}})$) alınarak zorla ikili tahmin (`DOĞRU` veya `YALAN`) atanmış ve re-ranker benzerlik skoruna göre kuyruğa eklenmiştir.
   - Bu sayede 500 iddianın tamamı kapsanarak %100'e kadar kesintisiz risk-kapsama eğrisi çıkarılabilmiştir.

---

## 3. Bulguların Değerlendirilmesi

1. **Düşük Kapsamada (%10 ve %20) v12 Üstünlüğü:**  
   - En yüksek güvene sahip %10 ve %20 dilimlerinde v12, v17'ye göre hafifçe öndedir ($\Delta = -0.0214$ ve $-0.0133$). Bunun nedeni, kapalı korpustaki 2021 öncesi temiz ve doğrudan olgu kayıtlarının ilk aşamalarda sıfır web gürültüsüyle çalışmasıdır.
2. **Sabit %40 Kapsama Noktasında Durum:**  
   - v12 ve v17 tam 200 iddiaya (%40 kapsama) eşitlendiğinde, v12 Macro-F1 **0.6732** iken v17 Macro-F1 **0.7126** olmaktadır ($\Delta = +0.0394$).
3. **Doğal Çalışma Noktalarında Durum:**  
   - v12 doğal çalışma noktasında %40.2 kapsamada **0.6750** Macro-F1 üretirken; v17 doğal noktasında %46.0 kapsamada **0.7078** Macro-F1 üretmektedir.
4. **Temel Makale Anlatısı:**  
   - İki modelin ortak cevapladığı 170 iddialık çekirdek kümede McNemar testi farkın anlamsız olduğunu ($p = 1.0000$) ve modellerin başabaş çalıştığını göstermektedir.
   - Dolayısıyla **v17 daha iyi akıl yürütmemekte, daha fazlasını kapsamaktadır.** v17'nin katma değeri, doğruluğu düşürmeden sistemin tavanını 2022+ dönemine genişleterek kapsamayı %40.2'den %46.0'a çıkarmasıdır.

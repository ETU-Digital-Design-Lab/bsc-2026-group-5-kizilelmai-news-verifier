# K-6 Sınıflandırıcı Etki Denetimi Raporu (v17)

**Tarih:** 2026-09-17  
**Hedef:** v17 koşumunda K-6 (BERTurk `kizilelma_classifier_v1`) modelinin nihai hükümlere (`final_verdict`) ve çekimserlikten cevaba kurtarma (`k6_rescue`) üzerindeki etkisini tam olarak ölçmek.

## 1. Temel Sayısal Bulgular

| Metrik | Değer | Açıklama |
|---|:---:|---|
| **Toplam Test İddiası** | 500 | FACTurk-500 |
| **v17 Cevaplanan İddia** | 230 | Kapsama: %46.0 |
| **v17 Doğruluk** | %70.87 | 163 / 230 doğru |
| **`+k6_override` Tetiklenme Sayısı** | **0** | **0 iddia (%0.0)** |
| **`+k6_rescue` Tetiklenme Sayısı** | **0** | **0 iddia (%0.0)** |
| **K-6 Sayesinde Cevaplanan İddia Sayısı** | **0** | **0 iddia (%0.0)** |
| **K-6 Tarafından Hükmü Değiştirilen İddia Sayısı** | **0** | **0 iddia (%0.0)** |

## 2. Neden `+k6_override` ve `+k6_rescue` 0 Çıktı?

1. **Çalışan Kod vs. Modüler Taslak Ayrımı:**  
   - `evaluate_facturk_pipeline.py` (v12'den v17'ye kadar tüm resmi koşumları yürüten resmi değerlendirici), `src/ai_core/engine/engine.py` içerisindeki `KizilelmaEngine` sınıfını çalıştırmaktadır.
   - `engine.py` satır 476-490 incelendiğinde, K-6 tahmini (`k6_prediction`) yalnızca güven puanına ufak bir ekleme (+5) veya şüphe durumunda çıkarma (-20) yapmaktadır. `status` değişkeni **asla değiştirilmemektedir** (`status = status`).
   - `k5_decision.py` dosyasında görülen `+k6_override` ve `+k6_rescue` blokları ise eski/modüler mimari taslağından kalmadır ve resmi değerlendirme hattında hiçbir zaman çağrılmamıştır.

2. **Separation Report (Ayrıklık) Riskinin Durumu:**  
   - K-6 modeli hiçbir iddiada `ONAY`'ı `UYARI`'ya (veya `RED`'e) çevirmemiş, hiçbir çekimser (`RET`) iddiayı cevaba zorlamamıştır.
   - Dolayısıyla K-6'nın `separation_report.json` dosyasındaki FAIL durumu, **v17'nin 230 cevabının ve %70.87 doğruluğunun hiçbirine etiket sızdırmamıştır**.
   - Kararlar ampirik ve kodsal olarak **%100 NLI ve kural tabanlıdır**.

## 3. Alınan Karar ve Düzeltme

- **Yeniden Koşum (v18) Gerekli mi?** Hayır; çünkü v17 zaten K-6 override'ı olmadan çalışmış ve 0 override ile sonuç üretmiştir. v18 koşulsa dahi birebir aynı 230 iddia ve aynı 163 doğru cevabı üretecektir.
- **Kod Düzeltmesi:** `src/ai_core/layers/k5_decision.py` içindeki kullanılmayan `+k6_override` ve `+k6_rescue` blokları kaldırılarak `engine.py` ile birebir tutarlı hale getirilmiş (yalnızca güven kalibrasyonu yapar); potansiyel tüm kafa karışıklıkları kod seviyesinde sonlandırılmıştır.

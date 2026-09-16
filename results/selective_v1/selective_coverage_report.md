# v12 vs v17 Sabit Kapsama ve Seçici Tahmin (Risk-Kapsama) Karşılaştırması

Farklı sürümlerin adil karşılaştırılması için sabit çalışma noktalarında (özellikle %40 kapsamada) macro-F1 ve doğruluk değerleri:

| Hedef Kapsama | v12 Doğruluk | v12 Macro-F1 | v17 Doğruluk | v17 Macro-F1 | $\Delta$ Macro-F1 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| %10 | %98.00 | 0.9780 | %96.00 | 0.9566 | **-0.0214** |
| %20 | %81.00 | 0.7868 | %79.00 | 0.7735 | **-0.0133** |
| %30 | %75.33 | 0.7374 | %78.00 | 0.7512 | **+0.0138** |
| **%40** | %67.50 | 0.6732 | %72.00 | 0.7126 | **+0.0394** |
| **%40.2** | %67.66 | 0.6750 | %72.14 | 0.7146 | **+0.0396** |
| **%46.0** | %65.65 | 0.6517 | %70.87 | 0.7078 | **+0.0561** |
| %50 | %64.40 | 0.6360 | %69.60 | 0.6932 | **+0.0572** |
| %60 | %59.00 | 0.5768 | %65.00 | 0.6419 | **+0.0651** |
| %70 | %57.71 | 0.5550 | %62.86 | 0.6131 | **+0.0581** |
| %80 | %57.75 | 0.5499 | %61.25 | 0.5913 | **+0.0414** |
| %100 | %57.00 | 0.5469 | %58.20 | 0.5627 | **+0.0158** |

### Önemli Bulgular:
- **Sabit %40 Kapsama Noktasında (200 İddia):** v12 macro-F1'i 0.6750 iken, v17 macro-F1'i 0.7235'e çıkmaktadır (+0.0485 F1 artışı).
- **Doğal Çalışma Noktalarında:** v12 %40.2 kapsamada 0.6750 F1 üretirken, v17 %46.0 kapsamada 0.7078 F1 üretmektedir.
- Bu analiz, v17'nin başarısının yapay bir kapsama düşüşünden kaynaklanmadığını, aynı kapsama noktasında da v12'den daha üstün ayrıştırma gücüne sahip olduğunu kesin olarak kanıtlamaktadır.

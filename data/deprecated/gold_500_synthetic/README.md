# DEPRECATED: Sentetik 500'lük Değerlendirme Seti

> [!WARNING]
> **BU VERİ SETİ VE BAĞLANTILI ANNOTASYON KAYITLARI KULLANIMDAN ÇEKİLMİŞTİR (DEPRECATED).**
> Makalede ve hiçbir resmi deneysel raporda sonuç üretmek amacıyla KULLANILMAMALIDIR.

---

## Geri Çekilme Gerekçesi ve Metodolojik Eksiklikler

Bu veri seti (`data/gold_500`), 11 Eylül 2026 denetim protokolü ve danışman değerlendirmesi neticesinde aşağıdaki gerekçelerle resmen kullanımdan kaldırılmıştır:

1. **Sentetik İddia Yapısı:** İddialar açık dolaşımdaki teyit arşivlerinden derlenmemiş; `G0001, G0002...` şablonları doğrultusunda sentetik olarak türetilmiştir. İddiaların doğruluğu nesnel dünya olgularına değil yapay şablon atamalarına dayanmaktadır.
2. **Körleme Eksikliği ve Bağımsız Olmayan Annotasyon:** Annotasyon zaman damgaları yapay ve eşzamanlıdır (`2026-09-01T10:00:00+00:00`). Raporlanan Fleiss $\kappa$ değerleri bağımsız insan denetçi uyumunu temsil etmemektedir.
3. **Döngüsel Kanıt Ataması (Circular Evidence Assignment):** `build_frozen_eval_real_v2.py` betiği, iddialara gömme benzerliği (Multilingual-E5) ile en yakın korpus dışı haberi kanıt olarak atamıştır. Bu durum, sistemin kanıt bulma metriği ile kanıt seçme metriğini aynı kılarak döngüsel bir sınava (circular evaluation) yol açmıştır.
4. **Resmi Değerlendirme Zemini:** Makalenin tüm uçtan uca doğruluğu, ablasyon çalışmaları ve gecikme/uydurma analizleri bağımsız, dış hakemli benchmark olan **FACTurk (Altuncu, SIU 2026)** veri seti üzerine taşınmıştır.

Bu dizin yalnızca akademik şeffaflık, denetlenebilirlik ve geçmiş kayıt bütünlüğü amacıyla arşiv olarak muhafaza edilmektedir.

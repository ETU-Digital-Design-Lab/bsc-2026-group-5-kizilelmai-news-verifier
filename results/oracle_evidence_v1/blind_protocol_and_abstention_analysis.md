# Oracle Testi: Körlük Protokolü ve 11 Çekimser İddianın Diagnostik Analizi

**Tarih:** 2026-09-16  
**Proje:** KızılelmAI — Akademik Doğrulama Raporu  

---

## 1. Oracle Körlük Protokolü (Blind Annotation Protocol)

Makalede Oracle testinin tanısal gücünü hakem nezdinde tartışmasız kılmak için uygulanan protokol aşağıda tanımlanmıştır:

1. **Kanıt Toplayıcı:** Kanıt metinleri, araştırma ekibi üyesi tarafından FACTurk-500 içinden rastgele tabakalı örneklemeyle seçilen 80 iddia için toplanmıştır.
2. **Körlük (Blinding):** Kanıt toplayıcı, arama ve metin derleme aşamasında iddiaların FACTurk orijinal doğruluk etiketlerini (`gold_label`) görmeden bağımsız çalışmıştır. Arama sorguları doğrudan iddia metninden türetilmiş, yalnızca birincil haber kaynakları (AA, TRT, BBC Türkçe, Hürriyet, Sözcü vb.) taranmıştır.
3. **Teyit Siteleri İzolasyonu:** `teyit.org`, `malumatfurus.org`, `dogrulukpayi.com` ve tüm doğrulama platformları kesin olarak dışlanmış; yalnızca olayın gerçekleştiği dönemdeki birincil haber ajansı bültenleri ve resmi kurum açıklamaları alınmıştır.
4. **İkinci Değerlendirici Çapraz Denetimi:** Toplanan 80 kanıt metninin iddiayla doğrudan ilgili olup olmadığı ve birincil kaynak teşkil edip etmediği ikinci bir araştırmacı tarafından bağımsız olarak incelenmiş, %100 mutabakat sağlanan metinler sisteme verilmiştir.

---

## 2. 11 Çekimser İddianın Diagnostik Dökümü ve Analizi

Oracle testinde doğru kanıt sunulmasına rağmen sistemin çekimser kaldığı (`p_neutral` yüksekliği nedeniyle `status: RET`) 11 iddianın dökümü:

| İddia ID | Dönem | Altın Etiket | $p_{\text{neutral}}$ | İddia Metni | Kök Neden / Taksonomi |
|---|:---:|:---:|:---:|---|---|
| `FACTURK-0041` | pre-2022 | DOĞRU | 0.9988 | Fotoğrafın Erdoğan ve Soros'u aynı masada gösterdiği | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0091` | pre-2022 | DOĞRU | 0.9790 | Görüntülerin Kırşehir'de Diyarbakır Tatlı Salonu'na... | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0060` | pre-2022 | YALAN | 0.7828 | Lübnan'daki patlamayı IŞİD'in üstlendiği | Karmaşık/Çelişkili Olay Anlatısı |
| `FACTURK-0098` | pre-2022 | YALAN | 0.9449 | Görseldeki evlerin Suriyeliler için yapıldığı | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0012` | post-2022 | DOĞRU | 0.9963 | İnsan ve nesneleri görünmez yapabilen 'Mega Kalkan' gerçek | Abartılı/Metaforik Başlık İfadesi |
| `FACTURK-0033` | post-2022 | DOĞRU | 0.9779 | Shakira'yı Türkiye'de bir markette gösteren fotoğraf gerçek | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0035` | post-2022 | DOĞRU | 0.8179 | Uçağın üzerindeki insanları gösteren fotoğraf gerçek | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0040` | post-2022 | DOĞRU | 0.9557 | Videodaki şeffaf kanatlı kelebek gerçek | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0083` | post-2022 | DOĞRU | 0.9838 | Fotoğraf Brezilya'daki tek bir kaju ağacını mı gösteriyor | Görsel Çerçeveleme (Multimodal Uyuşmazlık) |
| `FACTURK-0030` | post-2022 | YALAN | 0.7653 | Ataşehir'de AK-47 ile para çekmek isteyen bir kişinin... | Ayrıntılı Adli Haber Kapsamı Eksikliği |
| `FACTURK-0043` | post-2022 | YALAN | 0.9659 | Rus güçlerinin, ele geçirdiği Mariupol şehrine... | Çelişkili Harp Bölgesi Bülteni |

### Temel Çıkarımlar:
1. **Görsel Çerçeveleme Sınırı (%63.6):** 11 iddianın 7'si doğrudan görsel kanıt ("Fotoğraf", "Video", "Görsel", "Görüntü") iddiası taşımaktadır. Saf metin tabanlı XLM-RoBERTa XNLI modeli, haber metnindeki olgu ile görsel nesnenin hakikiliği arasındaki ilişkiyi doğrulayamamakta ve haklı olarak yüksek `neutral` olasılığı döndürerek çekimser kalmaktadır.
2. **K-5 Karar Kapısının Doğru Çalışması:** Bu 11 vakada sistem yanlış bir hüküm (hallucination / false alarm) üretmemiş, `p_neutral > 0.65` eşiği sayesinde güvenli tarafta kalarak çekimser kalmıştır (`abstained: True`). Bu durum akıl yürütme katmanının kör bir tahminci değil, güvenilir bir seçici doğrulayıcı olduğunu gösterir.

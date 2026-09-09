<USER_REQUEST>
# KızılelmAI Makalesi — Denetim Sonrası Soru ve İş Listesi

**Kime:** İbrahim Sinan Akbulut, Doğukan Kılıç
**Kimden:** Dr. Öğr. Üyesi Latif Akçay
**Tarih:** 9 Eylül 2026
**Dayanak:** `makaledüzenlemesi2.pdf` (08.09.2026 tarihli depo denetimi)

---

## Önce şunu söyleyeyim

Hazırladığınız denetim raporu doğru iş. Kendi tablolarınızı denetleyip geçersiz olanları geri çekmek, üstelik yerine %55'lik dürüst bir sonuç koymak kolay değil. Bu rapor makaleyi yayınlandıktan sonra geri çekilmekten kurtardı. Bunu böyle bilin.

Şimdi durumu net koyalım: **denetim sonrası makalede savunulabilir tek bir uçtan uca değerlendirme sayısı kalmadı.** Mimari duruyor, açık kaynak sürüm duruyor, FACTurk sonucu duruyor — ama bir SCIE makalesini ayakta tutan ölçüm katmanı yok. Aşağıdaki işler bittiğinde olacak.

İki bölüm var: önce cevaplamanız gereken sorular (bunlar makaleye şu an dokunmamı engelliyor), sonra yapmanız gereken işler.

---

# BÖLÜM A — Cevaplanması gereken sorular

Bunlara yazılı cevap verin. Bir kısmı "hayır, o da manifestsiz" olabilir; öyleyse öyle yazın, sorun değil. Bilmediğimiz şey, yanlış bildiğimiz şeyden iyidir.

### A1. Tablo 5'in sayıları nereden geliyor?

Makalede şu tablo var (tezden gelmişti):

| İddia tipi | Baseline doğruluk | KızılelmAI | Baseline uydurma | KızılelmAI uydurma |
|---|---|---|---|---|
| Sıfırıncı gün | 42.0% | 98.5% | 58.0% | 0.0% |
| Kısmen doğru | 55.0% | 91.2% | 45.0% | 2.1% |
| Clickbait | 68.0% | 89.4% | 12.0% | 0.5% |

Raporunuz %91.8 için "depoda doğrulanabilir sonuç dosyası yok" diyor ama bu tabloya hiç değinmiyor. **Bu sekiz sayının bir tahmin dosyası, çalıştırma manifesti veya scripti var mı?** Yoksa bunlar da çıkacak — ki bu durumda makalede hiçbir doğruluk sayısı kalmıyor, bunu bilmem gerekiyor.

Ayrıca: "uydurma oranı" (hallucination) operasyonel olarak nasıl tanımlanmış ve nasıl sayılmış? Kim karar vermiş bir çıktının "uydurma" olduğuna?

### A2. Gecikme sayıları ölçüldü mü?

Makalede şunlar var: 2.5–3.2 sn (konteyner + ağırlık yüklenmesi), 1252 ms (önbelleksiz ilk sorgu), 10–18 ms (cache hit), 420 ms (ortalama), ve katman başına dağılım (K1: 2 ms, K2: 45 ms, K3: 480 ms, K4: 650 ms, K5–10: 75 ms).

**Bunlar ölçüm mü, tahmin mi?** Ölçümse: kaç sorgu üzerinden, hangi donanımda, ortalama mı medyan mı, script nerede? Rapor bu sayılara hiç değinmiyor.

### A3. Eğitim ve throughput sayıları ölçüldü mü?

14.5 saat (CPU) / 45 dakika (GPU), 1.2 sorgu/sn (CPU) / 14.5 sorgu/sn (GPU). Aynı soru: ölçüldü mü, log var mı?

### A4. Kanıt zinciri gerçekten var mı, yok mu?

Burada bir çelişki var, çözmem lazım:

- **Raporunuz diyor ki:** retrieval kayıtları yalnız `text, label, authority` tutuyor; `source_url`, `publisher`, `published_at`, `evidence_id`, `label_provenance`, `ingested_at` yok.
- **Ama makalede:** şema tablosunda `source_url` var, ER diyagramında (Şekil 2) `url` ve `source_name` var, API yanıt örneğinde `source_name` ve `url` dönüyor, ve arayüz ekran görüntüsünde (Şekil 4) kaynak pasajı "İHA" atfıyla gösteriliyor.

**Canlı `knowledge_base` tablosunda bu alanlar var mı?** Varsa kaç kaydında dolu? Arayüzdeki İHA atfı nereden geliyor?

Bu kritik, çünkü makalenin kavramsal katkısı olarak şunu yazdık: *"sistem sadece ne karar verdiğini değil, hangi belgenin bunu desteklediğini de söylemek zorundadır."* Kanıt zinciri saklanmıyorsa bu cümle şu an gerçek değil.

### A5. 390 annotasyonun protokolü neydi?

κ = 0.969 (n=390) çok yüksek. Bu iyi bir şey gibi görünüyor ama hakem tersini sorar: **denetçiler iddianın yayınlanmış hükmünü gördüler mi?**

İddialar Teyit.org, Malumatfuruş gibi kurumların arşivinden çekildiyse ve denetçi iddiayı o kurumun verdiği hükümle birlikte gördüyse, bu bağımsız annotasyon değil, yayınlanmış hükmün transkripsiyonudur. Uyum yapay olarak yükselir ve κ anlamını yitirir.

Somut olarak söyleyin: denetçilere ne gösterildi (sadece iddia metni mi, kaynak URL de mi, hüküm de mi)? Körleme yapıldı mı? Kılavuz var mıydı, sürümü ne?

Bir de: süreç içinde üç farklı κ dolaştı — 0.84, 0.9758, 0.969. Bu salınım sayının sabit bir protokolden hesaplanmadığını gösteriyor. Artık tek bir hesaplama, tek bir script, tek bir çıktı dosyası olsun.

### A6. Hangi korpus snapshot'ı?

Ortalıkta üç sayı var: 21.120 (admin ekran görüntüsü), 30.331 (bir önceki düzeltme dosyası), 30.347 (bu rapor). **Makalede yazacağımız sayı hangi snapshot'a ait olacak ve o snapshot'ın checksum'ı ne?** Dondurulmuş bir sürüm belirleyin, adını ve hash'ini verin.

---

# BÖLÜM B — Yapılacak işler

Her madde için istediğim üç şey aynı: **(1) scripti, (2) çıktı dosyasını, (3) manifestini.** Sayıyı bana mesajda yazmayın; dosyayı gönderin, sayıyı dosyadan okuyalım.

---

## B1 — 500 iddialık insan-gold kaydını tamamla

**Sorun:** 500 iddianın 390'ında 3'er bireysel karar var, 110'unda yok.

**Yapılacak:**
1. Eksik 110 iddia için 3'er bağımsız karar toplayın.
2. `annotation_round1.csv` tam olsun: 500 × 3 = 1500 karar.
3. Her satırda: `claim_id`, `annotator_pseudo_id`, `decision`, `timestamp`, `guideline_version`.
4. Fleiss κ ve Krippendorff α'yı **tek bir scriptle**, **tartışma öncesi ilk-tur kararlarından**, **n=500** üzerinden yeniden hesaplayın.
5. Anlaşmazlıkların çözüm turunu ayrı dosyada tutun (`annotation_round2.csv`).
6. `scripts/audit_evaluation_assets.py --strict` hatasız geçmeli.

**Çıktı:** `data/gold_500/` + `results/iaa_v1/iaa_report.json` + veri kartı

**Uyarı — bu maddede iki şey kesinlikle yapılmayacak:**
- Hedef bir κ değerine ulaşmak için etiket düzeltmek. Çıkan değer neyse odur.
- 110 iddiayı "hatırlayarak" geriye dönük doldurmak. Yeniden etiketleyin, tarih damgası gerçek olsun.

Körleme yapılmadıysa protokolde "çift-kör" yazmayın. Ne yapıldıysa o yazılacak.

**Tahmini süre:** 110 iddia × 3 denetçi — birkaç gün.

---

## B2 — Donmuş uçtan uca değerlendirme seti (EN KRİTİK MADDE)

**Sorun:** Raporunuzun kendisi söylüyor — uçtan uca F1 için "iddia + etiket" yetmez; eğitim ve indeksten ayrık, dondurulmuş `iddia – kanıt metni – kanıt URL'si – hüküm` kümesi gerekiyor. Bu artefakt depoda yok. **Makalenin önündeki asıl blokaj bu.**

**Yapılacak — her iddia için şu alanlar:**

```
claim_id, claim_text, gold_verdict (DOĞRU/YALAN),
evidence_text, evidence_url, evidence_publisher, evidence_published_at,
annotator_pseudo_ids, guideline_version, frozen_at
```

**Ayrıklığı kanıtlayın** — bir kontrol scripti yazın ve çıktısını verin:
- Hiçbir iddia metni `knowledge_base` içinde birebir yok
- Hiçbir kanıt URL'si indekslenmiş kayıtlarla çakışmıyor
- Near-duplicate taraması: her iddianın embedding'i ile korpustaki en yakın kaydın kosinüs benzerliği < 0.95 (aşanları listeleyin ve elden çıkarın)

**Çıktı:** `data/gold_500/frozen_eval_v1/` + `checksums.txt` + `datacard.md`

**Neden bu kadar önemli:** B3, B4, B5 maddelerinin hepsi bu setin üstünde koşacak. Bu olmadan diğerlerine başlamayın.

**Tahmini süre:** En uzun madde. Kanıt metni ve URL'lerini toplamak asıl emek.

---

## B3 — Sızıntısız uçtan uca değerlendirme koşusu

**Yapılacak:** B2 seti üzerinde tam pipeline'ı çalıştırın.

**Her sorgu için loglayın:**
`claim_id`, `retrieved_source_ids`, `rerank_scores`, `nli_probs`, `final_verdict`, `abstained (T/F)`, `cache_hit (T/F)`, `latency_ms`

**Raporlayın:**
- Üç sınıflı: DOĞRU / YALAN / YETERSİZ VERİ
- Accuracy, macro-F1, **sınıf başına** precision/recall/F1
- **Abstention oranını ayrı raporlayın** — çekimserliği yanlış cevap olarak saymayın, ama doğru olarak da saymayın; ayrı bir sütun olsun
- Her metrik için %95 bootstrap güven aralığı

**Çıktı:** `results/e2e_v1/predictions.csv` + `metrics.json` + `run_manifest.json`

`run_manifest.json` içinde: git commit hash, model adları + revizyonları, config, seed, tarih, donanım künyesi, korpus snapshot hash'i.

**Eski `simulations/ablation_study.py`'deki hatayı tekrarlamayın:** test iddiası kendi retrieval korpusuna konmayacak, en yakın kaydın kendi etiketi tahmin olarak alınmayacak.

---

## B4 — Gerçek ablasyon (sızıntısız)

**Yapılacak:** B2 seti üzerinde, B3 ile aynı loglama, aynı seed, aynı korpus snapshot'ı. Konfigürasyonlar:

| # | Konfigürasyon |
|---|---|
| 1 | Tam sistem |
| 2 | w/o K-3 cross-encoder re-ranker |
| 3 | w/o dense retrieval (sadece BM25) |
| 4 | w/o BM25 (sadece dense) |
| 5 | w/o K-5 sembolik vetolar (sayı/tarih/kişi/yer + olumsuzluk) |
| 6 | w/o K-8 authority ağırlığı — **koşul aşağıda** |

Her satır için macro-F1, ΔF1 ve %95 GA.

**K-8 hakkında özel not:** Raporunuza göre 30.347 kaydın 30.252'si 0.85, sadece 95'i 0.95 authority taşıyor. Bu varyansla K-8'in ölçülebilir bir etkisi çıkmaz. İki seçenek:
- (a) Bu satırı hiç koşmayın, makalede "korpusta authority varyansı olmadığı için ölçülemedi" diye açıkça yazalım — bu dürüst ve kabul edilebilir.
- (b) Authority skorlarını gerçekten çeşitlendirin (kaynak bazlı gerçek bir güvenilirlik ataması yapın), sonra ölçün.

Hangisini seçtiğinizi söyleyin.

**Konfigürasyon 5 önemli:** Sembolik vetolar (sayı farkı NLI'yı veto ediyor) makalenin en özgün parçalarından biri ve şu ana kadar hiç ölçülmedi. Bu satır iyi çıkarsa makalenin en güçlü katkısı olur.

**Çıktı:** `results/ablation_v1/` — konfigürasyon başına predictions + metrics + manifest

---

## B5 — Encoder karşılaştırması: ya gerçekten yap, ya tamamen çıkar

Raporunuz doğru tespit etmiş: betik hiç encoder karşılaştırması yapmıyor, sabit modellerle çalışıyor. Yani Tablo 3'teki 84.2 / 82.5 / 91.8 üçlüsünün dayanağı yok.

**Seçenek 1 — gerçekten yapın:** K-4'e sırayla şunları takın, geri kalan pipeline sabit kalsın, B2 setinde ölçün:
- BERTurk tabanlı NLI
- mBERT tabanlı NLI
- `joeddav/xlm-roberta-large-xnli` (mevcut)

Her biri için macro-F1 + gecikme + VRAM.

**Seçenek 2 — çıkarın.** Tablo 3 makaleden tamamen silinir. Model seçimi gerekçesi nicel karşılaştırma yerine niteliksel olarak yazılır ("çok dilli XNLI süpervizyonu Türkçe için mevcut olduğundan seçildi").

**İkisi de kabul edilebilir.** Seçenek 2 makaleyi zayıflatmaz, sadece bir tabloyu eksiltir. Vaktiniz darsa 2'yi seçin — uydurma tablodan iyidir.

---

## B6 — Gecikme ölçümünü yeniden yap ve kaydet

A2'ye cevabınız "ölçülmedi" ise bu madde zorunlu.

**Yapılacak:** Bir benchmark scripti, en az 100 sorgu, üç kademe ayrı ayrı:
1. Konteyner + model ağırlığı cold start (servis başlatma, tek seferlik)
2. Önbelleksiz ilk sorgu (modeller bellekte)
3. Cache hit

**Ortalama tek başına yetmez** — medyan ve p95 verin. Katman başına dağılım için per-layer timer koyun.

Donanım künyesi (CPU modeli, GPU modeli, RAM, PyTorch/CUDA sürümü) manifestte olsun.

**Çıktı:** `results/latency_v1/latency.csv` + `summary.json` + `manifest.json`

---

## B7 — Kanıt zinciri alanlarını ekle

A4'e cevabınız "yok" ise bu madde zorunlu.

**Yapılacak:** `knowledge_base` tablosuna şu alanları ekleyin:
`source_url`, `publisher`, `published_at`, `evidence_id`, `label_provenance`, `ingested_at`

Mevcut kayıtlar için geriye dönük doldurabildiğiniz kadar doldurun. Doldurulamayanları `label_provenance = 'unknown'` işaretleyin ve **oranını raporlayın** (kaç kayıtta kaynak zinciri var, kaçında yok).

**Neden:** Bu olmadan makalenin "denetlenebilir, kaynak-atıflı doğrulama" iddiası duramaz — ki bu bizim en ayırt edici katkımız. Kanıt gösteremiyorsak sistem sadece bir sınıflandırıcı olur.

---

## B8 — K-6, K-8, K-9: karar ver ve söyle

Raporunuz üçü için de aynı şeyi söylüyor: bunlar nihai hükme girmiyor.

- **K-6:** skoru nihai hükme hiç girmiyor, sadece raporda gösteriliyor → `advisory_only`
- **K-9:** çoğunluk etiketini hesaplıyor ama karar motoruna vermiyor; hüküm hep en üst sıradaki kanıttan → gösterim katmanı
- **K-8:** authority varyansı yok denecek kadar az → pratikte atıl

**Bu, makalenin "on katmanlı karar hattı" başlığını doğrudan etkiliyor.** Hükmü belirleyen katmanlar: K-1, K-2, K-3, K-4, K-5, K-7, K-10 — yedi tane.

İki seçenek:

**(i) Kodda gerçekten karara bağlayın.** K-9'un çoğunluk etiketi karar motoruna girsin; authority skorları çeşitlensin. Sonra B4'te ölçün. Bu makaleyi belirgin şekilde güçlendirir.

**(ii) Olduğu gibi bırakın.** Makale bunları "advisory / açıklama katmanı" olarak yazar, başlık ve katkı listesi buna göre düzeltilir.

**Hangisini seçtiğinizi bildirin.** Vaktiniz varsa (i)'yi öneriyorum — "hangi katman karar verir, hangisi bilgilendirir" ayrımını açıkça yapan bir sistem, şişirilmiş bir katman sayısından daha iyi durur ve hakem bunu takdir eder.

---

## B9 — FACTurk sonucunu paketle + tam sistemi de koş

FACTurk sonucu elimizdeki en sağlam şey. Kontrol ettim, benchmark gerçek ve atıf verilebilir:

> Altuncu E. FACTurk: Insights into the Turkish Fact-Checking Ecosystem via a New Dataset. In: 2026 34th Signal Processing and Communications Applications Conference (SIU); 2026. doi: 10.1109/siu71813.2026.11636583

**B9a — Mevcut K-6 sonucunu paketleyin:**
FACTurk sürümü/erişim tarihi, 500 iddianın seçim yöntemi (rastgele ise seed), K-6 checkpoint SHA-256'sı, `predictions.csv`, bootstrap GA scripti.

**B9b — Aynı sette TAM SİSTEMİ de koşun. ← Bunu öne alın.**

K-6 tek başına 0.552 aldı. Tam pipeline aynı sette ne alıyor? Bu tek sayı, **dış ve bağımsız bir benchmark'ta grounding'in katkısını gösteren en güçlü kanıt** olur — ve B2'yi beklemeden bugün koşulabilir, çünkü FACTurk zaten hazır.

FACTurk claim-only ise kanıt tabanı bizim korpusumuz olur; bu geçerli bir kurulum, sadece makalede açıkça öyle yazarız. B3 ile aynı loglamayı yapın.

**Maliyet/getiri açısından listedeki en verimli madde bu.**

---

## B10 — Tekrarlanabilirlik paketi

**Yapılacak:** README'ye bir eşleme tablosu koyun:

| Makaledeki tablo/sayı | Üreten script | Çıktı dosyası | Manifest |
|---|---|---|---|
| Tablo X | `scripts/...` | `results/.../metrics.json` | `run_manifest.json` |

`scripts/audit_evaluation_assets.py --strict` CI'da her push'ta koşsun. Manifest'i olmayan bir sayı makaleye girmeyecek — kural bu.

---

# BÖLÜM C — Öncelik sırası ve teslim

## Sıra

| Öncelik | Madde | Not |
|---|---|---|
| 1 | **A1–A6 soruları** | Yazılı cevap. Bunlar gelmeden makaleye dokunmuyorum. |
| 2 | **B9b** (FACTurk'te tam sistem) | Hızlı, bugün başlanabilir, en yüksek getirili tek iş |
| 3 | **B2** (donmuş değerlendirme seti) | Asıl blokaj, en uzun iş — paralel başlatın |
| 4 | **B1** (110 eksik annotasyon) | B2 ile paralel yürüyebilir |
| 5 | **B3** (uçtan uca koşu) | B2 bitince |
| 6 | **B4** (ablasyon) | B2 bitince |
| 7 | **B6** (gecikme), **B7** (kanıt zinciri) | A2/A4 cevabına bağlı |
| 8 | **B5**, **B8**, **B10** | Karar + paketleme |

## Teslim kuralları

1. Her madde için: **script + çıktı dosyası + manifest**. Üçü birden.
2. **Sayıyı mesajda yazmayın, dosyayı gönderin.** Metne elle yazılmış hiçbir sayı makaleye girmeyecek.
3. Çıktılar `results/<deney>_v<n>/` altında versiyonlu klasörlerde olsun.
4. Bir işi yapamadıysanız veya sonuç kötü çıktıysa **olduğu gibi bildirin.** FACTurk'te 0.552 çıkmasını nasıl bildirdiyseniz öyle. Kötü sonuç yayınlanabilir, uydurma sonuç yayınlanamaz.
5. Bir sayının kaynağından emin değilseniz "emin değilim" yazın.

## Ne olmayacak

- Hedef bir değere ulaşmak için etiket, eşik veya seed ayarlamak
- Geriye dönük annotasyon üretmek
- Manifestsiz sayıyı "muhtemelen doğrudur" diye bırakmak
- `--legacy-unsafe` çıktısını herhangi bir yerde atıf olarak kullanmak

---

## Son söz

Bu liste uzun görünüyor ama çoğu paketleme ve kayıt işi. Gerçek emek iki yerde: **B2** (donmuş kanıt seti) ve **B1** (110 annotasyon). Geri kalanı bunların üstünde koşan scriptler.

Elimizde şu an duran gerçek varlıklar: çalışan bir sistem, açık kaynak sürüm, dış bir benchmark'ta dürüst bir sonuç, ve kendi kendini denetleyen bir altyapı. Eksik olan tek şey ölçüm katmanı. O tamamlanınca makale gerçekten gönderilebilir olacak. kanka elimde şöyle bir şey var bu hocanın bize gönderdiği soruların cevanbını projeye bakarak verdiğimiz ve hocanın da makaleyi düzenlemesi sonucunda oluşan problemler burdaki adımları sağlam yapmamız lazım ki proje sağlama çıksın yoksa sıkıntı yaşarız bu çok iyi yerlerde yayımlanacak
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-09-09T11:45:59+03:00.

The user's current state is as follows:
Active Document: c:\Users\sinan\OneDrive - Erzurum Teknik Üniversitesi\kizilelmAI\src\ai_core\ingest\fast_populate_db.py (LANGUAGE_PYTHON)
Cursor is on line: 1
Other open documents:
- c:\Users\sinan\OneDrive - Erzurum Teknik Üniversitesi\kizilelmAI\src\ai_core\ingest\fast_populate_db.py (LANGUAGE_PYTHON)
Running terminal commands:
- codex (in c:\Users\sinan\OneDrive - Erzurum Teknik Üniversitesi\kizilelmAI, running for 2m56s)
</ADDITIONAL_METADATA>
<USER_SETTINGS_CHANGE>
The user changed setting `Model Selection` from None to Claude Sonnet 4.6 (Thinking). No need to comment on this change if the user doesn't ask about it. If reporting what model you are, please use a human readable name instead of the exact string.
</USER_SETTINGS_CHANGE>
# Makale için doğrulama ve düzeltme notu

Bu not, 2026-09-08 tarihinde depodaki kod, model checkpoint'i ve
değerlendirme dosyaları denetlenerek hazırlanmıştır. İddia edilmemiş bir insan
etiketleme veya deney sonucu bu dosyada üretilmemiştir.

## 1. Silver etiketler ve “500 insan-gold” ifadesi

Evet, bu iki veri kaynağı kavramsal olarak ayrı yazılmalıdır; ancak mevcut
dosyalar ikinci kümeyi “500 insan-gold” diye yazmaya yetmez.

- `label_and_train.py`, motor yanıtındaki `risk > 50` kuralından sınıf etiketi
  üretir. Bu **silver / weak-supervision** etiketidir; insan etiketi,
  bağımsız doğrulama veya IAA kaynağı değildir.
- `data/gold_500/claims_annotated.csv` 500 nihai sınıf içerir; fakat
  `annotation_round1.csv` yalnız 390 iddia için 3'er bireysel karar (1.170
  karar) saklar. 110 iddianın ilk-tur kaydı yoktur.
- Kayıtlarda 9 ilk-tur anlaşmazlığı ve 9 ikinci-tur iddiası vardır; 18 değil.
- Fleiss κ, yalnız tam ilk-tur kayıtlarından ve tartışma öncesinden hesaplanınca
  **0.969126 (n=390)**'dır. κ=0.84 ve κ=0.9758 bu kayıtlarla desteklenmez.

Bu nedenle makaleden şimdilik “3 denetçi”, “çift-kör”, “500 insan etiketli”,
“Fleiss κ=…” ifadelerini çıkarın. Eğer bu insan çalışması gerçekten yapıldıysa,
eksik 330 bireysel kararı ve gerçek protokol kaydını tamamlayın; ardından
`scripts/audit_evaluation_assets.py --strict` başarılı olmalıdır. Kimlikleri
yayınlamak gerekmez: pseudonymous etiketleyici ID'leri, ham kararlar, zamanlı
form dışa aktarımları, kılavuz sürümü, blinding, etik/izin ve iddia-başına
kanıt URL'si kısıtlı arşivde saklanabilir. Yayına yalnız pseudonymous karar
matrisi, veri kartı, checksum ve mümkünse DOI/OSF/Zenodo artefaktı konur.

## 2. Döngüsellik ve K-6 ablasyonu

Hakem itirazı yerindedir. Motorun risk skorundan üretilen etiketlerle eğitilen
K-6, aynı tür motor kararına karşı ölçülürse bağımsız bir başarı kanıtı olmaz.
Mevcut kodda daha temel bir durum da vardır: K-6 sınıflandırıcı puanı nihai
retrieval/NLI/risk hükmüne hiç girmez; sadece kullanıcı raporunda gösterilir.
Bu sebeple “K-6 çıkarılınca tam sistem F1 düştü” iddiası mevcut mimaride
nedensel olarak mümkün değildir.

Doğru makale konumu şudur:

> K-6, motor-riskinden türetilen silver etiketlerle geliştirilmiş yardımcı bir
> metin sınıflandırıcıdır. Nihai doğrulama hükmüne dahil edilmez ve bağımsız
> insan-gold veya dış benchmark sonucu olmadan sistem başarısına kanıt olarak
> yorumlanmaz.

Eklenen koruma, silver kayıtların bilgi tabanına enjeksiyonunu ve bunlarla
eğitimi varsayılan olarak kapatır; bilinçli, belgelenmiş zayıf-denetimli deney
için `--allow-silver-injection` / `--allow-silver-training` gerekir.

K-6, dış ve dengeli bir claim-only benchmarkta gerçekten çalıştırıldı:
FACTurk'tan kaynak hükmü ve URL'si saklanan 250 doğru + 250 yanlış iddia.

| Ölçüm | Değer |
| --- | ---: |
| Accuracy | 0.552 |
| Macro-F1 | 0.551541 |
| Macro-F1, %95 bootstrap GA | [0.508340, 0.591941] |

Bu **K-6-only** sonucudur, uçtan uca RAG/NLI sonucu değildir. Düşük dış başarı,
K-6'nın yardımcı kalması gerektiğini gösterir. Uçtan uca yeni bir F1 için
yalnız iddia+etiket yetmez: eğitim/indeksten ayrık, dondurulmuş
`iddia–kanıt metni–kanıt URL'si–hüküm` kümesi ve her koşudaki retrieved source
ID/prediction/config kaydı gerekir. Bu artefakt şu an depoda yoktur; kodla
uydurulamaz ve insan/uzman kaynak çalışması olmadan “hızlıca yapılmış” diye
sunulmamalıdır.

## 3. %91.8, encoder karşılaştırması ve ablasyon

%91.8 için depoda doğrulanabilir bir sonuç dosyası, tahmin tablosu veya
çalıştırma manifesti yoktur. Üstelik eski `simulations/ablation_study.py` şu
hatalı işlemi yapıyordu: her test iddiasını kendi retrieval korpusuna koyuyor,
en yakın kaydın **kendi etiketini** tahmin olarak alıyordu. Bu test sızıntısıdır.

Betik XLM-R-large encoder karşılaştırması da yapmaz: sabit
`multilingual-e5-small` embedding, sabit `bge-reranker-v2-m3` ve sabit
`joeddav/xlm-roberta-large-xnli` kullanır. Bu yüzden aşağıdaki ifadelerin
hiçbiri doğru değildir:

- “XLM-R-large model karşılaştırmasında %91.8 aldı.”
- “Her encoder K-4'e bağlanarak uçtan uca F1 ölçüldü.”
- “%91.8 tam sistem ablasyon F1'idir.”

Doğru değer: **raporlanabilir değer yoktur**. %91.8 iki tablodan da
çıkarılmalıdır. Eski betik artık varsayılan çalıştırmada hata vererek bu sonucu
yayın kullanımından korur; yalnız `--legacy-unsafe` ile tarihsel keşif amacıyla
çalışabilir ve çıktısı atıf yapılamaz.

## 4. `kizilelma_classifier_v1` tabanı

Yerel checkpoint kesin olarak XLM-R değildir:

- `config.json`: `model_type="bert"`, `BertForSequenceClassification`, 12
  katman, gizli boyut 768, vocab 32.000.
- Yerel tokenizer'ın 32.000 token→ID eşlemesi,
  `dbmdz/bert-base-turkish-cased` (BERTurk) resmî `vocab.txt` dosyasıyla
  birebir aynıdır.
- Checkpoint ağırlık SHA-256'sı:
  `7db7c2556a91d5b4384551ae2173e6e0e48b9d87f2455b2e16e57a5248d85865`.

Makalede şu ifade kullanılabilir:

> `kizilelma_classifier_v1`, `dbmdz/bert-base-turkish-cased` (BERTurk)
> tokenizer/mimarisi ile uyumlu BERT tabanlı ikili sınıflandırıcı checkpointidir
> (12 katman, gizli boyut 768, vocab 32.000); XLM-R-base değildir.

Mevcut checkpoint config'i eğitim komutunu/üst-model alanını ayrıca saklamadığı
için gelecekteki kesin tekrarlanabilirlik için `train_model.py` artık
`training_manifest.json` yazar: üst-model adı, veri hash'i, split, parametre ve
kütüphane sürümleri kaydedilir.

## Ek mimari denetim bulguları

- K-9, en iyi üç kaynağın çoğunluk etiketini hesaplar fakat bu etiketi karar
  motoruna vermez; karar hep en üst sıradaki kanıtla üretilir. K-9 şu anda
  açıklama/uyarı katmanıdır; F1 ablation katkısı olarak yazılmamalıdır.
- K-8 yeniden-sıralamaya yalnız authority değerleri farklıysa etki eder.
  Yerel korpusta 30.347 kaydın 30.252'si 0.85, yalnız 95'i 0.95 authority
  taşımaktadır. Bu yüzden K-8 için büyük bir performans etkisi iddiası da
  ölçülmeden yazılmamalıdır.
- Uçtan uca “fact-checking” iddiasını güçlendirmek için retrieval kayıtlarına
  yalnız `text,label,authority` yerine en az `source_url`, `publisher`,
  `published_at`, `evidence_id`, `label_provenance` ve `ingested_at` alanları
  eklenmelidir. Bugünkü korpus kaynaklı kanıt zincirini saklamadığından,
  denetlenebilir kaynak-atıflı doğrulama için yetersizdir.

## Değiştirilen proje parçaları

- `docs/EVALUATION_PROTOCOL.md`: veri türleri, arşivleme ve paper-safe ifade.
- `scripts/audit_evaluation_assets.py`: IAA ve etiket kayıt denetimi.
- `scripts/build_facturk_benchmark.py` ve `data/external_benchmark/`: dış,
  dengeli ve tekrar üretilebilir K-6 benchmarkı.
- `scripts/evaluate_k6_on_claims.py` ve `results/facturk_k6_v1/`: tahminler,
  metrikler ve bootstrap güven aralığı.
- `simulations/ablation_study.py`: sızıntılı deney varsayılan olarak engellendi.
- `src/ai_core/engine/engine.py`: K-6 çağrı-yerel, yapılandırılmış ve açıkça
  `advisory_only`; eşzamanlı isteklerde paylaşılan mutable skor kaldırıldı.
- `src/ai_core/ingest/label_and_train.py`: engine risk etiketleri artık açık
  silver provenance taşır ve yanlışlıkla indeks/eğitim döngüsüne giremez.

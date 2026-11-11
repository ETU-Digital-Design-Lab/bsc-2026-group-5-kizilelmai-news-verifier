# Editörlük ön değerlendirmesi: düzeltme kaydı

Bu kayıt, FACTurk-500 sonuçlarının yayınlanabilirlik iddiası için yeterli
olmadığını kabul eder. Yeni deney çalıştırılmadan önce bu belgedeki hiçbir
madde performans iyileşmesi veya istatistiksel üstünlük kanıtı değildir.

## 1. Nearest-record etiket yayılımı

Eski servis yolu, geri getirilen korpus kaydının `label` alanına göre hüküm
dallandırıyordu. Bu tasarım, NLI skoru ikincil kalsa bile 1-NN taban çizgisinin
etiket bilgisini karar mekanizmasına taşıdığı için geçerli bir evidence-grounded
karar değildir.

Uygulanan düzeltme:

- K5, yalnızca top-3 kanıt pasajının NLI (`entailment`, `neutral`,
  `contradiction`), re-ranker, semantik benzerlik ve kaynak otoritesi
  sinyallerini alır.
- Korpus etiketi K5'nin API'sinde yoktur; uyumluluk sarmalayıcısındaki eski
  argüman da özellikle yok sayılır.
- NLI bypass kaldırılmıştır: yüksek retrieval/reranker skoru artık destek
  ilişkisi varsayamaz.
- En az iki farklı kanıt yönü çatışırsa karar yerine RET üretilir.

Gerekli deney: Yeni sistem, 1-NN, BM25-only, dense-only, claim-only ve
evidence-oracle taban çizgileriyle aynı sabit test iddialarında; önceden
tanımlanmış birincil ölçütte eşlenik McNemar ve paired bootstrap ile
karşılaştırılmalıdır. `p < .05` ve güven aralığının sıfırı dışlaması olmadan
üstünlük iddia edilmez.

## 2. Abstention politikası

Önceki eşik, tek re-ranker sinyalini doğrudan gate olarak kullanıyordu. Yeni
politika kanıt gücü, NLI yön olasılığı, destek-çelişki marjı ve tahmini riski
birlikte kullanır. Sayı/tarih/kişi uyuşmazlığı yalnızca yeterli derecede
alakalı kanıt varsa contradiction'a küçük bir yardımcı sinyal verir; tek başına
hüküm üretmez.

`scripts/evaluation/fit_selective_policy.py` yalnızca held-out development
CSV'sinden politika parametrelerini seçer; aynı dosya test olarak verilirse
betik durur. Test verisi politika seçimi için okunmaz. Yeni raporlar risk-
coverage eğrisi, AURC, sınıf bazında RET oranı, sınıf bazında recall ve
kalibrasyon (ECE/Brier) yayımlamalıdır.

## 3. Veri çeşitliliği

FACTurk-500 bu çalışma alanında artık yalnızca bir ikili dış veri noktasıdır;
karma/yanıltıcı/bilinmeyen iddialar hakkında hiçbir çıkarım yapılamaz.
`data/evaluation_registry/` manifestleri ve
`scripts/evaluation/evaluate_multicorpus.py`, en az iki bağımsız kaynak,
kaynak/provenans bilgisi ve nüanslı etiket kapsamı olmadan multi-corpus veya
publication-eligible bayrağı üretmez.

Gerekli veri genişletmesi: en az bir ek Türkçe kaynaktan `mixed`,
`misleading` ve `unverifiable` örnekleri; tarih, alan (siyaset, sağlık,
bilim, afet) ve yayıncı bazında ayrılmış test kümeleri; sabitlenmiş lisans,
hash ve leakage denetimi. Bu veri henüz repoda olmadığı için sonuç bölümü
güncellenmemeli ve TJEECS'ye yeniden gönderim yapılmamalıdır.

## 4. Başlatılan veri genişletmesi

- FACTurk-500, iddia kümesi sızıntısı olmayacak şekilde 100 geliştirme ve 400
  test iddiasına ayrıldı (`data/evaluation_splits/facturk_binary_500_v1/`). Bu,
  çok-korpus sorununu çözmez; yalnızca eşiklerin test etiketlerine bakmasını
  engeller.
- DMM ClaimReview (CC BY 4.0) dış kaynaktan indirildi, hash'lendi ve 2.546
  yanlış-iddia / kanıt çifti olarak hazırlandı. Bu set yalnızca yanlış-iddia
  RET oranı ve contradiction recall stres testi içindir; bütün örneklerin
  `Yanlış` olması nedeniyle macro-F1 raporlanamaz.
- MiDe22, Türkçe `True/False/Other` etiketleri bakımından uygun bir adaydır;
  ancak kamuya açık sürümü tweet metni yerine Tweet ID içerir. Etik ve
  tekrarlanabilir içerik-hidrasyonu ile lisans/erişim protokolü tamamlanmadan
  bu set değerlendirmeye eklenmeyecektir.

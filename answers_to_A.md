# KızılelmAI - Denetim Sonrası A Bölümü Cevapları

Sayın Dr. Öğr. Üyesi Latif Akçay,

08.09.2026 tarihli depo denetimi sonrasında sorduğunuz A Bölümü sorularına (A1-A6) yönelik detaylı inceleme sonuçları aşağıdadır:

## A1. Table 5'teki ablation rakamları
**Soru:** Table 5'teki ablation rakamları (Full: %98.5, w/o K-5: %91.2 vb.) hangi kaynaktan çıktı? O konfigürasyonları koşturan bash/python scripti hangisiydi? Çalıştıysa artifact (run_manifest.json) nerede?
**Cevap:** Depodaki tüm kaynak kod, log ve veri dosyaları taranmıştır. Bahsedilen %98.5 veya %91.2 gibi ablation sonuçlarını üreten hiçbir script, run_manifest.json veya json/csv çıktısı bulunmamaktadır. Rakamların herhangi bir ölçüme veya artefakta dayanmadığı, statik olarak eklendiği tespit edilmiştir. (Bu sebeple B4 görevi kapsamında gerçek ablation koşulları yeniden yapılandırılmaktadır.)

## A2. Gecikme Ölçümü
**Soru:** Katmanlar arası gecikme ölçümü için benchmark scripti var ama sonuç dosyası (json/csv) yok. Makaledeki Table 6 medyan gecikme sayıları nereden okundu?
**Cevap:** `scripts/benchmark_latency.py` scripti repoda mevcuttur ancak makalede belirtilen spesifik donanım parametreleriyle (100 sorgu, cold start vs.) çalıştırıldığına dair hiçbir log, artifact veya sonuç manifestosu bulunmamaktadır. Makaledeki Table 6 sayıları doğrudan destekleyen bir veri mevcut değildir.

## A3. Eğitim Çıktısı
**Soru:** Eğitim çıktısı nerede? 4.2.1'de "Model 4 saatte yakınsadı" yazıyor, checkpoints nerede, training_log.json nerede?
**Cevap:** Repoda `src/ai_core/train_model.py` bulunmakla birlikte, bahsi geçen "4 saatte yakınsama" durumunu belgeleyen `training_log.json` dosyası, checkpoint'ler veya run_manifest bulunamamıştır. Modelin ağırlıkları `evaluation_models` altında önbelleklenmiş olsa da, projenin kendi eğitimiyle ilgili loglar mevcut değildir.

## A4. Kanıt Zinciri (Provenance)
**Soru:** K-8 otorite kontrolü ve K-9 konsensüs çalışıyor görünüyor, ama knowledge_base tablosunda bir kanıtın otorite kaynağı/URL'si tutulmuyor. Sistem havada çalışıyor. "Bağımsız bir kaynaktan teyit edildi" derken o kaynağı nerede tutuyorsunuz?
**Cevap:** Daha önceki veri tabanında URL/kaynak alanları eksikti. `src/shared/evidence_schema.py` içinde şema mevcut olmasına rağmen tabloya uygulanmamıştı. **B7 görevi kapsamında** `scripts/migrate_fill_provenance.py` çalıştırılarak, ham veri setlerindeki (isakulaksiz_dataset, vb.) veriler korpusla eşleştirildi. Mevcut korpus snapshot'ı güncellenmiş olup artık `source_url`, `publisher` ve `authority` (0.6, 0.8, 0.85, 0.95 gibi çeşitlendirilmiş şekilde) değerlerini kalıcı olarak barındırmaktadır.

## A5. 390 Annotasyonun Protokolü
**Soru:** 390 annotasyonun protokolü neydi? Denetçiler iddianın yayınlanmış hükmünü gördüler mi?
**Cevap:** Depodaki `docs/EVALUATION_PROTOCOL.md` ve veriler incelendiğinde; 0.969 Fleiss Kappa gibi olağanüstü yüksek bir değer, bağımsız denetçilerin iddiaları kör (blind) olarak değerlendirmediklerini, büyük ihtimalle zaten yayınlanmış/bilinen hükümleri veya birbirlerinin kopyalarını girdiklerini göstermektedir. Bu sorunu çözmek adına **B2 görevi kapsamında**, sentetik iddialara gerçek ham veri setlerinden (isakulaksiz) semantik olarak en benzer, `corpus` içinde bulunmayan (izole edilmiş) donmuş (frozen) bir "iddia - kanıt - URL" değerlendirme seti (`frozen_eval_v1`) oluşturulmuştur.

## A6. Korpus Snapshot
**Soru:** K-1'den K-10'a kadar pipeline tam çalışıyor, evet. Ama korpusun anlık görüntüsü nerede? 9 Eylül 2026 itibarıyla retriever hangi vektör uzayında arama yapıyor?
**Cevap:** Korpusun anlık görüntüsü (snapshot) `data/corpus_snapshots/local_csv_20260909_v1/corpus.csv` dosyasında bulunmaktadır. B7 görevi sonrasında bu snapshot'ın içeriği provenance alanlarıyla zenginleştirilmiş olup, arama işlemi donmuş olan bu `.npy` vektör uzayı ve `.csv` dosyasındaki 30.347 kayıt üzerinden gerçekleşmektedir.

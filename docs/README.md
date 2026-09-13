# 📚 KızılelmAI Dokümantasyon ve Raporlar İndeksi

Bu dizin, KızılelmAI projesinin mimari kararlarını, akademik denetim yanıtlarını, model kalibrasyon süreçlerini ve resmi teknik raporlarını içerir.

---

## 📑 Raporlar ve Teknik Dokümanlar (`docs/reports/`)

| Tarih | Belge Adı | Açıklama / Kapsam |
|---|---|---|
| **2026-09-13** | [Tüm Düzeltmeler ve Sistem İyileştirme Raporu (v8)](reports/2026-09-13_kizilelmai_tum_duzeltmeler_ve_sistem_iyilestirme_raporu.md) | K-4 NLI etiket düzeltmesi, `e5-large` izolasyonu, v5→v8 sistem evrimi, FACTurk-500 tam karşılaştırma tablosu ve final v8 sistemi. |
| **2026-09-13** | [K-4 NLI Düzeltmesi ve İki Kapılı Doğrulama Raporu](reports/2026-09-13_k4_nli_duzeltmesi_ve_iki_kapili_dogrulama_raporu.md) | NLI tensör indeksleme (ters etiket) hatasının tespiti, Kapı 1 ve Kapı 2 matematiksel doğrulama protokolü. |
| **2026-09-12** | [Altı Mimari Düzeltme ve Kalibrasyon Raporu](reports/2026-09-12_alti_mimari_duzeltme_ve_kalibrasyon_raporu.md) | K-8 otorite tablosu, K-7 bağlam hafızası, K-9 konsensüs analizi ve K-6 yardımcı sinyal kalibrasyonları. |
| **2026-09-12** | [Hata Taksonomisi ve Risk Analizi](reports/2026-09-12_hata_taksonomisi_ve_risk_analizi.md) | Sayısal, zamansal, varlık ve bağlamsal hata kategorileri ve seçici tahmin (selective prediction) analizleri. |
| **2026-09-11** | [Akademik İnceleme Yanıtları ve Sistem Düzenlemeleri](reports/2026-09-11_danisman_denetim_yanitlari_ve_sistem_duzenlemeleri.md) | İlk denetim geri bildirimleri, sentetik gold setin geri çekilmesi, FACTurk bağımsız benchmark'ına geçiş süreci. |
| **2026-09-11** | [Hibrit Arama ve Kaynak Otorite Politikası](reports/2026-09-11_hibrit_arama_ve_kaynak_otorite_politikasi.md) | Dense (pgvector) + Sparse (BM25) RRF mantığı ve kaynak güvenilirlik puanlama politikası. |

---

## 🏛️ Politika ve Standart Belgeleri

* **Kaynak Otorite Politikası:** [`docs/AUTHORITY_POLICY.md`](AUTHORITY_POLICY.md) — Doğrulama kaynaklarının (Teyit.org, Malumatfuruş, Resmi Kurumlar, Ajanslar) güvenilirlik katsayıları ve matematiksel formülasyonu.
* **Tekrarlanabilirlik Manifestoları:** [`docs/reproducibility/`](reproducibility/) — Model mimarisi, checkpoint SHA-256 hash'leri ve yapılandırma bilgileri.

---

## 🔍 Hızlı Erişim

* **Deney Sonuçları ve Metrikler:** [`results/README.md`](../results/README.md)
* **Ana Sistem Tanıtımı ve Mimarisi:** [`README.md`](../README.md)

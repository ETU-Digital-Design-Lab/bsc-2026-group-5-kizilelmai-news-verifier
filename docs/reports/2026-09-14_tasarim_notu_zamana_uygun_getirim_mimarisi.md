# Tasarım Notu: Zamana Uygun Getirim Mimarisi (A Bileşeni Hazırlığı)

**Belge Türü:** 1 Sayfalık Mühendislik Tasarım Notu  
**Proje:** KızılelmAI — Hibrit Doğrulama Sistemi  
**Tarih:** 14 Eylül 2026  
**Yazarlar:** İbrahim Sinan AKBULUT, Doğukan KILIÇ  
**Danışman:** Dr. Öğr. Üyesi Latif AKÇAY  
**Hedef:** Statik korpusun zamansal tavanını (%38.2) aşarak, iddianın dönemine ait birincil haber kaynaklarından filtrelenmiş kanıt getirimi sağlamak.

---

## 1. Getirim Kaynağı ve Alan Adı Politikası

Statik korpustaki 2021 tavanı, 2022–2026 FACTurk iddialarının (%60.6) kanıtsız kalmasına ve sistemin mecburi çekimserliğe veya rastgele tahmine zorlanmasına neden olmaktadır. Bu sorunu çözmek için iddia zamanına duyarlı, açık web tabanlı birincil haber getiricisi tasarlanmıştır.

### 1.1. Kabul Edilen Birincil Haber ve Resmi Alan Adları (Whitelist)
Getirim araması yalnızca teyit edilmiş, kurumsal haber ajansları ve resmi devlet portallarıyla sınırlandırılacaktır:
- **Resmi Kurumlar:** `resmigazete.gov.tr`, `iletisim.gov.tr` (Dezenformasyonla Mücadele Merkezi dahil), `tbmm.gov.tr`, `tccb.gov.tr`, `tuik.gov.tr`, `saglik.gov.tr`
- **Haber Ajansları (Birincil):** `aa.com.tr` (Anadolu Ajansı), `dha.com.tr` (Demirören Haber Ajansı), `iha.com.tr` (İhlas Haber Ajansı), `anka.com.tr` (ANKA Haber Ajansı)
- **Güvenilir Ulusal Yayıncılar:** `trthaber.com`, `bbc.com/turkce`, `dw.com/tr`, `euronews.com/turkce`, `hurriyet.com.tr`, `milliyet.com.tr`, `sozcu.com.tr`, `haberturk.com`, `cumhuriyet.com.tr`, `ntv.com.tr`

### 1.2. Kesinlikle Dışlanacak Doğrulama Siteleri (Blacklist)
> [!IMPORTANT]
> **Bilimsel ve Metodolojik Kısıt:** `teyit.org`, `malumatfurus.org`, `dogrulukpayi.com`, `dogrula.org` ve `evrimagaci.org/dogrulama` alan adları getirim sorgularından ve indekslemeden **mutlak surette dışlanacaktır (`-site:teyit.org -site:malumatfurus.org ...`)**.  
> **Gerekçe:** FACTurk benchmark'ı doğrudan bu kuruluşların teyit bültenlerinden türetilmiştir. Sistemin bu sitelerden kanıt çekmesi bağımsız bir doğrulama yapmak değil, cevabı kopyalamak (ground-truth leakage) anlamına gelir. Hakem denetiminde bu sızıntı tespit edildiği an makale doğrudan reddedilir. Kanıt yalnızca olguyu haberleştiren birincil kaynaklardan gelecektir.

---

## 2. Arama Arayüzü ve Entegrasyon Mekanizması

Getirim boru hattı 3 kademeli çalışacaktır:

1. **Sorgu Üretimi (Query Generator):**
   - İddia metnindeki gürültü sözcükler temizlenir; temel özne, eylem ve zamansal çapa anahtar kelimeleri çıkarılır.
   - Arama sorgusuna alan adı kısıtları (`(site:aa.com.tr OR site:trthaber.com OR ...)`) ve dışlama kısıtları (`-site:teyit.org -site:malumatfurus.org -site:dogrulukpayi.com`) enjekte edilir.
2. **Arama Arayüzü (API / Retriever Engine):**
   - Birincil arayüz: **Google Custom Search JSON API** veya **Bing News Search API** (resmi kurumsal kotalı).
   - Alternatif / Çevrimdışı Geliştirme: **DuckDuckGo Python Search API** (`duckduckgo_search` kütüphanesi) haber sekmesi (`news=True`).
3. **Belge Çıkarma ve Parçalama (Scraping & Chunking):**
   - Dönen ilk 5 URL'nin tam metni `trafilatura` veya `readability` ile gürültüsüz (reklam, menü hariç) gövde metni olarak kazınır.
   - Metinler 256–512 tokenlik paragraflara bölünerek K-2 / K-3 katmanına aday havuzu olarak teslim edilir.

---

## 3. Zamansal Filtreleme Mekanizması (Temporal Guardrail)

Tarihsel sızıntıyı engellemek ve iddianın ortaya atıldığı dönemdeki olgusal gerçekliği yakalamak için iki kademeli zamansal filtre uygulanır:

1. **Sorgu Düzeyinde Zaman Penceresi:**
   - İddianın yayımlanma tarihi $t_{\text{claim}}$ belirlenir.
   - Arama motoru API'sine parametrik tarih filtresi verilir:  
     $$\text{Arama Aralığı} = [t_{\text{claim}} - 30\text{ gün}, \; t_{\text{claim}} + 7\text{ gün}]$$
   - $+7$ gün esnekliği, iddia ortaya atıldıktan sonraki günlerde çıkan tekzip veya resmi açıklamaların yakalanmasını sağlar; ancak geleceğe ait (örneğin aylar sonraki) retrospektif içeriklerin sızmasını kesin olarak engeller.
2. **Belge Düzeyinde Doğrulama:**
   - Kazınan belgenin HTML başlığındaki OpenGraph (`article:published_time`), Dublin Core (`DC.date.issued`) veya Schema.org (`datePublished`) etiketleri ayrıştırılır.
   - Belge tarihi $t_{\text{pub}} > t_{\text{claim}} + 7\text{ gün}$ ise belge aday havuzundan elenir.

---

## 4. Boru Hattına (K-3 $\to$ K-4 $\to$ K-5) Entegrasyon

- **K-3 (Re-Ranker):** Zamana uygun getirilen haber paragrafları ile iddia arasındaki alaka skoru `BAAI/bge-reranker-v2-m3` ile puanlanır. İlk 3 paragraf kanıt adayı seçilir.
- **K-4 (NLI):** Kanıt paragrafı (premise) ve iddia (hypothesis) XLM-RoBERTa tensör çıkarımına girer.
- **K-5 (Karar Katmanı):** İddia dönemiyle eşleşen birincil kanıt bulunduğu için sistem artık korpus zamansal tavanına takılmayacak; kanıtı olan örneklerde yüksek güvenle karar verecek, bulunamayanlarda ise güvenle çekimser (abstain) kalacaktır.

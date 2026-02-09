import pandas as pd
import os

# openpyxl kontrolü
try:
    import openpyxl
except ImportError:
    print("❌ HATA: openpyxl kütüphanesi eksik.")
    print("Lütfen şu komutu çalıştırın: pip install openpyxl")
    print("Veya tüm kütüphaneler için: pip install -r requirements.txt")
    exit(1)

# Eğer 'veriler' klasörü yoksa oluştur (Garanti olsun)
if not os.path.exists('veriler'):
    os.makedirs('veriler')

print("Dosyalar hazırlanıyor...")

# 1. GERÇEK HABER ÖRNEKLERİ (Artık daha fazla ve çeşitli)
gercek_haberler = [
    "Cumhurbaşkanı Erdoğan, kabine toplantısının ardından açıklamalarda bulundu.",
    "Türkiye'nin ilk yerli otomobili Togg, satış rekorları kırmaya devam ediyor.",
    "Meteoroloji Genel Müdürlüğü, Marmara Bölgesi için sağanak yağış uyarısı yaptı.",
    "Milli Eğitim Bakanlığı, okulların açılacağı tarihi resmi olarak duyurdu.",
    "Teknofest Havacılık, Uzay ve Teknoloji Festivali bu yıl İzmir'de düzenlenecek.",
    "Sağlık Bakanı, grip vakalarındaki artışa dikkat çekerek aşı uyarısında bulundu.",
    "Erzurum Teknik Üniversitesi öğrencileri yapay zeka projesiyle ödül aldı.",
    "Türkiye Cumhuriyet Merkez Bankası faiz kararını yarın açıklayacak.",
    "İstanbul'da trafik yoğunluğu sabah saatlerinde yüzde 70 seviyesine ulaştı.",
    "Milli sporcumuz Mete Gazoz, Avrupa Şampiyonası'nda altın madalya kazandı.",
    "ASELSAN, yeni geliştirdiği radar sistemini uluslararası fuarda tanıttı.",
    "Türkiye'nin turizm geliri geçen yılın aynı dönemine göre %15 arttı.",
    "Bilim Kurulu üyesi, maske takmanın önemine dair yeni bir makale yayınladı.",
    "THY, Avrupa'nın en çok uçuş yapan havayolu şirketi seçildi.",
    "İstanbul Borsası güne yükselişle başladı, BIST 100 endeksi rekor tazeledi.",
    "Tarım ve Orman Bakanlığı, çiftçilere yönelik yeni destek paketini açıkladı.",
    "Milli Savunma Bakanlığı, Pençe-Kilit operasyonunda ele geçirilen mühimmatları sergiledi.",
    "Yükseköğretim Kurumu (YÖK), üniversite kontenjanlarında düzenlemeye gitti.",
    "Türkiye Voleybol Federasyonu, Filenin Sultanları'nın maç takvimini paylaştı.",
    "BTK, sosyal medya düzenlemesiyle ilgili yeni yönetmeliği Resmi Gazete'de yayımladı.",
    "Deprem uzmanları, İstanbul için kentsel dönüşümün hızlanması gerektiğini vurguladı.",
    "Karadeniz'de bulunan doğalgaz rezervi sisteme entegre edilmeye başlandı.",
    "TÜİK, aylık enflasyon rakamlarını kamuoyu ile paylaştı.",
    "Milli kütüphane, dijital arşiviyle araştırmacılara ücretsiz hizmet vermeye başladı.",
    "Gençlik ve Spor Bakanlığı, yaz kampları başvurularının başladığını duyurdu."
]

# 2. YALAN HABER ÖRNEKLERİ (Komplo teorileri ve tıklama tuzakları artırıldı)
yalan_haberler = [
    "Şok iddia! Uzaylılar dün gece Ankara semalarında görüldü, işte görüntüler.",
    "Limonlu su içmek kanseri 3 günde tamamen yok ediyor, doktorlar saklıyor!",
    "Whatsapp bu geceden itibaren paralı olacak, bu mesajı 10 kişiye gönderin.",
    "Ünlü sanatçı hayatını kaybetti! (Tıklama tuzağı, aslında ölmedi)",
    "Hükümet herkese bedava araba dağıtacakmış, başvurular başladı.",
    "Gökten balık yağdı! Bilim insanları şaşkınlık içinde.",
    "Gizli dünya devleti, nüfusu azaltmak için sulara ilaç karıştırıyor.",
    "Mars'ta insan iskeleti bulundu, NASA görüntüleri sildi.",
    "Bu kürü yaparsanız 1 haftada 20 kilo verirsiniz, garanti yöntem.",
    "Elektrik faturaları artık ödenmeyecek, yeni kararname sızdı!",
    "Japon bilim insanları açıkladı: İnsanlar aslında simülasyonda yaşıyor!",
    "Banka hesaplarına gizlice para yatırılıyor, hemen kontrol edin!",
    "Bu meyveyi yiyen bir daha asla hasta olmuyor, eczaneler kapatılacak.",
    "5G direkleri virüs yayıyor, mahallenizdeki direkleri kontrol edin.",
    "Emeklilere her ay 50 bin TL ikramiye verilecekmiş, resmi açıklama yok ama kesin bilgi.",
    "Ünlü futbolcu uzaylılar tarafından kaçırıldığını iddia etti.",
    "Dünya aslında düzdür, NASA fotoğrafları photoshop ile yapıyor.",
    "Evinizdeki kediler aslında sizi izleyen ajan robotlar olabilir!",
    "Telefonunuzu mikrodalgaya koyarsanız şarjı 1 hafta gidiyor.",
    "Maden suyu içmek kemikleri eritiyor, sakın içmeyin!",
    "Tarihi eser kaçakçıları piramitlerin altında zaman makinesi buldu.",
    "Kola içmek DNA'nızı değiştiriyor, insanlıktan çıkabilirsiniz.",
    "Facebook profilinize bunu yazmazsanız tüm fotoğraflarınız halka açık olacak.",
    "Devlet herkese bedava iPhone dağıtacakmış, sıraya girin!",
    "Yarın internet tamamen kesilecek, bir daha gelmeyecek."
]

# DataFrame oluştur
df_gercek = pd.DataFrame({'text': gercek_haberler})
df_yalan = pd.DataFrame({'text': yalan_haberler}) 

# Dosyaları 'veriler' klasörüne CSV olarak kaydet (UTF-8 önemli, Türkçe karakterler için)
try:
    df_gercek.to_csv("veriler/gercekler.csv", index=False, encoding='utf-8')
    print(f"✅ 'veriler/gercekler.csv' oluşturuldu. ({len(gercek_haberler)} adet)")
except Exception as e:
    print(f"❌ HATA: Gerçekler CSV oluşturulurken hata: {e}")

try:
    df_yalan.to_csv("veriler/yalanlar.csv", index=False, encoding='utf-8')
    print(f"✅ 'veriler/yalanlar.csv' oluşturuldu. ({len(yalan_haberler)} adet)")
except Exception as e:
    print(f"❌ HATA: Yalanlar CSV oluşturulurken hata: {e}")

print("\n--- İŞLEM TAMAM ---")

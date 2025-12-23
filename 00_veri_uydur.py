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

# 1. GERÇEK HABER ÖRNEKLERİ (Excel formatında olacak)
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
    "Milli sporcumuz, Avrupa Şampiyonası'nda altın madalya kazandı."
]

# 2. YALAN HABER ÖRNEKLERİ (CSV formatında olacak)
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
    "Elektrik faturaları artık ödenmeyecek, yeni kararname sızdı!"
]

# DataFrame oluştur
df_gercek = pd.DataFrame({'Haber Metni': gercek_haberler})
df_yalan = pd.DataFrame({'text': yalan_haberler}) 

# Dosyaları 'veriler' klasörüne kaydet
try:
    df_gercek.to_excel("veriler/gercekler.xlsx", index=False)
    print("✅ 'veriler/gercekler.xlsx' oluşturuldu.")
except Exception as e:
    print(f"❌ HATA: Excel dosyası oluşturulurken hata: {e}")
    exit(1)

try:
    df_yalan.to_csv("veriler/yalanlar.csv", index=False)
    print("✅ 'veriler/yalanlar.csv' oluşturuldu.")
except Exception as e:
    print(f"❌ HATA: CSV dosyası oluşturulurken hata: {e}")
    exit(1)

print("\n--- İŞLEM TAMAM ---")  
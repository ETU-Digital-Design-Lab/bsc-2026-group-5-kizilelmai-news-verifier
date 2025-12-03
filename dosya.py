import os
import sys

# Rapor İçeriği (HTML formatında Word uyumlu)
html_content = """
<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
<meta charset="utf-8">
<style>
    body { font-family: 'Times New Roman', serif; line-height: 1.5; font-size: 12pt; }
    h1 { color: #b71c1c; text-align: center; text-transform: uppercase; font-size: 16pt; margin-bottom: 24px; }
    h2 { color: #0d47a1; border-bottom: 1px solid #0d47a1; padding-bottom: 5px; margin-top: 30px; font-size: 14pt; }
    h3 { color: #333; margin-top: 20px; font-size: 12pt; font-weight: bold; }
    p { margin-bottom: 10px; text-align: justify; }
    table { border-collapse: collapse; width: 100%; margin-top: 15px; margin-bottom: 15px; }
    th, td { border: 1px solid #000; padding: 10px; text-align: left; vertical-align: top; }
    th { background-color: #f5f5f5; font-weight: bold; }
    .center { text-align: center; }
</style>
</head>
<body>

<br><br><br>
<h1 style="font-size: 24pt;">KIZILELMAI</h1>
<h2 style="text-align: center; border: none; font-size: 18pt;">STATİK VERİ SETLERİ İLE EĞİTİLMİŞ<br>YAPAY ZEKA TABANLI DOĞRULUK ANALİZ SİSTEMİ</h2>
<br><br>
<p class="center"><b>Doküman Tipi:</b> Teknik Tasarım Raporu (Kaggle Dataset Entegrasyonu)</p>
<br><br><br>
<table style="width: 60%; margin-left: auto; margin-right: auto; border: none;">
    <tr style="border: none;"><td style="border: none;"><b>Proje Yürütücüsü:</b></td><td style="border: none;">Mevy</td></tr>
    <tr style="border: none;"><td style="border: none;"><b>Veri Kaynağı:</b></td><td style="border: none;">Kaggle & Açık Kaynak Veri Setleri</td></tr>
    <tr style="border: none;"><td style="border: none;"><b>Eğitim Yöntemi:</b></td><td style="border: none;">Denetimli Öğrenme (Supervised Learning)</td></tr>
</table>

<br clear=all style='mso-special-character:line-break;page-break-before:always'>

<h2>1. PROJE KAPSAMI VE VERİ STRATEJİSİ</h2>
<p>KızılelmAI, canlı veri kazıma (web scraping) yönteminin getirdiği yasal ve teknik riskleri elimine etmek amacıyla, eğitim sürecini <b>Statik Veri Setleri (Kaggle)</b> üzerine kurgulamıştır. Amaç, önceden etiketlenmiş binlerce haber verisi üzerinde modeli eğiterek "Manipülatif Dil" ve "Sahte Haber" örüntülerini sisteme öğretmektir.</p>

<h2>2. VERİ İŞLEME AKIŞI (PIPELINE)</h2>
<p>Proje, <b>Extract-Transform-Load (ETL)</b> ve <b>Training</b> olmak üzere iki ana aşamadan oluşur:</p>

<h3>Aşama 1: Veri Hazırlığı (Kaggle Entegrasyonu)</h3>
<ul>
    <li><b>Veri Kaynağı:</b> Kaggle üzerindeki "Turkish News", "Turkish Fake News Dataset" gibi CSV/JSON dosyaları indirilecektir.</li>
    <li><b>Veri Temizliği (Preprocessing):</b>
        <ul>
            <li>HTML etiketlerinin temizlenmesi.</li>
            <li>Stop-words (ve, veya, ama gibi etkisiz kelimeler) temizliği.</li>
            <li><b>Zemberek Kütüphanesi</b> ile kelimelerin köklerine (Lemma) indirgenmesi.</li>
        </ul>
    </li>
    <li><b>Tokenization:</b> Temizlenen metinlerin BERTurk tokenizer kullanılarak sayısal ID'lere dönüştürülmesi.</li>
</ul>

<h3>Aşama 2: Model Eğitimi (Classification)</h3>
<ul>
    <li><b>Manipülasyon Tespiti:</b> Etiketli veri setleri (Doğru/Yanlış) kullanılarak model "Denetimli Öğrenme" ile eğitilecektir.</li>
    <li><b>Algoritma:</b> BERTurk (Transfer Learning) veya LSTM kullanılacaktır. Model, kelime dizilimlerinden haberin "dili"nin manipülatif olup olmadığını öğrenecektir.</li>
</ul>

<h2>3. SİSTEM MİMARİSİ</h2>
<table>
    <tr>
        <th>Katman</th>
        <th>Teknoloji</th>
        <th>Açıklama</th>
    </tr>
    <tr>
        <td><b>Eğitim Ortamı</b></td>
        <td>Jupyter Notebook / Google Colab</td>
        <td>Kaggle verilerinin işlenmesi ve modelin eğitilip `.bin` dosyası olarak kaydedilmesi.</td>
    </tr>
    <tr>
        <td><b>NLP Kütüphaneleri</b></td>
        <td>PyTorch, Transformers, Zemberek</td>
        <td>Model mimarisi ve Türkçe morfolojik analiz.</td>
    </tr>
    <tr>
        <td><b>Inference (Tahmin) API</b></td>
        <td>FastAPI</td>
        <td>Eğitilmiş modelin canlı sistemde çalıştırılması.</td>
    </tr>
</table>

<h2>4. 6 AYLIK İŞ PLANI (KAGGLE ODAKLI)</h2>

<table>
    <tr>
        <th>Zaman</th>
        <th>İş Paketi</th>
        <th>Detaylar</th>
    </tr>
    <tr>
        <td><b>1. Ay</b></td>
        <td>Veri Seti Analizi ve Temini</td>
        <td>Kaggle'dan uygun Türkçe veri setlerinin indirilmesi. Pandas ile EDA (Keşifçi Veri Analizi) yapılması. Sınıf dağılımlarının (Doğru/Yanlış) dengelenmesi.</td>
    </tr>
    <tr>
        <td><b>2. Ay</b></td>
        <td>NLP Ön İşleme (Preprocessing)</td>
        <td>Verilerin temizlenmesi. Zemberek entegrasyonu ile kelime köklerinin bulunması. Verinin "Eğitim" ve "Test" olarak %80-%20 ayrılması.</td>
    </tr>
    <tr>
        <td><b>3. Ay</b></td>
        <td>Model Eğitimi (Training)</td>
        <td>BERTurk modelinin Kaggle verisiyle Fine-Tuning işlemi. Loss ve Accuracy grafiklerinin takibi.</td>
    </tr>
    <tr>
        <td><b>4. Ay</b></td>
        <td>Model Değerlendirme ve İyileştirme</td>
        <td>F1-Score, Precision ve Recall metriklerine bakılması. Modelin aşırı öğrenme (Overfitting) durumunun kontrolü.</td>
    </tr>
    <tr>
        <td><b>5. Ay</b></td>
        <td>API Geliştirme</td>
        <td>Eğitilen model dosyasının FastAPI içerisine gömülmesi. Mobil uygulama için endpoint açılması.</td>
    </tr>
    <tr>
        <td><b>6. Ay</b></td>
        <td>Mobil Entegrasyon ve Final</td>
        <td>Flutter uygulamasının API'ye bağlanması. Canlı demoların yapılması.</td>
    </tr>
</table>

<h2>5. RİSK YÖNETİMİ</h2>
<ul>
    <li><b>Risk:</b> Kaggle veri setlerinin güncel olmaması.<br>
    <b>Çözüm:</b> Modelin öğrendiği "dil yapısı" zamansızdır. Ancak güncel olaylar için sisteme manuel olarak küçük bir "Güncel Doğrular" veri tabanı eklenecektir.</li>
    <li><b>Risk:</b> Veri setinin yanlı (bias) olması.<br>
    <b>Çözüm:</b> Farklı kaynaklardan (Kaggle dışı açık kaynak GitHub repoları) verilerle set zenginleştirilecektir.</li>
</ul>

<br><br>
<p class="center"><i>Rapor Sonu</i></p>

</body>
</html>
"""

# Dosyayı kaydet
file_name = "kizilelmai_kaggle_teknik_rapor.doc"

try:
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(html_content)
    print(f"BAŞARILI: '{file_name}' dosyası bulunduğunuz klasöre oluşturuldu.")
    print(f"Tam Yol: {os.path.abspath(file_name)}")
except PermissionError:
    print(f"HATA: '{file_name}' dosyası şu an açık olabilir. Lütfen Word'ü kapatıp tekrar deneyin.")
except Exception as e:
    print(f"BEKLENMEYEN HATA: {e}")
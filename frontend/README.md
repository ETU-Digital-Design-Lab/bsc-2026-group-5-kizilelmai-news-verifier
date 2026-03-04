🚀 KızılelmAI - Kurulum ve Çalıştırma Kılavuzu
Bu proje, yapay zeka destekli dezenformasyon tespit sistemi olan KızılelmAI'nın Flutter tabanlı frontend ve mobil arayüzünü içermektedir.

🛠️ Ön Hazırlık
Projeyi çalıştırmadan önce sisteminizde aşağıdaki bileşenlerin yüklü olduğundan emin olun:

Flutter SDK: Yükleme Kılavuzu (Stable Channel)

Dart SDK: Flutter ile birlikte otomatik yüklenir.

IDE: VS Code (Önerilen) veya Android Studio.

Tarayıcı: Chrome veya Safari (Web testi için).

📥 Adım 1: Bağımlılıkları Yükleme
Terminali açın ve projenin bulunduğu dizine girerek paketleri güncelleyin:

Bash
cd frontend
flutter pub get
🌐 Adım 2: Web Platformunda Çalıştırma (Chrome / Safari)
Tasarımı ve genel akışı test etmek için en hızlı yöntemdir.

Cihaz Listesini Kontrol Edin:

Bash
flutter devices
Chrome ile Başlatın:

Bash
flutter run -d chrome
Safari ile Başlatın (macOS):

Bash
flutter run -d safari
📱 Adım 3: Mobil Platformda Çalıştırma
A. Emülatör / Simülatör (Sanal Cihaz)

iOS Simülatörü (Sadece Mac): Xcode üzerinden bir simülatör açın ve çalıştırın:

Bash
flutter run -d ios
Android Emulator: Android Studio üzerinden bir AVD (Android Virtual Device) başlatın:

Bash
flutter run -d android
B. Fiziksel Telefon (Kendi Cihazınız)

Android:

Telefonunuzdan "Geliştirici Seçenekleri"ni ve "USB Hata Ayıklama"yı açın.

Kablo ile bağlayın ve flutter run komutunu yazın.

iOS (iPhone):

iPhone'u Mac'e bağlayın.

ios/Runner.xcworkspace dosyasını Xcode ile açın.

Signing & Capabilities kısmından kendi Apple ID'niz ile bir "Team" seçin.

Terminalden flutter run yazarak başlatın.

⚠️ Önemli Notlar

Hata Ayıklama (Debug): Eğer MyApp veya paket yollarıyla ilgili kırmızı hata alırsanız, VS Code üzerinden KizilelmaAIApp ismini kullandığınızdan emin olun.

Bağlantı Sorunları: Eğer analiz paneli yanıt vermiyorsa, backend servisinin (src/backend/app.py) çalıştığından ve URL tanımlarının doğru olduğundan emin olun.
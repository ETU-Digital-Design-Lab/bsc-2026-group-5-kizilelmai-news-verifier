import 'package:flutter/material.dart';
import '../constants.dart';
import '../widgets/analysis_panel.dart';
import '../widgets/sections.dart';
import '../widgets/marquee_ticker.dart';

/// Mobil cihazlar (< 900px) için optimize edilmiş yerleşim düzeni.
/// Alt navigasyon çubuğu (BottomAppBar) ve Docked FAB (Ortalanmış Buton) mimarisini kullanır.
/// Sayfalar arası geçiş, [State] yönetimi ile aynı ekranda yapılır.
class MobileLayout extends StatefulWidget {
  final VoidCallback onSettingsTap;
  const MobileLayout({super.key, required this.onSettingsTap});

  @override
  State<MobileLayout> createState() => _MobileLayoutState();
}

class _MobileLayoutState extends State<MobileLayout> {
  // Varsayılan olarak Ana Sayfa (Index 1) açılır
  int _mobileIndex = 1;

  @override
  Widget build(BuildContext context) {
    // Aktif sayfa seçimi
    Widget activePage;
    switch (_mobileIndex) {
      case 0:
        activePage = const SingleChildScrollView(child: MissionSection(isWeb: false));
        break;
      case 2:
        activePage = const SingleChildScrollView(child: TeamSection(isWeb: false));
        break;
      case 1:
      default:
        activePage = _buildPanelPage();
        break;
    }

    return Scaffold(
      // Klavye açıldığında UI'ın bozulmasını önler (Pixel Overflow koruması)
      resizeToAvoidBottomInset: true, 
      
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                // En üstte sabit kayan yazı
                const MarqueeTickerModule(), 
                // Altında değişen içerik alanı
                Expanded(child: activePage),
              ],
            ),
            
            // Sağ üst köşedeki Ayarlar Butonu (Floating)
            Positioned(
              top: 50, // Marquee'nin hemen altına hizalar
              right: 15,
              child: FloatingActionButton.small(
                heroTag: "settings_btn",
                onPressed: widget.onSettingsTap,
                backgroundColor: AppColors.cardColor,
                elevation: 4,
                child: const Icon(Icons.settings, color: AppColors.primaryRed),
              ),
            )
          ],
        ),
      ),

      // Ortadaki Büyük Logo Butonu (Ana Sayfaya Dönüş)
      floatingActionButton: SizedBox(
        width: 70, height: 70,
        child: FloatingActionButton(
          heroTag: "main_fab",
          onPressed: () => setState(() => _mobileIndex = 1), 
          backgroundColor: AppColors.primaryRed, 
          elevation: 10,
          shape: const CircleBorder(),
          child: Padding(
            padding: const EdgeInsets.all(10.0),
            child: Image.asset('assets/images/new_logo_1.png', color: Colors.white),
          ),
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,

      // Alt Navigasyon Menüsü
      bottomNavigationBar: BottomAppBar(
        color: AppColors.cardColor,
        shape: const CircularNotchedRectangle(), // FAB için oyuk oluşturur
        notchMargin: 8.0,
        child: SizedBox(
          height: 60,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildNavBtn(Icons.info_outline, Icons.info, "Misyon", 0),
              // Ortada FAB için boşluk bırakıyoruz
              const SizedBox(width: 40), 
              _buildNavBtn(Icons.groups_outlined, Icons.groups, "Ekip", 2),
            ],
          ),
        ),
      ),
    );
  }

  /// Alt menü butonlarını oluşturan yardımcı metot.
  /// Aktif durumda rengi ve ikonu değiştirir.
  Widget _buildNavBtn(IconData icon, IconData activeIcon, String label, int index) {
    bool isActive = _mobileIndex == index;
    return InkWell(
      onTap: () => setState(() => _mobileIndex = index),
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isActive ? activeIcon : icon, 
              color: isActive ? AppColors.primaryRed : Colors.grey, 
              size: 26
            ),
            Text(
              label, 
              style: TextStyle(
                color: isActive ? AppColors.primaryRed : Colors.grey, 
                fontSize: 11, 
                fontWeight: isActive ? FontWeight.bold : FontWeight.normal
              )
            )
          ],
        ),
      ),
    );
  }

  /// Ana Sayfa içeriği (Logo + Slogan + Analiz Paneli)
  Widget _buildPanelPage() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 10.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(height: 10),
            
            // Logo Alanı
            Container(
              height: 120, width: 120,
              decoration: BoxDecoration(
                color: Colors.white, 
                shape: BoxShape.circle, 
                boxShadow: [
                  BoxShadow(color: AppColors.primaryRed.withOpacity(0.4), blurRadius: 20, spreadRadius: 2)
                ]
              ),
              child: ClipOval(
                child: Padding(
                  padding: const EdgeInsets.all(8.0), 
                  child: Image.asset('assets/images/new_logo_1.png', fit: BoxFit.contain)
                )
              ),
            ),
            const SizedBox(height: 15),
            
            // Slogan
            const Text(
              "GELECEĞİN SAVAŞLARI ALGI ÜZERİNDEN YÜRÜTÜLÜR.", 
              textAlign: TextAlign.center, 
              style: TextStyle(
                fontSize: 14, 
                fontWeight: FontWeight.w600, 
                color: Colors.white70, 
                letterSpacing: 0.5
              )
            ),
            const SizedBox(height: 25),
            
            // Analiz Paneli (Mobil Modunda)
            const AnalysisPanel(isWeb: false),
            
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
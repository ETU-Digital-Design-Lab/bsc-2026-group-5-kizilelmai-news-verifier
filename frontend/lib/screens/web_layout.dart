import 'package:flutter/material.dart';
import '../constants.dart';
import '../widgets/analysis_panel.dart';
import '../widgets/sections.dart';
import '../widgets/marquee_ticker.dart';

/// Web sürümü için ana yerleşim düzeni (Layout).
/// Tek sayfa (One-Page) mantığıyla çalışır ve üst menüden ilgili bölümlere (Panel, Misyon, Ekip)
/// yumuşak kaydırma (Smooth Scroll) ile geçiş sağlar.
class WebLayout extends StatefulWidget {
  final VoidCallback onSettingsTap;
  const WebLayout({super.key, required this.onSettingsTap});

  @override
  State<WebLayout> createState() => _WebLayoutState();
}

class _WebLayoutState extends State<WebLayout> {
  // Navigasyon için hedef anahtarları (Scroll Anchors)
  final GlobalKey _webPanelKey = GlobalKey();
  final GlobalKey _webMissionKey = GlobalKey();
  final GlobalKey _webTeamKey = GlobalKey();

  /// Belirtilen GlobalKey'in bulunduğu widget'a yumuşak geçişle kaydırır.
  void _scrollToSection(GlobalKey key) {
    if (key.currentContext != null) {
      Scrollable.ensureVisible(
        key.currentContext!,
        duration: const Duration(seconds: 1),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    // Ekran yüksekliğinden AppBar payını düşüyoruz
    double screenHeight = MediaQuery.of(context).size.height - 60;

    return Scaffold(
      appBar: _buildAppBar(),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // 1. Ana Panel (Logo + Slogan + Analiz Kutusu)
            SizedBox(
              key: _webPanelKey,
              // Minimum 800px yükseklik garanti edilir, ekran büyükse ekranı kaplar
              height: screenHeight > 800 ? screenHeight : 800,
              child: _buildPanelPage(),
            ),
            
            // 2. Misyon ve Teknoloji Bölümü
            Container(
              key: _webMissionKey, 
              child: const MissionSection(isWeb: true)
            ),
            
            // 3. Ekip Bölümü
            Container(
              key: _webTeamKey, 
              child: const TeamSection(isWeb: true)
            ),
            
            const SizedBox(height: 50),
          ],
        ),
      ),
      bottomNavigationBar: const MarqueeTickerModule(),
    );
  }

  /// Web için özel tasarlanmış AppBar
  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: AppColors.cardColor, // Tema rengine bağlandı
      elevation: 0,
      automaticallyImplyLeading: false,
      title: Row(
        children: [
          Container(
            height: 35, width: 35, 
            padding: const EdgeInsets.all(2),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
            child: Image.asset('assets/images/new_logo_1.png'),
          ),
          const SizedBox(width: 12),
          const Text(
            "KIZILELM-AI", 
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 2, fontSize: 18)
          ),
        ],
      ),
      actions: [
        // Navigasyon Butonları
        _navBtn("PANEL", _webPanelKey),
        _navBtn("MİSYON", _webMissionKey),
        _navBtn("EKİP", _webTeamKey),
        const SizedBox(width: 20),
        
        // Ayarlar Butonu
        IconButton(
          onPressed: widget.onSettingsTap,
          icon: const Icon(Icons.settings, color: AppColors.primaryRed),
          tooltip: "Görünüm Ayarları",
        ),
        const SizedBox(width: 10),
        
        // Online Durum Göstergesi
        Container(
          margin: const EdgeInsets.only(right: 24),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.green.withOpacity(0.5)), 
            borderRadius: BorderRadius.circular(4), 
            color: Colors.green.withOpacity(0.1)
          ),
          child: const Row(
            children: [
              Icon(Icons.circle, size: 8, color: Colors.green), 
              SizedBox(width: 6), 
              Text("ONLINE", style: TextStyle(color: Colors.green, fontSize: 11, fontWeight: FontWeight.bold))
            ],
          ),
        )
      ],
    );
  }

  /// Üst menü butonlarını oluşturan yardımcı metot
  Widget _navBtn(String title, GlobalKey targetKey) {
    return TextButton(
      onPressed: () => _scrollToSection(targetKey),
      style: TextButton.styleFrom(foregroundColor: Colors.white70),
      child: Text(
        title, 
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 1)
      ),
    );
  }

  /// Sayfanın ortasındaki Hero (Karşılama) bölümü
  Widget _buildPanelPage() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Parlayan Logo Efekti
          Container(
            height: 160, width: 160, 
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: Colors.white, 
              shape: BoxShape.circle, 
              boxShadow: [
                BoxShadow(color: AppColors.primaryRed.withOpacity(0.6), blurRadius: 40, spreadRadius: 2)
              ]
            ),
            child: Image.asset('assets/images/new_logo_1.png'),
          ),
          const SizedBox(height: 30),
          
          // Slogan
          const Text(
            "GELECEĞİN SAVAŞLARI\nALGI ÜZERİNDEN YÜRÜTÜLÜR.", 
            textAlign: TextAlign.center, 
            style: TextStyle(
              fontSize: 26, 
              fontWeight: FontWeight.w900, 
              color: Colors.white, 
              height: 1.1, 
              letterSpacing: -1
            )
          ),
          const SizedBox(height: 40),
          
          // Analiz Paneli (Web modunda)
          const AnalysisPanel(isWeb: true),
        ],
      ),
    );
  }
}
import 'package:flutter/material.dart';
import '../constants.dart';
import '../widgets/analysis_panel.dart';
import '../widgets/sections.dart';
import '../widgets/marquee_ticker.dart';
import '../widgets/footer_section.dart'; 

class WebLayout extends StatefulWidget {
  final VoidCallback onSettingsTap;
  const WebLayout({super.key, required this.onSettingsTap});

  @override
  State<WebLayout> createState() => _WebLayoutState();
}

class _WebLayoutState extends State<WebLayout> {
  final GlobalKey _webPanelKey = GlobalKey();
  final GlobalKey _webMissionKey = GlobalKey();
  final GlobalKey _webTeamKey = GlobalKey();

  void _scrollToSection(GlobalKey key) {
    if (key.currentContext != null) {
      Scrollable.ensureVisible(key.currentContext!, duration: const Duration(seconds: 1), curve: Curves.easeInOut);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Ekranın toplam yüksekliğini alıyoruz
    double screenHeight = MediaQuery.of(context).size.height;
    bool isLight = Theme.of(context).brightness == Brightness.light;

    return Scaffold(
      backgroundColor: Colors.transparent, 
      appBar: _buildAppBar(isLight),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // 1. ANA PANEL
            // MinHeight ile esnek yapı korundu (Patlamaz)
            Container(
              key: _webPanelKey,
              constraints: BoxConstraints(
                minHeight: screenHeight - 60, // AppBar payını düş
              ),
              padding: const EdgeInsets.symmetric(vertical: 40), 
              child: _buildPanelPage(isLight),
            ),
            
            // 2. MİSYON BÖLÜMÜ
            Container(key: _webMissionKey, child: const MissionSection(isWeb: true)),
            
            // 3. EKİP BÖLÜMÜ
            Container(key: _webTeamKey, child: const TeamSection(isWeb: true)),
            
            // 4. FOOTER (ALT BİLGİ)
            const FooterSection(isWeb: true),
          ],
        ),
      ),
      bottomNavigationBar: const MarqueeTickerModule(),
    );
  }

  PreferredSizeWidget _buildAppBar(bool isLight) {
    return AppBar(
      backgroundColor: isLight ? Colors.transparent : AppColors.cardDark,
      elevation: 0,
      automaticallyImplyLeading: false,
      iconTheme: IconThemeData(color: isLight ? AppColors.primary : Colors.white),
      title: Row(
        children: [
          isLight 
            ? Image.asset('assets/images/new_logo_1.png', height: 40) 
            : Container(
                height: 35, width: 35, padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
                child: Image.asset('assets/images/new_logo_1.png'),
              ),
          const SizedBox(width: 12),
          // --- BRANDING GÜNCELLEMESİ ---
          Text(
            "KızılelmAI", // Eskisi: KIZILELM-AI
            style: TextStyle(
              color: isLight ? AppColors.primary : Colors.white,
              fontWeight: FontWeight.w900, // Daha kalın (Logo fontuna yakın)
              letterSpacing: 1, // Harf aralığı sıkılaştırıldı
              fontSize: 20 // Bir tık büyütüldü
            )
          ),
        ],
      ),
      actions: [
        _navBtn("PANEL", _webPanelKey, isLight),
        _navBtn("MİSYON", _webMissionKey, isLight),
        _navBtn("EKİP", _webTeamKey, isLight),
        const SizedBox(width: 20),
        IconButton(
          onPressed: widget.onSettingsTap,
          icon: Icon(Icons.settings, color: isLight ? AppColors.primary : AppColors.primaryDark),
        ),
        const SizedBox(width: 10),
        Container(
          margin: const EdgeInsets.only(right: 24),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(border: Border.all(color: Colors.green.withOpacity(0.5)), borderRadius: BorderRadius.circular(4), color: Colors.green.withOpacity(0.1)),
          child: const Row(children: [Icon(Icons.circle, size: 8, color: Colors.green), SizedBox(width: 6), Text("ONLINE", style: TextStyle(color: Colors.green, fontSize: 11, fontWeight: FontWeight.bold))]),
        )
      ],
    );
  }

  Widget _navBtn(String title, GlobalKey targetKey, bool isLight) {
    return TextButton(
      onPressed: () => _scrollToSection(targetKey),
      style: TextButton.styleFrom(foregroundColor: isLight ? AppColors.secondary : Colors.white70),
      child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 1)),
    );
  }

  Widget _buildPanelPage(bool isLight) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          
          // --- LOGO BÖLÜMÜ ---
          Container(
            height: 280, width: 280,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: isLight 
                    ? AppColors.primary.withOpacity(0.2) 
                    : AppColors.primaryRed.withOpacity(0.4), 
                  blurRadius: 60,
                  spreadRadius: 10,
                ),
              ]
            ),
            child: Image.asset('assets/images/new_logo_1.png'),
          ),
            
          const SizedBox(height: 40),
          
          ShaderMask(
            shaderCallback: (Rect bounds) {
              return LinearGradient(
                colors: isLight 
                    ? [AppColors.secondary, AppColors.primary] 
                    : [Colors.white, Colors.grey.shade400],    
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ).createShader(bounds);
            },
            child: const Text(
              "GELECEĞİN SAVAŞLARI\nALGI ÜZERİNDEN YÜRÜTÜLÜR.", 
              textAlign: TextAlign.center, 
              style: TextStyle(
                fontSize: 36, 
                fontWeight: FontWeight.w900, 
                color: Colors.white, 
                height: 1.1, 
                letterSpacing: -1
              ),
            ),
          ),
          
          if (isLight) ...[
            const SizedBox(height: 15),
            Text("Yapay zeka destekli dezenformasyon tespit sistemi.", style: TextStyle(color: AppColors.secondary.withOpacity(0.7), fontSize: 16)),
          ],

          const SizedBox(height: 40),
          const AnalysisPanel(isWeb: true),
        ],
      ),
    );
  }
}
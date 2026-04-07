import 'package:flutter/material.dart';
import '../constants.dart';
import '../widgets/analysis_panel.dart';
import '../widgets/sections.dart';
import '../widgets/marquee_ticker.dart';
import '../widgets/footer_section.dart'; 

class MobileLayout extends StatefulWidget {
  final VoidCallback onSettingsTap;
  const MobileLayout({super.key, required this.onSettingsTap});

  @override
  State<MobileLayout> createState() => _MobileLayoutState();
}

class _MobileLayoutState extends State<MobileLayout> {
  // Kaydırma için Anahtarlar
  final GlobalKey _panelKey = GlobalKey();
  final GlobalKey _missionKey = GlobalKey();
  final GlobalKey _teamKey = GlobalKey();

  void _scrollToSection(GlobalKey key) {
    Navigator.pop(context); // Menüyü kapat
    if (key.currentContext != null) {
      Scrollable.ensureVisible(
        key.currentContext!, 
        duration: const Duration(seconds: 1), 
        curve: Curves.easeInOut
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    bool isLight = Theme.of(context).brightness == Brightness.light;

    return Scaffold(
      backgroundColor: Colors.transparent, // Arkaplan HomePage'den geliyor
      appBar: _buildAppBar(isLight),
      drawer: _buildDrawer(isLight), // Yan Menü
      body: SingleChildScrollView(
        physics: const ClampingScrollPhysics(),
        child: Column(
          children: [
            const SizedBox(height: 20),
            
            // 1. LOGO ALANI
            _buildHeroSection(isLight),

            // 2. ANALİZ PANELİ
            SizedBox(key: _panelKey, child: const AnalysisPanel(isWeb: false)),

            // 3. MİSYON BÖLÜMÜ
            Container(key: _missionKey, child: const MissionSection(isWeb: false)),

            // 4. EKİP BÖLÜMÜ
            Container(key: _teamKey, child: const TeamSection(isWeb: false)),

            // 5. FOOTER (ALT BİLGİ)
            const FooterSection(isWeb: false),
          ],
        ),
      ),
      bottomNavigationBar: const MarqueeTickerModule(),
    );
  }

  PreferredSizeWidget _buildAppBar(bool isLight) {
    return AppBar(
      backgroundColor: isLight ? Colors.transparent : AppColors.cardDark.withOpacity(0.8),
      elevation: 0,
      centerTitle: true,
      iconTheme: IconThemeData(color: isLight ? AppColors.primary : Colors.white),
      title: Text(
        "KızılelmAI", // DÜZELTİLDİ
        style: TextStyle(
          color: isLight ? AppColors.primary : Colors.white,
          fontWeight: FontWeight.w900, // Logo fontu gibi kalın
          letterSpacing: 1,
          fontSize: 20 // Mobilde de okunur ve şık olsun
        ),
      ),
      actions: [
        IconButton(
          onPressed: widget.onSettingsTap,
          icon: const Icon(Icons.settings),
        ),
        const SizedBox(width: 10),
      ],
    );
  }

  // YAN MENÜ (DRAWER)
  Widget _buildDrawer(bool isLight) {
    Color drawerBg = isLight ? Colors.white : const Color(0xFF1E293B);
    Color textColor = isLight ? AppColors.secondary : Colors.white;

    return Drawer(
      backgroundColor: drawerBg,
      child: Column(
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              color: isLight ? AppColors.primary.withOpacity(0.1) : Colors.black26,
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Image.asset('assets/images/new_logo_1.png', height: 80),
                  const SizedBox(height: 10),
                  // Yan menüdeki ismi de düzelttik
                  Text(
                    "KızılelmAI", 
                    style: TextStyle(
                      color: textColor, 
                      fontWeight: FontWeight.w900, 
                      letterSpacing: 1,
                      fontSize: 18
                    )
                  ),
                ],
              ),
            ),
          ),
          ListTile(
            leading: Icon(Icons.analytics, color: isLight ? AppColors.primary : AppColors.primaryRed),
            title: Text("Analiz Paneli", style: TextStyle(color: textColor)),
            onTap: () => _scrollToSection(_panelKey),
          ),
          ListTile(
            leading: Icon(Icons.rocket_launch, color: isLight ? AppColors.primary : AppColors.primaryRed),
            title: Text("Teknoloji & Misyon", style: TextStyle(color: textColor)),
            onTap: () => _scrollToSection(_missionKey),
          ),
          ListTile(
            leading: Icon(Icons.groups, color: isLight ? AppColors.primary : AppColors.primaryRed),
            title: Text("Ekip", style: TextStyle(color: textColor)),
            onTap: () => _scrollToSection(_teamKey),
          ),
        ],
      ),
    );
  }

  Widget _buildHeroSection(bool isLight) {
    return Column(
      children: [
        // LOGO
        Container(
          height: 180, width: 180,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: isLight 
                  ? AppColors.primary.withOpacity(0.2) 
                  : AppColors.primaryRed.withOpacity(0.4), 
                blurRadius: 50,
                spreadRadius: 5,
              ),
            ]
          ),
          child: Image.asset('assets/images/new_logo_1.png'),
        ),
        
        const SizedBox(height: 30),

        // GRADYAN BAŞLIK
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: ShaderMask(
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
                fontSize: 24, 
                fontWeight: FontWeight.w900, 
                color: Colors.white, 
                height: 1.2, 
                letterSpacing: -0.5
              ),
            ),
          ),
        ),

        const SizedBox(height: 10),

        if (isLight)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 30),
            child: Text(
              "Yapay zeka destekli dezenformasyon tespit sistemi.",
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.secondary.withOpacity(0.7), fontSize: 14),
            ),
          ),
        
        const SizedBox(height: 30),
      ],
    );
  }
}
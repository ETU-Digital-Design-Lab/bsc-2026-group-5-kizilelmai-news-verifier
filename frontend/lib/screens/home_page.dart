import 'package:flutter/material.dart';
import '../constants.dart';
import 'mobile_layout.dart';
import 'web_layout.dart';
import '../widgets/background_pattern.dart'; // <--- YENİ EKLENDİ

/// Uygulamanın giriş noktası ve ana denetleyicisi.
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  // --- TEMA VE ERİŞİLEBİLİRLİK STATE'LERİ ---
  double _textScale = 1.0; 
  
  // TEMA MODLARI:
  // 0: Kurumsal (Yeni Varsayılan - Beyaz & Bordo & Mesh Gradient)
  // 1: Siber Mod (Eski Lacivert & Neon & Hexagon Resim)
  // 2: Gece Modu (Simsiyah - AMOLED & Mesh Gradient)
  int _themeMode = 0; 

  /// Seçilen temaya göre dinamik arkaplan rengi
  Color get _currentBgColor {
    switch (_themeMode) {
      case 0: return AppColors.scaffoldLight; // BEYAZ
      case 1: return AppColors.scaffoldDark;  // LACİVERT
      case 2: return Colors.black;            // SİYAH
      default: return AppColors.scaffoldLight;
    }
  }

  /// Seçilen temaya göre kart rengi
  Color get _currentCardColor {
    switch (_themeMode) {
      case 0: return AppColors.cardLight;     // Çok açık gri
      case 1: return AppColors.cardDark;      // Lacivert
      case 2: return const Color(0xFF111111); // Koyu gri
      default: return AppColors.cardLight;
    }
  }

  /// Seçilen temaya göre metin rengi
  Color get _currentTextColor {
    if (_themeMode == 0) return AppColors.textMainLight; // Beyaz modda koyu yazı
    return AppColors.textMainDark; // Koyu modda açık yazı
  }

  /// Seçilen temaya göre Ana Renk
  Color get _currentPrimaryColor {
    if (_themeMode == 0) return AppColors.primary; // BORDO
    return AppColors.primaryDark; // NEON KIRMIZI
  }

  @override
  Widget build(BuildContext context) {
    var width = MediaQuery.of(context).size.width;
    bool isWeb = width > 900; 

    return Theme(
      data: ThemeData(
        brightness: _themeMode == 0 ? Brightness.light : Brightness.dark,
        primaryColor: _currentPrimaryColor,
        scaffoldBackgroundColor: _currentBgColor,
        cardColor: _currentCardColor, 
        canvasColor: _currentBgColor,
        iconTheme: IconThemeData(color: _currentPrimaryColor),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _themeMode == 0 ? AppColors.inputFillLight : AppColors.inputFillDark,
          hintStyle: TextStyle(color: _themeMode == 0 ? Colors.grey[500] : Colors.grey[400]),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: BorderSide.none,
          ),
        ),
        textTheme: Theme.of(context).textTheme.apply(
          fontSizeFactor: _textScale, 
          bodyColor: _currentTextColor,
          displayColor: _currentTextColor,
        ),
      ),
      child: Stack(
        children: [
          // 1. ARKAPLAN KATMANI (Dynamic Background)
          // Eğer Siber Mod (1) ise RESİM kullan.
          // Eğer Kurumsal (0) veya Gece (2) ise MESH GRADIENT kullan.
          (_themeMode == 1)
              ? Container(
                  height: double.infinity, width: double.infinity,
                  decoration: BoxDecoration(
                    color: _currentBgColor,
                    image: DecorationImage(
                      image: const NetworkImage("https://img.freepik.com/free-vector/dark-hexagonal-background-with-gradient-color_79603-1409.jpg"),
                      fit: BoxFit.cover,
                      colorFilter: ColorFilter.mode(_currentBgColor.withOpacity(0.9), BlendMode.darken),
                    ),
                  ),
                )
              : MeshGradientBackground(isLight: _themeMode == 0), // <--- YENİ PARÇA BURADA

          // 2. İÇERİK KATMANI
          isWeb 
          ? WebLayout(onSettingsTap: _showAccessibilitySettings) 
          : MobileLayout(onSettingsTap: _showAccessibilitySettings),
        ],
      ),
    );
  }

  // --- Ayarlar Menüsü (Aynen korundu) ---
  void _showAccessibilitySettings() {
    showModalBottomSheet(
      context: context,
      backgroundColor: _themeMode == 0 ? Colors.white : (_themeMode == 1 ? AppColors.cardDark : const Color(0xFF111111)),
      isScrollControlled: true, 
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return SingleChildScrollView(
              child: Container(
                padding: const EdgeInsets.all(24),
                constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.6),
                child: Column(
                  mainAxisSize: MainAxisSize.min, 
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.brush, color: _currentPrimaryColor),
                        const SizedBox(width: 10),
                        Text("Görünüm & Tema", style: TextStyle(fontSize: 20 * _textScale, fontWeight: FontWeight.bold, color: _currentTextColor)),
                      ],
                    ),
                    Divider(color: _currentTextColor.withOpacity(0.2), height: 30),
                    
                    Text("Yazı Boyutu", style: TextStyle(color: _currentTextColor.withOpacity(0.6), fontSize: 14 * _textScale)),
                    Row(
                      children: [
                        Text("A", style: TextStyle(fontSize: 14, color: _currentTextColor)),
                        Expanded(
                          child: Slider(
                            value: _textScale,
                            min: 1.0, max: 1.5, divisions: 5,
                            activeColor: _currentPrimaryColor, thumbColor: _currentPrimaryColor,
                            label: "${(_textScale * 100).toInt()}%",
                            onChanged: (val) {
                              setModalState(() => _textScale = val); 
                              setState(() {}); 
                            },
                          ),
                        ),
                        Text("A", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: _currentTextColor)),
                      ],
                    ),
                    const SizedBox(height: 30),
                    
                    Text("Renk Teması", style: TextStyle(color: _currentTextColor.withOpacity(0.6), fontSize: 14 * _textScale)),
                    const SizedBox(height: 15),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildThemeOption(0, "Kurumsal", Colors.white, isLight: true), 
                        _buildThemeOption(1, "Siber Mod", const Color(0xFF0F172A)),   
                        _buildThemeOption(2, "Gece", Colors.black),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }
        );
      },
    );
  }

  Widget _buildThemeOption(int index, String label, Color color, {bool isLight = false}) {
    bool isSelected = _themeMode == index;
    return GestureDetector(
      onTap: () {
        setState(() => _themeMode = index);
        Navigator.pop(context);
      },
      child: Column(
        children: [
          Container(
            width: 60, height: 60,
            decoration: BoxDecoration(
              color: color, 
              shape: BoxShape.circle,
              border: Border.all(color: isSelected ? _currentPrimaryColor : Colors.grey.withOpacity(0.5), width: isSelected ? 3 : 1),
              boxShadow: isLight ? [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 5)] : null,
            ),
            child: isSelected ? Icon(Icons.check, color: isLight ? AppColors.primary : Colors.white) : null,
          ),
          const SizedBox(height: 8),
          Text(label, style: TextStyle(fontSize: 12 * _textScale, fontWeight: FontWeight.w500, color: _currentTextColor)),
        ],
      ),
    );
  }
}
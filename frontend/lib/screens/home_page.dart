import 'package:flutter/material.dart';
import '../constants.dart';
import 'mobile_layout.dart';
import 'web_layout.dart';

/// Uygulamanın giriş noktası ve ana denetleyicisi (Root Controller).
/// Tema yönetimi (Dark/Light mode), Yazı ölçeklendirme (Accessibility) ve
/// Cihaz boyutuna göre (Responsive) sayfa yönlendirmesi burada yapılır.
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  // --- TEMA VE ERİŞİLEBİLİRLİK STATE'LERİ ---
  double _textScale = 1.0; 
  int _themeMode = 0; // 0: Varsayılan (Renkli), 1: Pitch Black (AMOLED), 2: Light Mode

  /// Seçilen temaya göre dinamik arkaplan rengi döndürür.
  Color get _currentBgColor {
    switch (_themeMode) {
      case 1: return Colors.black;
      case 2: return const Color(0xFFF1F5F9);
      default: return AppColors.bgDark;
    }
  }

  /// Seçilen temaya göre kart/panel rengi döndürür.
  Color get _currentCardColor {
    switch (_themeMode) {
      case 1: return const Color(0xFF111111);
      case 2: return Colors.white;
      default: return AppColors.cardColor;
    }
  }

  /// Seçilen temaya göre metin rengi döndürür.
  Color get _currentTextColor {
    if (_themeMode == 2) return const Color(0xFF0F172A); // Açık modda koyu yazı
    return Colors.white; // Koyu modda beyaz yazı
  }

  @override
  Widget build(BuildContext context) {
    var width = MediaQuery.of(context).size.width;
    bool isWeb = width > 900; 

    // Temayı ağacın altındaki tüm widget'lara enjekte ediyoruz (Dependency Injection)
    return Theme(
      data: ThemeData(
        brightness: _themeMode == 2 ? Brightness.light : Brightness.dark,
        primaryColor: AppColors.primaryRed,
        scaffoldBackgroundColor: _currentBgColor,
        cardColor: _currentCardColor, 
        canvasColor: _themeMode == 2 ? Colors.white : _currentCardColor,
        // Global yazı boyutu ölçeklendirme
        textTheme: Theme.of(context).textTheme.apply(
          fontSizeFactor: _textScale, 
          bodyColor: _currentTextColor,
          displayColor: _currentTextColor,
        ),
        iconTheme: const IconThemeData(color: AppColors.primaryRed),
      ),
      child: Stack(
        children: [
          // 1. Global Arkaplan Katmanı
          Container(
            height: double.infinity, width: double.infinity,
            decoration: BoxDecoration(
              color: _currentBgColor, 
              // Sadece varsayılan modda (0) görsel arkaplan kullan
              image: (_themeMode == 0) ? DecorationImage( 
                image: const NetworkImage("https://img.freepik.com/free-vector/dark-hexagonal-background-with-gradient-color_79603-1409.jpg"),
                fit: BoxFit.cover,
                // Görseli karartarak okunabilirliği artır
                colorFilter: ColorFilter.mode(_currentBgColor.withOpacity(0.85), BlendMode.darken),
              ) : null,
            ),
          ),

          // 2. İçerik Katmanı (Responsive Switcher)
          // Web ise WebLayout, Mobil ise MobileLayout yüklenir.
          isWeb 
          ? WebLayout(onSettingsTap: _showAccessibilitySettings) 
          : MobileLayout(onSettingsTap: _showAccessibilitySettings),
        ],
      ),
    );
  }

  // --- Ayarlar Menüsü (BottomSheet) ---
  
  /// Tema ve Görünüm ayarlarını içeren alt paneli açar.
  void _showAccessibilitySettings() {
    showModalBottomSheet(
      context: context,
      // Tema moduna göre panel rengini ayarla
      backgroundColor: _themeMode == 2 ? Colors.white : (_themeMode == 1 ? Colors.grey[900] : AppColors.cardColor),
      isScrollControlled: true, 
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        // BottomSheet içinde state değiştirebilmek için StatefulBuilder kullanıyoruz
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
                    // Başlık
                    Row(
                      children: [
                        const Icon(Icons.brush, color: AppColors.primaryRed),
                        const SizedBox(width: 10),
                        Text("Görünüm & Tema", style: TextStyle(fontSize: 20 * _textScale, fontWeight: FontWeight.bold, color: _currentTextColor)),
                      ],
                    ),
                    Divider(color: _currentTextColor.withOpacity(0.2), height: 30),
                    
                    // Yazı Boyutu Slider'ı
                    Text("Yazı Boyutu", style: TextStyle(color: _currentTextColor.withOpacity(0.6), fontSize: 14 * _textScale)),
                    Row(
                      children: [
                        Text("A", style: TextStyle(fontSize: 14, color: _currentTextColor)),
                        Expanded(
                          child: Slider(
                            value: _textScale,
                            min: 1.0, max: 1.5, divisions: 5,
                            activeColor: AppColors.primaryRed, thumbColor: AppColors.primaryRed,
                            label: "${(_textScale * 100).toInt()}%",
                            onChanged: (val) {
                              // Hem modalın hem de ana sayfanın state'ini güncelle
                              setModalState(() => _textScale = val); 
                              setState(() {}); 
                            },
                          ),
                        ),
                        Text("A", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: _currentTextColor)),
                      ],
                    ),
                    const SizedBox(height: 30),
                    
                    // Tema Seçenekleri
                    Text("Renk Teması", style: TextStyle(color: _currentTextColor.withOpacity(0.6), fontSize: 14 * _textScale)),
                    const SizedBox(height: 15),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildThemeOption(0, "Varsayılan", const Color(0xFF0F172A)), 
                        _buildThemeOption(1, "Siyah", Colors.black),                 
                        _buildThemeOption(2, "Beyaz", Colors.white, isLight: true),  
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

  /// Tema seçim butonlarını oluşturan yardımcı widget.
  Widget _buildThemeOption(int index, String label, Color color, {bool isLight = false}) {
    bool isSelected = _themeMode == index;
    return GestureDetector(
      onTap: () {
        setState(() => _themeMode = index);
        Navigator.pop(context); // Seçim yapınca menüyü kapat
      },
      child: Column(
        children: [
          Container(
            width: 60, height: 60,
            decoration: BoxDecoration(
              color: color, 
              shape: BoxShape.circle,
              border: Border.all(color: isSelected ? AppColors.primaryRed : Colors.grey.shade700, width: isSelected ? 3 : 1),
            ),
            child: isSelected ? Icon(Icons.check, color: isLight ? Colors.black : Colors.white) : null,
          ),
          const SizedBox(height: 8),
          Text(label, style: TextStyle(fontSize: 12 * _textScale, fontWeight: FontWeight.w500, color: _currentTextColor)),
        ],
      ),
    );
  }
}
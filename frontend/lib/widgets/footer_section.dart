import 'package:flutter/material.dart';
import '../constants.dart';

class FooterSection extends StatelessWidget {
  final bool isWeb;
  const FooterSection({super.key, required this.isWeb});

  @override
  Widget build(BuildContext context) {
    bool isLight = Theme.of(context).brightness == Brightness.light;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
      decoration: BoxDecoration(
        // Light: Çok açık gri, Dark: Koyu Lacivert
        color: isLight ? const Color(0xFFF1F5F9) : const Color(0xFF0F172A),
        border: Border(
          top: BorderSide(color: isLight ? Colors.grey.shade300 : Colors.white10),
        ),
      ),
      child: Column(
        children: [
          // 1. LOGO VE AÇIKLAMA
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Logo (Temaya göre değişir)
              isLight 
                ? Image.asset('assets/images/new_logo_1.png', height: 40)
                : ColorFiltered(
                    colorFilter: const ColorFilter.mode(Colors.white, BlendMode.srcIn),
                    child: Image.asset('assets/images/new_logo_1.png', height: 40),
                  ),
              const SizedBox(width: 12),
              
              // --- GÜNCELLENEN KISIM: ÇİFT RENKLİ YAZI ---
              RichText(
                text: TextSpan(
                  style: TextStyle(
                    fontSize: 22, // Biraz daha büyük ve okunaklı
                    fontWeight: FontWeight.w900, // Logo gibi kalın
                    letterSpacing: 1,
                    fontFamily: 'Roboto', // Varsa özel font, yoksa default
                  ),
                  children: [
                    TextSpan(
                      text: "Kızılelm",
                      style: TextStyle(
                        // Light modda Bordo, Dark modda Beyaz
                        color: isLight ? AppColors.primary : Colors.white,
                      ),
                    ),
                    TextSpan(
                      text: "AI",
                      style: TextStyle(
                        // Light modda Parlak Kırmızı, Dark modda Beyaz (veya açık kırmızı)
                        color: isLight ? const Color(0xFFD32F2F) : Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Text(
            "Yapay Zeka Destekli Dezenformasyon Tespit Sistemi",
            style: TextStyle(
              color: isLight ? Colors.grey[600] : Colors.grey[400],
              fontSize: 12,
            ),
          ),
          
          const SizedBox(height: 30),
          Divider(color: isLight ? Colors.grey.shade300 : Colors.white10, indent: 100, endIndent: 100),
          const SizedBox(height: 30),

          // 2. LİNKLER
          Wrap(
            spacing: 20,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              _footerLink("Gizlilik Politikası", isLight),
              _footerLink("Kullanım Şartları", isLight),
              _footerLink("Veri Setleri", isLight),
              _footerLink("İletişim", isLight),
            ],
          ),

          const SizedBox(height: 30),

          // 3. COPYRIGHT
          Text(
            "© 2026 KızılelmAI Teknofest Takımı. Tüm hakları saklıdır.",
            style: TextStyle(
              color: isLight ? Colors.grey[500] : Colors.grey[600],
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  Widget _footerLink(String text, bool isLight) {
    return TextButton(
      onPressed: () {},
      child: Text(
        text,
        style: TextStyle(
          color: isLight ? AppColors.secondary : Colors.white70,
          fontWeight: FontWeight.w600,
          fontSize: 13,
        ),
      ),
    );
  }
}
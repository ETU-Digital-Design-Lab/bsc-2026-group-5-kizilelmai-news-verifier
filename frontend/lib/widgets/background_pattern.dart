import 'dart:ui';
import 'package:flutter/material.dart';
import '../constants.dart';

class MeshGradientBackground extends StatelessWidget {
  final bool isLight;
  const MeshGradientBackground({super.key, required this.isLight});

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;

    return Stack(
      children: [
        // 1. ZEMİN RENGİ (Beyaz/Siyah)
        Container(color: isLight ? const Color(0xFFFFFFFF) : const Color(0xFF0F172A)),

        // 2. SOL ÜST - ANA RENK (KIZILELMA BORDOSU)
        Positioned(
          top: -100, // Daha aşağı indirdik, görünsün diye
          left: -50,
          child: _buildSolidBlob(
            color: isLight 
                ? const Color(0xFF6A0D23).withOpacity(0.5) // Koyu Bordo, %50 görünür
                : AppColors.primaryRed.withOpacity(0.6), 
            size: 800, // Kocaman yaptık
          ),
        ),

        // 3. SAĞ ALT - TAMAMLAYICI (MAVİ)
        Positioned(
          bottom: -100,
          right: -50,
          child: _buildSolidBlob(
            color: isLight 
                ? const Color(0xFF0EA5E9).withOpacity(0.4) // Canlı Mavi
                : Colors.purpleAccent.withOpacity(0.5), 
            size: 800,
          ),
        ),

        // 4. ORTA SAĞ - VURGU (TURUNCU/KIRMIZI)
        if (isLight)
          Positioned(
            top: size.height * 0.3,
            right: -150,
            child: _buildSolidBlob(
              color: Colors.redAccent.withOpacity(0.3), // Hafif Kırmızımsı
              size: 600,
            ),
          ),

        // 5. SOL ALT - MORLUK
        if (isLight)
          Positioned(
            bottom: size.height * 0.1,
            left: -100,
            child: _buildSolidBlob(
              color: Colors.deepPurple.withOpacity(0.2), 
              size: 500,
            ),
          ),

        // 6. BLUR EFEKTİ (SİHİR BURADA)
        // Solid topları alıp buzlu cam gibi yayacak
        BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 120.0, sigmaY: 120.0), // Blur çok yüksek
          child: Container(
            color: isLight 
              ? Colors.white.withOpacity(0.3) // Renkleri biraz yumuşatmak için beyaz perde
              : Colors.transparent, 
          ),
        ),
      ],
    );
  }

  // DEĞİŞİKLİK: Artık gradient yok, direkt SOLID renk basıyoruz.
  // Çünkü Blur zaten onu yumuşatacak.
  Widget _buildSolidBlob({required Color color, required double size}) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color, 
      ),
    );
  }
}
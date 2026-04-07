import 'dart:ui';
import 'package:flutter/material.dart';

class GlassBox extends StatelessWidget {
  final Widget child;
  final double? width;
  final double? height;
  final BorderRadius? borderRadius;
  final double opacity;

  const GlassBox({
    super.key,
    required this.child,
    this.width,
    this.height,
    this.borderRadius,
    this.opacity = 0.1, // Varsayılan şeffaflık
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius ?? BorderRadius.circular(16),
      child: BackdropFilter(
        // Buradaki 10 değerleri bulanıklık şiddetini ayarlar
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            // Beyazın çok şeffaf hali (Buzlu Cam Rengi)
            color: Colors.white.withOpacity(opacity),
            borderRadius: borderRadius ?? BorderRadius.circular(16),
            // İnce beyaz çerçeve (Cyberpunk hissi için)
            border: Border.all(color: Colors.white.withOpacity(0.1), width: 1),
          ),
          child: child,
        ),
      ),
    );
  }
}
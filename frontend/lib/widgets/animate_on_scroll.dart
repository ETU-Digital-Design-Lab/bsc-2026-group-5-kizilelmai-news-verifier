import 'package:flutter/material.dart';

/// İçindeki widget'ı ekran görünürlüğüne girdiğinde alttan yukarı kaydırarak getirir.
class FadeInUp extends StatefulWidget {
  final Widget child;
  final int delay; // Gecikme süresi (ms) - Sırayla gelmeleri için

  const FadeInUp({super.key, required this.child, this.delay = 0});

  @override
  State<FadeInUp> createState() => _FadeInUpState();
}

class _FadeInUpState extends State<FadeInUp> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacityAnim;
  late Animation<Offset> _translateAnim;
  bool _hasAnimate = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800), // Animasyon süresi
    );

    _opacityAnim = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _translateAnim = Tween<Offset>(begin: const Offset(0, 0.2), end: Offset.zero).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Ekrana girip girmediğini kontrol etmek yerine basitçe mount olduğunda çalıştırıyoruz.
    // Daha profesyonel çözüm için "visibility_detector" paketi gerekir ama 
    // paket yüklemeden basit bir gecikmeli başlatma yapacağız.
    
    if (!_hasAnimate) {
      Future.delayed(Duration(milliseconds: widget.delay), () {
        if (mounted) {
          _controller.forward();
          _hasAnimate = true;
        }
      });
    }

    return FadeTransition(
      opacity: _opacityAnim,
      child: SlideTransition(
        position: _translateAnim,
        child: widget.child,
      ),
    );
  }
}
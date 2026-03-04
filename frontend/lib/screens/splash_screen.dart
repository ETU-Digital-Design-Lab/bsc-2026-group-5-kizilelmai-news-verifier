import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart'; 
import '../constants.dart';
import 'home_page.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacityAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();

    // Status Bar ayarları (Temiz görünüm)
    SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark, 
    ));

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500), 
    );

    // 1. Opaklık: Görünmezden görünüre
    _opacityAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn),
    );

    // 2. Ölçek: Hafif zoom efekti
    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutBack), 
    );

    _controller.forward();

    // 3 saniye sonra Ana Sayfaya geç
    Timer(const Duration(seconds: 3), () {
      _navigateToHome();
    });
  }

  void _navigateToHome() {
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => const HomePage(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
        transitionDuration: const Duration(milliseconds: 1000),
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white, // Daima beyaz, temiz açılış
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // --- LOGO ALANI ---
            ScaleTransition(
              scale: _scaleAnimation,
              child: FadeTransition(
                opacity: _opacityAnimation,
                child: SizedBox(
                  height: 200, 
                  width: 200,
                  child: Image.asset('assets/images/new_logo_1.png'),
                ),
              ),
            ),
            
            const SizedBox(height: 20),

            // --- YAZI ALANI (GÜNCELLENDİ) ---
            FadeTransition(
              opacity: _opacityAnimation,
              child: Column(
                children: [
                  const Text(
                    "KızılelmAI", // DÜZELTİLDİ: Eski tireli yapı kalktı
                    style: TextStyle(
                      color: AppColors.primary, 
                      fontSize: 32, // Biraz daha büyük ve okunaklı
                      fontWeight: FontWeight.w900, // Logo gibi kalın
                      letterSpacing: 1, // Harfler birbirine daha yakın
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "GÜVENLİK VE ANALİZ SİSTEMİ",
                    style: TextStyle(
                      color: Colors.grey.shade500, 
                      fontSize: 10,
                      letterSpacing: 3,
                      fontWeight: FontWeight.w600
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
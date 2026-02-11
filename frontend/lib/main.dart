import 'package:flutter/material.dart';
import 'constants.dart'; // Renk paletini buradan çekiyoruz
import 'screens/home_page.dart'; // Ana sayfayı buradan çekiyoruz
import 'screens/splash_screen.dart'; 

void main() {
  runApp(const KizilelmaAIApp());
}

/// Uygulamanın kök (Root) widget'ı.
/// MaterialApp yapılandırmasını ve varsayılan temayı başlatır.
class KizilelmaAIApp extends StatelessWidget {
  const KizilelmaAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KızılelmAI',
      debugShowCheckedModeBanner: false, // Debug bandını kaldırır
      
      // Projenin varsayılan tema ayarları
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark, // Varsayılan olarak karanlık mod
        scaffoldBackgroundColor: AppColors.bgDark, // Constants'tan gelen renk
        primaryColor: AppColors.primaryRed,
        // Font ailesi (Eğer varlık olarak eklediysen çalışır, yoksa varsayılanı kullanır)
        fontFamily: 'Arial', 
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      
      // Uygulamanın başlangıç sayfası
      home: const SplashScreen(),
    );
  }
}
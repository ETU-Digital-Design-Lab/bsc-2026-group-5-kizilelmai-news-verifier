import 'package:flutter/material.dart';

/// Proje genelinde kullanılan renk paleti ve tasarım token'ları.
/// Bu sınıfın örneklenmesi (instance) engellenmiştir, sadece static erişim sağlanır.
class AppColors {
  AppColors._(); // Private constructor

  /// Ana arka plan rengi (Koyu Lacivert / Slate).
  /// Genellikle Scaffold background olarak kullanılır.
  static const Color bgDark = Color(0xFF0F172A);

  /// Kartlar, paneller ve modal pencereler için ikincil arka plan rengi (Metalik Slate).
  static const Color cardColor = Color(0xFF1E293B);

  /// Marka rengi ve birincil vurgu rengi (Kızılelma Kırmızısı).
  /// Butonlar ve önemli vurgular için kullanılır.
  static const Color primaryRed = Color(0xFFD72F53);

  /// Metinler ve ikonlar için kullanılan ana beyaz tonu (Buz Beyazı).
  static const Color textWhite = Color(0xFFF8FAFC);

  /// Teknolojik vurgular, ikonlar ve aktif durumlar için kullanılan detay mavisi (Cyan).
  static const Color accentCyan = Color(0xFF38BDF8);

  // --- Analiz Sonuç Ekranı Renkleri ---

  /// Manipülasyon tespiti durumunda kullanılan koyu kırmızı arka plan.
  static const Color resultBg = Color(0xFF3B0711);

  /// Manipülasyon tespiti durumunda kullanılan parlak kırmızı kenarlık.
  static const Color resultBorder = Color(0xFFEF4444);
}

/// Uygulama içinde kullanılan sabit veriler ve simülasyon içerikleri.
class AppData {
  AppData._(); // Private constructor

  /// Marquee (Kayan yazı) modülü için simüle edilmiş canlı sistem logları.
  static const List<String> liveLogs = [
    "Sistem online. Tehdit algılama modülü aktif...",
    "Resmi Gazete son sayı (32451) tarandı.",
    "TRT Haber arşivi ile veri eşleşmesi sağlandı.",
    "Anadolu Ajansı teyit servisi: Bağlantı stabil.",
    "KızılelmAI Bot: Sosyal medyada 14 yeni manipülatif etiket tespit edildi.",
    "BİLGİ: Geleceğin savaşları algı üzerinden yürütülür."
  ];
}
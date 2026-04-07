import 'package:flutter/material.dart';

class AppColors {
  AppColors._(); 

  // ==========================================================
  // 1. HAM RENK PALETİ (Sadece burada tanımlanır)
  // ==========================================================
  
  // --- YENİ KURUMSAL RENKLER (Sade/Beyaz Tema) ---
  static const Color _brandBurgundy = Color(0xFF6A0D23); // Koyu Bordo (Logo uyumlu)
  static const Color _brandWhite = Color(0xFFFFFFFF);    // Saf Beyaz
  static const Color _brandLightGrey = Color(0xFFF8FAFC); // Kartlar için çok açık gri
  static const Color _brandDarkGrey = Color(0xFF1F2937); // Koyu Gri Yazılar
  static const Color _brandTextSub = Color(0xFF64748B);  // İkincil Yazılar
  static const Color _brandBorder = Color(0xFFE2E8F0);   // İnce Gri Çizgiler

  // --- ESKİ SİBER MOD RENKLERİ (Lacivert Tema) ---
  static const Color _navyBg = Color(0xFF0F172A); 
  static const Color _navyCard = Color(0xFF1E293B);     
  static const Color _navyText = Color(0xFFF1F5F9);
  static const Color _navyTextSub = Color(0xFF94A3B8);
  static const Color _navyBorder = Color(0xFF334155);
  static const Color _neonRed = Color(0xFFD72F53);    
  static const Color _neonCyan = Color(0xFF0EA5E9);    

  // --- ANALİZ SONUÇ RENKLERİ (Sabit) ---
  static const Color _resultCorrect = Color(0xFF10B981); // Yeşil
  static const Color _resultWrong = Color(0xFFEF4444);   // Kırmızı
  static const Color _resultPartial = Color(0xFFF59E0B); // Turuncu
  
  // Eski Sonuç Arkaplanları (Hata almamak için tutuyoruz)
  static const Color _resultWrongBg = Color(0xFF450A0A);
  static const Color _resultCorrectBg = Color(0xFF064E3B);
  static const Color _resultPartialBg = Color(0xFF451A03);

  // ==========================================================
  // 2. DIŞARIYA AÇILAN İSİMLER (Kullanılacak Olanlar)
  // ==========================================================

  // --- Varsayılan Tema (Kurumsal/Beyaz) ---
  static const Color primary = _brandBurgundy; 
  static const Color secondary = _brandDarkGrey;
  static const Color scaffoldLight = _brandWhite;
  static const Color cardLight = _brandLightGrey;
  static const Color textMainLight = _brandDarkGrey;
  static const Color textSubLight = _brandTextSub;
  static const Color borderLight = _brandBorder;
  static const Color inputFillLight = Color(0xFFF1F5F9);

  // --- Alternatif Tema (Siber/Lacivert) ---
  static const Color scaffoldDark = _navyBg;
  static const Color cardDark = _navyCard;
  static const Color textMainDark = _navyText;
  static const Color textSubDark = _navyTextSub;
  static const Color primaryDark = _neonRed; // Siber modda butonlar neon kırmızı
  static const Color borderDark = _navyBorder;
  static const Color inputFillDark = Color(0xFF020617);

  // --- Analiz Renkleri (Tüm temalarda ortak) ---
  static const Color resultCorrect = _resultCorrect;
  static const Color resultWrong = _resultWrong;
  static const Color resultPartial = _resultPartial;
  
  static const Color resultCorrectBg = _resultCorrectBg;
  static const Color resultCorrectBorder = _resultCorrect;
  
  static const Color resultWrongBg = _resultWrongBg;
  static const Color resultWrongBorder = _resultWrong;
  
  static const Color resultPartialBg = _resultPartialBg;
  static const Color resultPartialBorder = _resultPartial;

  // ==========================================================
  // 3. ESKİ KODLARLA UYUMLULUK (Hata Önleyici)
  // ==========================================================
  // Projenin geri kalanında "AppColors.primaryRed" veya "AppColors.bgDark" 
  // diye çağrılan yerler patlamasın diye bunları yönlendiriyoruz.
  
  // Varsayılan rengi Bordo yapıyoruz
  static const Color primaryRed = _brandBurgundy; 
  static const Color accentCyan = _neonCyan;
  
  // "bgDark" denince artık varsayılan olarak laciverti değil, 
  // tema mantığına göre değişecek bir yapı olmadığı için 
  // burada sabit bir renk vermek zorundayız. 
  // Ancak HomePage içinde dinamik değişeceği için buradaki değer 
  // sadece fallback (yedek) olarak kalır.
  static const Color bgDark = _navyBg; 
  static const Color cardColor = _navyCard;
  static const Color textWhite = _navyText;

  // Analiz kutusu eski değişkenleri
  static const Color resultBg = _resultWrongBg;
  static const Color resultBorder = _resultWrong;
}

class AppData {
  AppData._();
  static const List<String> liveLogs = [
    "Sistem online. Gelişmiş algı modülü devrede...",
    "Resmi Gazete entegrasyonu: Başarılı.",
    "KızılelmAI Bot: Dezenformasyon taraması %100.",
  ];
}

enum AnalysisStatus { initial, loading, correct, wrong, partial, error }
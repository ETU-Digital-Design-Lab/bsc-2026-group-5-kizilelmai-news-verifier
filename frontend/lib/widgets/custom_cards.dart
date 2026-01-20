import 'package:flutter/material.dart';
import '../constants.dart';

// ==============================================================================
// 1. TEKNOLOJİ KARTI (MİSYON BÖLÜMÜ İÇİN)
// ==============================================================================

/// Teknolojik altyapı özelliklerini (örn: NLP, Veri Analizi) gösteren bilgi kartı.
class TechCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String desc;

  const TechCard({
    super.key,
    required this.icon,
    required this.title,
    required this.desc,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      // Genişlik esnek bırakıldı, parent (row/column) yönetecek.
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.cardColor.withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.accentCyan, size: 32),
          const SizedBox(height: 16),
          Text(title, style: const TextStyle(color: AppColors.textWhite, fontWeight: FontWeight.bold, fontSize: 18)),
          const SizedBox(height: 8),
          Text(desc, style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 14, height: 1.5)),
        ],
      ),
    );
  }
}

// ==============================================================================
// 2. TAKIM ÜYESİ KARTI (ÖĞRENCİLER İÇİN)
// ==============================================================================

/// Proje ekibindeki öğrencileri gösteren kart.
/// Baş harfi, İsim, Rol ve Üniversite bilgisini içerir.
class TeamMemberCard extends StatelessWidget {
  final String name;
  final String role;
  final String uni;

  const TeamMemberCard({
    super.key,
    required this.name,
    required this.role,
    required this.uni,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160, // Mobilde yan yana 2 tane sığması için optimize edildi (Eskisi 280 çok genişti)
      height: 190,
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: AppColors.cardColor,
        borderRadius: BorderRadius.circular(12),
        // Hafif bir gölge ve ince kenarlık
        border: Border.all(color: Colors.white.withOpacity(0.1)),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // İsim Baş Harfi Avatarı
          CircleAvatar(
            radius: 24,
            backgroundColor: AppColors.bgDark,
            child: Text(
              name.isNotEmpty ? name[0] : "?",
              style: const TextStyle(color: AppColors.primaryRed, fontWeight: FontWeight.bold, fontSize: 18),
            ),
          ),
          const SizedBox(height: 12),
          
          // İsim
          Text(
            name,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.textWhite, fontWeight: FontWeight.bold, fontSize: 14),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          
          // Rol
          Text(
            role,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.accentCyan, fontSize: 11, fontWeight: FontWeight.w600),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          
          // Üniversite
          Text(
            uni,
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 10),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

// ==============================================================================
// 3. DANIŞMAN KARTI (HOCALAR İÇİN)
// ==============================================================================

/// Proje danışmanlarını (Hocalar) gösteren özel kart.
/// Rengi ve stili öğrencilerden farklılaştırılarak hiyerarşi sağlanmıştır.
class AdvisorCard extends StatelessWidget {
  final String name;
  final String role;

  const AdvisorCard({
    super.key,
    required this.name,
    required this.role,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160, // TeamMemberCard ile aynı genişlikte hizalanması için
      height: 190,
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        // Danışmanlar için Kırmızı/Mavi tonlu özel arkaplan
        color: AppColors.primaryRed.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.primaryRed.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Özel İkon
          const Icon(Icons.school, color: AppColors.primaryRed, size: 40),
          const SizedBox(height: 12),
          
          // İsim
          Text(
            name,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.textWhite, fontWeight: FontWeight.bold, fontSize: 14),
          ),
          const SizedBox(height: 4),
          
          // Unvan
          Text(
            role,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.primaryRed, fontSize: 12, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
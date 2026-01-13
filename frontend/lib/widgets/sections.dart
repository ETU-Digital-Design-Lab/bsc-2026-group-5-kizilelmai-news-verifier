import 'package:flutter/material.dart';
import '../constants.dart';
import 'custom_cards.dart'; // Tüm kart tasarımlarını buradan çekiyoruz

/// Ana sayfanın "Misyon" ve "Teknolojik Altyapı" bölümlerini içeren widget.
/// Web sürümünde kartlar yatay (Row), mobil sürümde dikey (Column) listelenir.
class MissionSection extends StatelessWidget {
  final bool isWeb;
  const MissionSection({super.key, required this.isWeb});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const SizedBox(height: 50),
          
          // Bölüm Başlığı
          const Text(
            "TEKNOLOJİK ALTYAPI",
            style: TextStyle(color: AppColors.accentCyan, fontWeight: FontWeight.bold, letterSpacing: 2),
          ),
          const SizedBox(height: 20),
          
          // Responsive Düzen: Web ise Row, Mobil ise Column
          isWeb ? _buildWebLayout() : _buildMobileLayout(),

          const SizedBox(height: 40),
          Divider(color: Colors.white.withOpacity(0.1)),
          const SizedBox(height: 40),
          
          // Misyon Açıklama Kutusu
          _buildMissionStatement(),
          
          const SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _buildWebLayout() {
    return const Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: TechCard(icon: Icons.memory, title: "Doğal Dil İşleme", desc: "Türkçe BERT modeli ile anlamsal analiz.")),
        SizedBox(width: 20),
        Expanded(child: TechCard(icon: Icons.storage, title: "Resmi Veri", desc: "Resmi Gazete ve AA arşivlerinden teyit.")),
        SizedBox(width: 20),
        Expanded(child: TechCard(icon: Icons.security, title: "Manipülasyon Tespiti", desc: "Provokatif dili tespit eden özel algoritma.")),
      ],
    );
  }

  Widget _buildMobileLayout() {
    return const Column(
      children: [
        TechCard(icon: Icons.memory, title: "Doğal Dil İşleme", desc: "Türkçe BERT modeli ile anlamsal analiz."),
        SizedBox(height: 15),
        TechCard(icon: Icons.storage, title: "Resmi Veri", desc: "Resmi Gazete ve AA arşivlerinden teyit."),
        SizedBox(height: 15),
        TechCard(icon: Icons.security, title: "Manipülasyon Tespiti", desc: "Provokatif dili tespit eden özel algoritma."),
      ],
    );
  }

  Widget _buildMissionStatement() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardColor, 
        borderRadius: BorderRadius.circular(15), 
        border: Border.all(color: Colors.white.withOpacity(0.1))
      ),
      child: Column(
        children: [
          const Text("MİSYONUMUZ", style: TextStyle(color: AppColors.primaryRed, fontWeight: FontWeight.bold, letterSpacing: 2)),
          const SizedBox(height: 15),
          const Text("Dijital Kalkan", style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          Text(
            "Kızılelma, Türk kültüründe daima ulaşılması gereken en yüksek idealleri temsil eder. Bizler bu mirası 'AI' ile harmanladık.\n\nKızılelmAI, bilgi kirliliğine karşı inşa edilmiş dijital bir kalkandır.",
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withOpacity(0.7), height: 1.6),
          ),
        ],
      ),
    );
  }
}

/// Ana sayfanın "Ekip" bölümünü içeren widget.
/// Öğrenciler ve Danışman hocaları listeler.
/// Responsive tasarım için `Wrap` widget'ı kullanır.
class TeamSection extends StatelessWidget {
  final bool isWeb;
  const TeamSection({super.key, required this.isWeb});

  @override
  Widget build(BuildContext context) {
    // Ekip verisi
    final List<Widget> teamMembers = [
      const TeamMemberCard(name: "Erkam Ayhan", role: "Geliştirici & Frontend", uni: "Erzurum Teknik Üni."),
      const TeamMemberCard(name: "Merve Atılgan", role: "Model Eğitimi (AI)", uni: "Atatürk Üni."),
      const TeamMemberCard(name: "İbrahim S. Akbulut", role: "Model Eğitimi (AI)", uni: "Erzurum Teknik Üni."),
      const TeamMemberCard(name: "Rabia Sultan Yüce", role: "Backend Geliştirici", uni: "Atatürk Üni."),
      const TeamMemberCard(name: "Doğukan Kılıç", role: "Backend Geliştirici", uni: "Erzurum Teknik Üni."),
      const AdvisorCard(name: "Işıl Karabey Aksakallı", role: "Takım Danışmanı"),
      const AdvisorCard(name: "Latif Akçay", role: "Takım Danışmanı"),
    ];

    return Padding(
      padding: const EdgeInsets.all(20),
      child: SizedBox(
        width: double.infinity,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const SizedBox(height: 50),
            const Text("KızılelmAI Ekibi", style: TextStyle(color: AppColors.primaryRed, fontSize: 24, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text("Projenin arkasındaki beyin takımı", style: TextStyle(color: Colors.white.withOpacity(0.6))),
            const SizedBox(height: 30),
            
            // Otomatik Izgara Düzeni (Wrap)
            // Ekran genişse yan yana dizer, sığmazsa aşağı atar.
            Wrap(
              spacing: 20, // Yatay boşluk
              runSpacing: 20, // Dikey boşluk
              alignment: WrapAlignment.center, 
              crossAxisAlignment: WrapCrossAlignment.center,
              children: teamMembers,
            ),

            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }
}
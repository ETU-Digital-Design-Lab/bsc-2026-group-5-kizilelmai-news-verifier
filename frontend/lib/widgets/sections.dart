import 'package:flutter/material.dart';
import '../constants.dart';
import 'animate_on_scroll.dart'; 

// ==========================================================
// 1. MİSYON VE TEKNOLOJİ BÖLÜMÜ
// ==========================================================
class MissionSection extends StatelessWidget {
  final bool isWeb;
  const MissionSection({super.key, required this.isWeb});

  @override
  Widget build(BuildContext context) {
    bool isLight = Theme.of(context).brightness == Brightness.light;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 60, horizontal: 24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: Column(
            children: [
              _buildSectionTitle("TEKNOLOJİK ALTYAPI", isLight),
              const SizedBox(height: 50),
              
              Wrap(
                spacing: 30,
                runSpacing: 30,
                alignment: WrapAlignment.center,
                children: [
                  FadeInUp(
                    delay: 100,
                    child: _buildTechCard(
                      context,
                      icon: Icons.psychology, 
                      title: "Doğal Dil İşleme (NLP)", 
                      desc: "Türkçe dil yapısına özel eğitilmiş BERT modelleri ile anlamsal analiz.",
                      color1: const Color(0xFF0EA5E9), 
                      color2: const Color(0xFF6366F1), 
                      isLight: isLight
                    ),
                  ),

                  FadeInUp(
                    delay: 300,
                    child: _buildTechCard(
                      context,
                      icon: Icons.security, 
                      title: "Manipülasyon Tespiti", 
                      desc: "Haber metinlerindeki duygu sömürüsü ve yönlendirmeyi tespit eder.",
                      color1: const Color(0xFFEC4899), 
                      color2: const Color(0xFFD946EF), 
                      isLight: isLight
                    ),
                  ),

                  FadeInUp(
                    delay: 500,
                    child: _buildTechCard(
                      context,
                      icon: Icons.storage, 
                      title: "Resmi Veri Teyidi", 
                      desc: "Resmi Gazete ve AA arşivlerinden saniyelik veri çekerek doğrulama yapar.",
                      color1: const Color(0xFFF59E0B), 
                      color2: const Color(0xFFF97316), 
                      isLight: isLight
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 60),
              
              // MİSYON AÇIKLAMA KUTUSU
              FadeInUp(
                delay: 600,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(30),
                  decoration: BoxDecoration(
                    color: isLight ? Colors.white : AppColors.cardDark,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: isLight ? Colors.grey.shade200 : Colors.white.withOpacity(0.1)
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: isLight ? Colors.black.withOpacity(0.05) : Colors.black.withOpacity(0.3),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      )
                    ],
                  ),
                  child: Column(
                    children: [
                      Text("MİSYONUMUZ", style: TextStyle(color: isLight ? AppColors.primary : AppColors.primaryRed, fontWeight: FontWeight.bold, letterSpacing: 2)),
                      const SizedBox(height: 15),
                      Text("Dijital Kalkan", style: TextStyle(color: isLight ? AppColors.secondary : Colors.white, fontSize: 26, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 20),
                      Text(
                        "Kızılelma, Türk kültüründe daima ulaşılması gereken en yüksek idealleri temsil eder. Bizler bu mirası 'Yapay Zeka' ile harmanladık.\n\nKızılelmAI, bilgi kirliliğine karşı inşa edilmiş dijital bir kalkandır.",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: isLight ? AppColors.textSubLight : Colors.white70, height: 1.6, fontSize: 16),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, bool isLight) {
    return FadeInUp(
      child: Column(
        children: [
          Text(
            title,
            style: TextStyle(
              color: isLight ? AppColors.primary : Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 28,
              letterSpacing: 1.5,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 10),
          Container(
            width: 60, height: 4,
            decoration: BoxDecoration(
              color: isLight ? AppColors.primary : AppColors.primaryRed,
              borderRadius: BorderRadius.circular(2),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildTechCard(BuildContext context, {required IconData icon, required String title, required String desc, required Color color1, required Color color2, required bool isLight}) {
    double width = MediaQuery.of(context).size.width > 900 ? 300 : double.infinity;

    return HoverCard(
      child: Container(
        width: width,
        height: 280, 
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 30),
        decoration: BoxDecoration(
          color: isLight ? Colors.white : const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isLight ? Colors.grey.shade200 : Colors.white.withOpacity(0.1)),
          boxShadow: [BoxShadow(color: isLight ? Colors.grey.withOpacity(0.1) : Colors.black.withOpacity(0.3), blurRadius: 20, offset: const Offset(0, 10))],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: [color1.withOpacity(0.2), color2.withOpacity(0.2)]),
              ),
              child: Icon(icon, size: 40, color: color2),
            ),
            const SizedBox(height: 20),
            Text(title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: isLight ? AppColors.secondary : Colors.white), textAlign: TextAlign.center),
            const SizedBox(height: 10),
            Text(
              desc, 
              style: TextStyle(color: isLight ? AppColors.textSubLight : Colors.grey[400], height: 1.4, fontSize: 14), 
              textAlign: TextAlign.center,
              maxLines: 3, 
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

// ==========================================================
// 2. EKİP BÖLÜMÜ
// ==========================================================
class TeamSection extends StatelessWidget {
  final bool isWeb;
  const TeamSection({super.key, required this.isWeb});

  @override
  Widget build(BuildContext context) {
    bool isLight = Theme.of(context).brightness == Brightness.light;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 80, horizontal: 24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: Column(
            children: [
              FadeInUp(
                child: Text(
                  "KızılelmAI EKİBİ", // Branding Düzeltmesi
                  style: TextStyle(
                    color: isLight ? AppColors.primary : Colors.white,
                    fontWeight: FontWeight.w900,
                    fontSize: 28,
                    letterSpacing: 1.2,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 10),
              FadeInUp(
                delay: 100,
                child: Text("Projenin arkasındaki beyin takımı", style: TextStyle(color: isLight ? AppColors.textSubLight : Colors.white60))
              ),
              
              const SizedBox(height: 50),
              
              Wrap(
                spacing: 20,
                runSpacing: 20,
                alignment: WrapAlignment.center,
                children: [
                  FadeInUp(delay: 200, child: _buildMemberCard("Erkam Ayhan", "Geliştirici & Frontend", "Erzurum Teknik Üni.", "assets/images/erkam.jpg", isLight)),
                  FadeInUp(delay: 300, child: _buildMemberCard("Merve Atılgan", "Model Eğitimi (AI)", "Atatürk Üni.", "assets/images/merve.jpg", isLight)),
                  FadeInUp(delay: 400, child: _buildMemberCard("İbrahim S. Akbulut", "Model Eğitimi (AI)", "Erzurum Teknik Üni.", "assets/images/ibrahim.jpg", isLight)),
                  // Rabia çıkarıldı
                  FadeInUp(delay: 500, child: _buildMemberCard("Doğukan Kılıç", "Backend Geliştirici", "Erzurum Teknik Üni.", "assets/images/dogukan.jpg", isLight)),
                  
                  // Danışman Kartı
                  FadeInUp(delay: 600, child: _buildAdvisorCard("Latif Akçay", "Takım Danışmanı", isLight)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMemberCard(String name, String role, String uni, String imgPath, bool isLight) {
    // Resim kontrolü (Asset mi Network mü?)
    Widget imageWidget;
    if (imgPath.startsWith("http")) {
       imageWidget = CircleAvatar(radius: 40, backgroundImage: NetworkImage(imgPath));
    } else {
       imageWidget = CircleAvatar(
         radius: 40, 
         backgroundImage: AssetImage(imgPath), 
         onBackgroundImageError: (_, __) {
           // Resim bulunamazsa hata verme
         },
         // Resim yüklenene kadar veya hata durumunda ikon göster
         child: const Icon(Icons.person, size: 40, color: Colors.white),
       );
    }

    return HoverCard(
      child: Container(
        width: 280,
        height: 320, 
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 25),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isLight ? [Colors.white, const Color(0xFFF8FAFC)] : [const Color(0xFF1E293B), const Color(0xFF0F172A)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isLight ? Colors.grey.shade200 : Colors.white.withOpacity(0.05)),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(isLight ? 0.05 : 0.2), blurRadius: 15, offset: const Offset(0, 5))],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center, 
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: isLight ? [AppColors.primary, AppColors.secondary] : [AppColors.primaryRed, Colors.purple]),
              ),
              child: imageWidget,
            ),
            const SizedBox(height: 15),
            Text(name, textAlign: TextAlign.center, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: isLight ? AppColors.secondary : Colors.white)),
            const SizedBox(height: 5),
            Text(role, textAlign: TextAlign.center, style: TextStyle(color: isLight ? AppColors.primary : AppColors.accentCyan, fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 5),
            Text(uni, textAlign: TextAlign.center, style: TextStyle(color: isLight ? Colors.grey[500] : Colors.grey[400], fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Widget _buildAdvisorCard(String name, String role, bool isLight) {
    return HoverCard(
      child: Container(
        width: 280,
        height: 320, 
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 25),
        decoration: BoxDecoration(
          color: isLight ? AppColors.primary.withOpacity(0.05) : AppColors.primaryRed.withOpacity(0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isLight ? AppColors.primary.withOpacity(0.2) : AppColors.primaryRed.withOpacity(0.3), width: 1.5),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center, 
          children: [
            CircleAvatar(
              radius: 44, 
              backgroundColor: isLight ? AppColors.primary : AppColors.primaryRed,
              child: const Icon(Icons.school, color: Colors.white, size: 34),
            ),
            const SizedBox(height: 15),
            Text(name, textAlign: TextAlign.center, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: isLight ? AppColors.primary : Colors.white)),
            const SizedBox(height: 5),
            Text(role.toUpperCase(), textAlign: TextAlign.center, style: TextStyle(color: isLight ? AppColors.secondary : AppColors.accentCyan, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1)),
          ],
        ),
      ),
    );
  }
}

// ==========================================================
// 3. HOVER CARD 
// ==========================================================
class HoverCard extends StatefulWidget {
  final Widget child;
  const HoverCard({super.key, required this.child});

  @override
  State<HoverCard> createState() => _HoverCardState();
}

class _HoverCardState extends State<HoverCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedScale(
        scale: _isHovered ? 1.05 : 1.0, 
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        child: widget.child,
      ),
    );
  }
}
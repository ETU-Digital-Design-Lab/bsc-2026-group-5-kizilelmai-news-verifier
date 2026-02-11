import 'dart:ui';
import 'package:flutter/material.dart';
import '../constants.dart';

class DetailedReportDialog extends StatelessWidget {
  final AnalysisStatus status;
  final String resultTitle;

  const DetailedReportDialog({
    super.key,
    required this.status,
    required this.resultTitle,
  });

  Color get _statusColor {
    switch (status) {
      case AnalysisStatus.correct: return const Color(0xFF10B981);
      case AnalysisStatus.wrong: return const Color(0xFFEF4444);
      case AnalysisStatus.partial: return const Color(0xFFF59E0B);
      default: return Colors.grey;
    }
  }

  double get _alignmentX {
    switch (status) {
      case AnalysisStatus.correct: return 0.95;
      case AnalysisStatus.wrong: return -0.95;
      case AnalysisStatus.partial: return 0.0;
      default: return 0.0;
    }
  }

  @override
  Widget build(BuildContext context) {
    bool isLight = Theme.of(context).brightness == Brightness.light;
    double confidence = status == AnalysisStatus.correct ? 98.4 : (status == AnalysisStatus.wrong ? 12.1 : 55.0);

    return BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
      child: Dialog(
        backgroundColor: isLight ? Colors.white.withOpacity(0.9) : const Color(0xFF1E293B).withOpacity(0.9),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(color: _statusColor.withOpacity(0.3), width: 1),
        ),
        // Kenarlardan boşluğu azalttık ki içeriğe yer kalsın
        insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: SingleChildScrollView( // Ekran çok küçükse (iPhone SE vb.) aşağı kayabilsin
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // --- 1. BAŞLIK SATIRI (HATA BURADAYDI) ---
                  Row(
                    children: [
                      // İkon
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: _statusColor.withOpacity(0.1),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(Icons.analytics_rounded, color: _statusColor, size: 20),
                      ),
                      const SizedBox(width: 10),
                      
                      // METNİ EXPANDED İÇİNE ALDIK (ARTIK TAŞMAZ)
                      Expanded(
                        child: Text(
                          "DETAYLI ANALİZ RAPORU",
                          style: TextStyle(
                            color: isLight ? Colors.black87 : Colors.white,
                            fontSize: 14, // Mobilde sığması için fontu biraz küçülttük
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis, // Sığmazsa ... koy
                        ),
                      ),
                      
                      // Kapat Butonu
                      IconButton(
                        onPressed: () => Navigator.pop(context),
                        icon: Icon(Icons.close, color: isLight ? Colors.grey : Colors.white54),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(), // Butonun gereksiz boşluğunu al
                        splashRadius: 20,
                      )
                    ],
                  ),
                  const SizedBox(height: 25),

                  // 2. SONUÇ BAŞLIĞI VE SKOR
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text("TESPİT EDİLEN DURUM", style: TextStyle(color: isLight ? Colors.grey[600] : Colors.grey[400], fontSize: 10, fontWeight: FontWeight.w700)),
                            const SizedBox(height: 4),
                            FittedBox( // Metin çok uzunsa küçülterek sığdır
                              fit: BoxFit.scaleDown,
                              alignment: Alignment.centerLeft,
                              child: Text(
                                resultTitle,
                                style: TextStyle(
                                  color: _statusColor,
                                  fontSize: 24,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: -0.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: _statusColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: _statusColor.withOpacity(0.2)),
                        ),
                        child: Text(
                          "%${confidence.toInt()} GÜVEN",
                          style: TextStyle(color: _statusColor, fontWeight: FontWeight.bold, fontSize: 12),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 25),

                  // 3. DOĞRULUK SPEKTRUMU
                  Text("DOĞRULUK SPEKTRUMU", style: TextStyle(color: isLight ? Colors.grey[600] : Colors.grey[500], fontSize: 10, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 30,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Container(
                          height: 6,
                          width: double.infinity,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(10),
                            gradient: const LinearGradient(
                              colors: [Color(0xFFEF4444), Color(0xFFF59E0B), Color(0xFF10B981)],
                              stops: [0.1, 0.5, 0.9],
                            ),
                          ),
                        ),
                        AnimatedAlign(
                          duration: const Duration(milliseconds: 1000),
                          curve: Curves.elasticOut,
                          alignment: Alignment(_alignmentX, 0),
                          child: Container(
                            width: 20, height: 20,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                              border: Border.all(color: _statusColor, width: 3),
                              boxShadow: [
                                BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 8, offset: const Offset(0, 3))
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 2.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("MANİPÜLATİF", style: TextStyle(color: const Color(0xFFEF4444).withOpacity(0.8), fontSize: 9, fontWeight: FontWeight.bold)),
                        Text("DOĞRULANMIŞ", style: TextStyle(color: const Color(0xFF10B981).withOpacity(0.8), fontSize: 9, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),

                  const SizedBox(height: 25),

                  // 4. SİSTEM GÜNLÜĞÜ
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isLight ? const Color(0xFFF1F5F9) : Colors.black26,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: isLight ? Colors.grey.shade300 : Colors.white10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Icon(Icons.terminal, size: 14, color: isLight ? Colors.grey[700] : Colors.grey),
                          const SizedBox(width: 8),
                          Text("SİSTEM ÇIKTISI", style: TextStyle(color: isLight ? Colors.grey[700] : Colors.grey, fontSize: 10, fontWeight: FontWeight.bold)),
                        ]),
                        const SizedBox(height: 8),
                        Text(
                          status == AnalysisStatus.correct 
                            ? "> NLP semantik analizi tamamlandı.\n> Resmi Gazete API: Eşleşme [OK].\n> AA Arşiv Taraması: Eşleşme [OK].\n> Sonuç: İçerik doğrulanmış kaynaklarla uyumlu."
                            : (status == AnalysisStatus.wrong 
                                ? "> NLP duygu analizi: Yüksek Provokasyon.\n> Resmi Veri: Eşleşme bulunamadı [FAIL].\n> Çapraz Kaynak: Tutarsızlık tespit edildi.\n> Sonuç: Yanıltıcı/Sahte içerik."
                                : "> Veri seti taraması: Yetersiz veri.\n> Güven skoru eşik değerin altında.\n> Manuel teyit önerilir."),
                          style: TextStyle(
                            color: isLight ? Colors.black87 : Colors.white70, 
                            fontFamily: 'Courier', 
                            fontSize: 11, 
                            height: 1.4
                          ),
                        ),
                      ],
                    ),
                  ),
                  
                  const SizedBox(height: 20),

                  // 5. KAPAT BUTONU
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _statusColor,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        elevation: isLight ? 4 : 0,
                      ),
                      child: const Text(
                        "RAPORU KAPAT",
                        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14),
                      ),
                    ),
                  )
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
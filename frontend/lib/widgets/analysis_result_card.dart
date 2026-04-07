import 'package:flutter/material.dart';
import '../constants.dart';
import 'report_dialog.dart'; // Detaylı rapor dialog'u için

class AnalysisResultCard extends StatelessWidget {
  final AnalysisStatus status;
  final String resultText;
  final String resultDetail;
  final double confidence; // 0.0 ile 1.0 arası güven skoru

  const AnalysisResultCard({
    super.key,
    required this.status,
    required this.resultText,
    required this.resultDetail,
    required this.confidence,
  });

  // Rengi duruma göre belirle
  Color get _statusColor {
    switch (status) {
      case AnalysisStatus.correct: return Colors.green.shade600;
      case AnalysisStatus.wrong: return Colors.red.shade600;
      case AnalysisStatus.partial: return Colors.orange.shade700;
      case AnalysisStatus.error: return Colors.grey;
      default: return AppColors.primaryRed;
    }
  }

  // İkonu duruma göre belirle
  IconData get _statusIcon {
    switch (status) {
      case AnalysisStatus.correct: return Icons.check_circle;
      case AnalysisStatus.wrong: return Icons.cancel;
      case AnalysisStatus.partial: return Icons.warning_amber_rounded;
      case AnalysisStatus.error: return Icons.error_outline;
      default: return Icons.search;
    }
  }

  // Spektrum çubuğundaki topun konumu (-1 sol, 0 orta, +1 sağ)
  double get _alignmentX {
    if (status == AnalysisStatus.wrong) return -0.9;
    if (status == AnalysisStatus.correct) return 0.9;
    return 0.0; // Partial veya belirsiz
  }

  @override
  Widget build(BuildContext context) {
    // Hata durumunda basit kart göster
    if (status == AnalysisStatus.error) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off, color: Colors.red, size: 50),
            const SizedBox(height: 10),
            Text(resultText, style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 5),
            Text(resultDetail, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _statusColor.withOpacity(0.1), // Hafif renkli zemin
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: _statusColor.withOpacity(0.5), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. ÜST KISIM: İKON VE BAŞLIK
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: _statusColor.withOpacity(0.2), shape: BoxShape.circle),
                child: Icon(_statusIcon, color: _statusColor, size: 24),
              ),
              const SizedBox(width: 15),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("ANALİZ SONUCU", style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1)),
                  Text(resultText, style: TextStyle(color: _statusColor, fontWeight: FontWeight.bold, fontSize: 18)),
                ],
              )
            ],
          ),
          const SizedBox(height: 20),
          
          // 2. ORTA KISIM: SPEKTRUM ÇUBUĞU
          const Text("DOĞRULUK PAYI SPEKTRUMU:", style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          SizedBox(
            height: 30,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Renkli Çubuk
                Container(
                  height: 8,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    gradient: const LinearGradient(
                      colors: [Colors.red, Colors.orange, Colors.green],
                    ),
                  ),
                ),
                // Konum Göstergesi (Top)
                Align(
                  alignment: Alignment(_alignmentX, 0),
                  child: Container(
                    width: 18, height: 18,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.5), blurRadius: 5)],
                      border: Border.all(color: _statusColor, width: 3),
                    ),
                  ),
                )
              ],
            ),
          ),
          // Alt Etiketler
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("YANLIŞ", style: TextStyle(color: Colors.red, fontSize: 10, fontWeight: FontWeight.bold)),
              Text("KISMEN", style: TextStyle(color: Colors.orange, fontSize: 10, fontWeight: FontWeight.bold)),
              Text("DOĞRU", style: TextStyle(color: Colors.green, fontSize: 10, fontWeight: FontWeight.bold)),
            ],
          ),
          
          const SizedBox(height: 20),
          
          // 3. ALT KISIM: AÇIKLAMA VE BUTON
          Text(resultDetail, style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.4)),
          const SizedBox(height: 20),
          
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                showDialog(
                  context: context, 
                  builder: (_) => DetailedReportDialog(status: status, resultTitle: resultText)
                );
              },
              icon: const Icon(Icons.description),
              label: const Text("DETAYLI RAPORU GÖRÜNTÜLE"),
              style: OutlinedButton.styleFrom(
                foregroundColor: _statusColor,
                side: BorderSide(color: _statusColor.withOpacity(0.5)),
                padding: const EdgeInsets.symmetric(vertical: 15),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          )
        ],
      ),
    );
  }
}
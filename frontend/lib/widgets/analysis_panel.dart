import 'package:flutter/material.dart';
import '../constants.dart';
import '../services/api_service.dart';

/// Haber doğrulama ve analiz işlemlerinin yönetildiği ana panel bileşeni.
/// Kullanıcıdan metin alır, gerçek backend API'ye (BERT tabanlı NLP) istek gönderir ve sonuçları gösterir.
/// Web sürümünde "Split Layout" (İkiye Bölme), mobil sürümde dikey liste kullanır.
class AnalysisPanel extends StatefulWidget {
  final bool isWeb;
  const AnalysisPanel({super.key, required this.isWeb});

  @override
  State<AnalysisPanel> createState() => _AnalysisPanelState();
}

class _AnalysisPanelState extends State<AnalysisPanel> {
  // --- Controller & State ---
  final TextEditingController _newsController = TextEditingController();
  
  bool _isLoading = false;
  String _loadingText = "Sistem Hazır";
  String? _analizSonucu;
  double _guvenSkoru = 0.0;
  
  // --- Backend Yanıt Verileri ---
  String _backendResponse = "";
  bool _isCorrect = false; // label 1 = doğru, 0 = yanlış

  /// Gerçek backend API'ye istek gönderen fonksiyon.
  /// BERT tabanlı NLP doğrulama sistemi ile haber doğruluğunu kontrol eder.
  void _analizEt() async {
    FocusScope.of(context).unfocus(); // Klavyeyi kapat

    if (_newsController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Lütfen analiz edilecek metni girin.'), backgroundColor: AppColors.primaryRed),
      );
      return;
    }

    setState(() {
      _isLoading = true;
      _analizSonucu = null;
      _guvenSkoru = 0.0;
      _backendResponse = "";
      _loadingText = "BERT modeli sorgulanıyor...";
    });

    try {
      // Backend API'ye istek gönder
      final response = await ApiService.sendChatQuery(_newsController.text.trim());

      if (!mounted) return;

      // Backend yanıtını parse et
      String result = response['result'] ?? 'Yanıt alınamadı.';
      
      // Backend'den gelen yanıtı analiz et
      bool isCorrect = result.contains('Evet, bu haber doğru') || result.contains('✅');
      bool isFalse = result.contains('Hayır, bu haber yanlış') || result.contains('❌');
      
      // Benzerlik skorunu çıkar (eğer varsa)
      double similarity = 0.0;
      RegExp similarityRegex = RegExp(r'Benzerlik:\s*(\d+\.?\d*)%');
      Match? match = similarityRegex.firstMatch(result);
      if (match != null) {
        similarity = double.tryParse(match.group(1) ?? '0') ?? 0.0;
        similarity = similarity / 100.0; // Yüzdeyi 0-1 aralığına çevir
      }

      setState(() {
        _isLoading = false;
        _backendResponse = result;
        _isCorrect = isCorrect;
        
        if (isCorrect) {
          _analizSonucu = "HABER DOĞRU";
          _guvenSkoru = similarity > 0 ? similarity : 0.7; // Varsayılan güven skoru
        } else if (isFalse) {
          _analizSonucu = "HABER YANLIŞ";
          _guvenSkoru = similarity > 0 ? similarity : 0.3; // Düşük güven skoru
        } else {
          _analizSonucu = "BİLGİ BULUNAMADI";
          _guvenSkoru = 0.0;
        }
      });
    } catch (e) {
      if (!mounted) return;
      
      setState(() {
        _isLoading = false;
        _analizSonucu = "BAĞLANTI HATASI";
        _guvenSkoru = 0.0;
        _backendResponse = "Backend'e bağlanılamadı. Lütfen backend'in çalıştığından emin olun.\n\nHata: $e";
      });
      
      // Kullanıcıya hata mesajı göster
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Backend bağlantı hatası: $e'),
          backgroundColor: AppColors.primaryRed,
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  /// Detaylı analiz raporunu gösteren Modal Dialog.
  void _showReportDialog() {
    showDialog(
      context: context,
      builder: (context) {
        double screenHeight = MediaQuery.of(context).size.height;
        
        return AlertDialog(
          backgroundColor: AppColors.cardColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16), 
            side: BorderSide(color: Colors.white.withOpacity(0.1))
          ),
          title: const Row(
            children: [
              Icon(Icons.assessment, color: AppColors.accentCyan), 
              SizedBox(width: 10), 
              Flexible(child: Text("Detaylı Analiz Raporu", style: TextStyle(color: Colors.white, fontSize: 18)))
            ],
          ),
          // İçerik taşmasını önlemek için Constraints ve ScrollView kullanıldı
          content: Container(
            width: widget.isWeb ? 600 : double.maxFinite,
            constraints: BoxConstraints(maxHeight: screenHeight * 0.7),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 10),
                  const Text("BACKEND YANITI:", style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 10),
                  Container(
                    width: double.infinity, 
                    padding: const EdgeInsets.all(15), 
                    decoration: BoxDecoration(
                      color: Colors.black26, 
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.white.withOpacity(0.1)),
                    ), 
                    child: SelectableText(
                      _backendResponse.isNotEmpty ? _backendResponse : "Yanıt bekleniyor...",
                      style: TextStyle(
                        color: _isCorrect ? Colors.green : (_analizSonucu == "HABER YANLIŞ" ? AppColors.primaryRed : Colors.white),
                        fontSize: 14, 
                        height: 1.5, 
                        fontFamily: 'Courier'
                      )
                    )
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context), 
              child: const Text("KAPAT", style: TextStyle(color: AppColors.accentCyan, fontWeight: FontWeight.bold))
            )
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    // Web'de sonuç varsa ekranı ikiye böl (Overflow Fix)
    bool useSideBySide = widget.isWeb && _analizSonucu != null;

    return Container(
      width: widget.isWeb ? 900 : double.infinity, 
      margin: const EdgeInsets.symmetric(horizontal: 24),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
        boxShadow: [BoxShadow(color: AppColors.accentCyan.withOpacity(0.1), blurRadius: 40, spreadRadius: -10)],
      ),
      child: useSideBySide 
          ? _buildWebSplitLayout() // Web & Sonuç varsa yan yana
          : _buildStandardLayout(), // Mobil veya sonuç yoksa alt alta
    );
  }

  // --- Layout Builders ---

  Widget _buildStandardLayout() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildInputSection(),
        if (_analizSonucu != null) ...[
          const SizedBox(height: 30),
          _buildResultSection(),
        ]
      ],
    );
  }

  Widget _buildWebSplitLayout() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(flex: 5, child: _buildInputSection()),
        const SizedBox(width: 30),
        Expanded(
          flex: 4, 
          child: Column(
            children: [
              const SizedBox(height: 10), // Hizalama düzeltmesi
              _buildResultSection()
            ]
          )
        ),
      ],
    );
  }

  // --- Bölüm Widget'ları ---

  Widget _buildInputSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("HABER DOĞRULAMA PANELİ", style: TextStyle(color: AppColors.textWhite, fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 15),
        TextField(
          controller: _newsController,
          maxLines: widget.isWeb ? 4 : 5, 
          style: const TextStyle(color: AppColors.textWhite, fontFamily: 'Courier'),
          decoration: InputDecoration(
            hintText: "// Analiz edilecek metni yapıştırın...",
            hintStyle: TextStyle(color: Colors.grey[500], fontSize: 14),
            filled: true,
            fillColor: const Color(0xFF2D3748),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
          ),
        ),
        const SizedBox(height: 20),
        
        // Kaynak Etiketleri Başlığı
        Text(
          "TARANAN HABER KAYNAKLARI:", 
          style: TextStyle(color: Colors.grey[500], fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1)
        ),
        const SizedBox(height: 8),
        
        Wrap(
          spacing: 10, runSpacing: 10,
          children: [_sourceTag("Resmi Gazete"), _sourceTag("AA Arşivi"), _sourceTag("TRT")],
        ),
        const SizedBox(height: 20),
        
        // Analiz Butonu
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _analizEt,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primaryRed,
              padding: const EdgeInsets.symmetric(vertical: 20),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: _isLoading 
              ? Text(_loadingText, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontFamily: 'Courier', fontSize: 12)) 
              : const Text("DOĞRULUĞU KONTROL ET", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
          ),
        ),
      ],
    );
  }

  Widget _buildResultSection() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.resultBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.resultBorder, width: 1.5), 
        boxShadow: [BoxShadow(color: AppColors.resultBorder.withOpacity(0.3), blurRadius: 20, spreadRadius: 1)]
      ),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Güven Skoru Göstergesi (Circular)
              SizedBox(
                height: 50, width: 50,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    const CircularProgressIndicator(value: 1, color: Colors.black26, strokeWidth: 5),
                    CircularProgressIndicator(value: _guvenSkoru, color: AppColors.resultBorder, strokeWidth: 5),
                    Text("%${(_guvenSkoru*100).toInt()}", style: const TextStyle(color: AppColors.textWhite, fontWeight: FontWeight.bold, fontSize: 11)),
                  ],
                ),
              ),
              const SizedBox(width: 15),
              
              // Sonuç Metni
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _analizSonucu!, 
                      style: TextStyle(
                        color: _isCorrect ? Colors.green : AppColors.resultBorder, 
                        fontWeight: FontWeight.w900, 
                        fontSize: 15, 
                        letterSpacing: 0.5
                      )
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _isCorrect 
                        ? "Veri setinde doğrulanmış kaynak bulundu." 
                        : (_analizSonucu == "HABER YANLIŞ" 
                          ? "Yanıltıcı içerik tespit edildi." 
                          : "Bu konuda veri setinde bilgi bulunamadı."),
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ],
                ),
              )
            ],
          ),
          const SizedBox(height: 15),
          const Divider(color: Colors.white24),
          
          // Detay Butonu
          TextButton.icon(
            onPressed: _showReportDialog,
            icon: const Icon(Icons.analytics_outlined, color: AppColors.accentCyan, size: 20),
            label: const Text("DETAYLI RAPOR", style: TextStyle(color: AppColors.accentCyan, fontWeight: FontWeight.bold, fontSize: 13)),
          ),
        ],
      ),
    );
  }

  // --- Yardımcı Widget'lar ---

  Widget _sourceTag(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(6)),
      child: Text(text, style: TextStyle(color: Colors.grey[300], fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }

  Widget _detailRow(String label, double value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start, 
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween, 
          children: [
            Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)), 
            Text("%${(value*100).toInt()}", style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12))
          ]
        ),
        const SizedBox(height: 6),
        LinearProgressIndicator(
          value: value, 
          backgroundColor: Colors.white10, 
          color: color, 
          minHeight: 6, 
          borderRadius: BorderRadius.circular(3)
        ),
      ]
    );
  }
}
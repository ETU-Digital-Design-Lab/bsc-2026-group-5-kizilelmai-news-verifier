import 'package:flutter/material.dart';
import '../constants.dart';

/// Haber doğrulama ve analiz işlemlerinin yönetildiği ana panel bileşeni.
/// Kullanıcıdan metin alır, analiz simülasyonu yapar ve sonuçları gösterir.
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
  
  // --- Simülasyon Verileri ---
  double _yalanOrani = 0.0;
  double _manipulasyonOrani = 0.0;
  String _aiAciklama = "";

  /// Yapay zeka analiz sürecini simüle eden fonksiyon.
  /// 4 aşamalı bir bekleme süresi sonunda sahte bir rapor oluşturur.
  void _analizEt() async {
    FocusScope.of(context).unfocus(); // Klavyeyi kapat

    if (_newsController.text.isEmpty) return;

    setState(() {
      _isLoading = true;
      _analizSonucu = null;
      _guvenSkoru = 0.0;
    });

    // Kullanıcıya işlem yapıldığını hissettiren adımlar
    List<String> steps = [
      "NLP: Metin vektörleştiriliyor...",
      "Resmi Gazete API sorgulanıyor...",
      "Duygu analizi (Sentiment Analysis)...",
      "Rapor oluşturuluyor..."
    ];

    for (var step in steps) {
      if (!mounted) return;
      setState(() => _loadingText = step);
      await Future.delayed(const Duration(milliseconds: 600));
    }

    if (!mounted) return;
    
    // Simülasyon Sonucu
    setState(() {
      _isLoading = false;
      _analizSonucu = "MANİPÜLASYON TESPİT EDİLDİ"; 
      _guvenSkoru = 0.14; 
      _yalanOrani = 0.86; 
      _manipulasyonOrani = 0.92;
      _aiAciklama = "Metinde yoğun duygusal tetikleyiciler (korku, öfke) tespit edilmiştir. Kaynak belirtilmeden 'kesinleşti' gibi ifadelerin kullanımı manipülasyon skorunu artırmıştır.";
    });
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
                  _detailRow("Yalan Oranı", _yalanOrani, Colors.orange),
                  const SizedBox(height: 15),
                  _detailRow("Manipülasyon", _manipulasyonOrani, AppColors.primaryRed),
                  const SizedBox(height: 25),
                  const Text("YAPAY ZEKA AÇIKLAMASI:", style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 10),
                  Container(
                    width: double.infinity, 
                    padding: const EdgeInsets.all(15), 
                    decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(8)), 
                    child: Text(_aiAciklama, style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.5, fontFamily: 'Courier'))
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
                    Text(_analizSonucu!, style: const TextStyle(color: AppColors.resultBorder, fontWeight: FontWeight.w900, fontSize: 15, letterSpacing: 0.5)),
                    const SizedBox(height: 6),
                    const Text("Manipülatif dil tespit edildi.", style: TextStyle(color: Colors.white, fontSize: 12)),
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
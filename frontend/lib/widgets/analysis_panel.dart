import 'package:flutter/material.dart';
import '../constants.dart';
import '../services/api_service.dart';
import 'report_dialog.dart';
import 'glass_box.dart';

class AnalysisPanel extends StatefulWidget {
  final bool isWeb;
  const AnalysisPanel({super.key, required this.isWeb});

  @override
  State<AnalysisPanel> createState() => _AnalysisPanelState();
}

class _AnalysisPanelState extends State<AnalysisPanel> {
  final TextEditingController _newsController = TextEditingController();
  
  bool _isLoading = false;
  String _loadingText = "Sistem Hazır";
  String? _analizSonucu;
  double _guvenSkoru = 0.0;
  String _backendResponse = "";
  bool _isCorrect = false; 

  void _analizEt() async {
    FocusScope.of(context).unfocus(); 

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
      final response = await ApiService.sendChatQuery(_newsController.text.trim());
      if (!mounted) return;

      String result = response['result'] ?? 'Yanıt alınamadı.';
      bool isCorrect = result.contains('Evet, bu haber doğru') || result.contains('✅');
      bool isFalse = result.contains('Hayır, bu haber yanlış') || result.contains('❌');
      
      double similarity = 0.0;
      RegExp similarityRegex = RegExp(r'Benzerlik:\s*(\d+\.?\d*)%');
      Match? match = similarityRegex.firstMatch(result);
      if (match != null) {
        similarity = double.tryParse(match.group(1) ?? '0') ?? 0.0;
        similarity = similarity / 100.0; 
      }

      setState(() {
        _isLoading = false;
        _backendResponse = result;
        _isCorrect = isCorrect;
        
        if (isCorrect) {
          _analizSonucu = "HABER DOĞRU";
          _guvenSkoru = similarity > 0 ? similarity : 0.7; 
        } else if (isFalse) {
          _analizSonucu = "HABER YANLIŞ";
          _guvenSkoru = similarity > 0 ? similarity : 0.3; 
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
        _backendResponse = "Hata: $e";
      });
    }
  }

  void _showReportDialog() {
    AnalysisStatus status;
    if (_analizSonucu == "HABER DOĞRU") status = AnalysisStatus.correct;
    else if (_analizSonucu == "HABER YANLIŞ") status = AnalysisStatus.wrong;
    else if (_analizSonucu == "BİLGİ BULUNAMADI" || _analizSonucu == "BAĞLANTI HATASI") status = AnalysisStatus.error;
    else status = AnalysisStatus.partial;

    showDialog(
      context: context,
      builder: (context) => DetailedReportDialog(status: status, resultTitle: _analizSonucu ?? "SONUÇ YOK"),
    );
  }

  @override
  Widget build(BuildContext context) {
    bool useSideBySide = widget.isWeb && _analizSonucu != null;
    bool isLight = Theme.of(context).brightness == Brightness.light;

    return Center(
      child: GlassBox(
        width: widget.isWeb ? 900 : double.infinity,
        opacity: isLight ? 0.6 : 0.08, 
        borderRadius: BorderRadius.circular(20),
        // --- DÜZELTME BURADA: SingleChildScrollView Eklendi ---
        // Artık içerik sığmazsa taşmak yerine kaydırılabilir olacak.
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: useSideBySide 
                ? _buildWebSplitLayout(isLight) 
                : _buildStandardLayout(isLight),
          ),
        ),
      ),
    );
  }

  Widget _buildStandardLayout(bool isLight) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min, // İçerik kadar yer kapla
      children: [
        _buildInputSection(isLight),
        if (_analizSonucu != null) ...[const SizedBox(height: 30), _buildResultSection()],
      ],
    );
  }

  Widget _buildWebSplitLayout(bool isLight) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(flex: 5, child: _buildInputSection(isLight)),
        const SizedBox(width: 30),
        Expanded(flex: 4, child: Column(children: [const SizedBox(height: 10), _buildResultSection()])),
      ],
    );
  }

  Widget _buildInputSection(bool isLight) {
    Color textColor = isLight ? AppColors.secondary : Colors.white;
    Color hintColor = isLight ? Colors.grey[600]! : Colors.grey[500]!;
    Color inputFill = isLight ? Colors.white : const Color(0xFF2D3748);
    Color titleColor = isLight ? AppColors.primary : Colors.white;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text("HABER DOĞRULAMA PANELİ", style: TextStyle(color: titleColor, fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 15),
        TextField(
          controller: _newsController,
          maxLines: widget.isWeb ? 4 : 5, 
          style: TextStyle(color: textColor, fontFamily: 'Courier'),
          decoration: InputDecoration(
            hintText: "// Analiz edilecek metni yapıştırın...",
            hintStyle: TextStyle(color: hintColor, fontSize: 14),
            filled: true,
            fillColor: inputFill,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: isLight ? BorderSide(color: Colors.grey.shade300) : BorderSide.none),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: isLight ? BorderSide(color: Colors.grey.shade300) : BorderSide.none),
            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: AppColors.primary, width: 1.5)),
          ),
        ),
        const SizedBox(height: 20),
        Text("TARANAN HABER KAYNAKLARI:", style: TextStyle(color: isLight ? AppColors.secondary.withOpacity(0.7) : Colors.grey[500], fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1)),
        const SizedBox(height: 8),
        Wrap(spacing: 10, runSpacing: 10, children: [_sourceTag("Resmi Gazete", isLight), _sourceTag("AA Arşivi", isLight), _sourceTag("TRT", isLight)]),
        const SizedBox(height: 20),
        
        // --- GRADYAN BUTON ---
        Container(
          width: double.infinity,
          height: 55,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isLight 
                  ? [AppColors.primary, const Color(0xFFD72F53)] 
                  : [AppColors.primaryDark, Colors.blueAccent], 
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: (isLight ? AppColors.primary : AppColors.primaryDark).withOpacity(0.4),
                blurRadius: 10,
                offset: const Offset(0, 4),
              )
            ]
          ),
          child: ElevatedButton(
            onPressed: _isLoading ? null : _analizEt,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.transparent, 
              shadowColor: Colors.transparent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: _isLoading 
              ? Text(_loadingText, style: const TextStyle(color: Colors.white, fontFamily: 'Courier')) 
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
              SizedBox(
                height: 60, width: 60,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    const CircularProgressIndicator(value: 1, color: Colors.black26, strokeWidth: 6),
                    ShaderMask(
                      shaderCallback: (Rect bounds) {
                        return LinearGradient(
                          colors: [_isCorrect ? Colors.green : Colors.red, Colors.yellow],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        ).createShader(bounds);
                      },
                      child: CircularProgressIndicator(
                        value: _guvenSkoru, 
                        valueColor: const AlwaysStoppedAnimation<Color>(Colors.white), 
                        strokeWidth: 6
                      ),
                    ),
                    Text("%${(_guvenSkoru*100).toInt()}", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                  ],
                ),
              ),
              const SizedBox(width: 15),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_analizSonucu!, style: TextStyle(color: _isCorrect ? Colors.greenAccent : (_analizSonucu == "HABER YANLIŞ" ? AppColors.primaryRed : Colors.white), fontWeight: FontWeight.w900, fontSize: 15, letterSpacing: 0.5)),
                    const SizedBox(height: 6),
                    Text(_isCorrect ? "Veri setinde doğrulanmış kaynak bulundu." : (_analizSonucu == "HABER YANLIŞ" ? "Yanıltıcı içerik tespit edildi." : "Bu konuda veri setinde bilgi bulunamadı."), style: const TextStyle(color: Colors.white70, fontSize: 12)),
                  ],
                ),
              )
            ],
          ),
          const SizedBox(height: 15),
          const Divider(color: Colors.white24),
          TextButton.icon(
            onPressed: _showReportDialog, 
            icon: const Icon(Icons.analytics_outlined, color: Colors.white, size: 20),
            label: const Text("DETAYLI RAPOR", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
          ),
        ],
      ),
    );
  }

  Widget _sourceTag(String text, bool isLight) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isLight ? Colors.grey.shade200 : Colors.white.withOpacity(0.1), 
        borderRadius: BorderRadius.circular(6),
        border: isLight ? Border.all(color: Colors.grey.shade300) : null,
      ),
      child: Text(text, style: TextStyle(color: isLight ? Colors.black54 : Colors.grey[300], fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}
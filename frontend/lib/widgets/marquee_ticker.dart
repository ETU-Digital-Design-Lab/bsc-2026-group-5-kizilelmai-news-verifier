import 'package:flutter/material.dart';
import 'dart:async';
import '../constants.dart';

/// Ekranın altında akan "Canlı Akış" şeridi.
/// Tema uyumlu (Light/Dark) ve Timer ile otomatik kayan yapı.
class MarqueeTickerModule extends StatefulWidget {
  const MarqueeTickerModule({super.key});

  @override
  State<MarqueeTickerModule> createState() => _MarqueeTickerModuleState();
}

class _MarqueeTickerModuleState extends State<MarqueeTickerModule> {
  final ScrollController _scrollController = ScrollController();
  Timer? _timer;

  // Yeni Premium Mesaj Listesi
  final List<String> _messages = [
    "KIZILELM-AI SİSTEMİ DEVREDE...",
    "RESMİ GAZETE VERİLERİ ANLIK TARANIYOR...",
    "DEZENFORMASYON TESPİT ORANI %98.4...",
    "SOSYAL MEDYA ANALİZİ AKTİF...",
    "YAPAY ZEKA DESTEKLİ DOĞRULAMA...",
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startScrolling());
  }

  void _startScrolling() {
    // 30ms'de bir 1 piksel kaydır (Akıcı olması için)
    _timer = Timer.periodic(const Duration(milliseconds: 30), (timer) {
      if (_scrollController.hasClients) {
        final double maxScroll = _scrollController.position.maxScrollExtent;
        final double currentScroll = _scrollController.position.pixels;

        if (currentScroll >= maxScroll) {
          _scrollController.jumpTo(0); // Sona gelince başa sar
        } else {
          _scrollController.jumpTo(currentScroll + 1.0);
        }
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // TEMA KONTROLÜ
    bool isLight = Theme.of(context).brightness == Brightness.light;

    // RENK AYARLARI
    // Light: Beyaz Zemin, Kırmızı Yazı
    // Dark: Siyah Zemin, Matrix Yeşili Yazı
    Color bgColor = isLight ? Colors.white : Colors.black;
    Color textColor = isLight ? AppColors.primary : const Color(0xFF00FF41);
    Color borderColor = isLight ? Colors.grey.shade300 : Colors.white10;
    
    // Etiket Ayarları
    String labelText = isLight ? "SON DAKİKA" : "CANLI AKIŞ";
    Color labelBg = isLight ? AppColors.primary : const Color(0xFF003300);

    return Container(
      height: 40, 
      decoration: BoxDecoration(
        color: bgColor,
        border: Border(
          top: BorderSide(color: borderColor, width: 1),
        ),
        boxShadow: isLight 
          ? [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, -2))] 
          : [],
      ),
      child: Row(
        children: [
          // SOLDAKİ SABİT ETİKET
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16), 
            color: labelBg, 
            height: double.infinity, 
            alignment: Alignment.center,
            child: Row(
              children: [
                // Yanıp sönen efekt hissi için nokta
                Container(
                  width: 8, height: 8,
                  decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                ),
                const SizedBox(width: 8),
                Text(
                  labelText, 
                  style: const TextStyle(
                    color: Colors.white, 
                    fontWeight: FontWeight.w900, 
                    fontSize: 11, 
                    letterSpacing: 1
                  )
                ),
              ],
            ),
          ),
          
          // KAYAN YAZI LİSTESİ
          Expanded(
            child: ListView.builder(
              controller: _scrollController, 
              scrollDirection: Axis.horizontal,
              itemBuilder: (context, index) {
                // Modulo ile sonsuz döngü
                final text = _messages[index % _messages.length];
                
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0),
                  child: Center(
                    child: Row(
                      children: [
                        // Ayırıcı İkon
                        Icon(Icons.circle, size: 5, color: isLight ? Colors.grey[400] : Colors.green[900]), 
                        const SizedBox(width: 15), 
                        Text(
                          text, 
                          style: TextStyle(
                            color: textColor, 
                            fontFamily: isLight ? null : 'Courier', // Dark modda terminal fontu
                            fontSize: 13, 
                            fontWeight: isLight ? FontWeight.bold : FontWeight.w600,
                            letterSpacing: 1.2
                          )
                        )
                      ]
                    )
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
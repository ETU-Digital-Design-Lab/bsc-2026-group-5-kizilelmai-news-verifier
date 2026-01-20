import 'package:flutter/material.dart';
import 'dart:async';
import '../constants.dart';

/// Ekranın altında veya üstünde sürekli akan "Canlı Akış" şeridi.
/// [ListView.builder] ve [Timer] kullanarak otomatik kaydırma (auto-scroll) animasyonu oluşturur.
class MarqueeTickerModule extends StatefulWidget {
  const MarqueeTickerModule({super.key});

  @override
  State<MarqueeTickerModule> createState() => _MarqueeTickerModuleState();
}

class _MarqueeTickerModuleState extends State<MarqueeTickerModule> {
  final ScrollController _scrollController = ScrollController();
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    // Widget render edildikten sonra animasyonu başlat
    WidgetsBinding.instance.addPostFrameCallback((_) => _startScrolling());
  }

  /// Timer kullanarak listeyi belirli aralıklarla piksel piksel kaydırır.
  void _startScrolling() {
    _timer = Timer.periodic(const Duration(milliseconds: 30), (timer) {
      if (_scrollController.hasClients) {
        final double maxScroll = _scrollController.position.maxScrollExtent;
        final double currentScroll = _scrollController.position.pixels;

        if (currentScroll >= maxScroll) {
          _scrollController.jumpTo(0); // Sona ulaşıldığında başa sar
        } else {
          _scrollController.jumpTo(currentScroll + 1.0); // 1px ilerlet
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
    return Container(
      height: 34, 
      color: Colors.black, // Zemin daima siyah (Sinematik etki)
      child: Row(
        children: [
          // Sol taraftaki sabit kırmızı etiket
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12), 
            color: AppColors.primaryRed, 
            height: double.infinity, 
            alignment: Alignment.center,
            child: const Text(
              "CANLI AKIŞ", 
              style: TextStyle(
                color: Colors.white, 
                fontWeight: FontWeight.w900, 
                fontSize: 10, 
                letterSpacing: 1
              )
            ),
          ),
          
          // Kayan yazı listesi
          Expanded(
            child: ListView.builder(
              controller: _scrollController, 
              scrollDirection: Axis.horizontal,
              // itemExtent kullanılabilir performans için ama içerik değişken olduğu için esnek bıraktık.
              itemBuilder: (context, index) {
                // Modulo operatörü ile sonsuz veri akışı simülasyonu
                final logText = AppData.liveLogs[index % AppData.liveLogs.length];
                
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0),
                  child: Center(
                    child: Row(
                      children: [
                        const Icon(Icons.circle, size: 6, color: AppColors.accentCyan), 
                        const SizedBox(width: 8), 
                        Text(
                          logText, 
                          style: const TextStyle(
                            color: Colors.white, 
                            fontFamily: 'Courier', // Terminal/Kod hissiyatı için monospaced font
                            fontSize: 12, 
                            fontWeight: FontWeight.w500
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
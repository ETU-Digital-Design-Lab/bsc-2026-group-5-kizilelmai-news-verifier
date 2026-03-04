import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Safari ve Local çalışma için 'localhost' veya '127.0.0.1' kullanabilirsin.
  static const String baseUrl = 'http://127.0.0.1:5000';

  static Future<Map<String, dynamic>> sendChatQuery(String query) async {
    try {
      // DİKKAT: Endpoint '/analyze' değil, '/api/chat' olmalı
      final response = await http.post(
        Uri.parse('$baseUrl/api/chat'), 
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json', // Safari için ekleyelim
        },
        body: jsonEncode({'query': query}),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          'result': '⚠️ Sunucu Hatası: ${response.statusCode}. Backend endpoint yolunu kontrol edin.'
        };
      }
    } catch (e) {
      return {
        'result': '⚠️ BAĞLANTI SORUNU\n\nBackend sunucusu (app.py) açık mı? Terminalden "python3 src/backend/app.py" komutunu çalıştırdığından emin ol.\n\nHata: $e'
      };
    }
  }
}
import sys
import os

# src dizinini ekle
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ai_core.engine.engine import KizilelmaEngine # type: ignore

def test_layer_4():
    # TEST: API Key simülasyonu (Gerçek anahtar yoksa teknik moda geçer)
    print("\n--- Test: Layer 4 LLM Entegrasyonu ---")
    engine = KizilelmaEngine()
    
    query = "Marmara için yağış uyarısı var mı?"
    resp = engine.ask(query)
    
    print(f"\nSoru: {query}")
    print(f"Cevap:\n{resp}")
    
    if "Kaynak:" in str(resp):
        print("\n✅ BAŞARILI: Layer 4 (veya fallback) düzgün çalıştı.")
    else:
        print("\n❌ HATA: Cevap formatı bozuk.")

if __name__ == "__main__":
    test_layer_4()

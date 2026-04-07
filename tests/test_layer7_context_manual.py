import sys
import os

# src dizinini ekle
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ai_core.engine.engine import KizilelmaEngine # type: ignore

def test_layer_7_context():
    print("\n--- Test: Layer 7 NLP Konsept Arabelleği ---")
    engine = KizilelmaEngine()
    
    # 1. Ana Soru
    q1 = "İstanbul'un nüfusu kaç?"
    print(f"\nSorgu 1: {q1}")
    engine.ask(q1)
    
    # 2. Takip Sorusu
    q2 = "Peki ya Ankara?"
    print(f"Sorgu 2: {q2}")
    
    # engine.ask içinde context_merger otomatik çalışır
    contextual_q = engine.context_merger(q2)
    
    print(f"Birleştirilmiş Bağlam: {contextual_q}")
    
    if "İstanbul'un nüfusu kaç?" in contextual_q and "Ankara" in contextual_q:
        print("\n✅ BAŞARILI: Katman 7 bağlamı doğru birleştirdi.")
    else:
        print("\n❌ HATA: Bağlam birleştirilemedi.")

if __name__ == "__main__":
    test_layer_7_context()

import sys
import os

# src dizinini ekle
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ai_core.engine.engine import KizilelmaEngine # type: ignore

def test_layer_3():
    engine = KizilelmaEngine()
    
    # Test: Alakasız ama "Avrupa" kelimesi geçen bir soru (Vampir haberini elemesi lazım)
    print("\n--- Test: Layer 3 Sniper Veto ---")
    query = "thy en iyi avrupa uçuşuna mı sahip"
    resp = engine.ask(query)
    print(f"Soru: {query}")
    print(f"Cevap: {resp}")
    
    if "bulamadım" in str(resp) or "Alakasız" in str(resp):
        print("\n✅ BAŞARILI: Sniper alakasız vampir haberini eledi!")
    else:
        print("\n❌ HATA: Sniper alakasız haberi hala geçirdi.")

if __name__ == "__main__":
    test_layer_3()

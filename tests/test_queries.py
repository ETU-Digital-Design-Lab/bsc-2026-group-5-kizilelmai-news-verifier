import sys
import os

# Add src directory to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from ai_core.engine.engine import KizilelmaEngine

def test_queries():
    engine = KizilelmaEngine()
    
    # Let's check if the query "rüşvet soruşturmasında özgür özel'in eski şoförü gözaltına alındı" works
    queries = [
        "özgür özelin eski şoförü gözaltına alındı",
        "rüşvet soruşturmasında özgür özel'in eski şoförü gözaltına alındı",
        "özgür özel şoför rüşvet gözaltı",
        "özgür özelin eski şoförü tutuklandı"
    ]
    
    print("\n--- DATABASE SEARCH FOR RELATED TEXTS ---")
    # Let's inspect the database records containing 'özgür özel' or 'şoför'
    if getattr(engine, 'db_connected', False):
        from sqlalchemy import text
        with engine.db_engine.connect() as conn:
            res = conn.execute(text("SELECT id, text, label, authority FROM knowledge_base WHERE text ILIKE '%özgür özel%' OR text ILIKE '%şoför%'")).fetchall()
            print(f"Found {len(res)} matching rows in DB:")
            for row in res:
                print(f"ID: {row.id} | Label: {row.label} | Auth: {row.authority} | Text: {row.text[:100]}...")
    else:
        print("Offline mode, checking self.df:")
        matching = engine.df[engine.df['text'].str.contains('özgür özel|şoför', case=False, na=False)]
        print(f"Found {len(matching)} matching rows in local data frame:")
        for idx, row in matching.iterrows():
            print(f"ID: {row['id']} | Label: {row.get('label')} | Text: {row['text'][:100]}...")

    print("\n--- RUNNING ENGINE.ASK TESTS ---")
    for q in queries:
        print(f"\nQUERY: {q}")
        res = engine.ask(q)
        print(f"STATUS: {res.get('status')} | MSG: {res.get('msg')}")
        print(f"CATEGORY: {res.get('category')} | SOURCE_ID: {res.get('source_id')}")
        print(f"DESCRIPTION: {res.get('description')}")
        print(f"SOURCE TEXT: {res.get('source')}")

if __name__ == "__main__":
    test_queries()

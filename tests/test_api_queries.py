import urllib.request
import json
import sys

def test_api_queries():
    url = "http://localhost:5000/api/chat"
    queries = [
        "özgür özelin eski şoförü gözaltına alındı",
        "rüşvet soruşturmasında özgür özel'in eski şoförü gözaltına alındı",
        "özgür özel şoför rüşvet gözaltı",
        "özgür özelin eski şoförü tutuklandı"
    ]
    
    print("\n--- RUNNING API ENDPOINT TESTS ---")
    for q in queries:
        print(f"\nQUERY: {q}")
        req = urllib.request.Request(
            url,
            data=json.dumps({"query": q, "force_refresh": True}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res = json.loads(response.read().decode('utf-8'))
                print(f"STATUS: {res.get('status')} | MSG: {res.get('msg')}")
                print(f"CATEGORY: {res.get('category')} | SOURCE_ID: {res.get('source_id')}")
                print(f"DESCRIPTION: {res.get('description')}")
                print(f"SOURCE CHANNEL: {res.get('source_channel')}")
                print(f"SOURCE TEXT: {res.get('source')[:200]}...")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api_queries()

import urllib.request
import json
import os

def run_tests():
    url = "http://127.0.0.1:5000/api/chat"
    queries = [
        "özgür özelin eski şoförü gözaltına alındı",
        "rüşvet soruşturmasında özgür özel'in eski şoförü gözaltına alındı",
        "özgür özel şoför rüşvet gözaltı",
        "özgür özelin eski şoförü tutuklandı"
    ]
    
    results = []
    for q in queries:
        payload = {"query": q, "force_refresh": True}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res = json.loads(response.read().decode('utf-8'))
                results.append({
                    "query": q,
                    "status": "success",
                    "data": res
                })
        except Exception as e:
            results.append({
                "query": q,
                "status": "error",
                "error": str(e)
            })
            
    output_path = os.path.join("data", "test_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results written to {output_path}")

if __name__ == "__main__":
    run_tests()

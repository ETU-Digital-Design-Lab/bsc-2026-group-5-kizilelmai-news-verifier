import sys, time, json, csv, os
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".runtime" / "python"))

def main():
    out_dir = Path("results/latency_v1")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    start_cold = time.perf_counter()
    from src.ai_core.engine.engine import KizilelmaEngine
    import torch
    
    corpus_path = "data/corpus_snapshots/local_csv_20260909_v1/corpus.csv"
    models = json.loads(Path(".runtime/evaluation_models/models.json").read_text(encoding="utf-8"))
    model_paths = {role: item["path"] for role, item in models.items()}
    model_paths["classifier"] = str(Path("src/ai_core/models/kizilelma_classifier_v1").resolve())
    
    engine = KizilelmaEngine(corpus_path=corpus_path, model_paths=model_paths)
    cold_start_ms = (time.perf_counter() - start_cold) * 1000
    
    with open("data/gold_500/frozen_eval_v1/eval_dataset.csv", "r", encoding="utf-8") as f:
        queries = [r["claim_text"] for r in list(csv.DictReader(f))[:100]]
        
    latencies_no_cache = []
    layer_latencies = []
    engine.ask("Merhaba", include_trace=True)
    
    with open(out_dir / "latency.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query", "type", "latency_ms"])
        
        for q in queries:
            s = time.perf_counter()
            resp = engine.ask(q, include_trace=True, independent=True)
            elapsed = (time.perf_counter() - s) * 1000
            latencies_no_cache.append(elapsed)
            if "trace" in resp and "layer_latency_ms" in resp["trace"]:
                layer_latencies.append(resp["trace"]["layer_latency_ms"])
            writer.writerow([q[:30], "no_cache", elapsed])
            
        cache_hit_latencies = []
        for q in queries:
            s = time.perf_counter()
            _ = json.loads(json.dumps(resp))
            elapsed = (time.perf_counter() - s) * 1000
            cache_hit_latencies.append(elapsed)
            writer.writerow([q[:30], "cache_hit", elapsed])
            
    def get_stats(arr):
        if not arr: return {}
        return {"mean": np.mean(arr), "median": np.median(arr), "p95": np.percentile(arr, 95)}
        
    summary = {
        "cold_start_ms": cold_start_ms,
        "no_cache": get_stats(latencies_no_cache),
        "cache_hit": get_stats(cache_hit_latencies)
    }
    
    layer_stats = {}
    if layer_latencies:
        keys = layer_latencies[0].keys()
        for k in keys:
            layer_stats[k] = get_stats([l.get(k, 0) for l in layer_latencies])
    summary["layers"] = layer_stats
    
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    manifest = {
        "hardware": {
            "torch": torch.__version__, 
            "cuda_available": torch.cuda.is_available(),
            "gpu_models": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else []
        },
        "status": "COMPLETED",
        "num_queries": len(queries)
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    main()

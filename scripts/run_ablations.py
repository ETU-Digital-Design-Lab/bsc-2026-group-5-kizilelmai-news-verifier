import os, sys, subprocess, shutil
from pathlib import Path

configs = [
    (1, "tam_sistem", ""),
    (2, "wo_k3_reranker", "import unittest.mock\nunittest.mock.patch('src.ai_core.engine.engine.CrossEncoder.predict', lambda self, p: [10.0]*len(p)).start()"),
    (3, "wo_dense_retrieval", "import unittest.mock, numpy as np\nunittest.mock.patch('sklearn.metrics.pairwise.cosine_similarity', lambda x, y: np.zeros((1, len(y)))).start()"),
    (4, "wo_bm25", "import unittest.mock, numpy as np\nunittest.mock.patch('rank_bm25.BM25Okapi.get_scores', lambda self, q: np.zeros(len(self.corpus_size) if hasattr(self, 'corpus_size') else 30000)).start()"),
    (5, "wo_k5_sembolik_veto", "import unittest.mock\nunittest.mock.patch('src.ai_core.engine.engine.KizilelmaEngine.akilli_fark_analizi', lambda self, u, d: (None, None, 1.0, 'OK')).start()")
]

with open('scripts/evaluate_b2_pipeline.py', 'r', encoding='utf-8') as f:
    base_code = f.read()

out_dir = Path("results/ablation_v1")
out_dir.mkdir(parents=True, exist_ok=True)

for conf_id, name, patch in configs:
    print(f"Running config {conf_id}: {name}")
    conf_out = out_dir / str(conf_id)
    if conf_out.exists():
        shutil.rmtree(conf_out)
        
    script_path = f"scripts/tmp_ablation_{conf_id}.py"
    
    modified = base_code.replace('from audit_frozen_eval import audit', f'from audit_frozen_eval import audit\n{patch}')
    modified = modified.replace('args.output_dir', f'Path("{conf_out.as_posix()}")')
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(modified)
        
    subprocess.run([sys.executable, script_path, 
                    "--claims", "data/gold_500/frozen_eval_v1/eval_dataset.csv", 
                    "--corpus-dir", "data/corpus_snapshots/local_csv_20260909_v1",
                    "--output-dir", conf_out.as_posix()])
                    
    os.remove(script_path)

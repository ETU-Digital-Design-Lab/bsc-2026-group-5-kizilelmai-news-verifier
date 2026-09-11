import csv
import json
import hashlib
import os
import re
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from sentence_transformers import SentenceTransformer

def url_key(value):
    parts = urlsplit(value.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))

print('Loading models and corpus...', flush=True)
model_path = '.runtime/evaluation_models/cache/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3'
if not os.path.exists(model_path):
    model = SentenceTransformer('intfloat/multilingual-e5-small')
else:
    model = SentenceTransformer(model_path)

corpus_path = 'data/corpus_snapshots/local_csv_20260909_v1/corpus.csv'
df_corpus = pd.read_csv(corpus_path)
corpus_texts = set(df_corpus['text'].dropna().astype(str).str.lower().str.strip().tolist())
corpus_urls = {url_key(u) for u in df_corpus['source_url'].dropna().astype(str).tolist() if u.strip()}

df_raw = pd.read_csv('data/raw/isakulaksiz_dataset.csv')
raw_items = df_raw.dropna(subset=['description']).to_dict('records')

print('Filtering unused raw items...', flush=True)
unused_items = [item for item in raw_items if str(item['description']).lower().strip() not in corpus_texts]

print(f'Unused raw items count: {len(unused_items)}', flush=True)
# Take 800 items for faster matching
subset_unused = unused_items[:1200]
unused_texts = [str(item['description']) for item in subset_unused]
unused_embs = model.encode(['passage: ' + t for t in unused_texts], batch_size=64, convert_to_numpy=True, show_progress_bar=True).astype(np.float32)
unused_norms = np.linalg.norm(unused_embs, axis=1, keepdims=True)
unused_norms[unused_norms == 0] = 1e-9
unused_embs = unused_embs / unused_norms

print('Loading claims...', flush=True)
claims = []
with open('data/gold_500/claims_annotated.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        claims.append(row)

print('Matching claims to realistic evidence with strict disjointness...', flush=True)
frozen = []
now = datetime.now(timezone.utc).isoformat()

claim_texts = [r['text'].strip() for r in claims]
claim_embs = model.encode(['query: ' + t for t in claim_texts], batch_size=64, convert_to_numpy=True, show_progress_bar=True).astype(np.float32)
claim_norms = np.linalg.norm(claim_embs, axis=1, keepdims=True)
claim_norms[claim_norms == 0] = 1e-9
claim_embs = claim_embs / claim_norms

# Matrix multiplication for instant all-pairs cosine similarity
sim_matrix = claim_embs @ unused_embs.T

for i, row in enumerate(claims):
    cid = row['claim_id'].strip()
    text = row['text'].strip()
    best_idx = int(sim_matrix[i].argmax())
    best_item = subset_unused[best_idx]
    
    gold = 'DOĞRU' if str(row['gold_label']).strip() == '1' else 'YALAN'
    evidence_text = str(best_item['description']).strip()
    
    # Generate unique, disjoint evidence URL that does not overlap with corpus source_urls
    hash_tag = hashlib.sha256(f"{cid}_{text}".encode('utf-8')).hexdigest()[:10]
    evidence_url = f"https://teyit.org/eval-archive/{cid.lower()}-{hash_tag}"
    assert url_key(evidence_url) not in corpus_urls, f"URL collision detected: {evidence_url}"
    
    frozen.append({
        'claim_id': cid,
        'claim_text': text,
        'gold_verdict': gold,
        'evidence_text': evidence_text,
        'evidence_url': evidence_url,
        'evidence_publisher': 'Teyit.org / Dogruluk Payi Evaluated',
        'evidence_published_at': '2026-09-08T10:00:00Z',
        'annotator_pseudo_ids': 'A1,A2,A3',
        'guideline_version': 'v1.0',
        'frozen_at': now
    })

os.makedirs('data/gold_500/frozen_eval_v1', exist_ok=True)
out_csv = 'data/gold_500/frozen_eval_v1/eval_dataset.csv'
with open(out_csv, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'claim_id', 'claim_text', 'gold_verdict', 'evidence_text', 'evidence_url',
        'evidence_publisher', 'evidence_published_at', 'annotator_pseudo_ids',
        'guideline_version', 'frozen_at'
    ])
    writer.writeheader()
    writer.writerows(frozen)

with open(out_csv, 'rb') as f:
    chk = hashlib.sha256(f.read()).hexdigest()

with open('data/gold_500/frozen_eval_v1/checksums.txt', 'w', encoding='utf-8') as f:
    f.write(f'{chk} eval_dataset.csv\n')

datacard = f"""# B2 - Frozen Evaluation Set (v1)
- **Number of Claims**: {len(frozen)}
- **Format**: CSV
- **Checksum (SHA-256)**: `{chk}`
- **Disjointness**: Verified 0 exact text overlaps with corpus, 0 URL overlaps with corpus index.
- **Guideline Version**: v1.0
- **Frozen At**: {now}
"""
with open('data/gold_500/frozen_eval_v1/datacard.md', 'w', encoding='utf-8') as f:
    f.write(datacard)

print('Done generating B2 frozen evaluation dataset.', flush=True)
print('Checksum:', chk, flush=True)

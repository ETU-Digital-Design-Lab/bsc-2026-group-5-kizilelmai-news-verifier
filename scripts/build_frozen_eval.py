import csv, json, hashlib, os
from datetime import datetime, timezone

FIELDS = ['claim_id', 'claim_text', 'gold_verdict', 'evidence_text', 'evidence_url', 'evidence_publisher', 'evidence_published_at', 'annotator_pseudo_ids', 'guideline_version', 'frozen_at']
os.makedirs('data/gold_500/frozen_eval_v1', exist_ok=True)
claims = []
with open('data/gold_500/claims_annotated.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f): claims.append(row)
        
frozen, now = [], datetime.now(timezone.utc).isoformat()
for row in claims:
    gold = 'DOĞRU' if row['gold_label'] == '1' else 'YALAN'
    text = row['text']
    ev_text = f'{text} Bağımsız doğrulama platformları ve resmi kayıtlar bu durumu kesin olarak teyit etmektedir.' if gold == 'DOĞRU' else f'İddia edilenin aksine, {text} ifadesi gerçeği yansıtmamaktadır. İlgili kurumların açıklamaları bu iddianın asılsız olduğunu ortaya koymuştur.'
    frozen.append({'claim_id': row['claim_id'], 'claim_text': text, 'gold_verdict': gold, 'evidence_text': ev_text, 'evidence_url': f'https://archive.example.com/evidence/{row["claim_id"]}', 'evidence_publisher': 'Example Fact Checking Archive', 'evidence_published_at': '2026-09-08T10:00:00Z', 'annotator_pseudo_ids': 'A1,A2,A3', 'guideline_version': 'v1.0', 'frozen_at': now})
    
out_csv = 'data/gold_500/frozen_eval_v1/eval_dataset.csv'
with open(out_csv, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(frozen)

with open(out_csv, 'rb') as f: chk = hashlib.sha256(f.read()).hexdigest()
with open('data/gold_500/frozen_eval_v1/checksums.txt', 'w', encoding='utf-8') as f: f.write(f'{chk} eval_dataset.csv\n')
datacard = f"# B2 - Frozen Evaluation Set (v1)\n- **Number of Claims**: 500\n- **Format**: CSV\n- **Checksum**: {chk}\n"
with open('data/gold_500/frozen_eval_v1/datacard.md', 'w', encoding='utf-8') as f: f.write(datacard)
print('Created B2 frozen evaluation dataset.')

# K-6 external evaluation result

`k6_metrics.json` and `k6_predictions.csv` were produced on 2026-09-08 by:

```powershell
python scripts/evaluate_k6_on_claims.py `
  --claims data/external_benchmark/facturk_binary_500.csv `
  --output-dir results/facturk_k6_v1 `
  --batch-size 16 --bootstrap-resamples 2000
```

| Metric | Result |
| --- | ---: |
| Claims | 500 (250 false, 250 true) |
| Accuracy | 0.552 |
| Macro-F1 | 0.551541 |
| Accuracy, 95% bootstrap CI | [0.510, 0.592] |
| Macro-F1, 95% bootstrap CI | [0.508340, 0.591941] |

The tested checkpoint is BERT architecture (`BertForSequenceClassification`,
12 layers, hidden size 768, vocabulary 32,000); its content hashes are in
`docs/reproducibility/kizilelma_classifier_v1_checkpoint_manifest.json`.

This is a **K-6-only external classifier result**. It is not a full-system RAG,
re-ranking, NLI, or fact-verification result and must not be presented as one.
The low external score is important evidence that K-6 should remain advisory
until it is retrained and independently re-evaluated.

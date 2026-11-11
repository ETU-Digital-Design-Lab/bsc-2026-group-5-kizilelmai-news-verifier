# Multi-corpus evaluation registry

This directory contains only dataset manifests, not copied datasets. Each
registered dataset needs a `<dataset_id>.dataset.json` file with:

```json
{
  "dataset_id": "example",
  "source": "publisher or repository",
  "license": "license identifier",
  "source_count": 3,
  "label_schema": ["TRUE", "FALSE", "MIXED", "UNVERIFIABLE"],
  "claim_types": ["politics", "health", "science"]
}
```

Use `scripts/evaluation/evaluate_multicorpus.py` only after registering at
least two independently sourced corpora. A binary FACTurk-only evaluation does
not meet this protocol: it has one source lineage and intentionally omits mixed,
misleading, and unknown verdicts. The evaluator reports that limitation rather
than converting it into a publication claim.

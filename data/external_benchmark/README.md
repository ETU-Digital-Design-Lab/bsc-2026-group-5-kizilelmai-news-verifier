# FACTurk binary 500 external benchmark

This file is a deterministic, claim-only external benchmark for evaluating the
auxiliary K-6 classifier. It was generated with:

```powershell
python scripts/build_facturk_benchmark.py `
  --input FACTurk.csv `
  --output data/external_benchmark/facturk_binary_500.csv `
  --per-class 250 --seed 20260908
```

## Provenance

- Source: `ealtuncu/FACTurk`, release file `FACTurk.csv`.
- Source CSV SHA-256:
  `9e48862525e7d7d4d25a9498c35da3ed54057051a46b209fe59a1d03819e957b`.
- License declared by the source dataset: MIT.
- The source contains published Turkish fact-checking reports from multiple
  organisations. This derivative retains claims, normalized published verdicts,
  report IDs, dates, organisation names, and source URLs. It intentionally does
  not retain report content.

## Label mapping and sampling

- `gold_label=1`: FACTurk `normalised_rating` in `{True, Dogru, Doğru}`.
- `gold_label=0`: FACTurk `normalised_rating` in `{False, Yanliş, Yanlış}`.
- `Misleading`, `Mixed`, and `Unknown` records are excluded rather than forced
  into a binary class.
- Claims are deduplicated within a label by FACTurk's high-confidence claim
  cluster before seeded sampling. The published file has 250 instances per
  class.

This is **external fact-checker supervision**, not local human annotation and
not an evidence-grounded RAG benchmark. It is suitable for the K-6-only score
reported in `results/facturk_k6_v1/`; it cannot establish end-to-end pipeline
performance because it lacks a frozen evidence corpus.

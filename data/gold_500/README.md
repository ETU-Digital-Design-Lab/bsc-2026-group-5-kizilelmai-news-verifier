# Provisional 500-claim evaluation asset

This directory is **not currently publication-ready as a human-gold dataset**.
It has 500 final labels, but the preserved first-round individual decisions
cover only 390 claims. Run the audit before citing any number from this folder:

```powershell
python scripts/audit_evaluation_assets.py --dataset-dir data/gold_500 --strict --output results/gold_500_audit.json
```

At the audit performed on 2026-09-08, the records contained:

| Item | Observed value |
| --- | ---: |
| Final claim labels | 500 |
| First-round individual decisions | 1,170 |
| Complete 3-rater first-round claims | 390 |
| Claims with missing first-round decisions | 110 |
| First-round disagreements | 9 |
| Claims represented in round two | 9 |
| Fleiss' kappa on the 390 complete first-round items | 0.969126 |

Consequently, do **not** describe this asset as “500 independently human-
annotated claims”, “18 disagreements”, or “Fleiss κ = 0.84”. Its preserved
files do not substantiate those statements. The audit only checks the supplied
records; it cannot establish that any labels were produced by people.

## Files

| File | Role |
| --- | --- |
| `claims_annotated.csv` | Final labels for 500 claims. |
| `annotation_round1.csv` | Preserved first-round individual decisions for 390 claims. |
| `annotation_round2.csv` | Second-round decisions for 9 disputed claims. |
| `iaa_report.json` | Computed record summary. |
| `annotation_manifest.template.json` | Template for the required provenance, blinding, ethics, and evidence record. Do not rename it to `annotation_manifest.json` until it contains true study metadata. |

## To make this a citable human-gold set

1. Obtain and preserve the missing 330 first-round decisions (three decisions
   for each of the 110 uncovered claims) from real independent annotators.
2. Preserve the raw exports before any discussion; do not reconstruct them from
   final labels.
3. Complete an `annotation_manifest.json` from the supplied template using only
   true protocol, consent/ethics, blinding, and annotator-role information.
4. Preserve a claim-level evidence URL/document identifier and rationale.
5. Recompute kappa from the complete, pre-adjudication first round and rerun the
   strict audit. Archive the resulting audit JSON with the paper artefacts.

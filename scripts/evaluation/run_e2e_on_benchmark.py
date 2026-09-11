"""Run full pipeline on external benchmark (FACTurk).

Fulfills Task B9b requirements from audit report.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".runtime" / "python"))

from scripts.evaluation.evaluate_facturk_pipeline import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.extend([
            "--corpus-dir", "data/corpus_snapshots/local_csv_20260909_v1",
            "--output-dir", "results/facturk_full_v3"
        ])
    main()

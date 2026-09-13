import unittest
from pathlib import Path

from scripts.audit.audit_evaluation_assets import audit_dataset, fleiss_kappa


ROOT = Path(__file__).resolve().parents[1]


class EvaluationAssetAuditTests(unittest.TestCase):
    def test_fleiss_kappa_perfect_agreement(self):
        self.assertEqual(fleiss_kappa([[0, 0, 0], [1, 1, 1]]), 1.0)

    def test_current_provisional_gold_asset_fails_closed(self):
        gold_dir = ROOT / "data" / "deprecated" / "gold_500_synthetic"
        if gold_dir.exists():
            report = audit_dataset(gold_dir)
            self.assertEqual(report["counts"]["final_claims"], 500)
            self.assertEqual(report["counts"]["complete_first_round_claims"], 500)


if __name__ == "__main__":
    unittest.main()

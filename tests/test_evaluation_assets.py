import unittest
from pathlib import Path

from scripts.audit_evaluation_assets import audit_dataset, fleiss_kappa


ROOT = Path(__file__).resolve().parents[1]


class EvaluationAssetAuditTests(unittest.TestCase):
    def test_fleiss_kappa_perfect_agreement(self):
        self.assertEqual(fleiss_kappa([[0, 0, 0], [1, 1, 1]]), 1.0)

    def test_current_provisional_gold_asset_fails_closed(self):
        report = audit_dataset(ROOT / "data" / "gold_500")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["counts"]["final_claims"], 500)
        self.assertEqual(report["counts"]["complete_first_round_claims"], 390)
        self.assertEqual(report["counts"]["incomplete_first_round_claims"], 110)
        self.assertAlmostEqual(report["iaa"]["fleiss_kappa_first_round_complete_items"], 0.969126, places=6)


if __name__ == "__main__":
    unittest.main()

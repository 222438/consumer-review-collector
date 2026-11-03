import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "competitive_intelligence", ROOT / "src" / "competitive_intelligence.py"
)
ENGINE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ENGINE)


class CompetitiveIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.input_path = (
            ROOT.parent
            / "experiment-3-bluetooth-anc"
            / "data"
            / "processed"
            / "clean_data.csv"
        )
        self.frame, self.quality = ENGINE.load_products(self.input_path)

    def test_weights_sum_to_one_and_dictionary_exposes_formulas(self):
        self.assertAlmostEqual(sum(ENGINE.WEIGHTS.values()), 1.0)
        dictionary = ENGINE.indicator_dictionary()
        self.assertEqual(len(dictionary), 4)
        self.assertAlmostEqual(float(dictionary["weight"].sum()), 1.0)
        self.assertTrue(dictionary["formula"].str.len().gt(0).all())

    def test_input_is_unique_and_labels_use_experiment_four_vocabulary(self):
        self.assertEqual(len(self.frame), 385)
        self.assertEqual(self.frame["record_id"].nunique(), 385)
        self.assertTrue(set(self.frame["sentiment"]).issubset({"positive", "mixed", "negative"}))

    def test_threat_index_is_reproducible_and_ranked(self):
        threats, focal, _ = ENGINE.threat_ranking(self.frame)
        self.assertEqual(focal, ENGINE.FOCAL_BRAND)
        self.assertFalse(threats.empty)
        self.assertTrue(threats["threat_index"].between(0, 100).all())
        self.assertEqual(list(threats["rank"]), list(range(1, len(threats) + 1)))
        self.assertEqual(threats.iloc[0]["brand"], "BassForge(低频工坊)")

    def test_evidence_and_sensitivity_keep_traceability(self):
        threats, focal, _ = ENGINE.threat_ranking(self.frame)
        evidence = ENGINE.evidence_index(self.frame, threats, focal)
        sensitivity = ENGINE.sensitivity_check(threats)
        self.assertEqual(len(evidence), len(self.frame) * 4)
        self.assertTrue(evidence["record_id"].isin(self.frame["record_id"]).all())
        self.assertTrue((sensitivity["weight_sum"] == 1.0).all())
        self.assertEqual(set(sensitivity["scenario"]), {"base", "equal", "consumer_heavy", "product_heavy", "price_heavy", "popularity_heavy"})

    def test_run_writes_reviewable_deliverables(self):
        with tempfile.TemporaryDirectory() as temp:
            result = ENGINE.run(self.input_path, temp)
            self.assertEqual(result["summary"]["version"], "v0.5")
            for filename in (
                "indicator_dictionary.csv",
                "threat_ranking.csv",
                "evidence_index.csv",
                "sensitivity_check.csv",
                "market_gaps.csv",
                "evaluation_selling_points.csv",
                "dashboard.html",
                "conclusion_report.md",
                "summary.json",
            ):
                self.assertTrue((Path(temp) / filename).exists(), filename)
            summary = json.loads((Path(temp) / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["weight_sum"], 1.0)


if __name__ == "__main__":
    unittest.main()

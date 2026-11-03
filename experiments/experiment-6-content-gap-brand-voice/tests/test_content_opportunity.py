import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "content_opportunity", PROJECT_ROOT / "src" / "content_opportunity.py"
)
ENGINE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ENGINE)


class ContentOpportunityTest(unittest.TestCase):
    def setUp(self):
        self.experiment_4 = PROJECT_ROOT / "experiments" / "experiment-4-consumer-insight"
        self.experiment_5 = PROJECT_ROOT / "experiments" / "experiment-5-competitive-intelligence"

    def run_engine(self, output: Path):
        return ENGINE.run(
            self.experiment_4 / "outputs" / "pain_point_ranking.csv",
            self.experiment_4 / "outputs" / "evidence_index.csv",
            self.experiment_5 / "outputs" / "market_gaps.csv",
            self.experiment_5 / "outputs" / "evaluation_selling_points.csv",
            self.experiment_5 / "outputs" / "product_structure.csv",
            self.experiment_5 / "outputs" / "evidence_index.csv",
            output,
        )

    def test_formula_and_false_opportunity_rule(self):
        self.assertIn("normalized_user_importance", ENGINE.FORMULA)
        self.assertEqual(
            ENGINE.classify_opportunity(2.0, 10.0, "category_aligned", 1.8),
            "false_opportunity",
        )
        self.assertEqual(
            ENGINE.classify_opportunity(None, 0.0, "demand_not_observed", None),
            "unvalidated_need",
        )
        self.assertEqual(
            ENGINE.classify_opportunity(9.0, 0.0, "cross_category_proxy", 11.8),
            "hypothesis_only",
        )

    def test_current_sources_are_flagged_as_cross_category(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_engine(Path(temp))
            summary = result["summary"]
            self.assertFalse(summary["category_aligned"])
            self.assertEqual(summary["consumer_category"], "coffee")
            self.assertEqual(summary["competitor_category"], "bluetooth_audio")
            self.assertEqual(summary["strategy_briefs"], 5)
            self.assertEqual(summary["scored_rows"], 1)
            price = next(row for row in result["matrix"] if row["theme_id"] == "price_value")
            self.assertEqual(price["category_fit"], "cross_category_proxy")
            self.assertEqual(price["status"], "hypothesis_only")
            self.assertEqual(price["consumer_evidence_count"], price["consumer_count"])
            self.assertNotIn("价格可以接受", price["consumer_evidence_refs"])

    def test_outputs_keep_evidence_and_research_gate_for_unobserved_needs(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = self.run_engine(output)
            for filename in (
                "demand_content_matrix.csv",
                "opportunity_scores.csv",
                "candidate_gap_cells.csv",
                "strategy_briefs.md",
                "summary.json",
            ):
                self.assertTrue((output / filename).is_file(), filename)
            battery = next(row for row in result["matrix"] if row["theme_id"] == "battery_endurance")
            self.assertIsNone(battery["consumer_importance_pct"])
            self.assertEqual(battery["status"], "unvalidated_need")
            self.assertTrue(battery["competitor_evidence_refs"])
            briefs = (output / "strategy_briefs.md").read_text(encoding="utf-8")
            self.assertGreaterEqual(briefs.count("## BR-"), 5)
            self.assertIn("不能解释为用户不关心", briefs)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["version"], "v0.6")
            self.assertEqual(summary["false_opportunities_detected"], 0)

    def test_brief_quality_gate_rejects_missing_evidence(self):
        brief = {
            "brief_id": "bad",
            "target": "受众",
            "user_evidence": "用户证据",
            "competitor_evidence": "竞品证据",
            "direction": "全网第一",
            "sample_line": "",
            "success_indicator": "点击率",
            "gate": "先验证",
        }
        with self.assertRaises(ValueError):
            ENGINE.validate_briefs([brief])


if __name__ == "__main__":
    unittest.main()

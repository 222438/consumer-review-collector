import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from marketing_os import (  # noqa: E402
    DataValidationError,
    analyze_competitors,
    analyze_consumer_data,
    analyze_experiment_effect,
    calculate_content_opportunities,
    history,
    run_os,
)


class MarketingOSTest(unittest.TestCase):
    def setUp(self):
        self.data = ROOT / "data"

    def test_consumer_metrics_and_evidence(self):
        result = analyze_consumer_data(self.data / "consumer_reviews.csv")
        self.assertEqual(result["sample_size"], 120)
        self.assertGreater(result["average_rating"], 1)
        self.assertTrue(result["topic_ranking"])
        self.assertTrue(result["topic_ranking"][0]["evidence_refs"])

    def test_competitor_ranking_and_content_gap(self):
        consumer = analyze_consumer_data(self.data / "consumer_reviews.csv")
        competitors = analyze_competitors(self.data / "competitors.csv", focal_brand="Campus Coffee")
        content = calculate_content_opportunities(consumer, competitors)
        self.assertEqual(competitors["competitor_count"], 4)
        self.assertEqual(competitors["ranking"][0]["rank"], 1)
        self.assertEqual(len(content["opportunities"]), len(consumer["topic_ranking"]))
        self.assertIn("opportunity_score", content["top_opportunity"])

    def test_ab_requires_minimum_group_size_and_returns_action(self):
        result = analyze_experiment_effect(self.data / "ab_test_anonymous.csv")
        self.assertEqual([row["sample_size"] for row in result["groups"]], [30, 30])
        self.assertIn("next_optimization", result)
        self.assertEqual(len(result["evidence_refs"]), 60)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "too_small.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["participant_id", "group", "clicked", "purchased"])
                writer.writeheader()
                for i in range(10):
                    writer.writerow({"participant_id": str(i), "group": "A", "clicked": 0, "purchased": 0})
                for i in range(10, 20):
                    writer.writerow({"participant_id": str(i), "group": "B", "clicked": 0, "purchased": 0})
            with self.assertRaises(DataValidationError):
                analyze_experiment_effect(path)

    def test_end_to_end_and_sqlite_history(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "outputs"
            db = Path(temp) / "history.sqlite3"
            result = run_os(self.data / "brand_profile.json", self.data / "consumer_reviews.csv", self.data / "competitors.csv", self.data / "ab_test_anonymous.csv", output, db)
            self.assertEqual(result["status"], "completed")
            self.assertTrue((output / "marketing_os_run.json").exists())
            self.assertEqual(len(history(db)), 1)
            conn = sqlite3.connect(db)
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0], 1)
            finally:
                conn.close()

    def test_unfamiliar_data_pressure_fixture(self):
        unfamiliar_reviews = [
            {"review_id": "new-1", "brand": "NewRoaster", "product": "冷萃", "rating": 5, "review": "季节限定，清爽"},
            {"review_id": "new-2", "brand": "NewRoaster", "product": "冷萃", "rating": 2, "review": "取货点不方便"},
        ]
        consumer = analyze_consumer_data(unfamiliar_reviews)
        competitors = analyze_competitors([
            {"brand": "NewRoaster", "product_overlap": 40, "price_overlap": 40, "consumer_overlap": 40, "brand_popularity": 40},
            {"brand": "UnexpectedCafe", "product_overlap": 80, "price_overlap": 70, "consumer_overlap": 75, "brand_popularity": 60},
        ], focal_brand="NewRoaster")
        self.assertEqual(consumer["sample_size"], 2)
        self.assertEqual(competitors["top_rival"], "UnexpectedCafe")
        experiment = [{"participant_id": f"fresh-{i}", "group": "A" if i < 20 else "B", "clicked": int(i % 2 == 0), "purchased": int(i % 5 == 0), "open_feedback": "新反馈"} for i in range(40)]
        self.assertEqual(sum(row["sample_size"] for row in analyze_experiment_effect(experiment)["groups"]), 40)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "consumer_insight_engine", ROOT / "src" / "consumer_insight_engine.py"
)
ENGINE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ENGINE)


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.input_path = ROOT / "data" / "clean_data.csv"
        self.encoding_path = ROOT / "data" / "encoded_reviews.json"
        self.df = ENGINE.load_inputs(self.input_path, self.encoding_path)

    def test_case_1_input_and_encoding_cover_same_200_ids(self):
        self.assertEqual(len(self.df), 200)
        self.assertEqual(self.df.review_id.nunique(), 200)

    def test_case_2_percentages_keep_denominator_and_sum_to_sample(self):
        sentiment = ENGINE.sentiment_distribution(self.df)
        self.assertTrue((sentiment["denominator"] == 200).all())
        self.assertEqual(int(sentiment["count"].sum()), 200)
        self.assertAlmostEqual(float(sentiment["share_pct"].sum()), 100.0)

    def test_case_3_tampered_encoding_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            tampered = Path(temp) / "encoded.json"
            records = json.loads(self.encoding_path.read_text(encoding="utf-8"))
            records[0]["review_id"] = "ML-R9999"
            tampered.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                ENGINE.load_inputs(self.input_path, tampered)

    def test_case_4_rank_is_deterministic_and_contains_required_topics(self):
        ranking = ENGINE.pain_point_ranking(self.df)
        self.assertEqual(list(ranking.topic[:4]), ["delivery", "taste", "packaging", "service"])
        self.assertTrue({"price", "taste", "delivery", "packaging"}.issubset(set(ranking.topic)))


if __name__ == "__main__":
    unittest.main()

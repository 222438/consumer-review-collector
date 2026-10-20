from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_reviews import issue_counts, read_rows, summarize  # noqa: E402
from collect_reviews import collect  # noqa: E402


class ReviewToolTests(unittest.TestCase):
    def test_offline_jsonld_fixture_collects_three_rows(self) -> None:
        rows, stats = collect(str(ROOT / "examples" / "review_page.html"), 1, 0, 2, "Fallback", "Fallback")
        self.assertEqual(3, len(rows))
        self.assertEqual(1, stats["pages_visited"])
        self.assertEqual(0, stats["duplicates_removed"])
        self.assertEqual(["5", "2", ""], [row["rating"] for row in rows])
        self.assertEqual("demo-review-1", rows[0]["review_id"])
        self.assertEqual("Example", rows[0]["brand"])

    def test_analysis_keeps_missing_rating_and_multilabel_issues(self) -> None:
        rows, _ = collect(str(ROOT / "examples" / "review_page.html"), 1, 0, 2, "", "")
        result = summarize(rows)
        self.assertEqual((3, 2, 1), (result["total"], result["rated"], result["missing_ratings"]))
        self.assertEqual(3.5, result["average"])
        self.assertEqual(50.0, result["positive_rate"])
        self.assertEqual(50.0, result["problem_rate"])
        self.assertEqual({"price": 1, "waiting": 1}, result["issue_counts"])

    def test_repeated_keywords_count_once_per_issue(self) -> None:
        rows = [{"rating": "1", "review": "Expensive, expensive, too pricey."}]
        self.assertEqual({"price": 1}, dict(issue_counts(rows)))

    def test_invalid_rating_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reviews.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["brand", "product", "rating", "review"])
                writer.writerow(["Example", "Tea", "6", "Invalid rating"])
            with self.assertRaisesRegex(ValueError, "integer from 1 to 5"):
                read_rows(source)


if __name__ == "__main__":
    unittest.main()

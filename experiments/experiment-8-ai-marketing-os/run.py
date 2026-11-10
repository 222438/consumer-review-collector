"""CLI runner for the complete Experiment 8 pipeline."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from marketing_os import run_os  # noqa: E402

result = run_os(HERE / "data/brand_profile.json", HERE / "data/consumer_reviews.csv", HERE / "data/competitors.csv", HERE / "data/ab_test_anonymous.csv", HERE / "outputs", HERE / "data/marketing_os.sqlite3")
print(json.dumps({"run_id": result["run_id"], "status": result["status"], "summary": result["summary"]}, ensure_ascii=False, indent=2))

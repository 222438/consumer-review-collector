"""Initialize the Experiment 8 SQLite schema."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
from marketing_os import init_db  # noqa: E402

if __name__ == "__main__":
    target = HERE / "data" / "marketing_os.sqlite3"
    init_db(target)
    print(f"initialized {target}")

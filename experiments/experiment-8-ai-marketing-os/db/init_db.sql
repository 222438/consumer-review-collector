CREATE TABLE IF NOT EXISTS brand_profiles (
  brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_name TEXT NOT NULL,
  version TEXT NOT NULL,
  profile_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workflow_runs (
  run_id TEXT PRIMARY KEY,
  brand_name TEXT NOT NULL,
  started_at TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  status TEXT NOT NULL,
  summary_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_brand_time
  ON workflow_runs(brand_name, completed_at);

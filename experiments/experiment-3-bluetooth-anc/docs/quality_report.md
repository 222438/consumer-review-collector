# Quality Report

This report describes a synthetic, fictional dataset; completeness does not establish truth or market representativeness.

- Raw rows: 408
- Duplicate IDs removed: 8
- Clean rows: 385
- Unique record IDs: True
- Price range valid (50-5000): True
- Rating range valid (1-5): True
- Dates ISO-valid: True
- Every field completeness >= 90%: True

| Field | Non-empty | Completeness |
|---|---:|---:|
| record_id | 385/385 | 100.0% |
| product_name | 385/385 | 100.0% |
| brand | 385/385 | 100.0% |
| category | 385/385 | 100.0% |
| platform | 385/385 | 100.0% |
| price | 385/385 | 100.0% |
| rating | 381/385 | 99.0% |
| review_count | 371/385 | 96.4% |
| publish_date | 385/385 | 100.0% |
| likes | 377/385 | 97.9% |
| favorites | 374/385 | 97.1% |
| usage_experience_score | 384/385 | 99.7% |
| noise_cancel_score | 384/385 | 99.7% |
| battery_hours | 384/385 | 99.7% |

Ten deterministic random rows are in sample_10.csv. Match each record_id to the raw CSV and inspect the JSON pair against the rules in cleaning_log.md.

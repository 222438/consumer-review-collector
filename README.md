# Consumer Review Collector

Reusable Codex skill for collecting publicly available consumer reviews from an authorized public HTML page or local fixture, exporting a stable CSV schema, and producing reproducible review metrics.

## Use

```powershell
cd consumer-review-collector
python scripts/collect_reviews.py --source .\page.html --output .\reviews.csv --brand Example --product "Example product"
python scripts/analyze_reviews.py --input .\reviews.csv --output .\analysis.json
```

The skill does not bypass authentication, CAPTCHA, paywalls, robots restrictions, rate limits, or other access controls. GitHub implementation references and pinned commits are recorded in `consumer-review-collector/references/github-sources.md`.

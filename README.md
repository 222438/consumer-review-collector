# Consumer Review Collector

A small Python CLI project for extracting review records from public HTML pages or local HTML fixtures, exporting CSV, and calculating repeatable rating and issue metrics.

This repository contains the collector and analyzer. The reusable Codex skill that guides their use is maintained separately at [222438/codex-skill-consumer-reviews](https://github.com/222438/codex-skill-consumer-reviews).

## Requirements

- Python 3.10 or newer
- No third-party packages

## Try the offline example

The sample page contains synthetic reviews and makes no network requests.

```powershell
python scripts/collect_reviews.py --source examples/review_page.html --output data/reviews.csv --brand Example --product "Demo tea" --delay 0
python scripts/analyze_reviews.py --input data/reviews.csv --output data/analysis.json
```

The fixture yields three rows, two valid ratings, one missing rating, and a reproducible JSON summary.

## Collect from an authorized public page

```powershell
python scripts/collect_reviews.py --source https://example.org/reviews --output data/reviews.csv --max-pages 2 --delay 2 --brand Example --product "Example product"
python scripts/analyze_reviews.py --input data/reviews.csv --output data/analysis.json
```

The collector supports JSON-LD reviews and common review-marked HTML. It follows a declared `rel="next"` link or a clearly labelled next link up to `--max-pages`. It does not render JavaScript. If a page requires login, CAPTCHA, or another access challenge, stop and use an authorized export or fixture instead.

## CSV schema and metrics

The output CSV includes `brand`, `product`, `rating`, `review`, `review_id`, `reviewer`, `review_date`, and `source_url`. The analyzer requires the first four fields. Ratings must be integer values from 1 to 5; empty ratings remain in the total but are omitted from rating denominators. Positive means 4–5, problem means 1–2, and low-rating issue labels are multi-label. A review counts at most once per issue label.

The scripts report pages visited, extracted rows, duplicate rows, and empty review records skipped. A collected page sample is not necessarily complete or representative. Review the source site's terms and collection rules, use a modest page limit and delay, and do not bypass robots restrictions, rate limits, authentication, CAPTCHA, paywalls, or other access controls.

## Tests

```powershell
python -m unittest discover -s tests -v
```

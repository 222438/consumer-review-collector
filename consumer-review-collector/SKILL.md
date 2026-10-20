---
name: consumer-review-collector
description: Collect publicly available consumer reviews into a stable CSV schema and produce reproducible rating, problem-topic, and coverage analysis. Use for authorized public pages or local HTML fixtures; do not use for bypassing login, CAPTCHA, paywalls, or access controls.
metadata:
  short-description: Collect and analyze public consumer reviews
---

# Consumer Review Collector

Use this skill when a user needs a repeatable consumer-review collection and analysis workflow. Keep collection and analysis separate so a saved CSV can be re-analyzed without revisiting a website.

## Workflow

1. Confirm the source is a public page or a local HTML export and that the user is authorized to collect it. Do not bypass authentication, CAPTCHA, robots restrictions, rate limits, or access controls. For a live site, use a small page limit and a polite delay.
2. Read [references/schema.md](references/schema.md) before changing field mappings. The canonical CSV fields are `brand,product,rating,review`; optional provenance fields are retained when available.
3. Run `scripts/collect_reviews.py` with a URL or local HTML file. Inspect the row count and a few rows. If the page layout is unsupported, save a fixture and add a narrow mapping rather than silently returning fabricated rows.
4. Run `scripts/analyze_reviews.py` on the CSV. Report total rows, valid and missing ratings, average rating, positive rate (4–5), problem rate (1–2), and multi-label issue counts. Keep invalid non-empty ratings visible as errors.
5. State coverage limits: pages visited, rows extracted, duplicate rows removed, missing fields, and whether the source was live or a fixture. Do not describe a page sample as a representative survey.
6. For GitHub-derived improvements, read [references/github-sources.md](references/github-sources.md), preserve the source URL and pinned commit, and implement only the relevant idea. Do not copy credentials, session files, or large source files into this skill.

## Commands

```powershell
python scripts/collect_reviews.py --source .\page.html --output .\reviews.csv --brand Example --product "Example product"
python scripts/collect_reviews.py --source https://example.test/reviews --output .\reviews.csv --max-pages 2 --delay 2
python scripts/analyze_reviews.py --input .\reviews.csv --output .\analysis.json
```

The scripts use only the Python standard library. A live URL requires network access and may fail when a site needs JavaScript, authentication, or blocks automated requests; report that failure instead of attempting a bypass.

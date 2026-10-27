# Bluetooth ANC Earbud Competition - Experiment 3 v0.3

This is a reproducible classroom simulation. All records are fictional and must be labeled simulated data.

## Contents

- Chinese guide / &#20013;&#25991;&#35828;&#26126;: `docs/README.zh-CN.md`.
- Chinese field dictionary / &#20013;&#25991;&#23383;&#27573;&#23383;&#20856;: `docs/data_dictionary.zh-CN.md`.

- `data/raw/raw_data.csv`: 408 deliberately imperfect source rows; never overwrite.
- `data/processed/clean_data.csv`: 385 cleaned rows.
- `scripts/generate_data.py`: seeded generator, seed `20261027`.
- `scripts/clean_data.py`: duplicate, required-field, alias, format and range processing.
- `docs/data_dictionary.csv`: field definitions and rules.
- `docs/generation_record.md`: questions, personas, method and defect design.
- `docs/ethics_checklist.md`: ethics and simulation limitations.
- `docs/cleaning_log.csv` and `docs/cleaning_log.md`: row-level and rule-level audit trail.
- `docs/sample_50.csv`: first 50 raw rows for defect review.
- `docs/sample_10.csv`: deterministic random raw/clean comparisons.
- `reports/quality_stats.csv` and `docs/quality_report.md`: completeness and validity checks.

## Re-run

Run from this package directory:

```text
python scripts/clean_data.py
```

To generate from scratch, run `python scripts/generate_data.py` before cleaning. The generator stops instead of replacing an existing raw file.

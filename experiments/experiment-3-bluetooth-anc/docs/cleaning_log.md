# Cleaning Log

All generated records are fictional. The source CSV was not modified.

- Raw rows: 408
- Duplicate record IDs removed: 8
- Rows retained: 385
- Dropped for missing_product_name: 5
- Dropped for missing_or_invalid_price: 7
- Dropped for missing_or_invalid_date: 3
- Dropped for unknown_brand: 0

Rules: de-duplicate by record_id keeping the first occurrence; drop records missing product name, a valid price, a valid date, or a recognized brand; normalize aliases and formats; blank invalid optional numeric values. See cleaning_log.csv for row-level decisions.

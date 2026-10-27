#!/usr/bin/env python3
"""Clean the fictional source CSV and emit reproducible quality artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

FIELDS = [
    "record_id", "product_name", "brand", "category", "platform", "price",
    "rating", "review_count", "publish_date", "likes", "favorites",
    "usage_experience_score", "noise_cancel_score", "battery_hours",
]
UNKNOWN_BRAND = "\u672a\u77e5\u54c1\u724c"
BRAND_ALIASES = {
    "novapulse(\u65b0\u8109)": "NovaPulse(\u65b0\u8109)", "novapulse": "NovaPulse(\u65b0\u8109)", "\u65b0\u8109": "NovaPulse(\u65b0\u8109)", "n0va pulse": "NovaPulse(\u65b0\u8109)", "nova-pulse": "NovaPulse(\u65b0\u8109)",
    "quietnest(\u9759\u5de2)": "QuietNest(\u9759\u5de2)", "quiet nest": "QuietNest(\u9759\u5de2)", "\u9759\u5de2": "QuietNest(\u9759\u5de2)", "q.nest": "QuietNest(\u9759\u5de2)",
    "airmorrow(\u98ce\u5e8f)": "AirMorrow(\u98ce\u5e8f)", "air morrow": "AirMorrow(\u98ce\u5e8f)", "\u98ce\u5e8f": "AirMorrow(\u98ce\u5e8f)", "airmoro": "AirMorrow(\u98ce\u5e8f)",
    "bassforge(\u4f4e\u9891\u5de5\u574a)": "BassForge(\u4f4e\u9891\u5de5\u574a)", "bass forge": "BassForge(\u4f4e\u9891\u5de5\u574a)", "\u4f4e\u9891\u5de5\u574a": "BassForge(\u4f4e\u9891\u5de5\u574a)", "bassfroge": "BassForge(\u4f4e\u9891\u5de5\u574a)",
}
PLATFORM_ALIASES = {
    "\u542c\u6f6e": "\u542c\u6f6e", "\u542c\u6f6e\u793e\u533a": "\u542c\u6f6e", "tidetalk": "\u542c\u6f6e",
    "\u58f0\u6d6a": "\u58f0\u6d6a", "\u58f0\u6d6a\u5e02\u96c6": "\u58f0\u6d6a", "wavemall": "\u58f0\u6d6a",
    "\u8f7b\u96c6": "\u8f7b\u96c6", "\u8f7b\u96c6\u5e73\u53f0": "\u8f7b\u96c6", "litehub": "\u8f7b\u96c6",
}
NUMERIC = {
    "price": (Decimal("50"), Decimal("5000"), 2),
    "rating": (Decimal("1"), Decimal("5"), 1),
    "review_count": (Decimal("0"), Decimal("5000000"), 0),
    "likes": (Decimal("0"), Decimal("5000000"), 0),
    "favorites": (Decimal("0"), Decimal("5000000"), 0),
    "usage_experience_score": (Decimal("1"), Decimal("5"), 1),
    "noise_cancel_score": (Decimal("1"), Decimal("10"), 1),
    "battery_hours": (Decimal("2"), Decimal("80"), 1),
}


def parse_number(value: str) -> Decimal | None:
    text = (value or "").strip().lower().replace(",", "").replace("\uff0c", "")
    if not text or text in {"nan", "null", "none"}:
        return None
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?\s*/\s*5", text):
        text = text.split("/", 1)[0].strip()
    multiplier = Decimal("1000") if text.endswith("k") else Decimal("1")
    text = text[:-1] if text.endswith("k") else text
    text = re.sub(r"[^0-9.+-]", "", text)
    if not text or text in {"+", "-", "."}:
        return None
    try:
        return Decimal(text) * multiplier
    except InvalidOperation:
        return None


def parse_date(value: str) -> date | None:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y\u5e74%m\u6708%d\u65e5", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_brand(value: str) -> str:
    key = re.sub(r"\s+", " ", (value or "").strip()).lower()
    return BRAND_ALIASES.get(key, UNKNOWN_BRAND)


def format_number(value: Decimal, places: int) -> str:
    quant = Decimal("1").scaleb(-places)
    result = value.quantize(quant, rounding=ROUND_HALF_UP)
    return str(int(result)) if places == 0 else format(result, f".{places}f")


def normalize_row(source: dict[str, str], parsed_date: date, parsed_numbers: dict[str, Decimal | None], changes: list[str]) -> dict[str, str]:
    row = dict(source)
    old_brand = row.get("brand", ""); row["brand"] = normalize_brand(old_brand)
    if row["brand"] != old_brand: changes.append(f"brand alias normalized to {row['brand']}")
    row["product_name"] = row["product_name"].strip()
    row["category"] = "\u84dd\u7259\u964d\u566a\u8033\u673a"
    old_platform = row.get("platform", "")
    row["platform"] = PLATFORM_ALIASES.get(old_platform.strip().lower(), "\u5176\u4ed6\u5e73\u53f0")
    if row["platform"] != old_platform: changes.append(f"platform alias normalized to {row['platform']}")
    for field, (low, high, places) in NUMERIC.items():
        number = parsed_numbers[field]
        if number is None or not low <= number <= high:
            row[field] = ""
            if (source.get(field) or "").strip(): changes.append(f"{field} invalid/out of range -> blank")
        else:
            row[field] = format_number(number, places)
    row["publish_date"] = parsed_date.isoformat()
    if source.get("publish_date", "").strip() != row["publish_date"]:
        changes.append("publish_date normalized to YYYY-MM-DD")
    return {field: row.get(field, "") for field in FIELDS}


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str] = FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=root / "data" / "raw" / "raw_data.csv")
    parser.add_argument("--output", type=Path, default=root / "data" / "processed" / "clean_data.csv")
    args = parser.parse_args(); args.input = args.input.resolve(); args.output = args.output.resolve()
    if not args.input.exists(): raise SystemExit(f"Input not found: {args.input}")
    with args.input.open(encoding="utf-8-sig", newline="") as handle: source_rows = list(csv.DictReader(handle))

    seen: set[str] = set(); first_by_id: dict[str, dict[str, str]] = {}; clean_rows = []; log_rows = []
    drop_counts = {"duplicate": 0, "missing_product_name": 0, "missing_or_invalid_price": 0, "missing_or_invalid_date": 0, "unknown_brand": 0}
    for source in source_rows:
        record_id = source.get("record_id", "").strip()
        if not record_id:
            log_rows.append({"record_id": "", "action": "drop", "details": "missing record_id"}); continue
        if record_id in seen:
            drop_counts["duplicate"] += 1; log_rows.append({"record_id": record_id, "action": "drop duplicate", "details": "keep first record_id"}); continue
        seen.add(record_id); first_by_id[record_id] = source
        reason = ""
        if not source.get("product_name", "").strip(): reason = "missing_product_name"
        brand = normalize_brand(source.get("brand", ""))
        if not reason and brand == UNKNOWN_BRAND: reason = "unknown_brand"
        parsed_numbers = {field: parse_number(source.get(field, "")) for field in NUMERIC}
        price = parsed_numbers["price"]
        if not reason and (price is None or not NUMERIC["price"][0] <= price <= NUMERIC["price"][1]): reason = "missing_or_invalid_price"
        parsed_date = parse_date(source.get("publish_date", ""))
        if not reason and parsed_date is None: reason = "missing_or_invalid_date"
        if reason:
            drop_counts[reason] += 1; log_rows.append({"record_id": record_id, "action": "drop required field", "details": reason}); continue
        changes: list[str] = []; cleaned = normalize_row(source, parsed_date, parsed_numbers, changes)
        clean_rows.append(cleaned); log_rows.append({"record_id": record_id, "action": "keep and clean", "details": "; ".join(changes) or "no conversion"})

    if not clean_rows: raise SystemExit("No clean rows remain")
    docs = root / "docs"; reports = root / "reports"; docs.mkdir(exist_ok=True); reports.mkdir(exist_ok=True)
    write_csv(args.output, clean_rows)
    write_csv(docs / "cleaning_log.csv", log_rows, ["record_id", "action", "details"])

    rng = random.Random(20261027); audit_rows = []
    for cleaned in rng.sample(clean_rows, min(10, len(clean_rows))):
        raw = first_by_id[cleaned["record_id"]]
        raw_summary = {field: raw.get(field, "") for field in FIELDS}
        clean_summary = {field: cleaned.get(field, "") for field in FIELDS}
        audit_rows.append({"record_id": cleaned["record_id"], "raw_record_json": json.dumps(raw_summary, ensure_ascii=False), "clean_record_json": json.dumps(clean_summary, ensure_ascii=False), "record_id_match": "yes"})
    write_csv(docs / "sample_10.csv", audit_rows, ["record_id", "raw_record_json", "clean_record_json", "record_id_match"])

    stats = []
    for field in FIELDS:
        nonempty = sum(bool(row.get(field, "").strip()) for row in clean_rows)
        stats.append({"field": field, "row_count": len(clean_rows), "non_empty_count": nonempty, "missing_count": len(clean_rows) - nonempty, "completeness_rate": f"{nonempty / len(clean_rows):.4f}"})
    write_csv(reports / "quality_stats.csv", stats, ["field", "row_count", "non_empty_count", "missing_count", "completeness_rate"])

    raw_count = len(source_rows); duplicate_count = drop_counts["duplicate"]
    id_unique = len({row["record_id"] for row in clean_rows}) == len(clean_rows)
    prices_valid = all(Decimal("50") <= Decimal(row["price"]) <= Decimal("5000") for row in clean_rows)
    ratings_valid = all(not row["rating"] or Decimal("1") <= Decimal(row["rating"]) <= Decimal("5") for row in clean_rows)
    dates_valid = all(datetime.strptime(row["publish_date"], "%Y-%m-%d").date() for row in clean_rows)
    completeness_ok = all(float(row["completeness_rate"]) >= .90 for row in stats)
    with (docs / "cleaning_log.md").open("w", encoding="utf-8") as handle:
        handle.write("# Cleaning Log\n\nAll generated records are fictional. The source CSV was not modified.\n\n")
        handle.write(f"- Raw rows: {raw_count}\n- Duplicate record IDs removed: {duplicate_count}\n- Rows retained: {len(clean_rows)}\n")
        for key, count in drop_counts.items():
            if key != "duplicate": handle.write(f"- Dropped for {key}: {count}\n")
        handle.write("\nRules: de-duplicate by record_id keeping the first occurrence; drop records missing product name, a valid price, a valid date, or a recognized brand; normalize aliases and formats; blank invalid optional numeric values. See cleaning_log.csv for row-level decisions.\n")
    with (docs / "quality_report.md").open("w", encoding="utf-8") as handle:
        handle.write("# Quality Report\n\nThis report describes a synthetic, fictional dataset; completeness does not establish truth or market representativeness.\n\n")
        handle.write(f"- Raw rows: {raw_count}\n- Duplicate IDs removed: {duplicate_count}\n- Clean rows: {len(clean_rows)}\n- Unique record IDs: {id_unique}\n- Price range valid (50-5000): {prices_valid}\n- Rating range valid (1-5): {ratings_valid}\n- Dates ISO-valid: {dates_valid}\n- Every field completeness >= 90%: {completeness_ok}\n\n| Field | Non-empty | Completeness |\n|---|---:|---:|\n")
        for item in stats: handle.write(f"| {item['field']} | {item['non_empty_count']}/{item['row_count']} | {float(item['completeness_rate']):.1%} |\n")
        handle.write("\nTen deterministic random rows are in sample_10.csv. Match each record_id to the raw CSV and inspect the JSON pair against the rules in cleaning_log.md.\n")
    print(f"Cleaned {raw_count} -> {len(clean_rows)} rows; unique IDs={id_unique}; completeness>=90%={completeness_ok}")


if __name__ == "__main__":
    main()

"""Produce transparent, repeatable metrics from the canonical review CSV."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

REQUIRED = {"brand", "product", "rating", "review"}
ISSUES = {
    "price": ("price", "expensive", "cheap", "cost", "价格", "贵", "便宜", "性价比"),
    "taste": ("taste", "flavor", "delicious", "味道", "口感", "好喝"),
    "service": ("service", "staff", "support", "服务", "态度", "客服"),
    "waiting": ("wait", "queue", "delivery", "slow", "排队", "等待", "配送", "送达"),
    "packaging": ("package", "packaging", "包装", "破损", "漏"),
    "quantity": ("small", "amount", "portion", "size", "分量", "太少", "不够"),
    "freshness": ("fresh", "stale", "spoiled", "新鲜", "变质", "冰块"),
}


def parse_rating(raw: str, line: int) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"line {line}: rating is not numeric: {value!r}") from exc
    if not number.is_integer() or not 1 <= int(number) <= 5:
        raise ValueError(f"line {line}: rating must be an integer from 1 to 5: {value!r}")
    return int(number)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("CSV missing required columns: " + ", ".join(sorted(missing)))
        rows: list[dict[str, str]] = []
        for line, raw in enumerate(reader, start=2):
            rating = parse_rating(raw.get("rating", ""), line)
            rows.append({
                "brand": (raw.get("brand") or "").strip(),
                "product": (raw.get("product") or "").strip(),
                "rating": "" if rating is None else str(rating),
                "review": (raw.get("review") or "").strip(),
            })
        return rows


def issue_counts(rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if not row["rating"] or int(row["rating"]) > 3:
            continue
        text = row["review"].lower()
        for label, keywords in ISSUES.items():
            if any(keyword.lower() in text for keyword in keywords):
                counts[label] += 1
    return counts


def summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    ratings = [int(row["rating"]) for row in rows if row["rating"]]
    brands: dict[str, dict[str, Any]] = {}
    for brand in sorted({row["brand"] or "unknown" for row in rows}):
        subset = [row for row in rows if (row["brand"] or "unknown") == brand]
        sub_ratings = [int(row["rating"]) for row in subset if row["rating"]]
        brands[brand] = {
            "total": len(subset),
            "rated": len(sub_ratings),
            "missing_ratings": len(subset) - len(sub_ratings),
            "average": round(mean(sub_ratings), 2) if sub_ratings else None,
            "positive_rate": round(sum(r >= 4 for r in sub_ratings) / len(sub_ratings) * 100, 1) if sub_ratings else 0.0,
            "problem_rate": round(sum(r <= 2 for r in sub_ratings) / len(sub_ratings) * 100, 1) if sub_ratings else 0.0,
        }
    return {
        "total": len(rows),
        "rated": len(ratings),
        "missing_ratings": len(rows) - len(ratings),
        "average": round(mean(ratings), 2) if ratings else None,
        "positive_rate": round(sum(r >= 4 for r in ratings) / len(ratings) * 100, 1) if ratings else 0.0,
        "problem_rate": round(sum(r <= 2 for r in ratings) / len(ratings) * 100, 1) if ratings else 0.0,
        "issue_counts": dict(issue_counts(rows).most_common()),
        "brands": brands,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze canonical consumer review CSV")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(read_rows(args.input))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

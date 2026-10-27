#!/usr/bin/env python3
"""Generate reproducible, explicitly fictional Bluetooth ANC competition data."""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261027
FIELDS = [
    "record_id", "product_name", "brand", "category", "platform", "price",
    "rating", "review_count", "publish_date", "likes", "favorites",
    "usage_experience_score", "noise_cancel_score", "battery_hours",
]
CATEGORY = "\u84dd\u7259\u964d\u566a\u8033\u673a"
BRANDS = [
    ("NovaPulse(\u65b0\u8109)", ["NovaPulse(\u65b0\u8109)", "NOVAPULSE", "\u65b0\u8109", "N0va Pulse"], ["NP Air 2", "NP Move", "NP Lite ANC", "NP Studio"], 199, 599, 4.35),
    ("QuietNest(\u9759\u5de2)", ["QuietNest(\u9759\u5de2)", "QUIET NEST", "\u9759\u5de2", "Q.Nest"], ["QN Silence Pro", "QN Cloud", "QN Office 3", "QN Mini ANC"], 699, 1599, 4.55),
    ("AirMorrow(\u98ce\u5e8f)", ["AirMorrow(\u98ce\u5e8f)", "AIR MORROW", "\u98ce\u5e8f", "AirMoro"], ["AM Run ANC", "AM Feather", "AM Trail", "AM Sport 2"], 249, 799, 4.25),
    ("BassForge(\u4f4e\u9891\u5de5\u574a)", ["BassForge(\u4f4e\u9891\u5de5\u574a)", "BASS FORGE", "\u4f4e\u9891\u5de5\u574a", "BassFroge"], ["BF Pulse X", "BF Beat ANC", "BF Stage", "BF Core"], 329, 999, 4.15),
]
PLATFORMS = [("\u542c\u6f6e", ["\u542c\u6f6e", "\u542c\u6f6e\u793e\u533a", "TideTalk"]), ("\u58f0\u6d6a", ["\u58f0\u6d6a", "\u58f0\u6d6a\u5e02\u96c6", "WaveMall"]), ("\u8f7b\u96c6", ["\u8f7b\u96c6", "\u8f7b\u96c6\u5e73\u53f0", "LiteHub"])]


def price_text(value: int, rng: random.Random) -> str:
    return rng.choice([f"{value}\u5143", f"\uffe5{value}", f"{value:.2f}", f"RMB {value}", f"{value:,}.00"])


def count_text(value: int, rng: random.Random) -> str:
    if value >= 1000 and rng.random() < 0.16:
        return f"{value / 1000:.1f}k"
    return rng.choice([str(value), f"{value:,}", f"{value:,}.00"])


def date_text(value: date, rng: random.Random) -> str:
    return rng.choice([value.isoformat(), value.strftime("%Y/%m/%d"), f"{value.year}\u5e74{value.month}\u6708{value.day}\u65e5", value.strftime("%d-%m-%Y")])


def generate_rows() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    rows: list[dict[str, str]] = []
    start = date(2025, 1, 1)
    for brand_index, (brand, aliases, models, low, high, rating_base) in enumerate(BRANDS):
        for local_index in range(100):
            number = brand_index * 100 + local_index + 1
            _, platform_aliases = rng.choice(PLATFORMS)
            published = start + timedelta(days=rng.randrange(665))
            rating = max(3.2, min(4.9, round(rng.uniform(rating_base - 0.45, rating_base + 0.35), 1)))
            reviews = rng.randint(15, 18000)
            row = {
                "record_id": f"BT-{number:04d}",
                "product_name": f"{models[local_index % len(models)]} \u964d\u566a\u8033\u673a",
                "brand": rng.choice(aliases), "category": CATEGORY,
                "platform": rng.choice(platform_aliases), "price": price_text(rng.randint(low, high), rng),
                "rating": rng.choice([f"{rating:.1f}", f"{rating:.1f}\u5206", f"{rating:.1f}/5"]),
                "review_count": count_text(reviews, rng), "publish_date": date_text(published, rng),
                "likes": count_text(rng.randint(0, max(20, reviews * 8)), rng),
                "favorites": count_text(rng.randint(0, max(20, reviews * 5)), rng),
                "usage_experience_score": f"{rng.uniform(3.4, 4.9):.1f}",
                "noise_cancel_score": f"{rng.uniform(5.5, 9.8):.1f}",
                "battery_hours": f"{rng.randint(6, 48)}\u5c0f\u65f6",
            }
            for field, probability in [("product_name", .006), ("price", .006), ("publish_date", .006), ("rating", .015), ("review_count", .025), ("likes", .02), ("favorites", .02)]:
                if rng.random() < probability:
                    row[field] = ""
            rows.append(row)

    # Deliberate defects in the first 50 rows for the required sample review.
    rows[2]["price"] = "\uffe5-19"; rows[5]["price"] = "99999"; rows[6]["rating"] = "70\u5206"
    rows[10]["publish_date"] = "2026\u5e743\u67088\u65e5"; rows[12]["brand"] = "N0va Pulse"; rows[14]["review_count"] = "1,234"
    rows[16]["likes"] = "1.2k"; rows[18]["favorites"] = "-12"; rows[20]["battery_hours"] = "99\u5c0f\u65f6"
    rows[22]["noise_cancel_score"] = "70"; rows[24]["price"] = ""; rows[26]["product_name"] = ""
    rows[28]["publish_date"] = ""; rows[30]["review_count"] = "\u4e00\u4e8c\u4e09"; rows[36]["rating"] = "5.8"
    rows[38]["usage_experience_score"] = "0"; rows[40]["brand"] = "NOVA-PULSE"; rows[42]["review_count"] = "-2"
    rows[44]["likes"] = "4,321"; rows[32]["price"] = "\uffe5299"; rows[34]["price"] = "RMB 399"

    duplicates = [{**rows[i]} for i in [2, 6, 12, 14, 40, 129, 259, 389]]
    duplicates[2]["brand"] = "NOVAPULSE"; duplicates[3]["review_count"] = "1234"
    return rows + duplicates


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    default_output = root / "data" / "raw" / "raw_data.csv"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args(); output = args.output.resolve()
    sample = root / "docs" / "sample_50.csv" if output == default_output.resolve() else output.with_name(f"{output.stem}_sample50.csv")
    if output.exists() or sample.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {output if output.exists() else sample}")
    rows = generate_rows(); write_csv(output, rows); write_csv(sample, rows[:50])
    print(f"Wrote {len(rows)} raw fictional rows to {output}")


if __name__ == "__main__":
    main()

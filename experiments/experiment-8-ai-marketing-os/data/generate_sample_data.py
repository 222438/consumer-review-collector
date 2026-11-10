"""Create deterministic, anonymous classroom fixtures for Experiment 8."""
from csv import DictWriter
from pathlib import Path

HERE = Path(__file__).resolve().parent

reviews = []
templates = [
    ("delivery", "高峰期排队太久，但味道还可以"),
    ("taste", "口味顺滑，第二天还会再买"),
    ("price", "价格有点贵，希望有学生优惠"),
    ("packaging", "包装方便，杯盖不容易漏"),
    ("service", "店员服务很快，态度也很好"),
]
for i in range(1, 121):
    topic, text = templates[(i * 7) % len(templates)]
    rating = 2 if i % 9 == 0 else 3 if i % 7 == 0 else 5 if i % 4 == 0 else 4
    reviews.append({"review_id": f"CC-R{i:04d}", "brand": "Campus Coffee", "product": ["拿铁", "美式", "燕麦拿铁"][i % 3], "rating": rating, "review": text, "analysis_period": f"2026-{(i % 6) + 1:02d}"})
with (HERE / "consumer_reviews.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = DictWriter(handle, fieldnames=list(reviews[0]))
    writer.writeheader(); writer.writerows(reviews)

rows = []
for i in range(1, 61):
    group = "A" if i <= 30 else "B"
    clicked = 1 if (i % 3 != 0 if group == "A" else i % 4 != 0) else 0
    purchased = 1 if (clicked and i % (5 if group == "A" else 4) == 0) else 0
    feedback = ("等待时间太久，希望更快" if i % 5 == 0 else "口味清楚，愿意尝试" if i % 2 == 0 else "价格可以接受")
    rows.append({"participant_id": f"anon-{i:03d}", "group": group, "exposed": 1, "clicked": clicked, "purchased": purchased, "open_feedback": feedback, "channel": "campus_group" if i % 2 else "qr_card"})
with (HERE / "ab_test_anonymous.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print(f"wrote {len(reviews)} reviews and {len(rows)} anonymous experiment rows")

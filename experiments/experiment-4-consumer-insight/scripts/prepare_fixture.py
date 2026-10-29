"""Materialise the review fixture and its auditable semantic coding.

The source fixture is intentionally small and synthetic. The coding rules are
kept here so a student can regenerate the JSON without changing the statistic
engine.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "marketing-lab" / "data" / "reviews.csv"
TARGET = Path(__file__).resolve().parents[1]


def add_evidence(items: list[dict], topic: str, polarity: str, span: str) -> None:
    items.append({"topic": topic, "polarity": polarity, "span": span})


def encode(review: str) -> dict:
    evidence: list[dict] = []
    negative_topics: list[str] = []
    positive = False

    def negative(topic: str, span: str) -> None:
        if topic not in negative_topics:
            negative_topics.append(topic)
        add_evidence(evidence, topic, "negative", span)

    def positive_evidence(topic: str, span: str) -> None:
        nonlocal positive
        positive = True
        add_evidence(evidence, topic, "positive", span)

    if "价格" in review and "贵" in review:
        negative("price", "价格有点贵" if "价格有点贵" in review else "价格也有点贵")
    elif "价格可以接受" in review:
        positive_evidence("price", "价格可以接受")

    if "太苦" in review:
        negative("taste", "太苦了")
    if "太淡" in review:
        negative("taste", "味道太淡")
    if "味道一般" in review:
        negative("taste", "味道一般")
    if "口感中规中矩" in review:
        negative("taste", "口感中规中矩")
    for phrase in ("味道很棒", "新鲜好喝", "味道不错", "口感不错"):
        if phrase in review:
            positive_evidence("taste", phrase)

    if "等待" in review or "排队" in review:
        span = "排队太久" if "排队" in review else "等待时间较长"
        negative("delivery", span)
    if "配送速度很快" in review:
        positive_evidence("delivery", "配送速度很快")

    if "包装漏" in review:
        negative("packaging", "包装漏了")
    elif "包装" in review and "希望" in review:
        negative("packaging", "希望包装再精致一点")
    elif "包装结实" in review:
        positive_evidence("packaging", "包装结实")
    elif "包装看起来不错" in review:
        positive_evidence("packaging", "包装看起来不错")

    if "分量太少" in review:
        negative("portion", "分量太少")
    elif "分量也比较少" in review:
        negative("portion", "分量也比较少")

    if "服务态度很差" in review:
        negative("service", "服务态度很差")
    elif "服务态度需要改进" in review:
        negative("service", "服务态度需要改进")
    if "服务也很快" in review:
        positive_evidence("service", "服务也很快")

    if negative_topics and positive:
        sentiment = "mixed"
    elif negative_topics:
        sentiment = "negative"
    elif positive:
        sentiment = "positive"
    else:
        sentiment = "neutral"
    return {
        "negative_topics": negative_topics,
        "sentiment": sentiment,
        "evidence": evidence,
        "confidence": "high" if evidence else "medium",
        "coder": "semantic-coding-v0.4",
    }


def main() -> None:
    source = pd.read_csv(SOURCE, dtype={"brand": "string", "product": "string", "review": "string"})
    rows = []
    encodings = []
    for index, row in source.reset_index(drop=True).iterrows():
        review_id = f"ML-R{index + 1:04d}"
        # The source fixture has no dates. Cycle through four labelled analysis
        # batches so every brand can be compared in the same periods.
        period_month = 1 + (index % 4)
        analysis_date = date(2026, period_month, 1 + ((index // 4) % 28))
        rows.append(
            {
                "review_id": review_id,
                "source_row": index + 2,
                "source_file": "marketing-lab/data/reviews.csv",
                "brand": row["brand"],
                "product": row["product"],
                "rating": row["rating"],
                "review": row["review"],
                "analysis_date": analysis_date.isoformat(),
                "analysis_period": f"2026-{period_month:02d}",
            }
        )
        encoded = encode(str(row["review"]))
        encodings.append({"review_id": review_id, **encoded})
    data_dir = TARGET / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(data_dir / "clean_data.csv", index=False, encoding="utf-8-sig")
    (data_dir / "encoded_reviews.json").write_text(
        json.dumps(encodings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(rows)} rows and {len(encodings)} encodings")


if __name__ == "__main__":
    main()

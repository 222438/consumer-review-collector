"""Reproducible statistics for experiment 4.

Semantic labels are supplied in JSON. This module never infers labels from the
review text; it validates the labels and performs deterministic aggregation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


TOPICS = ("price", "taste", "delivery", "packaging", "portion", "service")


def load_inputs(input_path: str | Path, encoding_path: str | Path) -> pd.DataFrame:
    reviews = pd.read_csv(input_path, dtype={"review_id": "string", "brand": "string"})
    required = {"review_id", "brand", "product", "rating", "review", "analysis_period"}
    missing = required - set(reviews.columns)
    if missing:
        raise ValueError(f"Input is missing columns: {sorted(missing)}")
    with open(encoding_path, "r", encoding="utf-8") as handle:
        encodings = json.load(handle)
    if not isinstance(encodings, list):
        raise ValueError("Encoding JSON must be a list")
    encoded = pd.DataFrame(encodings)
    required_encoded = {"review_id", "sentiment", "negative_topics", "evidence"}
    missing_encoded = required_encoded - set(encoded.columns)
    if missing_encoded:
        raise ValueError(f"Encoding JSON is missing columns: {sorted(missing_encoded)}")
    if reviews["review_id"].duplicated().any():
        raise ValueError("Input review_id values must be unique")
    if encoded["review_id"].duplicated().any():
        raise ValueError("Encoding review_id values must be unique")
    if set(reviews.review_id) != set(encoded.review_id):
        raise ValueError("Input and encoding IDs do not match exactly")
    encoded = encoded.copy()
    encoded["negative_topics"] = encoded["negative_topics"].apply(
        lambda value: value if isinstance(value, list) else []
    )
    encoded["evidence"] = encoded["evidence"].apply(
        lambda value: value if isinstance(value, list) else []
    )
    merged = reviews.merge(encoded, on="review_id", how="inner", validate="one_to_one")
    for topic in TOPICS:
        merged[f"has_{topic}_pain"] = merged["negative_topics"].apply(
            lambda topics, current=topic: current in topics
        )
    return merged


def _share(count: int, denominator: int) -> float:
    return round(count / denominator * 100, 2) if denominator else 0.0


def pain_point_ranking(df: pd.DataFrame) -> pd.DataFrame:
    denominator = len(df)
    rows = []
    for rank, topic in enumerate(
        sorted(TOPICS, key=lambda item: (-int(df[f"has_{item}_pain"].sum()), item)), start=1
    ):
        count = int(df[f"has_{topic}_pain"].sum())
        rows.append(
            {
                "rank": rank,
                "topic": topic,
                "count": count,
                "denominator": denominator,
                "sample_size": denominator,
                "share_pct": _share(count, denominator),
            }
        )
    return pd.DataFrame(rows)


def sentiment_distribution(df: pd.DataFrame) -> pd.DataFrame:
    denominator = len(df)
    counts = df["sentiment"].value_counts().to_dict()
    ordered = ["positive", "mixed", "neutral", "negative"]
    return pd.DataFrame(
        [
            {
                "sentiment": sentiment,
                "count": int(counts.get(sentiment, 0)),
                "denominator": denominator,
                "sample_size": denominator,
                "share_pct": _share(int(counts.get(sentiment, 0)), denominator),
            }
            for sentiment in ordered
        ]
    )


def brand_time_comparison(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["brand", "analysis_period"], dropna=False)
        .agg(
            sample_size=("review_id", "size"),
            avg_rating=("rating", "mean"),
            negative_count=("sentiment", lambda values: int((values == "negative").sum())),
        )
        .reset_index()
    )
    grouped["negative_share_pct"] = grouped.apply(
        lambda row: _share(int(row["negative_count"]), int(row["sample_size"])), axis=1
    )
    grouped["avg_rating"] = grouped["avg_rating"].round(2)
    return grouped.sort_values(["analysis_period", "brand"]).reset_index(drop=True)


def evidence_index(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        for item in row["evidence"]:
            rows.append(
                {
                    "review_id": row["review_id"],
                    "brand": row["brand"],
                    "product": row["product"],
                    "topic": item.get("topic", ""),
                    "polarity": item.get("polarity", ""),
                    "evidence_span": item.get("span", ""),
                    "review": row["review"],
                }
            )
    return pd.DataFrame(rows)


def run(input_path: str | Path, encoding_path: str | Path, output_dir: str | Path) -> dict[str, pd.DataFrame]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    df = load_inputs(input_path, encoding_path)
    tables = {
        "pain_point_ranking": pain_point_ranking(df),
        "sentiment_distribution": sentiment_distribution(df),
        "brand_time_comparison": brand_time_comparison(df),
        "evidence_index": evidence_index(df),
    }
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False, encoding="utf-8-sig")
    summary = {
        "input_rows": int(len(df)),
        "encoded_rows": int(len(df)),
        "review_id_min": str(df.review_id.min()),
        "review_id_max": str(df.review_id.max()),
        "pain_points": tables["pain_point_ranking"].to_dict(orient="records"),
        "sentiment": tables["sentiment_distribution"].to_dict(orient="records"),
        "note": "Percentages use the full merged sample as denominator; analysis_period is a deterministic batch field.",
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--encoding", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run(args.input, args.encoding, args.output_dir)


if __name__ == "__main__":
    main()

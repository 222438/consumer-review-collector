"""Reproducible competitive-intelligence analysis for experiment 5 (v0.5).

The input is the cleaned, fictional Bluetooth ANC product table from experiment 3.
Experiment 4's compact sentiment vocabulary (``positive``, ``mixed``,
``negative``) is reused as a transparent rating label.  No review text is
invented: labels are derived from the structured rating field and every
conclusion keeps a record id and source field for tracing.

The threat index follows the classroom brief exactly::

    threat = consumer_overlap * 30%
           + product_overlap * 25%
           + price_overlap * 20%
           + brand_popularity * 25%

All four dimensions are normalised to 0--100.  ``NovaPulse(新脉)`` is the
default focal brand; if it is absent, the brand with the largest engagement is
used and recorded in the output metadata.
"""

from __future__ import annotations

import argparse
import html
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


VERSION = "v0.5"
FOCAL_BRAND = "NovaPulse(新脉)"
WEIGHTS: dict[str, float] = {
    "consumer_overlap": 0.30,
    "product_overlap": 0.25,
    "price_overlap": 0.20,
    "brand_popularity": 0.25,
}
DIMENSION_LABELS = {
    "consumer_overlap": "消费者重合度",
    "product_overlap": "产品重合度",
    "price_overlap": "价格重合度",
    "brand_popularity": "品牌热度",
}
NUMERIC_FIELDS = [
    "price",
    "rating",
    "review_count",
    "likes",
    "favorites",
    "usage_experience_score",
    "noise_cancel_score",
    "battery_hours",
]
REQUIRED_FIELDS = {"record_id", "product_name", "brand", "price"}
OPTIONAL_NUMERIC_FIELDS = [field for field in NUMERIC_FIELDS if field != "price"]


def indicator_dictionary() -> pd.DataFrame:
    """Return the auditable indicator dictionary and formula metadata."""

    rows = [
        {
            "indicator": "consumer_overlap",
            "name_zh": "消费者重合度",
            "unit": "%",
            "weight": WEIGHTS["consumer_overlap"],
            "direction": "higher_threat",
            "source_fields": "review_count,likes,favorites",
            "formula": "100 * min(1, rival_engagement / focal_engagement)",
            "missing_handling": "numeric field median by brand, then market median",
        },
        {
            "indicator": "product_overlap",
            "name_zh": "产品重合度",
            "unit": "%",
            "weight": WEIGHTS["product_overlap"],
            "direction": "higher_threat",
            "source_fields": "price,usage_experience_score,noise_cancel_score,battery_hours",
            "formula": "mean of nearest focal-product similarity across price and performance",
            "missing_handling": "brand/market median imputation; similarity uses available dimensions",
        },
        {
            "indicator": "price_overlap",
            "name_zh": "价格重合度",
            "unit": "%",
            "weight": WEIGHTS["price_overlap"],
            "direction": "higher_threat",
            "source_fields": "price",
            "formula": "mean(exp(-abs(rival_price - nearest_focal_price) / focal_median_price)) * 100",
            "missing_handling": "price is required; invalid rows are excluded",
        },
        {
            "indicator": "brand_popularity",
            "name_zh": "品牌热度",
            "unit": "%",
            "weight": WEIGHTS["brand_popularity"],
            "direction": "higher_threat",
            "source_fields": "review_count,likes,favorites",
            "formula": "100 * brand_engagement / maximum_brand_engagement",
            "missing_handling": "missing interaction fields contribute zero after imputation",
        },
    ]
    result = pd.DataFrame(rows)
    result["weight_pct"] = (result["weight"] * 100).round(2)
    return result[
        [
            "indicator",
            "name_zh",
            "unit",
            "weight",
            "weight_pct",
            "direction",
            "source_fields",
            "formula",
            "missing_handling",
        ]
    ]


def _safe_number(value: Any) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = float(str(value).replace(",", "").replace("k", "000"))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def load_products(input_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load products, validate keys, impute optional metrics, and return quality log.

    ``price`` and the four identity fields are required.  Other numeric fields
    are allowed to be missing because experiment 3 intentionally contains
    incomplete interaction and score fields.  Imputation is deterministic and
    is recorded in ``data_quality.csv``.
    """

    path = Path(input_path)
    frame = pd.read_csv(path, dtype={"record_id": "string", "brand": "string"})
    missing = REQUIRED_FIELDS - set(frame.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")
    frame = frame.copy()
    frame["record_id"] = frame["record_id"].astype("string").str.strip()
    if frame["record_id"].isna().any() or (frame["record_id"] == "").any():
        raise ValueError("record_id cannot be blank")
    if frame["record_id"].duplicated().any():
        raise ValueError("record_id values must be unique")
    for field in NUMERIC_FIELDS:
        if field in frame.columns:
            frame[field] = frame[field].map(_safe_number)
        else:
            frame[field] = float("nan")
    before = len(frame)
    frame = frame[frame["brand"].notna() & (frame["brand"].astype(str).str.strip() != "")]
    frame = frame[frame["product_name"].notna() & (frame["product_name"].astype(str).str.strip() != "")]
    frame = frame[frame["price"].notna() & (frame["price"] > 0)]
    frame = frame.reset_index(drop=True)
    if frame.empty:
        raise ValueError("No usable product rows remain after validation")

    quality_rows: list[dict[str, Any]] = []
    for field in NUMERIC_FIELDS:
        missing_before = int(frame[field].isna().sum())
        if missing_before:
            brand_medians = frame.groupby("brand")[field].transform("median")
            market_median = frame[field].median()
            fill_values = brand_medians.fillna(market_median)
            frame[field] = frame[field].fillna(fill_values)
        quality_rows.append(
            {
                "field": field,
                "missing_before": missing_before,
                "missing_after": int(frame[field].isna().sum()),
                "imputation": "brand median -> market median" if missing_before else "none",
                "source_file": str(path),
            }
        )
    frame["engagement"] = (
        frame["review_count"].fillna(0)
        + frame["likes"].fillna(0)
        + frame["favorites"].fillna(0)
    )
    frame["rating"] = frame["rating"].clip(1, 5)
    frame["sentiment"] = frame["rating"].map(_rating_label)
    frame["label_source"] = "experiment-4 vocabulary; deterministic rating threshold"
    frame["source_file"] = str(path)
    quality_rows.append(
        {
            "field": "__rows__",
            "missing_before": before - len(frame),
            "missing_after": 0,
            "imputation": "rows without identity/positive price excluded",
            "source_file": str(path),
        }
    )
    quality = pd.DataFrame(quality_rows)
    return frame, quality


def _rating_label(value: float) -> str:
    if pd.isna(value):
        return "neutral"
    if value >= 4.3:
        return "positive"
    if value >= 3.7:
        return "mixed"
    return "negative"


def _mean_or_zero(values: Iterable[float]) -> float:
    series = pd.Series(list(values), dtype="float64").dropna()
    return float(series.mean()) if not series.empty else 0.0


def _similarity(left: pd.Series, right: pd.Series, fields: list[str]) -> float:
    """Return 0--1 similarity using available, range-normalised dimensions."""

    differences: list[float] = []
    scales = {"price": 500.0, "usage_experience_score": 4.0, "noise_cancel_score": 9.0, "battery_hours": 60.0}
    for field in fields:
        a, b = _safe_number(left.get(field)), _safe_number(right.get(field))
        if a is None or b is None:
            continue
        scale = scales.get(field, 1.0)
        differences.append(min(abs(a - b) / scale, 1.0))
    return max(0.0, 1.0 - _mean_or_zero(differences)) if differences else 0.0


def _focal_brand(frame: pd.DataFrame, requested: str = FOCAL_BRAND) -> tuple[str, str]:
    if requested in set(frame["brand"].astype(str)):
        return requested, "requested focal brand is present"
    engagement = frame.groupby("brand")["engagement"].sum().sort_values(ascending=False)
    selected = str(engagement.index[0])
    return selected, f"requested focal brand {requested!r} absent; selected highest-engagement brand"


def brand_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate product structure, pricing, ratings, and heat by brand."""

    grouped = (
        frame.groupby("brand", dropna=False)
        .agg(
            product_rows=("record_id", "size"),
            product_count=("product_name", "nunique"),
            avg_price=("price", "mean"),
            median_price=("price", "median"),
            min_price=("price", "min"),
            max_price=("price", "max"),
            avg_rating=("rating", "mean"),
            review_count=("review_count", "sum"),
            likes=("likes", "sum"),
            favorites=("favorites", "sum"),
            avg_usage_experience=("usage_experience_score", "mean"),
            avg_noise_cancel=("noise_cancel_score", "mean"),
            avg_battery_hours=("battery_hours", "mean"),
        )
        .reset_index()
    )
    grouped["engagement"] = grouped["review_count"] + grouped["likes"] + grouped["favorites"]
    max_engagement = max(float(grouped["engagement"].max()), 1.0)
    grouped["brand_popularity"] = (grouped["engagement"] / max_engagement * 100).round(2)
    grouped["product_share_pct"] = (grouped["product_rows"] / len(frame) * 100).round(2)
    grouped["avg_price"] = grouped["avg_price"].round(2)
    grouped["median_price"] = grouped["median_price"].round(2)
    grouped["avg_rating"] = grouped["avg_rating"].round(2)
    grouped["avg_usage_experience"] = grouped["avg_usage_experience"].round(2)
    grouped["avg_noise_cancel"] = grouped["avg_noise_cancel"].round(2)
    grouped["avg_battery_hours"] = grouped["avg_battery_hours"].round(2)
    grouped["sentiment"] = grouped["avg_rating"].map(_rating_label)
    return grouped.sort_values("brand_popularity", ascending=False).reset_index(drop=True)


def threat_ranking(frame: pd.DataFrame, focal_brand: str = FOCAL_BRAND) -> tuple[pd.DataFrame, str, str]:
    """Compute the four weighted threat dimensions for each non-focal brand."""

    focal, focal_reason = _focal_brand(frame, focal_brand)
    focal_rows = frame[frame["brand"] == focal]
    focal_engagement = max(float(focal_rows["engagement"].sum()), 1.0)
    focal_median_price = max(float(focal_rows["price"].median()), 1.0)
    rows: list[dict[str, Any]] = []
    all_engagement = frame.groupby("brand")["engagement"].sum()
    max_market_engagement = max(float(all_engagement.max()), 1.0)
    similarity_fields = ["price", "usage_experience_score", "noise_cancel_score", "battery_hours"]
    for brand, rival_rows in frame.groupby("brand", sort=True):
        if brand == focal:
            continue
        product_scores: list[float] = []
        price_scores: list[float] = []
        for _, rival in rival_rows.iterrows():
            similarities = [_similarity(rival, target, similarity_fields) for _, target in focal_rows.iterrows()]
            price_diffs = [
                math.exp(-abs(float(rival["price"]) - float(target["price"])) / focal_median_price)
                for _, target in focal_rows.iterrows()
            ]
            product_scores.append(max(similarities) if similarities else 0.0)
            price_scores.append(max(price_diffs) if price_diffs else 0.0)
        rival_engagement = float(rival_rows["engagement"].sum())
        consumer = min(100.0, rival_engagement / focal_engagement * 100)
        product = _mean_or_zero(product_scores) * 100
        price = _mean_or_zero(price_scores) * 100
        popularity = rival_engagement / max_market_engagement * 100
        weighted = (
            consumer * WEIGHTS["consumer_overlap"]
            + product * WEIGHTS["product_overlap"]
            + price * WEIGHTS["price_overlap"]
            + popularity * WEIGHTS["brand_popularity"]
        )
        rows.append(
            {
                "brand": brand,
                "focal_brand": focal,
                "consumer_overlap": round(consumer, 2),
                "product_overlap": round(product, 2),
                "price_overlap": round(price, 2),
                "brand_popularity": round(popularity, 2),
                "threat_index": round(weighted, 2),
                "evidence_records": int(len(rival_rows)),
                "weight_sum": round(sum(WEIGHTS.values()), 4),
            }
        )
    result = pd.DataFrame(rows).sort_values(["threat_index", "brand"], ascending=[False, True]).reset_index(drop=True)
    result.insert(0, "rank", range(1, len(result) + 1))
    return result, focal, focal_reason


def price_bands(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise portfolio coverage in transparent, fixed price bands."""

    bins = [0, 299, 499, 799, 1199, float("inf")]
    labels = ["≤299", "300–499", "500–799", "800–1199", "≥1200"]
    working = frame.copy()
    working["price_band"] = pd.cut(working["price"], bins=bins, labels=labels, include_lowest=True)
    rows: list[dict[str, Any]] = []
    for (brand, band), group in working.groupby(["brand", "price_band"], observed=False):
        rows.append(
            {
                "brand": brand,
                "price_band": str(band),
                "product_rows": int(len(group)),
                "brand_share_pct": round(len(group) / max(int((working["brand"] == brand).sum()), 1) * 100, 2),
                "avg_price": round(float(group["price"].mean()), 2) if len(group) else 0.0,
                "avg_rating": round(float(group["rating"].mean()), 2) if len(group) else 0.0,
                "avg_noise_cancel": round(float(group["noise_cancel_score"].mean()), 2) if len(group) else 0.0,
                "avg_battery_hours": round(float(group["battery_hours"].mean()), 2) if len(group) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def product_structure(frame: pd.DataFrame) -> pd.DataFrame:
    """Return one traceable row per product model."""

    result = frame[
        [
            "record_id",
            "brand",
            "product_name",
            "price",
            "rating",
            "review_count",
            "usage_experience_score",
            "noise_cancel_score",
            "battery_hours",
            "sentiment",
            "source_file",
        ]
    ].copy()
    bins = [0, 299, 499, 799, 1199, float("inf")]
    labels = ["≤299", "300–499", "500–799", "800–1199", "≥1200"]
    result["price_band"] = pd.cut(result["price"], bins=bins, labels=labels, include_lowest=True).astype(str)
    result["evidence_field"] = "price,rating,review_count,usage_experience_score,noise_cancel_score,battery_hours"
    return result.sort_values(["brand", "price", "product_name"]).reset_index(drop=True)


def market_gaps(frame: pd.DataFrame) -> pd.DataFrame:
    """Find low-coverage price/performance cells as candidate opportunity gaps."""

    working = frame.copy()
    working["price_band"] = pd.cut(
        working["price"],
        bins=[0, 299, 499, 799, 1199, float("inf")],
        labels=["≤299", "300–499", "500–799", "800–1199", "≥1200"],
        include_lowest=True,
    ).astype(str)
    working["anc_band"] = pd.cut(
        working["noise_cancel_score"],
        bins=[-float("inf"), 7, 8, float("inf")],
        labels=["低于7", "7–<8", "≥8"],
        include_lowest=True,
    ).astype(str)
    working["battery_band"] = pd.cut(
        working["battery_hours"],
        bins=[-float("inf"), 20, 30, float("inf")],
        labels=["<20h", "20–<30h", "≥30h"],
        include_lowest=True,
    ).astype(str)
    counts = (
        working.groupby(["price_band", "anc_band", "battery_band"], observed=False)
        .agg(product_rows=("record_id", "size"), brand_count=("brand", "nunique"), avg_rating=("rating", "mean"))
        .reset_index()
    )
    rows: list[dict[str, Any]] = []
    for price_band, anc_band, battery_band in itertools.product(
        ["≤299", "300–499", "500–799", "800–1199", "≥1200"],
        ["低于7", "7–<8", "≥8"],
        ["<20h", "20–<30h", "≥30h"],
    ):
        match = counts[
            (counts["price_band"].astype(str) == price_band)
            & (counts["anc_band"].astype(str) == anc_band)
            & (counts["battery_band"].astype(str) == battery_band)
        ]
        count = int(match["product_rows"].iloc[0]) if not match.empty else 0
        brand_count = int(match["brand_count"].iloc[0]) if not match.empty else 0
        avg_rating = float(match["avg_rating"].iloc[0]) if not match.empty else 0.0
        rows.append(
            {
                "price_band": price_band,
                "anc_band": anc_band,
                "battery_band": battery_band,
                "product_rows": count,
                "brand_count": brand_count,
                "avg_rating": round(avg_rating, 2),
                "gap_flag": "candidate_gap" if count <= 1 else "covered",
                "gap_note": "样本覆盖≤1条；需用真实需求数据验证" if count <= 1 else "样本已有多条记录",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["product_rows", "price_band", "anc_band", "battery_band"]
    ).reset_index(drop=True)


def evaluation_selling_points(brand_table: pd.DataFrame) -> pd.DataFrame:
    """Translate structured averages into reviewable evaluation/selling-point rows."""

    metric_labels = {
        "avg_rating": ("用户评价", "rating"),
        "avg_usage_experience": ("佩戴体验", "usage_experience_score"),
        "avg_noise_cancel": ("降噪能力", "noise_cancel_score"),
        "avg_battery_hours": ("续航", "battery_hours"),
    }
    rows: list[dict[str, Any]] = []
    for _, brand in brand_table.iterrows():
        scored = []
        for field, (label, source) in metric_labels.items():
            value = float(brand[field])
            market_min = float(brand_table[field].min())
            market_max = float(brand_table[field].max())
            percentile = 100.0 if market_max == market_min else (value - market_min) / (market_max - market_min) * 100
            scored.append((percentile, label, source, value))
        _, label, source, value = max(scored, key=lambda item: (item[0], item[1]))
        rows.append(
            {
                "brand": brand["brand"],
                "evaluation_label": brand["sentiment"],
                "selling_point": label,
                "selling_point_value": round(value, 2),
                "source_field": source,
                "evidence_note": "品牌均值；卖点仅表示样本中的相对优势",
            }
        )
    return pd.DataFrame(rows)


def label_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the experiment-4-compatible sentiment labels by brand."""

    counts = frame.groupby(["brand", "sentiment"], dropna=False).size().rename("count").reset_index()
    totals = frame.groupby("brand").size().rename("denominator").reset_index()
    result = counts.merge(totals, on="brand", how="left")
    result["share_pct"] = (result["count"] / result["denominator"] * 100).round(2)
    result["label_source"] = "experiment-4 vocabulary; rating threshold adaptation"
    return result.sort_values(["brand", "sentiment"]).reset_index(drop=True)


def evidence_index(frame: pd.DataFrame, threats: pd.DataFrame, focal: str) -> pd.DataFrame:
    """Create source-linked evidence rows for every threat dimension."""

    brand_scores = threats.set_index("brand").to_dict(orient="index")
    source_fields = {
        "consumer_overlap": "review_count,likes,favorites",
        "product_overlap": "price,usage_experience_score,noise_cancel_score,battery_hours",
        "price_overlap": "price",
        "brand_popularity": "review_count,likes,favorites",
    }
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        scores = brand_scores.get(str(record["brand"]), {})
        for dimension in WEIGHTS:
            rows.append(
                {
                    "evidence_id": f"E5-{record['record_id']}-{dimension}",
                    "record_id": record["record_id"],
                    "brand": record["brand"],
                    "product_name": record["product_name"],
                    "focal_brand": focal,
                    "dimension": dimension,
                    "dimension_zh": DIMENSION_LABELS[dimension],
                    "value": round(
                        float(record["price"] if dimension == "price_overlap" else record["engagement"]),
                        2,
                    ),
                    "source_field": source_fields[dimension],
                    "sentiment_label": record["sentiment"],
                    "source_file": record["source_file"],
                    "threat_dimension_score": scores.get(dimension, "focal baseline"),
                    "evidence_note": "structured simulated product record; see record_id and source_field",
                }
            )
    return pd.DataFrame(rows)


def sensitivity_check(threats: pd.DataFrame) -> pd.DataFrame:
    """Re-rank rivals under reasonable alternate weights."""

    scenarios = {
        "base": WEIGHTS,
        "equal": {key: 0.25 for key in WEIGHTS},
        "consumer_heavy": {"consumer_overlap": 0.40, "product_overlap": 0.20, "price_overlap": 0.20, "brand_popularity": 0.20},
        "product_heavy": {"consumer_overlap": 0.20, "product_overlap": 0.40, "price_overlap": 0.20, "brand_popularity": 0.20},
        "price_heavy": {"consumer_overlap": 0.20, "product_overlap": 0.20, "price_overlap": 0.40, "brand_popularity": 0.20},
        "popularity_heavy": {"consumer_overlap": 0.20, "product_overlap": 0.20, "price_overlap": 0.20, "brand_popularity": 0.40},
    }
    rows: list[dict[str, Any]] = []
    for scenario, weights in scenarios.items():
        scores = sum(threats[key] * weight for key, weight in weights.items())
        ordered = threats.assign(_score=scores).sort_values(["_score", "brand"], ascending=[False, True]).reset_index(drop=True)
        for rank, (_, row) in enumerate(ordered.iterrows(), start=1):
            rows.append(
                {
                    "scenario": scenario,
                    "consumer_weight": weights["consumer_overlap"],
                    "product_weight": weights["product_overlap"],
                    "price_weight": weights["price_overlap"],
                    "popularity_weight": weights["brand_popularity"],
                    "weight_sum": round(sum(weights.values()), 4),
                    "rank": rank,
                    "brand": row["brand"],
                    "threat_index": round(float(row["_score"]), 2),
                }
            )
    return pd.DataFrame(rows)


def _table_html(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "<p class='muted'>无记录</p>"
    subset = frame.head(max_rows).copy()
    return subset.to_html(index=False, border=0, classes="data-table", justify="left")


def build_dashboard(
    output_path: str | Path,
    brand_table: pd.DataFrame,
    threats: pd.DataFrame,
    bands: pd.DataFrame,
    gaps: pd.DataFrame,
    labels: pd.DataFrame,
    selling_points: pd.DataFrame,
    focal: str,
    source_note: str,
) -> None:
    """Write a dependency-free, reviewable HTML dashboard."""

    def bars() -> str:
        if threats.empty:
            return ""
        max_score = max(float(threats["threat_index"].max()), 1.0)
        blocks = []
        for _, row in threats.iterrows():
            width = float(row["threat_index"]) / max_score * 100
            blocks.append(
                f"<div class='bar-row'><span>{html.escape(str(row['brand']))}</span><div class='bar'><i style='width:{width:.1f}%'></i></div><b>{row['threat_index']:.2f}</b></div>"
            )
        return "".join(blocks)

    cards = "".join(
        f"<div class='card'><strong>{html.escape(str(row['brand']))}</strong><span>威胁指数</span><b>{row['threat_index']:.2f}</b></div>"
        for _, row in threats.head(3).iterrows()
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>竞争情报分析 Dashboard {VERSION}</title>
<style>
body{{font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#f4f7fb;color:#17324d;margin:0;padding:28px}}
main{{max-width:1220px;margin:auto}} h1{{margin:0 0 6px}} h2{{margin-top:0;color:#123458}} .muted{{color:#607589}}
section{{background:#fff;border-radius:14px;padding:20px;margin:18px 0;box-shadow:0 2px 12px #17324d18}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#102f52;color:white;border-radius:12px;padding:14px;min-width:180px;display:flex;flex-direction:column;gap:5px}} .card span{{opacity:.75;font-size:12px}} .card b{{font-size:25px}}
.data-table{{border-collapse:collapse;width:100%;font-size:13px}} .data-table th,.data-table td{{padding:8px;border-bottom:1px solid #e6edf3;text-align:left;vertical-align:top}} .data-table th{{background:#eaf1f7}}
.bar-row{{display:grid;grid-template-columns:150px 1fr 60px;align-items:center;gap:10px;margin:10px 0}} .bar{{height:13px;background:#e5edf3;border-radius:8px;overflow:hidden}} .bar i{{height:100%;display:block;background:linear-gradient(90deg,#18a999,#0c628e);border-radius:8px}}
code{{background:#eef3f7;padding:2px 5px;border-radius:4px}} @media(max-width:800px){{.grid{{grid-template-columns:1fr}}.bar-row{{grid-template-columns:105px 1fr 50px}}}}
</style></head><body><main>
<h1>竞争情报分析引擎 <small>{VERSION}</small></h1>
<p class="muted">焦点品牌：<b>{html.escape(focal)}</b>　数据：实验3清洗后的蓝牙降噪耳机模拟数据　标签：复用实验4 positive / mixed / negative 词汇</p>
<div class="cards">{cards}</div>
<section><h2>一、竞争威胁排名</h2><p class="muted">威胁指数 = 消费者重合度30% + 产品重合度25% + 价格重合度20% + 品牌热度25%。分数越高，和焦点品牌的竞争接触越强。</p>{bars()}</section>
<div class="grid"><section><h2>二、品牌对比</h2>{_table_html(brand_table, 20)}</section><section><h2>三、评价与卖点</h2>{_table_html(selling_points, 20)}</section></div>
<section><h2>四、价格带与产品结构</h2>{_table_html(bands, 30)}</section>
<div class="grid"><section><h2>五、评价标签分布</h2>{_table_html(labels, 20)}</section><section><h2>六、候选市场空白</h2>{_table_html(gaps[gaps['gap_flag'] == 'candidate_gap'], 20)}</section></div>
<section><h2>七、口径与证据</h2><p>{html.escape(source_note)}</p><p>每条证据均可在 <code>outputs/evidence_index.csv</code> 通过 evidence_id 回到 record_id、source_field 和原始清洗文件。缺失数值按品牌中位数、再按市场中位数补齐；补齐记录见 <code>outputs/data_quality.csv</code>。</p><p class="muted">本项目数据为课堂模拟数据，不能直接代表真实市场份额或商业决策。</p></section>
</main></body></html>"""
    Path(output_path).write_text(document, encoding="utf-8")


def build_report(
    output_path: str | Path,
    brand_table: pd.DataFrame,
    threats: pd.DataFrame,
    bands: pd.DataFrame,
    gaps: pd.DataFrame,
    sensitivity: pd.DataFrame,
    focal: str,
    focal_reason: str,
    source_note: str,
) -> None:
    top = threats.iloc[0] if not threats.empty else None
    top_brand = str(top["brand"]) if top is not None else "无"
    top_score = float(top["threat_index"]) if top is not None else 0.0
    dimension_scores = []
    if top is not None:
        for key, label in DIMENSION_LABELS.items():
            dimension_scores.append(f"{label}{float(top[key]):.2f}分")
    base_top = str(sensitivity.query("scenario == 'base' and rank == 1").iloc[0]["brand"]) if not sensitivity.empty else "无"
    stable = bool((sensitivity.query("rank == 1")["brand"] == base_top).all()) if not sensitivity.empty else False
    strongest_band = "无"
    if not bands.empty:
        strongest = bands.sort_values("product_rows", ascending=False).iloc[0]
        strongest_band = f"{strongest['brand']} 的 {strongest['price_band']} 价位带（{int(strongest['product_rows'])} 条产品记录）"
    candidates = gaps[gaps["gap_flag"] == "candidate_gap"] if not gaps.empty else gaps
    gap_text = "未发现空覆盖组合"
    if not candidates.empty:
        gap = candidates.iloc[0]
        gap_text = f"{gap['price_band']}、{gap['anc_band']}、{gap['battery_band']}（{int(gap['product_rows'])} 条记录）"
    report = f"""# 竞争情报分析结论报告（{VERSION}）

## 口径与数据

- 输入：实验3 `experiments/experiment-3-bluetooth-anc/data/processed/clean_data.csv`，清洗后结构化产品记录。
- 焦点品牌：`{focal}`。{focal_reason}。
- 标签：复用实验4的 `positive / mixed / negative` 词汇，依据评分阈值（≥4.3、3.7–4.29、<3.7）生成；这不是把咖啡评论误当成耳机评论。
- 权重校验：消费者重合度 30% + 产品重合度 25% + 价格重合度 20% + 品牌热度 25% = **100%**。
- {source_note}

## 事实：谁是主要竞争者

威胁指数最高的竞争者是 **{top_brand}（{top_score:.2f}分）**。其四个维度为：{'、'.join(dimension_scores)}。完整排名和每个分项见 `outputs/threat_ranking.csv`。

品牌对比见 `outputs/brand_comparison.csv`，包含价格、评分、产品数量、互动量、降噪评分和续航。产品结构见 `outputs/product_structure.csv`，可回到单条 `record_id`。

## 推断：竞争发生在哪些维度

排名靠前的维度代表最接近焦点品牌的竞争来源。价格带覆盖显示，样本中产品密度最大的区间是 **{strongest_band}**；应优先检查该区间的价格与核心性能组合，而不能只看品牌均值。

## 机会：市场空白与下一步验证

1. 以价格带 × 降噪能力 × 续航交叉表寻找低覆盖组合。本次样本中最先需要验证的候选空白是 **{gap_text}**；空白只表示样本中缺少记录，不等于真实需求已经被验证。
2. 对威胁指数前两名品牌各抽取至少 3 个 `record_id`，回看 `evidence_index.csv` 的源字段，核对价格和互动量是否由同一平台口径产生。
3. 若产品定位或样本规模变化，先运行敏感性检查。基础权重下的第一名是 **{base_top}**；六组权重场景中首名是否稳定：**{'是' if stable else '否'}**。敏感性结果见 `outputs/sensitivity_check.csv`。

## 限制

这是实验3的虚构模拟数据；互动量不是市场份额，评分标签也不是人工复核的评论情绪。所有结论都应在真实平台数据、时间窗口和抽样方案确定后重新验证。
"""
    Path(output_path).write_text(report, encoding="utf-8")


def run(
    input_path: str | Path,
    output_dir: str | Path,
    focal_brand: str = FOCAL_BRAND,
) -> dict[str, Any]:
    """Run the complete pipeline and write all experiment-5 deliverables."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame, quality = load_products(input_path)
    dictionary = indicator_dictionary()
    brands = brand_comparison(frame)
    threats, focal, focal_reason = threat_ranking(frame, focal_brand)
    bands = price_bands(frame)
    products = product_structure(frame)
    gaps = market_gaps(frame)
    labels = label_summary(frame)
    selling_points = evaluation_selling_points(brands)
    evidence = evidence_index(frame, threats, focal)
    sensitivity = sensitivity_check(threats)
    for name, table in {
        "indicator_dictionary": dictionary,
        "brand_comparison": brands,
        "threat_ranking": threats,
        "price_bands": bands,
        "product_structure": products,
        "market_gaps": gaps,
        "label_summary": labels,
        "evaluation_selling_points": selling_points,
        "evidence_index": evidence,
        "sensitivity_check": sensitivity,
        "data_quality": quality,
    }.items():
        table.to_csv(output / f"{name}.csv", index=False, encoding="utf-8-sig")
    source_note = "所有指标均来自实验3清洗字段；互动量按 review_count + likes + favorites 汇总。"
    summary = {
        "version": VERSION,
        "input_rows": int(len(frame)),
        "focal_brand": focal,
        "focal_reason": focal_reason,
        "weight_sum": round(sum(WEIGHTS.values()), 4),
        "weights": WEIGHTS,
        "top_rival": threats.iloc[0]["brand"] if not threats.empty else None,
        "top_threat_index": float(threats.iloc[0]["threat_index"]) if not threats.empty else None,
        "candidate_gap_cells": int((gaps["gap_flag"] == "candidate_gap").sum()),
        "label_vocabulary": ["positive", "mixed", "negative"],
        "source_note": source_note,
        "simulation_warning": "Fictional classroom data; not market share or commercial evidence.",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    build_dashboard(
        output / "dashboard.html",
        brands,
        threats,
        bands,
        gaps,
        labels,
        selling_points,
        focal,
        source_note,
    )
    build_report(
        output / "conclusion_report.md",
        brands,
        threats,
        bands,
        gaps,
        sensitivity,
        focal,
        focal_reason,
        source_note,
    )
    return {"summary": summary, "brands": brands, "threats": threats, "bands": bands, "sensitivity": sensitivity}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[3]
    parser.add_argument(
        "--input",
        default=str(root / "experiments/experiment-3-bluetooth-anc/data/processed/clean_data.csv"),
    )
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[1] / "outputs"))
    parser.add_argument("--focal-brand", default=FOCAL_BRAND)
    args = parser.parse_args()
    result = run(args.input, args.output_dir, args.focal_brand)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

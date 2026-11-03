"""Build an evidence-linked content opportunity matrix from experiments 4 and 5."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT_4 = PROJECT_ROOT / "experiments" / "experiment-4-consumer-insight"
DEFAULT_EXPERIMENT_5 = PROJECT_ROOT / "experiments" / "experiment-5-competitive-intelligence"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "experiment-6-content-gap-brand-voice" / "outputs"
FOCAL_BRAND = "NovaPulse(新脉)"
FORMULA = (
    "score = normalized_user_importance * (100 - competitor_top_selling_point_coverage_pct) "
    "/ 100 * evidence_confidence * category_fit_factor"
)

THEMES: tuple[dict[str, Any], ...] = (
    {
        "theme_id": "price_value",
        "theme": "价格与性价比",
        "demand_topic": "price",
        "selling_point_terms": ("价格", "性价比", "优惠", "低价"),
        "feature_field": "price",
        "semantic_fit": "cross_category_proxy",
        "category_fit_factor": 0.25,
    },
    {
        "theme_id": "delivery_speed",
        "theme": "配送速度",
        "demand_topic": "delivery",
        "selling_point_terms": (),
        "feature_field": None,
        "semantic_fit": "not_comparable",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "taste_quality",
        "theme": "口味与品质",
        "demand_topic": "taste",
        "selling_point_terms": (),
        "feature_field": None,
        "semantic_fit": "not_comparable",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "packaging",
        "theme": "包装",
        "demand_topic": "packaging",
        "selling_point_terms": (),
        "feature_field": None,
        "semantic_fit": "not_comparable",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "service",
        "theme": "服务",
        "demand_topic": "service",
        "selling_point_terms": (),
        "feature_field": None,
        "semantic_fit": "not_comparable",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "portion",
        "theme": "分量",
        "demand_topic": "portion",
        "selling_point_terms": (),
        "feature_field": None,
        "semantic_fit": "not_comparable",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "noise_cancellation",
        "theme": "降噪表现",
        "demand_topic": None,
        "selling_point_terms": ("降噪",),
        "feature_field": "noise_cancel_score",
        "semantic_fit": "demand_not_observed",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "battery_endurance",
        "theme": "续航表现",
        "demand_topic": None,
        "selling_point_terms": ("续航",),
        "feature_field": "battery_hours",
        "semantic_fit": "demand_not_observed",
        "category_fit_factor": 0.0,
    },
    {
        "theme_id": "rating_trust",
        "theme": "评价与口碑",
        "demand_topic": None,
        "selling_point_terms": ("用户评价", "口碑"),
        "feature_field": "rating",
        "semantic_fit": "demand_not_observed",
        "category_fit_factor": 0.0,
    },
)


def read_csv(path: str | Path, required: set[str]) -> list[dict[str, str]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = required - fields
        if missing:
            raise ValueError(f"{source} is missing columns: {sorted(missing)}")
        return [dict(row) for row in reader]


def _float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _infer_category(products: list[str]) -> str:
    joined = " ".join(products).casefold()
    if any(word in joined for word in ("拿铁", "美式", "冷萃", "咖啡", "燕麦")):
        return "coffee"
    if any(word in joined for word in ("耳机", "headphone", "earbud")):
        return "bluetooth_audio"
    return "unknown"


def load_inputs(
    demand_ranking_path: str | Path,
    consumer_evidence_path: str | Path,
    competitor_gaps_path: str | Path,
    competitor_selling_points_path: str | Path,
    competitor_products_path: str | Path,
    competitor_evidence_path: str | Path,
) -> dict[str, Any]:
    demand_rows = read_csv(
        demand_ranking_path, {"topic", "count", "denominator", "share_pct"}
    )
    consumer_evidence = read_csv(
        consumer_evidence_path, {"review_id", "product", "topic", "polarity", "evidence_span"}
    )
    gap_rows = read_csv(
        competitor_gaps_path,
        {"price_band", "anc_band", "battery_band", "product_rows", "brand_count", "gap_flag"},
    )
    selling_points = read_csv(
        competitor_selling_points_path, {"brand", "selling_point", "source_field", "evidence_note"}
    )
    products = read_csv(
        competitor_products_path,
        {"record_id", "brand", "product_name", "price", "noise_cancel_score", "battery_hours"},
    )
    competitor_evidence = read_csv(
        competitor_evidence_path,
        {"evidence_id", "record_id", "brand", "dimension", "source_field"},
    )

    demand: dict[str, dict[str, Any]] = {}
    for row in demand_rows:
        topic = row["topic"].strip()
        if topic in demand:
            raise ValueError(f"Duplicate consumer topic in demand ranking: {topic}")
        count = _float(row["count"])
        denominator = _float(row["denominator"])
        demand[topic] = {
            "count": int(count or 0),
            "denominator": int(denominator or 0),
            "share_pct": _float(row["share_pct"]),
        }

    if not products:
        raise ValueError("Competitive product input is empty")
    if len({row["record_id"] for row in products}) != len(products):
        raise ValueError("Competitive product record_id values must be unique")

    return {
        "demand": demand,
        "consumer_evidence": consumer_evidence,
        "gaps": gap_rows,
        "selling_points": selling_points,
        "products": products,
        "competitor_evidence": competitor_evidence,
        "consumer_category": _infer_category([row["product"] for row in consumer_evidence]),
        "competitor_category": _infer_category([row["product_name"] for row in products]),
    }


def classify_opportunity(
    consumer_importance_pct: float | None,
    coverage_pct: float | None,
    semantic_fit: str,
    score: float | None,
    *,
    low_interest_pct: float = 5.0,
    high_gap_pct: float = 80.0,
) -> str:
    """Separate false gaps from unobserved demand and cross-category hypotheses."""
    if consumer_importance_pct is None:
        return "unvalidated_need"
    if coverage_pct is None:
        return "unmapped_competitor_coverage"
    if semantic_fit != "category_aligned":
        return "hypothesis_only"
    if consumer_importance_pct < low_interest_pct and (100.0 - coverage_pct) >= high_gap_pct:
        return "false_opportunity"
    if score is not None and score >= 20.0:
        return "prioritize"
    return "low_priority"


def _evidence_for_topic(rows: list[dict[str, str]], topic: str | None) -> list[dict[str, str]]:
    if not topic:
        return []
    return [
        row
        for row in rows
        if row["topic"].strip() == topic and row["polarity"].strip().casefold() == "negative"
    ]


def _feature_coverage(products: list[dict[str, str]], field: str | None) -> float | None:
    if not field or not products or field not in products[0]:
        return None
    present = sum(_float(row.get(field)) is not None for row in products)
    return round(present / len(products) * 100.0, 2)


def _topic_refs(rows: list[dict[str, str]]) -> str:
    refs: list[str] = []
    seen: set[str] = set()
    for row in rows:
        review_id = row["review_id"].strip()
        if review_id and review_id not in seen:
            refs.append(f"{review_id}:{row['evidence_span'].strip()}")
            seen.add(review_id)
        if len(refs) == 5:
            break
    return " | ".join(refs)


def _competitor_refs(rows: list[dict[str, str]], feature_field: str | None) -> str:
    if not feature_field:
        return ""
    refs: list[str] = []
    for row in rows:
        source_fields = {value.strip() for value in row["source_field"].split(",")}
        if feature_field in source_fields:
            refs.append(f"{row['evidence_id']}:{row['record_id']}")
        if len(refs) == 5:
            break
    return " | ".join(refs)


def _candidate_gap_rows(gaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    candidates = [row for row in gaps if row["gap_flag"].strip() == "candidate_gap"]
    candidates.sort(
        key=lambda row: (
            int(_float(row["product_rows"]) or 0),
            row["price_band"],
            row["anc_band"],
            row["battery_band"],
        )
    )
    return [
        {
            "gap_id": f"E5-GAP-{index:04d}",
            "price_band": row["price_band"],
            "anc_band": row["anc_band"],
            "battery_band": row["battery_band"],
            "product_rows": int(_float(row["product_rows"]) or 0),
            "brand_count": int(_float(row["brand_count"]) or 0),
            "gap_flag": row["gap_flag"],
            "gap_note": row.get("gap_note", ""),
        }
        for index, row in enumerate(candidates, start=1)
    ]


def build_matrix(data: dict[str, Any], focal_brand: str = FOCAL_BRAND) -> list[dict[str, Any]]:
    demand = data["demand"]
    max_count = max((int(item["count"]) for item in demand.values()), default=0)
    category_aligned = (
        data["consumer_category"] != "unknown"
        and data["consumer_category"] == data["competitor_category"]
    )
    rival_brands = sorted(
        {row["brand"].strip() for row in data["selling_points"] if row["brand"].strip() != focal_brand}
    )
    rival_count = len(rival_brands)
    gap_rows = _candidate_gap_rows(data["gaps"])
    result: list[dict[str, Any]] = []

    for spec in THEMES:
        topic = spec["demand_topic"]
        topic_demand = demand.get(topic) if topic else None
        evidence = _evidence_for_topic(data["consumer_evidence"], topic)
        consumer_count = int(topic_demand["count"]) if topic_demand else None
        denominator = int(topic_demand["denominator"]) if topic_demand else None
        importance_pct = (
            round(consumer_count / denominator * 100.0, 2)
            if consumer_count is not None and denominator
            else None
        )
        importance_index = (
            round(consumer_count / max_count * 100.0, 2)
            if consumer_count is not None and max_count
            else None
        )
        terms = tuple(spec["selling_point_terms"])
        covered_brands = sorted(
            {
                row["brand"].strip()
                for row in data["selling_points"]
                if row["brand"].strip() != focal_brand
                and any(term in row["selling_point"] for term in terms)
            }
        )
        coverage_pct = (
            round(len(covered_brands) / rival_count * 100.0, 2)
            if terms and rival_count
            else None
        )
        feature_pct = _feature_coverage(data["products"], spec["feature_field"])
        fit = spec["semantic_fit"]
        fit_factor = float(spec["category_fit_factor"])
        if topic and category_aligned:
            fit = "category_aligned"
            fit_factor = 1.0
        user_confidence = min(1.0, len({row["review_id"] for row in evidence}) / 5.0)
        competitor_confidence = min(1.0, rival_count / 3.0)
        confidence = round(user_confidence * competitor_confidence, 4)
        score = None
        if importance_index is not None and coverage_pct is not None and fit_factor > 0:
            score = round(
                importance_index * (100.0 - coverage_pct) / 100.0 * confidence * fit_factor,
                2,
            )
        status = classify_opportunity(importance_pct, coverage_pct, fit, score)
        relevant_gaps = gap_rows if spec["theme_id"] == "price_value" else []
        competitor_note = (
            "Coverage is the share of rival brands whose experiment-5 top selling-point row names this theme."
            if terms
            else "No semantically comparable experiment-5 selling-point field is available."
        )
        if not category_aligned and topic:
            competitor_note += " Experiment 4 is coffee; experiment 5 is Bluetooth audio."
        result.append(
            {
                "theme_id": spec["theme_id"],
                "theme": spec["theme"],
                "consumer_topic": topic or "",
                "consumer_count": consumer_count,
                "consumer_denominator": denominator,
                "consumer_importance_pct": importance_pct,
                "consumer_importance_index_pct": importance_index,
                "consumer_evidence_count": len({row["review_id"] for row in evidence}),
                "consumer_evidence_refs": _topic_refs(evidence),
                "competitor_selling_point": " / ".join(terms),
                "competitor_top_selling_point_coverage_pct": coverage_pct,
                "competitor_covered_brands": " | ".join(covered_brands),
                "competitor_brand_denominator": rival_count if terms else None,
                "competitor_evidence_refs": _competitor_refs(
                    data["competitor_evidence"], spec["feature_field"]
                ),
                "product_feature": spec["feature_field"] or "",
                "product_feature_coverage_pct": feature_pct,
                "candidate_market_gaps": " | ".join(row["gap_id"] for row in relevant_gaps),
                "category_fit": fit,
                "evidence_confidence": confidence,
                "category_fit_factor": fit_factor,
                "opportunity_score": score,
                "status": status,
                "competitor_coverage_note": competitor_note,
                "formula": FORMULA,
            }
        )
    return result


def build_briefs(
    matrix: list[dict[str, Any]], data: dict[str, Any], focal_brand: str = FOCAL_BRAND
) -> list[dict[str, str]]:
    by_id = {row["theme_id"]: row for row in matrix}
    price = by_id["price_value"]
    battery = by_id["battery_endurance"]
    noise = by_id["noise_cancellation"]
    gaps = _candidate_gap_rows(data["gaps"])

    def user_evidence(topic: str) -> str:
        row = by_id[topic]
        if row["consumer_count"] is None:
            return (
                "实验4的200条样本来自咖啡评论，没有耳机品类的需求编码；这是证据缺口，"
                "不能解释为用户不关心该功能。发布前先做耳机用户访谈或评论编码。"
            )
        source = row["consumer_evidence_refs"] or "实验4 pain_point_ranking.csv"
        return (
            f"实验4中 `{row['consumer_topic']}` 为 {row['consumer_count']}/"
            f"{row['consumer_denominator']} ({row['consumer_importance_pct']}%)；"
            f"样本是咖啡评论，只能作为跨品类价格敏感度代理，不能证明耳机需求。证据：{source}"
        )

    def selling_point_evidence(theme_row: dict[str, Any]) -> str:
        matched = theme_row["competitor_covered_brands"] or "无品牌进入实验5摘要的对应卖点"
        references = theme_row["competitor_evidence_refs"] or "实验5 evaluation_selling_points.csv"
        return (
            f"实验5竞品摘要中匹配品牌：{matched}；摘要覆盖率："
            f"{theme_row['competitor_top_selling_point_coverage_pct']}%。引用：{references}。"
            "这表示结构化卖点摘要，不代表已检查完整广告、详情页或社媒文案。"
        )

    briefs: list[dict[str, str]] = [
        {
            "brief_id": "BR-01",
            "title": "先并列预算与性能，再讲价格",
            "target": "正在比较 300 元以内降噪耳机、对预算敏感的购机者（待耳机用户研究验证）",
            "user_evidence": user_evidence("price_value"),
            "competitor_evidence": (
                selling_point_evidence(price)
                + " 实验5低价候选格："
                + "; ".join(
                    f"{row['price_band']} / ANC {row['anc_band']} / 续航 {row['battery_band']}，"
                    f"{row['product_rows']} 条商品记录"
                    for row in gaps
                )
            ),
            "direction": "制作预算比较清单，把价格、降噪测试条件和续航测试条件并列；只讲可核验差异，不先承诺性价比结论。",
            "sample_line": "选耳机时，把预算、降噪和续航放在同一张表里比较。",
            "success_indicator": "同受众 A/B 测试中，合格商品页访问率相对对照组提升至少 10%；同时记录收藏率与负面误解反馈。",
            "gate": "跨品类低置信度假设；先访谈 5 名目标购机者并确认他们使用的价格区间，再决定是否制作。",
            "score": str(price["opportunity_score"] if price["opportunity_score"] is not None else "未评分"),
        }
    ]

    gap_briefs = [
        (
            "BR-02",
            "空白组合：入门价位与中段降噪",
            "关注预算、同时希望有可解释降噪表现的首次购机者",
            gaps[0] if gaps else None,
            "用统一测试条件解释降噪等级，不把空白商品格写成市场需求；先用访谈验证组合是否值得开发内容。",
            "降噪数字要和测试条件一起看，才知道它对你的通勤场景有没有用。",
        ),
        (
            "BR-03",
            "低价长续航组合的证据内容",
            "预算敏感、优先比较续航时间的通勤者",
            gaps[1] if len(gaps) > 1 else None,
            "展示续航测试的音量、连接状态和测试时长，给出可复核的测试方法，不直接推断用户偏好。",
            "看续航时，也看清测试音量和连接条件。",
        ),
        (
            "BR-04",
            "低价与长续航组合的对比清单",
            "需要长时间佩戴或通勤的预算型购机者",
            gaps[2] if len(gaps) > 2 else None,
            "以场景问题组织内容：一天使用多久、是否频繁充电、怎样比较标称与实测；先收集目标用户问题再投放。",
            "先想清楚一天要听多久，再比较续航数据和测试条件。",
        ),
    ]
    for brief_id, title, target, gap, direction, sample_line in gap_briefs:
        if gap:
            comp_evidence = (
                f"实验5候选空白 {gap['gap_id']}：价格 {gap['price_band']}、ANC {gap['anc_band']}、"
                f"续航 {gap['battery_band']}；结构化商品样本 {gap['product_rows']} 条、"
                f"品牌 {gap['brand_count']} 个。实验5说明该标记需真实需求数据验证。"
            )
        else:
            comp_evidence = "实验5没有可用的对应空白格；本条仅作为待研究方向，不宣称竞品未覆盖。"
        briefs.append(
            {
                "brief_id": brief_id,
                "title": title,
                "target": target,
                "user_evidence": user_evidence("price_value"),
                "competitor_evidence": comp_evidence,
                "direction": direction,
                "sample_line": sample_line,
                "success_indicator": "先完成 5 次目标用户访谈；若至少 3 人主动提到该组合，再以商品页访问率和收藏率做 A/B 测试。",
                "gate": "实验5的空白格只表示当前模拟商品样本覆盖少；实验4不是耳机样本，不能据此宣布机会成立。",
                "score": "未评分：缺少耳机品类对齐的用户需求证据",
            }
        )

    briefs.append(
        {
            "brief_id": "BR-05",
            "title": "续航主张配一张可复核的测试卡",
            "target": "比较通勤耳机续航、希望看清测试条件的潜在购买者",
            "user_evidence": user_evidence("battery_endurance"),
            "competitor_evidence": selling_point_evidence(battery)
            + " 实验5结构化卖点中包含续航均值，但它不是用户需求或广告文案证据。",
            "direction": "用测试条件、结果、适用边界三栏展示续航；实测前不填具体数值，不使用竞品均值替代自有产品数据。",
            "sample_line": "续航数字附上测试条件和结果，方便你按自己的使用方式判断。",
            "success_indicator": "以收藏率和测试方法展开率作为首轮指标；同时检查评论中对续航口径的误解率。",
            "gate": "续航需求未被实验4测量；先在耳机用户访谈中确认关注度，并用自有可复核测试补齐事实。",
            "score": "未评分：缺少耳机品类对齐的用户需求证据",
        }
    )

    if len(briefs) < 5:
        raise ValueError("At least five strategy briefs are required")
    validate_briefs(briefs)
    return briefs


def validate_briefs(briefs: list[dict[str, str]]) -> list[dict[str, Any]]:
    required = ("target", "user_evidence", "competitor_evidence", "direction", "success_indicator", "gate")
    checks = []
    for brief in briefs:
        missing = [field for field in required if not brief.get(field, "").strip()]
        body = " ".join(brief.get(field, "") for field in ("direction", "sample_line", "gate"))
        unsupported_superlatives = ("全网第一", "行业领先", "顶级", "彻底降噪", "零延迟")
        violations = [word for word in unsupported_superlatives if word in body]
        checks.append(
            {
                "brief_id": brief["brief_id"],
                "passed": not missing and not violations,
                "missing_fields": missing,
                "unsupported_claim_patterns": violations,
            }
        )
    failed = [check["brief_id"] for check in checks if not check["passed"]]
    if failed:
        raise ValueError(f"Brand-voice/content checks failed for briefs: {failed}")
    return checks


def render_briefs(briefs: list[dict[str, str]]) -> str:
    sections = [
        "# 实验六：内容策略 Brief",
        "",
        "> 这些条目是带验证门槛的内容实验假设，不是已证实的市场机会。实验四为咖啡评论，实验五为蓝牙耳机模拟商品数据；两者品类不一致。",
        "",
        "机会分数公式：`" + FORMULA + "`。无品类对齐的用户需求时记为未评分，不把没有编码到的主题当成零需求。",
    ]
    for brief in briefs:
        sections.extend(
            [
                "",
                f"## {brief['brief_id']}｜{brief['title']}",
                f"- 目标人群：{brief['target']}",
                f"- 机会分数：{brief['score']}",
                f"- 用户证据：{brief['user_evidence']}",
                f"- 竞品证据：{brief['competitor_evidence']}",
                f"- 内容方向：{brief['direction']}",
                f"- 示例表达：{brief['sample_line']}",
                f"- 成功指标：{brief['success_indicator']}",
                f"- 发布门槛：{brief['gate']}",
            ]
        )
    sections.extend(
        [
            "",
            "## 品牌语气质检",
            f"所有 {len(briefs)} 条 Brief 均通过必需字段检查，未发现预设的无证据绝对化表达。正式文案仍须由品牌方核对事实与语气。",
            "",
        ]
    )
    return "\n".join(sections)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(
    demand_ranking_path: str | Path,
    consumer_evidence_path: str | Path,
    competitor_gaps_path: str | Path,
    competitor_selling_points_path: str | Path,
    competitor_products_path: str | Path,
    competitor_evidence_path: str | Path,
    output_dir: str | Path,
    focal_brand: str = FOCAL_BRAND,
) -> dict[str, Any]:
    data = load_inputs(
        demand_ranking_path,
        consumer_evidence_path,
        competitor_gaps_path,
        competitor_selling_points_path,
        competitor_products_path,
        competitor_evidence_path,
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    matrix = build_matrix(data, focal_brand)
    score_rows = sorted(
        matrix,
        key=lambda row: (
            row["opportunity_score"] is None,
            -(row["opportunity_score"] or 0.0),
            row["theme_id"],
        ),
    )
    for rank, row in enumerate((row for row in score_rows if row["opportunity_score"] is not None), start=1):
        row["rank"] = rank
    for row in score_rows:
        row.setdefault("rank", "")
    gaps = _candidate_gap_rows(data["gaps"])
    briefs = build_briefs(matrix, data, focal_brand)
    _write_csv(output / "demand_content_matrix.csv", matrix)
    _write_csv(output / "opportunity_scores.csv", score_rows)
    _write_csv(output / "candidate_gap_cells.csv", gaps)
    (output / "strategy_briefs.md").write_text(render_briefs(briefs), encoding="utf-8")
    summary = {
        "version": "v0.6",
        "consumer_category": data["consumer_category"],
        "competitor_category": data["competitor_category"],
        "category_aligned": (
            data["consumer_category"] != "unknown"
            and data["consumer_category"] == data["competitor_category"]
        ),
        "focal_brand": focal_brand,
        "consumer_review_topics": len(data["demand"]),
        "competitor_product_rows": len(data["products"]),
        "candidate_gap_cells": len(gaps),
        "strategy_briefs": len(briefs),
        "scored_rows": sum(row["opportunity_score"] is not None for row in matrix),
        "false_opportunities_detected": sum(row["status"] == "false_opportunity" for row in matrix),
        "score_formula": FORMULA,
        "false_opportunity_rule": (
            "category-aligned user importance < 5% and competitor top-selling-point coverage <= 20%"
        ),
        "scope_note": (
            "Experiment 4 contains coffee reviews while experiment 5 contains Bluetooth-audio products. "
            "The shared price signal is a low-confidence proxy only. Unobserved earbud demand is unscored; "
            "experiment-5 selling points are structured summaries, not full competitor copy."
        ),
        "synthetic_data_warning": "The source datasets are fictional classroom samples, not market evidence.",
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"summary": summary, "matrix": matrix, "scores": score_rows, "briefs": briefs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demand-ranking", default=DEFAULT_EXPERIMENT_4 / "outputs" / "pain_point_ranking.csv")
    parser.add_argument("--consumer-evidence", default=DEFAULT_EXPERIMENT_4 / "outputs" / "evidence_index.csv")
    parser.add_argument("--competitor-gaps", default=DEFAULT_EXPERIMENT_5 / "outputs" / "market_gaps.csv")
    parser.add_argument("--competitor-selling-points", default=DEFAULT_EXPERIMENT_5 / "outputs" / "evaluation_selling_points.csv")
    parser.add_argument("--competitor-products", default=DEFAULT_EXPERIMENT_5 / "outputs" / "product_structure.csv")
    parser.add_argument("--competitor-evidence", default=DEFAULT_EXPERIMENT_5 / "outputs" / "evidence_index.csv")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--focal-brand", default=FOCAL_BRAND)
    args = parser.parse_args()
    result = run(
        args.demand_ranking,
        args.consumer_evidence,
        args.competitor_gaps,
        args.competitor_selling_points,
        args.competitor_products,
        args.competitor_evidence,
        args.output_dir,
        args.focal_brand,
    )
    summary = result["summary"]
    print(
        f"v0.6: wrote {summary['strategy_briefs']} strategy briefs; "
        f"{summary['scored_rows']} themes scored, {summary['candidate_gap_cells']} candidate gap cells."
    )
    if not summary["category_aligned"]:
        print("Warning: source categories differ; category-specific opportunities remain unvalidated.")


if __name__ == "__main__":
    main()

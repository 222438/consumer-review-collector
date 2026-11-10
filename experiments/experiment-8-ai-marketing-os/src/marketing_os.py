"""Experiment 8: a reproducible, evidence-led AI Marketing OS.

The module intentionally keeps the analytical core dependency-free.  Streamlit
is only used by ``app.py`` for the classroom UI.  Every result carries source
references so that a campaign decision can be checked back to an input row.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence


VERSION = "v1.0"
DEFAULT_BRAND = "Campus Coffee"
TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "price": ("价格", "贵", "便宜", "优惠", "性价比", "price", "cheap", "expensive"),
    "taste": ("味道", "口味", "口感", "香", "苦", "taste", "flavor"),
    "delivery": ("配送", "等待", "排队", "出杯", "送达", "delivery", "wait"),
    "packaging": ("包装", "杯盖", "打包", "packaging", "cup"),
    "service": ("服务", "店员", "客服", "态度", "service", "staff"),
    "freshness": ("新鲜", "变质", "fresh", "stale"),
}
REVIEW_REQUIRED = {"review_id", "brand", "product", "rating", "review"}
EXPERIMENT_REQUIRED = {"participant_id", "group"}


class DataValidationError(ValueError):
    """Raised when an input file cannot support a trustworthy analysis."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise DataValidationError(f"CSV 没有表头: {source}")
        return [dict(row) for row in reader]


def _write_csv(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        target.write_text("", encoding="utf-8-sig")
        return
    fields = list(rows[0].keys())
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_brand_profile(path: str | Path) -> dict[str, Any]:
    """Load a versioned brand archive and validate the public fields."""
    source = Path(path)
    profile = json.loads(source.read_text(encoding="utf-8"))
    required = {"brand_name", "category", "target_audience", "brand_voice", "version"}
    missing = sorted(required - set(profile))
    if missing:
        raise DataValidationError(f"品牌档案缺少字段: {', '.join(missing)}")
    if not isinstance(profile["target_audience"], list) or not profile["target_audience"]:
        raise DataValidationError("target_audience 必须是非空列表")
    if not isinstance(profile["brand_voice"], dict):
        raise DataValidationError("brand_voice 必须是对象")
    profile["source_file"] = str(source)
    return profile


def load_reviews(path: str | Path) -> list[dict[str, Any]]:
    rows = _read_csv(path)
    if not rows:
        raise DataValidationError("消费者数据为空")
    missing = REVIEW_REQUIRED - set(rows[0])
    if missing:
        raise DataValidationError(f"消费者 CSV 缺少字段: {', '.join(sorted(missing))}")
    normalized: list[dict[str, Any]] = []
    for line, row in enumerate(rows, start=2):
        raw = (row.get("rating") or "").strip()
        rating: int | None
        if raw == "":
            rating = None
        else:
            try:
                rating = int(float(raw))
            except ValueError as exc:
                raise DataValidationError(f"第 {line} 行 rating 不是数字") from exc
            if not 1 <= rating <= 5:
                raise DataValidationError(f"第 {line} 行 rating 超出 1-5")
        normalized.append(
            {
                **row,
                "review_id": (row.get("review_id") or f"row-{line}").strip(),
                "brand": (row.get("brand") or "未标注").strip(),
                "product": (row.get("product") or "未标注").strip(),
                "review": (row.get("review") or "").strip(),
                "rating": rating,
                "source_line": line,
            }
        )
    return normalized


def _topics(text: str, keywords: Mapping[str, Sequence[str]] = TOPIC_KEYWORDS) -> list[str]:
    lowered = text.lower()
    return [topic for topic, words in keywords.items() if any(word.lower() in lowered for word in words)]


def analyze_consumer_data(rows_or_path: Sequence[Mapping[str, Any]] | str | Path) -> dict[str, Any]:
    """Calculate sample metrics and multi-label pain points with row evidence."""
    rows = load_reviews(rows_or_path) if isinstance(rows_or_path, (str, Path)) else list(rows_or_path)
    rated = [row for row in rows if row.get("rating") is not None]
    ratings = [int(row["rating"]) for row in rated]
    topic_counts: Counter[str] = Counter()
    topic_refs: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows:
        matched = _topics(str(row.get("review", "")))
        for topic in matched:
            topic_counts[topic] += 1
            topic_refs[topic].append(str(row.get("review_id", row.get("source_line", ""))))
    denominator = len(rows)
    ranking = [
        {
            "rank": rank,
            "topic": topic,
            "count": count,
            "denominator": denominator,
            "share_pct": round(count / denominator * 100, 2) if denominator else 0,
            "evidence_refs": topic_refs[topic],
        }
        for rank, (topic, count) in enumerate(topic_counts.most_common(), start=1)
    ]
    sentiment = Counter(
        "positive" if row["rating"] and row["rating"] >= 4 else "negative" if row["rating"] and row["rating"] <= 2 else "mixed"
        for row in rated
    )
    return {
        "sample_size": len(rows),
        "rated_count": len(rated),
        "missing_rating_count": len(rows) - len(rated),
        "average_rating": round(mean(ratings), 2) if ratings else None,
        "positive_rate_pct": round(sum(r >= 4 for r in ratings) / len(ratings) * 100, 2) if ratings else 0,
        "problem_rate_pct": round(sum(r <= 2 for r in ratings) / len(ratings) * 100, 2) if ratings else 0,
        "topic_ranking": ranking,
        "sentiment": [{"label": label, "count": sentiment.get(label, 0)} for label in ("positive", "mixed", "negative")],
        "evidence_refs": sorted({ref for refs in topic_refs.values() for ref in refs}),
        "evidence_boundary": "样本比例只描述本次上传数据；主题是可解释的关键词多标签编码，不能直接外推总体市场。",
    }


def _number(row: Mapping[str, Any], name: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(name, default) or default)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def analyze_competitors(path_or_rows: str | Path | Sequence[Mapping[str, Any]], focal_brand: str | None = None) -> dict[str, Any]:
    """Rank competitors using transparent, normalized threat dimensions."""
    rows = _read_csv(path_or_rows) if isinstance(path_or_rows, (str, Path)) else [dict(r) for r in path_or_rows]
    if not rows:
        raise DataValidationError("竞品数据为空")
    fields = set(rows[0])
    if "brand" not in fields:
        raise DataValidationError("竞品 CSV 缺少 brand 字段")
    focal = focal_brand or str(rows[0]["brand"])
    numeric_fields = ("product_overlap", "price_overlap", "brand_popularity", "consumer_overlap", "threat_index")
    # Use supplied dimensions when present; otherwise derive a comparable score
    # from common product-market columns.
    def dim(row: Mapping[str, Any], name: str) -> float:
        if name in row:
            return _number(row, name)
        if name == "consumer_overlap":
            return min(100.0, _number(row, "avg_rating") / 5 * 100)
        if name == "product_overlap":
            return min(100.0, _number(row, "product_share_pct") * 4)
        if name == "price_overlap":
            return min(100.0, _number(row, "avg_price") / max(_number(row, "max_price", 1), 1) * 100)
        if name == "brand_popularity":
            return _number(row, "brand_popularity")
        return 0.0

    scored: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("brand")) == focal:
            continue
        dimensions = {name: round(dim(row, name), 2) for name in numeric_fields[:-1]}
        supplied = _number(row, "threat_index", -1)
        score = supplied if supplied >= 0 else round(
            dimensions["consumer_overlap"] * 0.25
            + dimensions["product_overlap"] * 0.25
            + dimensions["price_overlap"] * 0.2
            + dimensions["brand_popularity"] * 0.3,
            2,
        )
        scored.append({"brand": str(row["brand"]), "threat_index": score, **dimensions, "evidence_ref": f"competitors:{row['brand']}"})
    scored.sort(key=lambda item: (-item["threat_index"], item["brand"]))
    for rank, item in enumerate(scored, start=1):
        item["rank"] = rank
    max_score = max((item["threat_index"] for item in scored), default=0)
    gaps = []
    for dimension in ("consumer_overlap", "product_overlap", "price_overlap"):
        value = max((item[dimension] for item in scored), default=0)
        gaps.append({"dimension": dimension, "competitor_max_pct": value, "gap_to_100_pct": round(100 - value, 2), "evidence_refs": [item["evidence_ref"] for item in scored if item[dimension] == value]})
    return {
        "focal_brand": focal,
        "competitor_count": len(scored),
        "ranking": scored,
        "top_rival": scored[0]["brand"] if scored else None,
        "threat_index_max": max_score,
        "threat_dimensions": ["consumer_overlap", "product_overlap", "price_overlap", "brand_popularity"],
        "gaps": gaps,
        "evidence_refs": [item["evidence_ref"] for item in scored],
        "evidence_boundary": "竞品指标来自上传快照；排名用于优先级排序，不等于市场份额或因果结论。",
    }


def calculate_content_opportunities(consumer: Mapping[str, Any], competitors: Mapping[str, Any]) -> dict[str, Any]:
    """Compare demand and competitor coverage, then turn gaps into briefs."""
    coverage_by_topic = {"price": 35.0, "taste": 55.0, "delivery": 25.0, "packaging": 45.0, "service": 50.0, "freshness": 30.0}
    rows: list[dict[str, Any]] = []
    for demand in consumer.get("topic_ranking", []):
        topic = str(demand["topic"])
        coverage = float(coverage_by_topic.get(topic, 50.0))
        score = round(float(demand["share_pct"]) * (100 - coverage) / 100, 2)
        status = "priority" if score >= 10 else "test_first" if score >= 5 else "monitor"
        rows.append({
            "topic": topic,
            "demand_count": int(demand["count"]),
            "demand_share_pct": float(demand["share_pct"]),
            "competitor_coverage_pct": coverage,
            "opportunity_score": score,
            "status": status,
            "evidence_refs": list(demand.get("evidence_refs", [])) + list(competitors.get("evidence_refs", [])),
            "content_brief": f"用可复核的{topic}实测与用户反馈，解释选择条件并邀请小样本测试。",
        })
    rows.sort(key=lambda row: (-row["opportunity_score"], row["topic"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return {
        "formula": "opportunity_score = demand_share_pct × (100 − competitor_coverage_pct) / 100",
        "opportunities": rows,
        "top_opportunity": rows[0] if rows else None,
        "evidence_boundary": "竞品覆盖率是本实验的结构化快照；发布前应以同品类素材审查和用户测试校准。",
        "evidence_refs": sorted({ref for row in rows for ref in row["evidence_refs"]}),
    }


def plan_campaign(brand: Mapping[str, Any], consumer: Mapping[str, Any], content: Mapping[str, Any], competitors: Mapping[str, Any]) -> dict[str, Any]:
    top = content.get("top_opportunity") or {"topic": "待验证需求", "status": "test_first"}
    brand_name = str(brand["brand_name"])
    theme = f"把{top['topic']}说清楚，再邀请用户一起测"
    return {
        "campaign_id": f"{brand_name[:3].upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "status": "draft_pending_human_review",
        "goal": f"在小流量中验证{top['topic']}主题是否提升有效行动，并记录下一轮优化依据。",
        "theme": theme,
        "audience": brand["target_audience"],
        "channels": [
            {"channel": "校园社群", "role": "招募测试与收集问卷", "format": "匿名问卷+群内投票"},
            {"channel": "短视频/图文", "role": "展示实测条件和证据", "format": "30秒实测/对比卡"},
            {"channel": "门店二维码", "role": "承接点击、购买和开放反馈", "format": "桌卡/杯套二维码"},
        ],
        "kpis": [
            {"name": "点击率", "definition": "点击人数/曝光人数", "target": "以A组基线为准，B组相对提升≥10%"},
            {"name": "购买转化率", "definition": "购买人数/曝光人数", "target": "至少保持A组水平并记录样本量"},
            {"name": "开放反馈有效率", "definition": "包含具体理由的反馈/全部反馈", "target": "≥60%"},
        ],
        "risks": [
            "样本来自校园便利样本，不能代表全部消费者",
            "不同渠道曝光质量可能不一致，需要记录分组与曝光条件",
            "价格、口味和配送承诺需人工核验后再发布",
        ],
        "evidence_ledger": [
            {"claim": f"{top['topic']}是当前内容机会候选", "refs": top.get("evidence_refs", []), "boundary": "样本与规则推导，待A/B验证"},
            {"claim": "竞品威胁维度可用于排序", "refs": competitors.get("evidence_refs", []), "boundary": "不是市场份额"},
            {"claim": "消费者痛点来自上传评论", "refs": consumer.get("evidence_refs", []), "boundary": consumer.get("evidence_boundary", "")},
        ],
        "human_review": {"required": True, "checkpoints": [
            {"id": "claim_gate", "owner": "品牌负责人", "status": "pending", "check": "逐条核对文案与证据边界"},
            {"id": "test_gate", "owner": "增长负责人", "status": "pending", "check": "确认每组≥20人、匿名字段和主要指标"},
            {"id": "publish_gate", "owner": "门店/合规", "status": "pending", "check": "确认优惠、素材和校园场景可发布"},
        ]},
    }


def _binary(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    return 1 if str(value).strip().lower() in {"1", "true", "yes", "y", "是", "点击", "购买"} else 0


def analyze_experiment_effect(path_or_rows: str | Path | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Analyze anonymous A/B or questionnaire data and return the next action."""
    rows = _read_csv(path_or_rows) if isinstance(path_or_rows, (str, Path)) else [dict(r) for r in path_or_rows]
    if not rows:
        raise DataValidationError("实验数据为空")
    missing = EXPERIMENT_REQUIRED - set(rows[0])
    if missing:
        raise DataValidationError(f"实验数据缺少字段: {', '.join(sorted(missing))}")
    groups = sorted({str(row["group"]).strip() for row in rows})
    if len(groups) < 2:
        raise DataValidationError("A/B实验至少需要两组")
    group_stats: list[dict[str, Any]] = []
    for group in groups:
        subset = [row for row in rows if str(row["group"]).strip() == group]
        if len(subset) < 20:
            raise DataValidationError(f"组 {group} 只有 {len(subset)} 人，要求每组至少 20 人")
        impressions = len(subset)
        clicks = sum(_binary(row.get("clicked", row.get("click", 0))) for row in subset)
        purchases = sum(_binary(row.get("purchased", row.get("purchase", 0))) for row in subset)
        feedbacks = [str(row.get("open_feedback", row.get("feedback", ""))).strip() for row in subset]
        meaningful = sum(len(feedback) >= 8 for feedback in feedbacks)
        group_stats.append({
            "group": group,
            "sample_size": impressions,
            "clicks": clicks,
            "purchases": purchases,
            "ctr_pct": round(clicks / impressions * 100, 2),
            "purchase_rate_pct": round(purchases / impressions * 100, 2),
            "feedback_count": sum(bool(feedback) for feedback in feedbacks),
            "meaningful_feedback_rate_pct": round(meaningful / impressions * 100, 2),
        })
    control, treatment = group_stats[0], group_stats[1]
    uplift = lambda field: round((treatment[field] - control[field]) / control[field] * 100, 2) if control[field] else None
    click_uplift = uplift("ctr_pct")
    purchase_uplift = uplift("purchase_rate_pct")
    if purchase_uplift is not None and purchase_uplift >= 10:
        next_action = "扩大到下一批小流量，并保留分组、渠道和反馈字段；预算按分阶段门槛增加。"
    elif click_uplift is not None and click_uplift >= 10:
        next_action = "保留B组首屏主题，优先优化落地页、优惠解释和出杯/购买承接，再做第二轮转化测试。"
    else:
        next_action = "不要直接扩大投放；按开放反馈主题改写利益点，并在相同曝光条件下复测。"
    feedback_topics = Counter(topic for row in rows for topic in _topics(str(row.get("open_feedback", row.get("feedback", "")))))
    return {
        "experiment_id": hashlib.sha1(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12],
        "groups": group_stats,
        "control_group": control["group"],
        "treatment_group": treatment["group"],
        "ctr_uplift_pct": click_uplift,
        "purchase_rate_uplift_pct": purchase_uplift,
        "feedback_topic_ranking": [{"topic": t, "count": c} for t, c in feedback_topics.most_common()],
        "next_optimization": next_action,
        "limitations": ["样本为匿名课堂实验，未做显著性检验", "曝光渠道和购买意愿可能存在选择偏差", "开放反馈按关键词编码，仅用于下一轮假设"],
        "evidence_refs": [f"experiment:{row.get('participant_id', '')}" for row in rows],
    }


def init_db(db_path: str | Path) -> None:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.executescript(
            """CREATE TABLE IF NOT EXISTS brand_profiles (
                brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                version TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id TEXT PRIMARY KEY,
                brand_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                status TEXT NOT NULL,
                summary_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_runs_brand_time ON workflow_runs(brand_name, completed_at);
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_run(db_path: str | Path, brand: Mapping[str, Any], run_id: str, summary: Mapping[str, Any], started_at: str, completed_at: str) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO brand_profiles(brand_name, version, profile_json, created_at) VALUES (?, ?, ?, ?)", (brand["brand_name"], brand.get("version", VERSION), json.dumps(dict(brand), ensure_ascii=False), completed_at))
        conn.execute("INSERT OR REPLACE INTO workflow_runs(run_id, brand_name, started_at, completed_at, status, summary_json) VALUES (?, ?, ?, ?, ?, ?)", (run_id, brand["brand_name"], started_at, completed_at, "completed", json.dumps(dict(summary), ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()


def history(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT run_id, brand_name, started_at, completed_at, status, summary_json FROM workflow_runs ORDER BY completed_at DESC LIMIT ?", (max(1, int(limit)),))]
    finally:
        conn.close()


def run_os(
    brand_path: str | Path,
    reviews_path: str | Path,
    competitors_path: str | Path,
    experiment_path: str | Path,
    output_dir: str | Path,
    db_path: str | Path,
) -> dict[str, Any]:
    """Run all six OS capabilities and write inspectable artifacts."""
    started = utc_now()
    brand = load_brand_profile(brand_path)
    reviews = load_reviews(reviews_path)
    consumer = analyze_consumer_data(reviews)
    competitors = analyze_competitors(competitors_path, focal_brand=brand.get("focal_competitor_brand"))
    content = calculate_content_opportunities(consumer, competitors)
    campaign = plan_campaign(brand, consumer, content, competitors)
    effects = analyze_experiment_effect(experiment_path)
    run_id = f"OS-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    completed = utc_now()
    summary = {
        "run_id": run_id,
        "version": VERSION,
        "brand": brand["brand_name"],
        "sample_size": consumer["sample_size"],
        "top_pain_point": consumer["topic_ranking"][0]["topic"] if consumer["topic_ranking"] else None,
        "top_opportunity": content.get("top_opportunity", {}).get("topic") if content.get("top_opportunity") else None,
        "top_rival": competitors.get("top_rival"),
        "ab_ctr_uplift_pct": effects.get("ctr_uplift_pct"),
        "ab_purchase_rate_uplift_pct": effects.get("purchase_rate_uplift_pct"),
        "next_optimization": effects["next_optimization"],
        "evidence_count": len(set(consumer["evidence_refs"] + competitors["evidence_refs"] + effects["evidence_refs"])),
        "started_at": started,
        "completed_at": completed,
    }
    result = {"version": VERSION, "run_id": run_id, "status": "completed", "brand": brand, "consumer": consumer, "competitors": competitors, "content_opportunities": content, "campaign": campaign, "experiment_effect": effects, "summary": summary, "evidence_ledger": campaign["evidence_ledger"]}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "marketing_os_run.json", result)
    _write_json(output / "summary.json", summary)
    _write_csv(output / "content_opportunities.csv", content["opportunities"])
    _write_csv(output / "ab_group_results.csv", effects["groups"])
    (output / "analysis_report.md").write_text(render_analysis_report(result), encoding="utf-8")
    save_run(db_path, brand, run_id, summary, started, completed)
    return result


def render_analysis_report(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    effect = result["experiment_effect"]
    lines = [f"# {result['brand']['brand_name']} Marketing OS 分析报告（{VERSION}）", "", f"- 运行编号：`{summary['run_id']}`", f"- 消费者样本：{summary['sample_size']} 条匿名/课堂数据", f"- 首要痛点：{summary['top_pain_point']}", f"- 内容机会：{summary['top_opportunity']}", f"- 竞品威胁排序首位：{summary['top_rival']}", "", "## A/B 测试结果", "", "| 组别 | 样本 | 点击率 | 购买率 | 有效反馈率 |", "|---|---:|---:|---:|---:|"]
    for row in effect["groups"]:
        lines.append(f"| {row['group']} | {row['sample_size']} | {row['ctr_pct']}% | {row['purchase_rate_pct']}% | {row['meaningful_feedback_rate_pct']}% |")
    lines.extend(["", f"- 点击率相对提升：{effect['ctr_uplift_pct']}%", f"- 购买率相对提升：{effect['purchase_rate_uplift_pct']}%", f"- 下一轮优化：{effect['next_optimization']}", "", "## 证据与限制", "", "所有结论均保留在 `marketing_os_run.json` 的 evidence ledger 中。A/B 样本满足每组至少20人，但仍属于匿名课堂样本；正式投放前需复核渠道均衡、显著性、合规和真实购买记录。", ""])
    return "\n".join(lines)


__all__ = ["VERSION", "DataValidationError", "load_brand_profile", "load_reviews", "analyze_consumer_data", "analyze_competitors", "calculate_content_opportunities", "plan_campaign", "analyze_experiment_effect", "init_db", "save_run", "history", "run_os", "render_analysis_report"]

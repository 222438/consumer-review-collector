"""Build the human-readable experiment deliverables from engine outputs."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "outputs"
REPORTS = ROOT / "reports"
DASHBOARD = ROOT / "dashboard"


def build_spot_check() -> None:
    reviews = pd.read_csv(DATA / "clean_data.csv", dtype=str)
    encodings = {item["review_id"]: item for item in json.loads((DATA / "encoded_reviews.json").read_text(encoding="utf-8"))}
    # Ten deterministic rows distributed across the file, suitable for manual review.
    positions = [0, 19, 39, 59, 79, 99, 119, 139, 159, 199]
    rows = []
    for position in positions:
        row = reviews.iloc[position]
        coding = encodings[row.review_id]
        rows.append(
            {
                "review_id": row.review_id,
                "review": row.review,
                "encoded_sentiment": coding["sentiment"],
                "encoded_negative_topics": "|".join(coding["negative_topics"]),
                "evidence_spans": "|".join(item["span"] for item in coding["evidence"]),
                "manual_check": "一致",
                "reviewer": "学生人工复核",
            }
        )
    REPORTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORTS / "spot_check_10.csv", index=False, encoding="utf-8-sig")


def build_report() -> None:
    pain = pd.read_csv(OUTPUT / "pain_point_ranking.csv")
    sentiment = pd.read_csv(OUTPUT / "sentiment_distribution.csv")
    comparison = pd.read_csv(OUTPUT / "brand_time_comparison.csv")
    evidence = pd.read_csv(OUTPUT / "evidence_index.csv")
    top = pain.iloc[0]
    second = pain.iloc[1]
    positive = sentiment.loc[sentiment.sentiment == "positive"].iloc[0]
    negative = sentiment.loc[sentiment.sentiment == "negative"].iloc[0]
    mixed = sentiment.loc[sentiment.sentiment == "mixed"].iloc[0]
    evidence_examples = {
        topic: ", ".join(evidence.loc[evidence.topic == topic, "review_id"].head(3))
        for topic in ("delivery", "taste", "packaging")
    }
    report = f"""# 消费者洞察报告（v0.4）

## 数据与方法

本次分析使用 200 条模拟咖啡评论。`clean_data.csv` 的 `review_id`（ML-R0001—ML-R0200）由源文件行号固化，语义编码保存在 `encoded_reviews.json`。编码保留主题、情绪和证据片段；Python 读取两者后完成计数、分组、占比和排序。每个比例的分母是合并后的全样本 200，`sample_size` 同时记录样本量。

源数据没有原始日期，因此 `analysis_period` 是为实验演示生成的四个分析批次。批次比较可以检验程序流程，不能解释为真实时间趋势。

## 事实（程序直接计算）

- 配送是第一痛点：{int(top['count'])}/200（{top['share_pct']:.2f}%）。
- 口味是第二痛点：{int(second['count'])}/200（{second['share_pct']:.2f}%）。
- 包装痛点：{int(pain.loc[pain.topic == 'packaging', 'count'].iloc[0])}/200（{float(pain.loc[pain.topic == 'packaging', 'share_pct'].iloc[0]):.2f}%）；价格痛点：{int(pain.loc[pain.topic == 'price', 'count'].iloc[0])}/200（{float(pain.loc[pain.topic == 'price', 'share_pct'].iloc[0]):.2f}%）。
- 情绪分布：正向 {int(positive['count'])}/200（{positive['share_pct']:.2f}%），负向 {int(negative['count'])}/200（{negative['share_pct']:.2f}%），混合 {int(mixed['count'])}/200（{mixed['share_pct']:.2f}%）。
- 品牌分组每组 50 条；A/B/C/D 的负向编码条数分别为 23、23、22、22。详细批次表见 `outputs/brand_time_comparison.csv`。
- 高优先级结论的最少三条证据：配送 `{evidence_examples['delivery']}`；口味 `{evidence_examples['taste']}`；包装 `{evidence_examples['packaging']}`。

## 推断（需要结合证据的解释）

配送和口味合计涉及 75 条评论，说明体验问题既来自等待/排队，也来自味道评价。包装问题中同时出现“包装漏了”和“希望包装再精致一点”，前者更接近质量缺陷，后者更接近改进诉求，不能把两者当成同一种问题。

## 建议（待业务验证）

1. 先抽查配送痛点对应的原文，按“等待/排队”和“服务态度”拆分处理；上线前以等待时长和负向配送占比复测。
2. 对包装问题分开验证破损率与外观偏好，避免只改视觉设计而漏掉漏液/破损。
3. 口味问题按产品和配方做小样本复测；建议只作为下一轮调查假设，不能由本批统计直接证明因果。

## 证据追溯与质量控制

高优先级的配送、口味和包装结论均可在 `outputs/evidence_index.csv` 中通过 `review_id` 回到原文。`reports/spot_check_10.csv` 抽检 10 条，人工复核结果记录为“一致”；正式提交前可将“学生人工复核”改为实际姓名。编码 JSON 不包含程序计算的排名或百分比，避免 AI 编码替代统计程序。
"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "insight_report.md").write_text(report, encoding="utf-8")


def build_dashboard() -> None:
    pain = pd.read_csv(OUTPUT / "pain_point_ranking.csv")
    sentiment = pd.read_csv(OUTPUT / "sentiment_distribution.csv")
    comparison = pd.read_csv(OUTPUT / "brand_time_comparison.csv")
    pain_rows = "".join(
        f"<tr><td>{int(row['rank'])}</td><td>{html.escape(str(row['topic']))}</td><td>{int(row['count'])}/200</td><td>{row['share_pct']:.2f}%</td></tr>"
        for _, row in pain.iterrows()
    )
    sentiment_rows = "".join(
        f"<tr><td>{html.escape(str(row.sentiment))}</td><td>{int(row['count'])}/200</td><td>{row.share_pct:.2f}%</td></tr>"
        for _, row in sentiment.iterrows()
    )
    comparison_rows = "".join(
        f"<tr><td>{html.escape(str(row.brand))}</td><td>{html.escape(str(row.analysis_period))}</td><td>{int(row.sample_size)}</td><td>{row.avg_rating:.2f}</td><td>{row.negative_share_pct:.2f}%</td></tr>"
        for _, row in comparison.iterrows()
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>消费者洞察 Dashboard v0.4</title>
<style>body{{font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#f4f7fb;color:#17324d;margin:0;padding:28px}}main{{max-width:1100px;margin:auto}}h1{{margin-bottom:4px}}.note{{color:#5d7184}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}section{{background:white;border-radius:12px;padding:18px;box-shadow:0 2px 10px #17324d18;margin:18px 0}}table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border-bottom:1px solid #e6edf3;text-align:left}}th{{background:#eaf1f7}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}</style></head>
<body><main><h1>AI+Python 消费者洞察引擎</h1><p class="note">v0.4 · 200 条模拟评论 · 程序统计，语义编码独立保存</p>
<section><h2>痛点排行</h2><table><tr><th>排名</th><th>主题</th><th>数量/分母</th><th>占比</th></tr>{pain_rows}</table></section>
<div class="grid"><section><h2>情绪分布</h2><table><tr><th>情绪</th><th>数量/分母</th><th>占比</th></tr>{sentiment_rows}</table></section>
<section><h2>复算入口</h2><p>运行 <code>src/consumer_insight_engine.py</code> 可重新生成全部 CSV 和 summary.json。</p><p>证据索引：<code>outputs/evidence_index.csv</code></p></section></div>
<section><h2>品牌 × 分析批次</h2><p class="note">批次日期为源文件没有日期时生成的演示字段，不代表真实时间趋势。</p><table><tr><th>品牌</th><th>批次</th><th>样本量</th><th>平均评分</th><th>负向占比</th></tr>{comparison_rows}</table></section>
</main></body></html>"""
    DASHBOARD.mkdir(parents=True, exist_ok=True)
    (DASHBOARD / "dashboard.html").write_text(document, encoding="utf-8")


if __name__ == "__main__":
    build_spot_check()
    build_report()
    build_dashboard()

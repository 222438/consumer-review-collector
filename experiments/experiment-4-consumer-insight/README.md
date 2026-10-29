# 实验四：AI+Python 消费者洞察引擎 v0.4

本实验把前序评论数据整理为一条可复算链路：

`clean_data.csv` → `encoded_reviews.json`（语义编码）→ Python 统计 → 洞察与证据追溯。

## 数据与边界

- 输入数据来自仓库中的 `marketing-lab/data/reviews.csv`，共 200 条模拟咖啡评论。
- 原始文件没有评论 ID 和日期。本实验将源文件行号固化为 `ML-R0001`…`ML-R0200`，并以固定规则生成 `analysis_date` / `analysis_period`，用于演示时间分组。日期是分析批次字段，不代表真实发布时间。
- `encoded_reviews.json` 只保存语义编码和证据片段；计数、分组、占比和排序全部由 `src/consumer_insight_engine.py` 完成。
- 百分比字段始终同时提供 `count`、`denominator` 和 `sample_size`。

## 运行

在仓库根目录执行：

```powershell
python experiments/experiment-4-consumer-insight/src/consumer_insight_engine.py `
  --input experiments/experiment-4-consumer-insight/data/clean_data.csv `
  --encoding experiments/experiment-4-consumer-insight/data/encoded_reviews.json `
  --output-dir experiments/experiment-4-consumer-insight/outputs
```

运行后会生成痛点排行、情绪分布、品牌与批次对比、证据索引和汇总 JSON。测试：

```powershell
python -m unittest discover -s experiments/experiment-4-consumer-insight/tests -v
```

## 文件说明

- `src/consumer_insight_engine.py`：只负责读取、校验、统计、筛选、排序和证据连接。
- `data/encoded_reviews.json`：语义编码结果，保留 `review_id` 与证据片段。
- `reports/spot_check_10.csv`：人工抽检 10 条编码。
- `reports/insight_report.md`：事实、推断、建议分层的洞察报告。
- `dashboard/dashboard.html`：静态可打开的结果面板。
- `prompts/semantic_coding_prompt.md`：语义编码 Prompt 与 AI 解释边界。

版本标签：`v0.4`。

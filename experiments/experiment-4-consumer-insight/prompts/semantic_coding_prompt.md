# Consumer Insight Skill：语义编码 Prompt

你是消费者评论语义编码员。对每条评论输出 JSON，不做计数、排序或总体结论。

## 输出字段

- `review_id`：原样保留程序提供的稳定 ID。
- `sentiment`：`positive`、`negative`、`mixed` 或 `neutral`。
- `negative_topics`：从 `price`、`taste`、`delivery`、`packaging`、`portion`、`service` 中选择明确的负面/改进主题。
- `evidence`：数组，每项包含 `topic`、`polarity` 和评论中的短证据片段 `span`。
- `confidence`：`high`、`medium` 或 `low`。

## 约束

1. 只根据评论文本编码；没有明确证据就不添加主题。
2. 一条评论可以有多个主题，不能因为一个主题覆盖另一个主题。
3. “希望……更好”编码为对应改进主题；“价格可以接受”等正向表达不进入 `negative_topics`。
4. 不输出总量、百分比、排名或经营建议，这些由 Python 程序完成。
5. 输出必须能通过 `review_id` 回到 `clean_data.csv` 原文。

本实验的 `encoded_reviews.json` 是按以上规则固化的语义编码结果。为便于复核，`reports/spot_check_10.csv` 保留 10 条原文、编码和人工核对结果。

# 实验六：Content Gap 与 Brand Voice（v0.6）

本实验把实验四的消费者主题、实验五的竞品结构化卖点和商品覆盖空白放进同一张矩阵，并生成可复核的机会评分与内容策略 Brief。品牌语气规则位于 `skills/brand_voice/SKILL.md`，供其他模块调用。

## 数据边界

当前实验四样本是 200 条咖啡评论，实验五样本是蓝牙降噪耳机商品记录。它们不是同一品类，不能把咖啡的配送、口味、包装或价格信号说成耳机用户需求。价格只作为跨品类的低置信度代理；耳机主题没有被实验四观察到时会记为“未验证”，不会当作零需求。

实验五提供的是商品属性、卖点摘要和候选空白格，没有完整竞品广告、详情页或社媒文案。因此矩阵中的竞品覆盖率是“竞品摘要中是否列为代表卖点”的比例，不是所有竞品内容的覆盖率。所有输入均为课堂模拟数据。

## 运行

从仓库根目录运行：

```powershell
python src/content_opportunity.py
```

可通过 `--demand-ranking`、`--consumer-evidence`、`--competitor-gaps`、`--competitor-selling-points`、`--competitor-products`、`--competitor-evidence` 和 `--output-dir` 替换默认输入输出路径。

## 评分口径

```text
normalized_user_importance = 主题用户提及数 / 所有主题中的最大提及数 × 100
evidence_confidence = min(1, 有唯一 review_id 的证据数 / 5) × min(1, 竞品品牌数 / 3)
opportunity_score = normalized_user_importance × (100 - 竞品代表卖点覆盖率) / 100 × evidence_confidence × 品类匹配系数
```

同品类映射的匹配系数为 1；跨品类但语义可迁移的价格信号为 0.25；不可比或没有消费者主题时不评分。分数低不等于市场没有需求；数据缺失会单独标为“未验证”。只有同品类需求重要度低于 5%、且竞品代表卖点覆盖率不高于 20% 时，才标记为“伪机会”。

## 两周安排

- 第 11 周：检查需求主题和竞品摘要口径，查看矩阵证据，复核低需求高空白的伪机会判定。
- 第 12 周：用 Brand Voice Skill 形成至少 5 条策略 Brief；逐条检查人群、方向、证据、发布门槛和成功指标。

## 输出

- `outputs/demand_content_matrix.csv`：消费者重要度、用户证据、竞品代表卖点覆盖、商品属性覆盖与品类匹配状态。
- `outputs/opportunity_scores.csv`：可评分主题的排序及未评分主题的原因。
- `outputs/candidate_gap_cells.csv`：实验五标记的候选商品空白格。
- `outputs/strategy_briefs.md`：5 条含证据边界和验证门槛的内容策略 Brief。
- `outputs/summary.json`：版本、公式、数据范围和质量警示。

## 验收

```powershell
python -m unittest discover -s experiments/experiment-6-content-gap-brand-voice/tests -v
```

测试检查公式、跨品类降置信度、低需求空白识别、证据引用和至少 5 条 Brief。

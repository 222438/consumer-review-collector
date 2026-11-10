# 实验八：AI Marketing OS 综合开发（v1.0）

这个目录把实验1—7的结构化产物串成一条可复核的营销闭环：

`品牌档案 → 消费者洞察 → 竞品情报 → 内容机会 → Campaign Planner → A/B/问卷效果 → 下一轮优化`

示例品牌是 **Campus Coffee**。目录内的评论、竞品快照和 A/B 记录是匿名课堂模拟数据，字段和流程可以直接替换为经授权的真实数据；程序不会把示例结果当作真实市场结论。

## 运行

```powershell
cd experiments/experiment-8-ai-marketing-os
python data/generate_sample_data.py       # 可选：重新生成确定性的匿名样本
python run.py                              # 无界面运行并写入 outputs/ 和 data/marketing_os.sqlite3
streamlit run app.py                       # 上传、运行、结果、证据和下载页面
python -m unittest discover -s tests -v
```

首次运行需要 Python 3.10+；Streamlit 页面依赖见 `requirements.txt`。核心 `src/marketing_os.py` 只使用 Python 标准库，便于自动化测试。

## 交付物与数据流

- `data/brand_profile.json`、`data/brand_history.json`：品牌资料、受众、Brand Voice 版本和 Campaign 历史。
- `data/consumer_reviews.csv`：统一字段的消费者评论；主题编码是可解释的多标签规则，并保存 `review_id` 证据。
- `data/competitors.csv`：竞品指标、价格/产品/消费者重叠度和来源字段。
- `data/ab_test_anonymous.csv`：60 条匿名 A/B 记录（A/B 各30人），含曝光、点击、购买和开放反馈；换成真实数据前必须通过同一字段校验。
- `data/field_mapping.csv`：实验1—7字段映射和命名版本。
- `src/marketing_os.py`：六个能力模块、证据台账、SQLite 历史记录和统一运行入口。
- `app.py`：Streamlit 的上传、运行、结果、证据、下载和历史记录页面。
- `db/init_db.sql`：数据库初始化脚本；实际运行也会自动初始化。
- `docs/workflow.mmd`：Workflow 图；`docs/experiment_plan.md`：测试方案、指标和限制。
- `docs/defense_answers.md`：Demo 固定八问的答辩参考答案。
- `docs/luckin_cotti_ab_test_plan.md`：瑞幸与库迪广告的匹配模板 A/B 测试方案。
- `docs/skill_usage_log.md`：本次实际使用 `ab-testing` Skill 的记录。
- `skills/`：本实验实际采用的 Brand Voice、A/B Testing、Analytics Skill 规则与来源说明。
- `outputs/`：最近一次运行的 JSON、CSV、Markdown 分析报告。

## 指标口径

平均评分只使用 1—5 的有效评分；正向率为评分4—5，问题率为评分1—2。痛点是多标签统计，同一条评论可以进入多个主题，但同一主题不会重复计数。A/B 点击率为点击/曝光，购买率为购买/曝光，两个组的观察窗口必须一致；结果还同时报告样本量、开放反馈和下一步动作。

## 证据边界与人工门

每个主题、竞品维度和 Campaign 主张都保留 `evidence_refs`。生成结果默认是 `draft_pending_human_review`，发布前必须逐条核对文案、渠道、预算和校园合规。A/B 样本达到课堂要求的每组至少20人，但示例数据是模拟数据，未替代真实用户研究或显著性检验。

## 版本与冲突处理

集成版本为 `v1.0`。实验7使用的字段与本实验的 `field_mapping.csv` 对齐；需要合并的接口、依赖和版本冲突记录在 `docs/integration_conflicts.md`。上游实验仍保留在仓库中，便于追溯原始证据。

## GitHub Skill 采用记录

本实验采用了 GitHub `coreyhaines31/marketingskills` 的 MIT 许可公开 Skill 思路：`ab-testing`（v2.0.7）用于假设、主/次/护栏指标、预先设定样本量和不提前停测；`analytics`（v2.2.5）用于事件命名、从行级数据计算、窗口一致性和不收集 PII。来源、固定提交和本地适配见 `skills/UPSTREAM.md`。本地 `skills/brand_voice` 继续用于禁用未经证实的绝对化表述。

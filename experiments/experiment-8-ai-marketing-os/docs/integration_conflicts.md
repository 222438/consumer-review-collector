# 集成与冲突处理记录（v1.0）

| 冲突 | 处理 | 验证 |
|---|---|---|
| 实验4使用 `review_id`/`review`，实验7只引用聚合 CSV | `field_mapping.csv` 统一为 `evidence_id`、`review_text`，聚合仍保留原始 ID 列表 | 主题排名中的 `evidence_refs` 可回到评论行 |
| 实验5的蓝牙耳机示例与本实验校园咖啡品类不一致 | v1.0 使用同品类 `competitors.csv` 快照；上游跨品类结果只保留为历史证据，不进入咖啡结论 | 竞品档案带 `category`/`source_ref` 边界，Campaign 默认需人工审核 |
| 实验7输出是 `campaign_strategy.json`，本实验需要结果、证据、下载 | `run_os` 统一输出 `marketing_os_run.json`，保留 campaign、ledger、experiment_effect，并提供下载 | JSON/CSV/Markdown 三种格式均写入 outputs |
| Streamlit、pandas 版本可能与课堂环境不一致 | 核心模块只依赖标准库；Streamlit/pandas 仅列在 requirements，上传页面不依赖 pandas API | `python run.py` 和 unittest 可无 Streamlit 运行 |
| 示例 A/B 数据不是真实用户数据 | 在 README、测试方案和报告中明确标注 classroom simulation；导入真实匿名数据时复用同一校验 | 每组样本门槛、字段和证据 ID 自动校验 |

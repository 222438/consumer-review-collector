# 实验七：AI营销Workflow（v0.7）

本实验把前六个实验的结构化产物串成一条可追踪的营销策划链：

`用户输入 → 品牌资料 → 消费者洞察 → 竞争分析 → Content Gap → Brand Voice → 目标消费者 → 传播主题 → 渠道计划 → Campaign`

运行：

```powershell
python src/marketing_workflow.py
```

程序默认处理“给Campus Coffee设计一次新品推广”，读取实验4—6的输出和 `skills/brand_voice/SKILL.md`，并生成：

- `outputs/campaign_strategy.json`：完整状态、步骤输入输出、证据引用、人工审核点和错误演练结果；
- `outputs/campaign_strategy.md`：可直接阅读的 Campaign 策略；
- `docs/workflow.mmd`：Mermaid Workflow 图；
- `docs/json_schema.json`：运行结果 Schema；
- `docs/api_interface.md`：API 请求、响应、超时和重试说明；
- `docs/error_handling.md`：API 失败、JSON 错误、缺字段、超时处理表；
- `logs/workflow_run.jsonl`：每个步骤和 API 调用的时间戳、状态与重试记录。

前序数据是课堂模拟数据。实验5的蓝牙耳机竞品与实验4的咖啡评论不属于同一品类，因此流程会把跨类别结果标成假设，并要求人工审核、用户访谈、实测和小流量 A/B 测试后再发布。

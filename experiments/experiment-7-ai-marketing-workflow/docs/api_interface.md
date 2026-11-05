# API 调用模块与接口说明（v0.7）

`src/marketing_workflow.py` 中的 `LocalAPIClient` 模拟远程 API，保持和真实 HTTP 客户端相同的四个行为：JSON 请求、JSON 响应、超时、重试。默认不访问网络，方便复现实验。

| Endpoint | 请求字段 | 响应约束 | 用途 |
|---|---|---|---|
| `workflow/brand_info` | `request_id`, `step` | JSON object | 记录用户任务和品牌上下文 |
| `workflow/consumer_insight` | `request_id`, `step` | JSON object | 触发实验4读取与汇总 |
| `workflow/competitor_analysis` | `request_id`, `step` | JSON object | 触发实验5读取与汇总 |
| `workflow/content_gap` | `request_id`, `step` | JSON object | 触发实验6读取与证据边界检查 |
| `workflow/*` | `request_id`, `step` | JSON object | 其他工作流节点的状态确认 |

每个请求最多执行 `retries + 1` 次；单次调用超过 `timeout` 秒记为超时。响应必须是 JSON object，否则进入错误处理。每次请求会写入 `workflow_run.jsonl`，包括 endpoint、attempt、状态和时间戳。

真实服务接入时，只需替换 `LocalAPIClient.transport(endpoint, payload)`，保留相同的响应校验和日志字段。

# 错误处理与 Debug 记录

| 场景 | 处理 | 结果 |
|---|---|---|
| API 失败 | 指数退避重试，耗尽后抛出 `ApiError` | 演示记录见运行日志 |
| JSON 错误 | 捕获 `JSONDecodeError`，阻止脏数据进入下一步 | 演示记录见运行日志 |
| 缺字段 | 按 JSON Schema 校验并停在当前步骤 | 演示记录见运行日志 |
| 超时 | 每次调用设置 timeout，重试后抛出 `ApiTimeout` | 演示记录见运行日志 |

## 本次 Debug 演练

| 场景 | 状态 | 详情 |
|---|---|---|
| API失败与重试 | recovered | 第3次调用成功: True |
| JSON格式错误 | handled | 第1行第11列: Expecting value |
| 缺字段 | handled | $: missing required field 'run_id'; $: missing required field 'request'; $: missing required field 'status'; $: missing required field 'steps'; $: missing required field 'campaign… |
| 超时 | handled | debug/slow failed after 2 attempt(s): timeout after 0.020s |

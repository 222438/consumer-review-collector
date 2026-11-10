---
name: analytics
description: 以决策为导向建立可追溯的营销事件与指标。
metadata:
  upstream: coreyhaines31/marketingskills@7c187944fa63d149879459ba53ef4fd3c0364c50
---

# 本实验执行清单

- 先写决策问题，再定义最少事件；使用 `object_action` 风格的字段名。
- 从逐行记录计算总数、比率和 uplift，并用分组汇总交叉核对。
- 分子、分母必须来自同一封闭观察窗口；未知或未完成的记录标为 pending，不偷偷计入失败。
- 不在事件、UTM 或开放反馈中保存姓名、电话、邮箱、学号等个人信息。
- 每个结论保留输入文件、匿名 ID 或聚合行的 evidence reference。

# GitHub Skill 采用与适配记录

本实验参考并适配以下公开 MIT 项目（固定到同一主分支提交，避免课堂复现时版本漂移）：

- Repository: <https://github.com/coreyhaines31/marketingskills>
- Commit: `7c187944fa63d149879459ba53ef4fd3c0364c50`
- License: MIT（仓库 `LICENSE`）
- `skills/ab-testing/SKILL.md` v2.0.7：采用“先写假设、单变量、主/次/护栏指标、预注册样本量、不要提前停测、结果要转成下一轮动作”。本地代码保留课堂每组≥20人的硬门槛，并明确未做显著性检验。
- `skills/analytics/SKILL.md` v2.2.5：采用事件命名规范、从行级数据计算、对齐观察窗口、交叉核对和不记录 PII。对应字段和事件见 `docs/experiment_plan.md`、`data/field_mapping.csv`。

本地 `skills/ab_testing/SKILL.md` 与 `skills/analytics/SKILL.md` 是面向本实验的短版执行清单，不复制上游全文；它们记录了实际落地的规则和与课堂样本限制之间的差异。

## 2026-11-17：加入未经改写的原版

`vendor/marketingskills/ab-testing/` 现包含原版 SKILL.md、references 与 evals，MIT 许可证和逐文件 SHA-256 记录放在其父目录，仍固定到上述提交。原有自编简版继续保留，两者来源不同。原版用于对话中的 AI 工作流；当前 Python 界面没有自动读取它。实际复核产物：`reports/ab_testing_skill_review_2026-11-17.md`；课堂操作：`docs/classroom_walkthrough.md`。
